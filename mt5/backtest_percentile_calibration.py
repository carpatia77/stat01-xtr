"""
backtest_percentile_calibration.py — testa empiricamente qual banda está
calibrada corretamente: GEOMÉTRICA (fração linear da distância, estilo do
indicador antigo) ou ESTATÍSTICA (percentil real via quantil).

Ideia: um rótulo "[25%,75%]" promete que o preço fica DENTRO desse
intervalo 50% das vezes (violação esperada = 50%). Contamos a violação
REAL em dados históricos pra cada banda e comparamos com essa promessa.
A banda mais perto do valor prometido é a calibrada corretamente — não
importa qual "parece" enquadrar melhor o preço visualmente (banda mais
larga sempre enquadra mais, isso não é virtude, é geometria).

Usa os MESMOS parâmetros fixos (gregas) que você colaria no indicador
MT5 e replica exatamente a lógica de recursão diária do
GARCH_Vol_Percentile.mq5 (sem lookahead: o forecast do dia D usa só
dados até o fechamento de D-1).

Uso:
    python mt5/backtest_percentile_calibration.py ^BVSP
"""
import sys
import numpy as np
import pandas as pd
from scipy.stats import norm, t as student_t
from scipy.special import gammaln

sys.path.insert(0, ".")  # roda a partir da raiz do repo (onde data.py está)
from data import get_returns

# ── Gregas fixas (as mesmas que vão no indicador MT5) ──────────────────
MODEL = "EGARCH"      # "GARCH" | "EGARCH" | "GJR"
OMEGA = -0.070664533452
ALPHA = 0.07253778
BETA  = 0.99212226
GAMMA = 0.00298651
DIST  = "t"            # "normal" | "t"
NU    = 9.701027

HORIZON_DAYS = 5
CONFIDENCE   = 0.95     # banda externa (95% -> z=1.96)
# pares (lo, hi) testados; devem bater com a config default do .mq5
# ("5,25,50,75,95" -> pares (0.05,0.95) e (0.25,0.75), na ordem de rank
# que o _.mq5_ usa pra posicionar a banda geométrica).
PCTL_PAIRS = [(0.05, 0.95), (0.25, 0.75)]


def expected_abs_z(dist: str, nu: float) -> float:
    if dist == "t" and nu > 2:
        log_num = np.log(2) + 0.5*np.log(nu-2) + gammaln((nu+1)/2)
        log_den = np.log(nu-1) + 0.5*np.log(np.pi*nu) + gammaln(nu/2)
        return float(np.exp(log_num - log_den) * np.sqrt((nu-2)/nu))
    return float(np.sqrt(2/np.pi))


def quantile(p: float, dist: str, nu: float) -> float:
    if dist == "t":
        tq = student_t.ppf(p, df=nu)
        return float(tq * np.sqrt((nu-2)/nu))  # reescala p/ variância unitária
    return float(norm.ppf(p))


def daily_sigma_series(ret: pd.Series) -> np.ndarray:
    """
    Replica a recursão do MQL5: sigma1[i] = previsão 1-passo À FRENTE do
    dia i, calculada ANTES de consumir o retorno realizado nesse dia
    (sem lookahead). `ret` deve estar em ordem cronológica crescente.
    """
    eabsz = expected_abs_z(DIST, NU)
    n = len(ret)
    sigma1 = np.full(n, np.nan)

    if MODEL == "EGARCH":
        denom = 1.0 - BETA
        ln_seed = OMEGA/denom if abs(denom) > 1e-8 else OMEGA
        sigma2_prev, ln_prev = np.exp(ln_seed), ln_seed
    else:
        denom = 1.0 - ALPHA - BETA
        sigma2_prev = OMEGA/denom if denom > 1e-8 else OMEGA*100.0
        ln_prev = 0.0

    vals = ret.values
    for i in range(n):
        sigma1[i] = np.sqrt(max(sigma2_prev, 0.0))  # previsão PARA o dia i

        e = vals[i]
        sd_prev = np.sqrt(max(sigma2_prev, 1e-14))
        z = e / sd_prev
        if MODEL == "EGARCH":
            ln_new = OMEGA + BETA*ln_prev + ALPHA*(abs(z)-eabsz) + GAMMA*z
            sigma2_new = np.exp(ln_new)
        elif MODEL == "GJR":
            ind = 1.0 if e < 0 else 0.0
            sigma2_new = OMEGA + (ALPHA + GAMMA*ind)*e*e + BETA*sigma2_prev
            ln_new = np.log(max(sigma2_new, 1e-14))
        else:
            sigma2_new = OMEGA + ALPHA*e*e + BETA*sigma2_prev
            ln_new = np.log(max(sigma2_new, 1e-14))
        sigma2_prev, ln_prev = sigma2_new, ln_new

    return sigma1


