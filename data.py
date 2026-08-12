"""
data.py — download via yfinance + retornos log
Usa cache em CSV para garantir determinismo nos testes de regressão.
"""
import os
import warnings
from datetime import timedelta
import numpy as np
import pandas as pd
import yfinance as yf
from config import START_DATE, END_DATE

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Quantos dias ÚTEIS de folga tolerar entre a última barra esperada e a
# última barra realmente recebida antes de avisar que o dado pode estar
# desatualizado. Usa dia útil (não corrido) para não disparar falso alarme
# toda segunda-feira — comparar por dia corrido mascarava exatamente o caso
# real que queremos pegar (gap de só 1 dia útil no ^VIX em 07-15).
_STALE_TOLERANCE_BDAYS = 0


def _cache_path(ticker: str) -> str:
    safe = ticker.replace("=", "_").replace("^", "_").replace("-", "_")
    return os.path.join(CACHE_DIR, f"{safe}.csv")


def get_prices(ticker: str, force_download: bool = False) -> pd.Series:
    """
    Retorna série de fechamentos ajustados.
    Lê do cache CSV se existir e force_download=False.
    """
    path = _cache_path(ticker)
    if os.path.exists(path) and not force_download:
        px = pd.read_csv(path, index_col=0, parse_dates=True).squeeze()
    else:
        # end é exclusivo no yfinance: NÃO somar dias aqui. O report original
        # usa END_DATE=2026-07-17 só como rótulo do período; a última barra
        # efetivamente puxada é a de 2026-07-16 (end exclusivo corta o próprio
        # dia 17). Confirmado batendo os "Fechamentos Anteriores" do Report 2
        # contra reports_originais/ (ver PLANO_RECONSTRUCAO.md).
        # auto_adjust=False: usa Close bruto, não ajustado por dividendos —
        # os "Fechamentos Anteriores" do Report 2 são preços crus.
        raw = yf.download(ticker, start=START_DATE, end=END_DATE,
                          auto_adjust=False, progress=False)
        if raw.empty:
            raise ValueError(f"Sem dados para {ticker}")
        px = raw["Close"].squeeze().dropna()
        px.to_csv(path)
    px.name = ticker

    # --- guarda de frescor: yfinance às vezes ainda não publicou a barra
    # mais recente (comum de manhã cedo, ou índices com settlement atrasado
    # como ^VIX). Sem isso o motor usa preço/retorno velho em silêncio e o
    # forecast do dia sai errado sem nenhum aviso. Confirmado: foi a causa
    # real da divergência do ^VIX no backtest de 2026-07-15 (report do autor
    # usou o fechamento de 07-13 achando que era o mais recente — gap de
    # apenas 1 dia ÚTIL, por isso a comparação é em dia útil, não corrido).
    last_bar = px.index[-1].date()
    expected = END_DATE - timedelta(days=1)
    while expected.weekday() >= 5:  # recua até o último dia útil (sáb/dom)
        expected -= timedelta(days=1)
    gap_bdays = int(np.busday_count(last_bar, expected))
    if gap_bdays > _STALE_TOLERANCE_BDAYS:
        warnings.warn(
            f"[data.py] {ticker}: última barra recebida é {last_bar}, "
            f"esperava o último dia útil {expected} (gap de {gap_bdays} "
            f"dia(s) útil(eis)). Dado possivelmente desatualizado no Yahoo "
            f"Finance no momento do download — considere rodar de novo "
            f"mais tarde ou com force_download=True.",
            stacklevel=2,
        )
    return px


def get_returns(ticker: str, scale100: bool = False,
                force_download: bool = False) -> tuple[pd.Series, pd.Series]:
    """
    Retorna (px, ret) onde:
      ret = log(px_t / px_{t-1})          se scale100=False  (Report 1)
      ret = 100 * log(px_t / px_{t-1})    se scale100=True   (Report 2)
    """
    px = get_prices(ticker, force_download=force_download)
    ret = np.log(px / px.shift(1)).dropna()
    if scale100:
        ret = ret * 100
    return px, ret
