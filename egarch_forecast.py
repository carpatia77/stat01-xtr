"""
egarch_forecast.py — Report 2: EGARCH(1,1)-t, previsão 1d, bandas 95%

Uso:
    python egarch_forecast.py [--save]
"""
import argparse
import numpy as np
from arch import arch_model
from data import get_returns
from render import render_report2
from config import TICKERS_R2


def forecast_one(ticker: str) -> dict:
    """
    Ajusta EGARCH(1,1)-t em ret*100 e retorna dict para render_report2.
    σ já sai em % (arch com ret*100).
    Banda 95%: close × (1 ± 1.96 × σ/100)
    """
    try:
        px, ret100 = get_returns(ticker, scale100=True)
        am = arch_model(ret100, mean="Constant", vol="EGARCH",
                        p=1, q=1, dist="t")
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


def run(tickers: list[str] | None = None, save: bool = False) -> str:
    tickers = tickers or TICKERS_R2
    resultados = [forecast_one(t) for t in tickers]
    report = render_report2(resultados)
    if save:
        from datetime import date
        fname = f"EGARCH_FORECAST_{date.today()}.txt"
        with open(fname, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"[egarch_forecast] Salvo em {fname}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EGARCH(1,1)-t forecast")
    parser.add_argument("--save", action="store_true",
                        help="Salva o report em arquivo .txt")
    parser.add_argument("--tickers", nargs="*", default=None,
                        help="Subset de tickers (padrão: todos do config)")
    args = parser.parse_args()
    print(run(tickers=args.tickers, save=args.save))
