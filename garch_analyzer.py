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


def _sane(res, dist, ret_scale) -> bool:
    """Guarda de sanidade compartilhada: rejeita fits 'tecnicamente bem
    sucedidos' mas numericamente degenerados (o otimizador não levanta
    exceção ao pousar num limite/mínimo ruim, só emite warning)."""
    if getattr(res, "convergence_flag", 0) != 0:
        return False  # scipy reportou não-convergência real
    mu_val = float(res.params.get("mu", 0.0))
    if ret_scale > 0 and abs(mu_val) > 10 * ret_scale:
        return False  # média disparada — sinal de otimização perdida
    # "nu" tem significado DIFERENTE por distribuição no `arch`: em t/skewt
    # é grau de liberdade (deve ser > 2 p/ variância finita — nu perto de 2
    # ou muito alto É degenerado). No GED, "nu" é o parâmetro de FORMA/
    # curtose — nu < 2 é um resultado LEGÍTIMO (caudas mais pesadas que a
    # normal, a própria razão de escolher GED).
    nu_val = res.params.get("nu")
    if nu_val is not None and dist in ("t", "skewt") and not (2.05 <= nu_val <= 90):
        return False  # graus de liberdade grudados no limite do otimizador
    lam_val = res.params.get("lambda")
    if lam_val is not None and abs(lam_val) > 0.995:
        return False  # assimetria da Skewed-t grudada no limite ±1
    return True


def _warm_start_vector(am, anchor_params):
    """
    Monta o vetor de partida para o modelo-alvo `am` casando por NOME de
    parâmetro com o fit-âncora `anchor_params` (Series do GARCH(1,1) do
    mesmo `dist`). Parâmetros extras que só existem no alvo (ex.:
    alpha[2], beta[2], gamma[1] do GJR) ficam com o chute default do
    próprio `arch`, obtido via dry-run (`maxiter=0`) — mais robusto do
    que montar o vetor por POSIÇÃO hardcoded: não depende de premissa
    sobre a ordem interna dos parâmetros, que pode variar por modelo/
    distribuição/versão do `arch`.

    Sem warm-start, o SciPy (nesta versão do `arch`) some no vazio pra
    p>1 ou q>1: fica cego sem um chute inicial perto da solução e
    converge pra um mínimo local muito pior (confirmado no ^BVSP:
    GARCH(1,2) sem warm-start cai em AIC=-3279; com warm-start do
    GARCH(1,1), AIC=-6287, batendo o valor histórico do report original).
    """
    probe = am.fit(disp="off", show_warning=False, options={"maxiter": 0})
    sv = probe.params.copy()
    for name in sv.index:
        if name in anchor_params.index:
            sv[name] = anchor_params[name]
    return sv.values


def fit_grid(ret, alias: str, classe: str) -> dict | None:
    """
    Testa toda a grade (GRID × DISTS), aplica critério LB/AIC,
    devolve dict pronto para render_report1.

    Para a família GARCH/GJR (o<=1), usa warm-start em cascata: ajusta
    GARCH(1,1) primeiro por distribuição e usa o resultado como chute
    inicial dos modelos de ordem maior — necessário pra evitar que o
    otimizador se perca em superfícies com p>1 ou q>1 (ver _warm_start_vector).
    """
    candidatos = []
    ret_scale = float(ret.std())
    ancoras: dict[str, "object"] = {}  # dist -> res do GARCH(1,1) (se sadio)

    for (vol, p, o, q) in GRID:
        for dist in DISTS:
            try:
                am = arch_model(
                    ret, mean="Constant", vol=vol,
                    p=p, o=o, q=q, dist=dist,
                    rescale=False,  # ESSENCIAL: manter retornos sem reescala
                )

                sv = None
                if vol == "GARCH" and (p, o, q) != (1, 0, 1) and dist in ancoras:
                    try:
                        sv = _warm_start_vector(am, ancoras[dist].params)
                    except Exception:
                        sv = None  # dry-run falhou — cai pro chute default normal

                if sv is not None:
                    res = am.fit(disp="off", show_warning=False, starting_values=sv)
                else:
                    res = am.fit(disp="off", show_warning=False)

                if not _sane(res, dist, ret_scale):
                    continue

                if vol == "GARCH" and (p, o, q) == (1, 0, 1):
                    ancoras[dist] = res  # guarda a âncora sadia pra próxima iteração

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
