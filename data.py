"""
data.py — download via yfinance + retornos log
Usa cache em CSV para garantir determinismo nos testes de regressão.
"""
import os
import numpy as np
import pandas as pd
import yfinance as yf
from config import START_DATE, END_DATE

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)


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
        raw = yf.download(ticker, start=START_DATE, end=END_DATE,
                          auto_adjust=True, progress=False)
        if raw.empty:
            raise ValueError(f"Sem dados para {ticker}")
        px = raw["Close"].squeeze().dropna()
        px.to_csv(path)
    px.name = ticker
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
