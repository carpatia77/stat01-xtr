"""
config.py — listas de ativos, aliases, classes, datas
"""
from datetime import date, timedelta

# ── Datas ──────────────────────────────────────────────────────────────────────
END_DATE   = date.today()
START_DATE = END_DATE - timedelta(days=1460)  # 4 anos corridos

# ── Report 2 — 19 tickers Yahoo (ordem alfabética do report original) ──────────
TICKERS_R2 = [
    "6A=F", "6B=F", "6C=F", "6E=F", "6J=F", "6S=F",
    "BRL=X", "DX-Y.NYB", "EURBRL=X",
    "GC=F", "M2K=F", "MES=F", "MGC=F", "MNQ=F", "MYM=F",
    "NZDUSD=X", "USDBRL=X", "^BVSP", "^VIX",
]

# ── Report 1 — 33 ativos (ordem de inserção = ordem do report) ────────────────
# Coluna: (alias_exibido, ticker_yahoo, classe)
ASSETS_R1 = [
    ("6A",       "6A=F",      "FUTUROS"),
    ("6B",       "6B=F",      "FUTUROS"),
    ("6C",       "6C=F",      "FUTUROS"),
    ("6E",       "6E=F",      "FUTUROS"),
    ("6J",       "6J=F",      "FUTUROS"),
    ("6L",       "6L=F",      "FUTUROS"),
    ("6S",       "6S=F",      "FUTUROS"),
    ("AAPL",     "AAPL",      "AÇÃO"),
    ("AMZN",     "AMZN",      "AÇÃO"),
    ("AUDNZD",   "AUDNZD=X",  "AÇÃO"),   # mapeado como AÇÃO no código original
    ("USDBRL",   "BRL=X",     "FOREX"),
    ("BTC-USD",  "BTC-USD",   "AÇÃO"),
    ("CHF",      "6S=F",      "FUTUROS"),  # alias alternativo — calibrar
    ("CL",       "CL=F",      "FUTUROS"),
    ("DIA",      "DIA",       "AÇÃO"),
    ("DX-Y.NYB", "DX-Y.NYB",  "AÇÃO"),   # mapeado como AÇÃO no original
    ("EURUSD",   "EURUSD=X",  "FOREX"),
    ("EWZ",      "EWZ",       "AÇÃO"),
    ("GC",       "GC=F",      "FUTUROS"),
    ("GOOGL",    "GOOGL",     "AÇÃO"),
    ("JPY",      "6J=F",      "FUTUROS"),  # alias alternativo
    ("RTY",      "RTY=F",     "FUTUROS"),
    ("ES",       "ES=F",      "FUTUROS"),
    ("MGC",      "MGC=F",     "FUTUROS"),
    ("NQ",       "NQ=F",      "FUTUROS"),
    ("YM",       "YM=F",      "FUTUROS"),
    ("NVDA",     "NVDA",      "AÇÃO"),
    ("NZDUSD",   "NZDUSD=X",  "AÇÃO"),   # mapeado como AÇÃO no original
    ("TSLA",     "TSLA",      "AÇÃO"),
    ("USDX",     "DX-Y.NYB",  "AÇÃO"),   # AÇÃO VOLÁTIL no original
    ("XAF",      "DX=F",      "FUTUROS"), # a confirmar — calibrar pelo AIC
    ("^BVSP",    "^BVSP",     "AÇÃO"),
    ("^VIX",     "^VIX",      "AÇÃO"),
    # ("^VVIX",  "^VVIX",     "AÇÃO"),  # 34.º se presente no report
]
