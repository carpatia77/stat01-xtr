"""
backtest_percentile_calibration.py — testa empiricamente qual banda está
calibrada corretamente: GEOMÉTRICA (fração linear da distância, estilo do
indicador antigo) ou ESTATÍSTICA (percentil real via quantil).

Ideia: um rótulo "[25%,75%]" promete que o preço fica DENTRO desse
intervalo 50% das vezes (violação esperada = 50%). Contamos a violação
REAL em dados históricos pra cada banda e comparamos com essa promessa.
A banda mais larga sempre "enquadra melhor" o preço visualmente — isso
não é segurança matemática, é geometria trivial; o teste de calibração
é o que decide se o rótulo bate com a realidade.

Dois modos de gregas:
  --gregas fixo         usa UM conjunto de gregas (as que você colaria
                         no indicador MT5) pro período inteiro. Rápido,
                         mas mistura "erro da banda" com "contaminação
                         de regime" se as gregas vierem de fora da
                         janela testada (ex.: gregas de julho testando
                         janeiro-junho).
  --gregas walkforward   (default, RECOMENDADO) recalibra o modelo a
                         cada N dias úteis usando SÓ dados anteriores
                         (sem lookahead de parâmetro nenhum, não só de
                         preço). Isola de verdade "banda geométrica vs
                         estatística" de "regime de vol mudou".

Uso:
    python mt5/backtest_percentile_calibration.py ^BVSP 2026-01-01
    python mt5/backtest_percentile_calibration.py ^BVSP 2026-01-01 --gregas fixo
    python mt5/backtest_percentile_calibration.py ^BVSP 2026-01-01 --refit-every 21
"""
import sys
import argparse
import numpy as np
import pandas as pd
from scipy.stats import norm, t as student_t
from scipy.special import gammaln

sys.path.insert(0, ".")  # roda a partir da raiz do repo (onde data.py está)
from data import get_returns

# ── Spec do modelo e gregas fixas (usadas só no modo --gregas fixo) ────
MODEL = "EGARCH"      # "GARCH" | "EGARCH" | "GJR"
DIST  = "t"            # "normal" | "t"
OMEGA_FIXO = -0.070664533452
ALPHA_FIXO = 0.07253778
BETA_FIXO  = 0.99212226
GAMMA_FIXO = 0.00298651
NU_FIXO    = 9.701027

HORIZON_DAYS = 5
CONFIDENCE   = 0.95     # banda externa (95% -> z=1.96)
PCTL_PAIRS   = [(0.05, 0.95), (0.25, 0.75)]  # devem bater com a config default do .mq5

MIN_TRAIN_DAYS  = 500   # dias úteis mínimos de histórico antes do 1º refit
REFIT_EVERY_DAYS = 21   # ~1 mês de pregões


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


def _uncond_seed(omega, alpha, beta):
    if MODEL == "EGARCH":
        denom = 1.0 - beta
        ln_u = omega/denom if abs(denom) > 1e-8 else omega
        return np.exp(ln_u), ln_u
    denom = 1.0 - alpha - beta
    sigma2_u = omega/denom if denom > 1e-8 else omega*100.0
    return sigma2_u, 0.0


def _step(e, sigma2_prev, ln_prev, omega, alpha, beta, gamma, eabsz):
    """Um passo da recursão (GARCH/EGARCH/GJR), retorna (sigma2_new, ln_new)."""
    sd_prev = np.sqrt(max(sigma2_prev, 1e-14))
    z = e / sd_prev
    if MODEL == "EGARCH":
        ln_new = omega + beta*ln_prev + alpha*(abs(z)-eabsz) + gamma*z
        # clamp de segurança: alguns refits (walk-forward) podem convergir
        # tecnicamente (convergence_flag=0) mas ficar perto do limite de
        # estacionariedade, fazendo a recursão explodir ao longo de
        # centenas de dias. ln(sigma2) em [-30,3] permite sigma1 (vol
        # diária) até ~450% -- absurdamente generoso pra qualquer mercado
        # real, mas baixo o bastante pra nunca estourar os exp() a jusante
        # (banda de preço, forecast multi-dia).
        ln_new = np.clip(ln_new, -30.0, 3.0)
        return np.exp(ln_new), ln_new
    if MODEL == "GJR":
        ind = 1.0 if e < 0 else 0.0
        sigma2_new = omega + (alpha + gamma*ind)*e*e + beta*sigma2_prev
        return sigma2_new, np.log(max(sigma2_new, 1e-14))
    sigma2_new = omega + alpha*e*e + beta*sigma2_prev
    return sigma2_new, np.log(max(sigma2_new, 1e-14))