def cum_sigma_n(sigma1: float) -> float:
    """Forecast multi-dia (choque futuro esperado = 0), mesma lógica do .mq5."""
    if MODEL == "EGARCH":
        denom = 1.0 - BETA
        ln_u = OMEGA/denom if abs(denom) > 1e-8 else OMEGA
        sigma2_uncond = np.exp(ln_u)
    else:
        denom = 1.0 - ALPHA - BETA
        sigma2_uncond = OMEGA/denom if denom > 1e-8 else OMEGA*100.0

    s2 = sigma1**2
    ln_s2 = np.log(max(s2, 1e-14))
    total = s2
    for h in range(2, HORIZON_DAYS + 1):
        if MODEL == "EGARCH":
            ln_s2 = OMEGA + BETA*ln_s2
            s2 = np.exp(ln_s2)
        elif MODEL == "GJR":
            s2 = OMEGA + (ALPHA + 0.5*GAMMA)*s2 + BETA*s2
        else:
            s2 = sigma2_uncond + (ALPHA+BETA)**(h-1) * (sigma1**2 - sigma2_uncond)
        total += s2
    return float(np.sqrt(max(total, 0.0)))


def backtest(ticker: str, window_start: str | None = None) -> pd.DataFrame:
    """
    window_start: se dado (ex.: "2026-01-01"), restringe as JANELAS
    CONTADAS na estatística a partir dessa data — mas a recursão de
    sigma continua usando TODO o histórico disponível antes disso como
    aquecimento (senão a série fica curta demais pra "esquecer" o seed
    inicial, viciando a calibração logo no começo da janela).
    """
    px, ret = get_returns(ticker, scale100=False)
    px = px.sort_index()
    ret = ret.sort_index()
    sigma1 = daily_sigma_series(ret)

    cutoff = pd.Timestamp(window_start) if window_start else None

    n = len(px)
    rows = []
    for i in range(n - HORIZON_DAYS - 1):
        s1 = sigma1[i]
        if np.isnan(s1):
            continue
        base_date = px.index[i]
        if cutoff is not None and base_date < cutoff:
            continue
        base = float(px.iloc[i])
        realized_price = float(px.iloc[i + HORIZON_DAYS])
        rows.append((base_date, base, cum_sigma_n(s1), realized_price))

    df = pd.DataFrame(rows, columns=["date", "base", "sigmaN", "realized_price"])
    janela_txt = f" (desde {window_start})" if window_start else ""
    print(f"\n=== {ticker} — {len(df)} janelas de {HORIZON_DAYS} dias testadas{janela_txt} ===")
    if len(df):
        print(f"Período coberto: {df['date'].min().date()} até {df['date'].max().date()}")

    z_conf = quantile(0.5 + CONFIDENCE/2, DIST, NU)
    lo_conf = df["base"] * np.exp(-z_conf * df["sigmaN"])
    hi_conf = df["base"] * np.exp( z_conf * df["sigmaN"])
    viol_conf = float(((df["realized_price"] < lo_conf) | (df["realized_price"] > hi_conf)).mean())
    print(f"\nBanda de confiança (nominal {CONFIDENCE*100:.0f}%): "
          f"violação esperada={100*(1-CONFIDENCE):.1f}%  violação REAL={100*viol_conf:.1f}%")

    npairs = len(PCTL_PAIRS)

    print("\n--- ESTATÍSTICO (percentil real via quantil) ---")
    for lo, hi in PCTL_PAIRS:
        z_lo, z_hi = quantile(lo, DIST, NU), quantile(hi, DIST, NU)
        lo_b = df["base"] * np.exp(z_lo * df["sigmaN"])
        hi_b = df["base"] * np.exp(z_hi * df["sigmaN"])
        viol = float(((df["realized_price"] < lo_b) | (df["realized_price"] > hi_b)).mean())
        nominal = 1.0 - (hi - lo)
        print(f"  [{lo*100:.0f}%,{hi*100:.0f}%]  violação esperada={100*nominal:.1f}%  "
              f"violação REAL={100*viol:.1f}%  (Δ={100*(viol-nominal):+.1f}pp)")

    print("\n--- GEOMÉTRICO (fração linear de rank, estilo indicador antigo) ---")
    for k, (lo, hi) in enumerate(PCTL_PAIRS):
        f = (k + 1) / (npairs + 1)  # mesma fórmula rank-based do .mq5 (modo GEOMETRICO)
        up_b = df["base"] * (1 + f * (hi_conf/df["base"] - 1))
        dn_b = df["base"] * (1 - f * (1 - lo_conf/df["base"]))
        viol = float(((df["realized_price"] < dn_b) | (df["realized_price"] > up_b)).mean())
        nominal_label = 1.0 - (hi - lo)  # o que o RÓTULO promete
        print(f"  rotulado [{lo*100:.0f}%,{hi*100:.0f}%]  violação PROMETIDA pelo rótulo={100*nominal_label:.1f}%  "
              f"violação REAL={100*viol:.1f}%  (Δ={100*(viol-nominal_label):+.1f}pp)")

    print("\nQuanto mais perto de 0pp o Δ, mais calibrada a banda está. "
          "Δ negativo = banda mais larga que o prometido (violação rara demais, "
          "'segurança' ilusória); Δ positivo = banda mais estreita que o prometido.")
    return df


if __name__ == "__main__":
    ticker_arg = sys.argv[1] if len(sys.argv) > 1 else "^BVSP"
    window_arg = sys.argv[2] if len(sys.argv) > 2 else None
    backtest(ticker_arg, window_start=window_arg)
