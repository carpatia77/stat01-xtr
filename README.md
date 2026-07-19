# stat01-xtr — Reconstrução dos Reports GARCH

Engenharia reversa + reimplementação dos dois reports estatísticos originais.

## Estrutura

```
stat01-xtr/
├── config.py            # listas de ativos, aliases, classes, datas
├── data.py              # download via yfinance + retornos log (com cache CSV)
├── interpretacao.py     # regras de interpretação automática (seção 1.7 do plano)
├── render.py            # formatação fixed-width dos dois reports
├── egarch_forecast.py   # Report 2: EGARCH(1,1)-t, previsão 1d, bandas 95%
├── garch_analyzer.py    # Report 1: grade de modelos, seleção LB/AIC, render
├── validate.py          # teste de regressão (diff contra reports_originais/)
├── requirements.txt
└── reports_originais/   # arquivos de referência
```

## Setup rápido

```bash
python -m venv venv && source venv/bin/activate   # Linux/Mac
# ou: venv\Scripts\activate                        # Windows
pip install -r requirements.txt
mkdir cache
```

## Validação rápida (Fase 1 — Report 2)

```bash
# Gera o report e imprime no stdout:
python egarch_forecast.py

# Compara com o original (ignora linhas de data/hora):
python validate.py --phase 1

# Salva arquivo de saída:
python egarch_forecast.py --save
```

## Validação completa (Fase 2 — Report 1, ~10-20 min)

```bash
# Subset rápido para calibração inicial:
python garch_analyzer.py --tickers AAPL GC ^VIX EURUSD

# Grade completa:
python garch_analyzer.py --save
python validate.py --phase 2
```

## Pontos de calibração (ver PLANO_RECONSTRUCAO.md §5)

- Se α/β travarem em 0.05/0.93 → confirmar `rescale=False` + versão do `arch`
- Cache em `cache/` garante determinismo; delete para forçar re-download
- Aliases `CHF`, `JPY`, `USDX`, `XAF` podem precisar ajuste no `config.py`
- Lag do Ljung-Box: testar 5/10/20 se p-values divergirem
