"""
egarch_forecast.py — Report 2: EGARCH(1,1) com assimetria, previsão 1d, bandas 95%

Uso:
    python egarch_forecast.py [--save] [--dist t|skewt]

Spec do modelo (spec fixo para os 19 ativos, ver DIST_R2 abaixo):
    EGARCH(1,1,1) — p=1, o=1, q=1. O termo de assimetria (o=1) é ESSENCIAL:
    sem ele o forecast erra ~8% (ex.: GC=F sigma 1.6120 vs 1.4950 do original).
    Versões antigas do `arch` assumiam o=1 por padrão em vol='EGARCH'; a 6.x
    exige o=1 explícito. Confirmado: com o=1 o sigma do GC bate o original.
"""
import argparse
import numpy as np
from arch import arch_model
from data import get_returns
from render import render_report2
from config import TICKERS_R2

# Distribuição fixa do Report 2. O título diz "-t", mas a calibração empírica
# (probe sobre os 19 ativos) decide entre 't' e 'skewt' — ajuste aqui conforme
# o que reproduzir mais linhas do original.
DIST_R2 = "t"


def forecast_one(ticker: str, dist: str = DIST_R2) -> dict:
    """
    Ajusta EGARCH(1,1,1) em ret*100 e retorna dict para render_report2.
    σ já sai em % (arch com ret*100).
    Banda 95%: close × (1 ± 1.96 × σ/100)
    """
    try:
        px, ret100 = get_returns(ticker, scale100=True)
        am = arch_model(ret100, mean="Constant", vol="EGARCH",
                        p=1, o=1, q=1, dist=dist)
        res = am.fit(disp="off")
        f   = res.forecast(horizon=1)
        sigma_pct = float(np.sqrt(f.variance.iloc[-1, 0]))
        close     = float(px.iloc[-1])
        minimo    = close * (1 - 1.96 * sigma_pct / 100)
        maximo    = close * (1 + 1.96 * sigma_pct / 100)
        status    = "Sucesso"
    except Exception as e:
        sigma_pct = float("nan")
        close     = float("nan")
        minimo    = float("nan")
        maximo    = float("nan")
        status    = f"Erro: {e}"

    return dict(
        ticker=ticker,
        close=close,
        vol_pct=sigma_pct,
        minimo=minimo,
        maximo=maximo,
        status=status,
    )


def run(tickers: list[str] | None = None, save: bool = False,
        dist: str = DIST_R2) -> str:
    tickers = tickers or TICKERS_R2
    resultados = [forecast_one(t, dist=dist) for t in tickers]
    report = render_report2(resultados)
    if save:
        from datetime import date
        fname = f"EGARCH_FORECAST_{date.today()}.txt"
        with open(fname, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"[egarch_forecast] Salvo em {fname}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EGARCH(1,1,1) forecast")
    parser.add_argument("--save", action="store_true",
                        help="Salva o report em arquivo .txt")
    parser.add_argument("--tickers", nargs="*", default=None,
                        help="Subset de tickers (padrão: todos do config)")
    parser.add_argument("--dist", default=DIST_R2, choices=["normal", "t", "skewt", "ged"],
                        help=f"Distribuição do EGARCH (padrão: {DIST_R2})")
    args = parser.parse_args()
    print(run(tickers=args.tickers, save=args.save, dist=args.dist))