def daily_sigma_series_fixo(ret: pd.Series):
    """Recursão com gregas FIXAS (as *_FIXO do topo do arquivo) o período inteiro."""
    eabsz = expected_abs_z(DIST, NU_FIXO)
    n = len(ret)
    sigma1 = np.full(n, np.nan)
    gregas_por_dia = [(OMEGA_FIXO, ALPHA_FIXO, BETA_FIXO, GAMMA_FIXO, NU_FIXO)] * n

    sigma2_prev, ln_prev = _uncond_seed(OMEGA_FIXO, ALPHA_FIXO, BETA_FIXO)
    vals = ret.values
    for i in range(n):
        sigma1[i] = np.sqrt(max(sigma2_prev, 0.0))  # previsão PARA o dia i, sem olhar ret[i]
        sigma2_prev, ln_prev = _step(vals[i], sigma2_prev, ln_prev,
                                      OMEGA_FIXO, ALPHA_FIXO, BETA_FIXO, GAMMA_FIXO, eabsz)
    return sigma1, gregas_por_dia, []


def daily_sigma_series_walkforward(ret: pd.Series, min_train: int, refit_every: int):
    """
    Recalibra o modelo (mesmo spec: MODEL/DIST) periodicamente usando SÓ
    dados anteriores ao dia i (walk-forward real, sem lookahead de
    parâmetro). O ESTADO da variância (sigma2_prev) é contínuo — só os
    coeficientes mudam nos pontos de recalibração, re-semeados pela
    variância incondicional das NOVAS gregas nesse instante.
    """
    from arch import arch_model

    n = len(ret)
    sigma1 = np.full(n, np.nan)
    gregas_por_dia = [None] * n
    refit_log = []

    omega = alpha = beta = gamma = None
    nu_ = NU_FIXO
    eabsz = expected_abs_z(DIST, nu_)
    sigma2_prev = ln_prev = None

    vals = ret.values
    p_, o_ = 1, (1 if MODEL in ("EGARCH", "GJR") else 0)

    for i in range(n):
        need_refit = (omega is None and i >= min_train) or \
                     (omega is not None and i >= min_train and (i - min_train) % refit_every == 0)
        if need_refit:
            train = ret.iloc[:i]
            try:
                am = arch_model(train, mean="Constant", vol=MODEL, p=p_, o=o_, q=1,
                                dist=DIST, rescale=False)
                res = am.fit(disp="off", show_warning=False)
                if getattr(res, "convergence_flag", 0) == 0:
                    omega = float(res.params["omega"])
                    alpha = float(res.params["alpha[1]"])
                    beta  = float(res.params["beta[1]"])
                    gamma = float(res.params.get("gamma[1]", 0.0))
                    nu_   = float(res.params.get("nu", NU_FIXO))
                    eabsz = expected_abs_z(DIST, nu_)
                    sigma2_prev, ln_prev = _uncond_seed(omega, alpha, beta)
                    refit_log.append((ret.index[i], omega, alpha, beta, gamma, nu_))
            except Exception:
                pass  # mantém as gregas anteriores se o refit falhar

        if omega is None:
            continue  # ainda no período de aquecimento, sem gregas calibradas ainda

        sigma1[i] = np.sqrt(max(sigma2_prev, 0.0))
        gregas_por_dia[i] = (omega, alpha, beta, gamma, nu_)
        sigma2_prev, ln_prev = _step(vals[i], sigma2_prev, ln_prev, omega, alpha, beta, gamma, eabsz)

    return sigma1, gregas_por_dia, refit_log


def cum_sigma_n(sigma1: float, omega, alpha, beta, gamma) -> float:
    """Forecast multi-dia (choque futuro esperado = 0), mesma lógica do .mq5."""
    sigma2_uncond, _ = _uncond_seed(omega, alpha, beta)
    s2 = sigma1**2
    ln_s2 = np.log(max(s2, 1e-14))
    total = s2
    for h in range(2, HORIZON_DAYS + 1):
        if MODEL == "EGARCH":
            ln_s2 = omega + beta*ln_s2
            s2 = np.exp(ln_s2)
        elif MODEL == "GJR":
            s2 = omega + (alpha + 0.5*gamma)*s2 + beta*s2
        else:
            s2 = sigma2_uncond + (alpha+beta)**(h-1) * (sigma1**2 - sigma2_uncond)
        total += s2
    return float(np.sqrt(max(total, 0.0)))


