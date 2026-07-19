"""
garch_analyzer.py — Report 1: grade de modelos GARCH/EGARCH/GJR, seleção LB+AIC,
interpretação automática.

Uso:
    python garch_analyzer.py [--save] [--tickers AAPL GC=F ...]
"""
import argparse
import warnings
import numpy as np
from arch import arch_model
from statsmodels.stats.diagnostic import acorr_ljungbox
from data import get_returns
from config import ASSETS_R1
from interpretacao import interpretar
from render import render_report1

warnings.filterwarnings("ignore")

# ── Grade de modelos: (vol_type, p, o, q) ──────────────────────────────────────
GRID = (
    [("GARCH",  p, 0, q) for p in (1, 2) for q in (1, 2)]   # GARCH(p,q)
    + [("GARCH",  1, 1, 1)]                                    # GJR-GARCH(1,1)
    + [("EGARCH", 1, 1, 1), ("EGARCH", 1, 1, 2)]              # EGARCH
)
DISTS = ["normal", "t", "skewt", "ged"]

LB_LAG = 20  # calibrado: autor usou lag=20 nos quadrados (ARCH effect)


def _model_label(vol: str, p: int, o: int, q: int) -> str:
    if vol == "EGARCH":
        return f"EGARCH({p},{o},{q})"
    if vol == "GARCH" and o == 1:
        return f"GJR-GARCH({p},{q})"
    return f"GARCH({p},{q})"


def _extract_params(res) -> tuple[float, float, float, float]:
    """Retorna (omega, alpha_sum, beta_sum, gamma_sum)."""
    params = res.params
    omega = float(params["omega"])

    alpha = sum(
        float(params[k]) for k in params.index if k.startswith("alpha[")
    )
    beta = sum(
        float(params[k]) for k in params.index if k.startswith("beta[")
    )
    gamma = sum(
        float(params[k]) for k in params.index if k.startswith("gamma[")
    )
    return omega, alpha, beta, gamma


def fit_grid(ret, alias: str, classe: str) -> dict | None:
    """
    Testa toda a grade (GRID × DISTS), aplica critério LB/AIC,
    devolve dict pronto para render_report1.
    """
    candidatos = []
    ret_scale = float(ret.std())

    for (vol, p, o, q) in GRID:
        for dist in DISTS:
            try:
                am = arch_model(
                    ret, mean="Constant", vol=vol,
                    p=p, o=o, q=q, dist=dist,
                    rescale=False,  # ESSENCIAL: manter retornos sem reescala
                )
                res = am.fit(disp="off", show_warning=False)

                # --- guarda de sanidade: rejeita fits "tecnicamente bem
                # sucedidos" mas numericamente degenerados (o optimizer não
                # levanta exceção quando pousa num limite/mínimo ruim, só
                # emite warning — que o except abaixo nunca pegaria).
                if getattr(res, "convergence_flag", 0) != 0:
                    continue  # scipy reportou não-convergência real
                mu_val = float(res.params.get("mu", 0.0))
                if ret_scale > 0 and abs(mu_val) > 10 * ret_scale:
                    continue  # média disparada — sinal de otimização perdida
                nu_val = res.params.get("nu")
                if nu_val is not None and not (2.05 <= nu_val <= 90):
                    continue  # graus de liberdade grudados no limite do otimizador
                lam_val = res.params.get("lambda")
                if lam_val is not None and abs(lam_val) > 0.995:
                    continue  # assimetria da Skewed-t grudada no limite ±1

                lb_pval = float(
                    acorr_ljungbox(res.std_resid.dropna()**2, lags=[LB_LAG])["lb_pvalue"].iloc[0]
                )
                candidatos.append({
                    "lb": lb_pval,
                    "aic": res.aic,
                    "res": res,
                    "vol": vol, "p": p, "o": o, "q": q, "dist": dist,
                })
            except Exception:
                pass  # modelo não convergiu — ignorar

    if not candidatos:
        return None

    # Critério: LB > 0.05 → menor AIC; fallback: menor AIC geral
    validos = [c for c in candidatos if c["lb"] > 0.05]
    best = min(validos, key=lambda x: x["aic"]) if validos else \
           min(candidatos, key=lambda x: x["aic"])

    status = "EXCELENTE" if best["lb"] > 0.05 else ("BOM" if best["lb"] > 0.01 else "RUIM")
    modelo = _model_label(best["vol"], best["p"], best["o"], best["q"])
    omega, alpha, beta, gamma = _extract_params(best["res"])

    dist_label = {
        "normal": "Normal",
        "t":      "Student-t",
        "skewt":  "Skewed t",
        "ged":    "GED",
    }.get(best["dist"], best["dist"])

    interp = interpretar(best["vol"], omega, alpha, beta, classe, best["dist"])

    return dict(
        alias=alias,
        modelo=modelo,
        dist=dist_label,
        aic=best["aic"],
        lb=best["lb"],
        omega=omega,
        alpha=alpha,
        beta=beta,
        gamma=gamma,
        status=status,
        interpretacao=interp,
    )


def run(assets: list[tuple] | None = None, save: bool = False) -> str:
    assets = assets or ASSETS_R1
    resultados = []
    for alias, ticker, classe in assets:
        if ticker is None:
            print(f"    [SKIP] {alias}: ticker Yahoo não identificado (ver config.py)")
            continue
        print(f"  Processando {alias} ({ticker}) ...", flush=True)
        try:
            _, ret = get_returns(ticker, scale100=False)
            r = fit_grid(ret, alias, classe)
            if r:
                resultados.append(r)
        except Exception as e:
            print(f"    [ERRO] {alias}: {e}")

    report = render_report1(resultados)
    if save:
        from config import REPORT_DATE
        fname = f"ANALISE_GARCH_COMPLETO_{REPORT_DATE}.txt"
        with open(fname, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"[garch_analyzer] Salvo em {fname}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GARCH Analyzer v3.9.4")
    parser.add_argument("--save", action="store_true",
                        help="Salva o report em arquivo .txt")
    parser.add_argument("--tickers", nargs="*", default=None,
                        help="Subconjunto de aliases (ex: AAPL GC ^VIX)")
    args = parser.parse_args()

    if args.tickers:
        subset = [a for a in ASSETS_R1 if a[0] in args.tickers]
    else:
        subset = None

    print(run(assets=subset, save=args.save))