def backtest(ticker: str, window_start: str | None = None, mode: str = "walkforward",
             refit_every: int = REFIT_EVERY_DAYS, min_train: int = MIN_TRAIN_DAYS) -> pd.DataFrame:
    px, ret = get_returns(ticker, scale100=False)
    px = px.sort_index()
    ret = ret.sort_index()

    if mode == "fixo":
        sigma1, gregas_por_dia, refit_log = daily_sigma_series_fixo(ret)
    else:
        sigma1, gregas_por_dia, refit_log = daily_sigma_series_walkforward(ret, min_train, refit_every)

    cutoff = pd.Timestamp(window_start) if window_start else None

    n = len(px)
    rows = []
    for i in range(n - HORIZON_DAYS - 1):
        s1 = sigma1[i]
        if np.isnan(s1) or gregas_por_dia[i] is None:
            continue
        base_date = px.index[i]
        if cutoff is not None and base_date < cutoff:
            continue
        omega, alpha, beta, gamma, nu_ = gregas_por_dia[i]
        base = float(px.iloc[i])
        realized_price = float(px.iloc[i + HORIZON_DAYS])
        sN = cum_sigma_n(s1, omega, alpha, beta, gamma)
        rows.append((base_date, base, sN, realized_price, nu_))

    df = pd.DataFrame(rows, columns=["date", "base", "sigmaN", "realized_price", "nu"])
    janela_txt = f" (desde {window_start})" if window_start else ""
    modo_txt = "GREGAS FIXAS" if mode == "fixo" else f"WALK-FORWARD (refit a cada {refit_every} dias, min_train={min_train})"
    print(f"\n=== {ticker} — {len(df)} janelas de {HORIZON_DAYS} dias testadas{janela_txt} — modo: {modo_txt} ===")
    if len(df):
        print(f"Período coberto: {df['date'].min().date()} até {df['date'].max().date()}")

    if mode == "walkforward" and refit_log:
        print(f"\n{len(refit_log)} recalibrações no período de treino completo (antes do corte de janela incluído):")
        for dt_, o, a, b, g, nu2 in refit_log[-8:]:  # mostra as últimas 8 pra não poluir
            print(f"  {pd.Timestamp(dt_).date()}: omega={o:.6f} alpha={a:.6f} beta={b:.6f} gamma={g:.6f} nu={nu2:.3f}")

    # usa a média das gregas ativas na janela testada só pro cálculo de z_conf/quantile
    # (o quantil por sigma_t já reflete a vol certa; nu varia pouco na prática)
    nu_medio = float(df["nu"].mean()) if len(df) else NU_FIXO

    z_conf = quantile(0.5 + CONFIDENCE/2, DIST, nu_medio)
    lo_conf = df["base"] * np.exp(-z_conf * df["sigmaN"])
    hi_conf = df["base"] * np.exp( z_conf * df["sigmaN"])
    viol_conf = float(((df["realized_price"] < lo_conf) | (df["realized_price"] > hi_conf)).mean())
    print(f"\nBanda de confiança (nominal {CONFIDENCE*100:.0f}%): "
          f"violação esperada={100*(1-CONFIDENCE):.1f}%  violação REAL={100*viol_conf:.1f}%")

    npairs = len(PCTL_PAIRS)

    print("\n--- ESTATÍSTICO (percentil real via quantil) ---")
    for lo, hi in PCTL_PAIRS:
        z_lo, z_hi = quantile(lo, DIST, nu_medio), quantile(hi, DIST, nu_medio)
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

    print("\nΔ perto de 0pp = banda calibrada. Δ negativo = banda mais larga que o "
          "prometido (violação rara demais, 'segurança' ilusória); Δ positivo = banda "
          "mais estreita que o prometido (viola mais do que promete).")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest de calibração das bandas GARCH")
    parser.add_argument("ticker", nargs="?", default="^BVSP")
    parser.add_argument("window_start", nargs="?", default=None)
    parser.add_argument("--gregas", choices=["fixo", "walkforward"], default="walkforward")
    parser.add_argument("--refit-every", type=int, default=REFIT_EVERY_DAYS)
    parser.add_argument("--min-train", type=int, default=MIN_TRAIN_DAYS)
    args = parser.parse_args()

    backtest(args.ticker, window_start=args.window_start, mode=args.gregas,
             refit_every=args.refit_every, min_train=args.min_train)
