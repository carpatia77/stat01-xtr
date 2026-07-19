# Plano de Reconstrução — Engenharia Reversa dos Reports Estatísticos

Este documento especifica, a partir de engenharia reversa de dois reports originais, como
reconstruir em Python o código que os gerou, de forma que a saída **bata numericamente**
com os reports de referência (armazenados em `reports_originais/`).

- **Report 1**: `ANALISE_GARCH_COMPLETO_ORIGINAL.txt` — "GARCH ANALYZER COMPLETO v3.9.4"
  (seleção automática de modelo GARCH/EGARCH + distribuição, com interpretação automática).
- **Report 2**: `EGARCHTSTUDENT1.1t_20260717__ORIGINAL.txt` — "Análise EGARCH(1,1)-t"
  (previsão de volatilidade 1 dia à frente + banda mín/máx de preço).

---

## 1. Conclusões da engenharia reversa (evidências)

### 1.1 Stack e fonte de dados
- **Biblioteca de modelagem: `arch` (Kevin Sheppard)**. Evidências fortes:
  - Diversos ativos GARCH convergiram exatamente em **α=0.05 e β=0.93** (6A, 6B, 6C, 6E,
    6L, AUDNZD, USDBRL, EURUSD, ^BVSP) e USDX em **α=0.20 / β=0.70** — esses são
    **valores iniciais internos do otimizador do pacote `arch`**. Isso ocorre quando os
    retornos são passados **sem reescala** (valores ~1e-2), deixando a superfície de
    verossimilhança achatada e o otimizador parado próximo do ponto inicial.
  - Ω (omega) dos GARCH na ordem de `1e-6` a `1e-5` confirma retornos **não multiplicados
    por 100** no Report 1 (variância diária de retornos log puros).
  - Nomes de distribuição do report ("Normal", "Student-t", "Skewed t", "GED") mapeiam
    1:1 para `dist='normal' | 't' | 'skewt' | 'ged'` do `arch`.
- **Fonte de dados: `yfinance`**. Evidências: tickers no formato Yahoo (`DX-Y.NYB`,
  `^BVSP`, `^VIX`, `BTC-USD`; no Report 2: `6A=F`, `BRL=X`, `NZDUSD=X` etc.).
- **Janela de dados**: `Período analisado: 2022-07-18 → 2026-07-17` = **4 anos corridos
  retroativos a partir da data de execução** (`end = hoje`, `start = hoje - 1460 dias`).
  "Dias úteis: 1044" = número de linhas retornadas para o ativo de referência.

### 1.2 Report 2 — fórmula da banda (verificada numericamente)
Para cada ativo: `min = close·(1 − 1.96·σ)` e `max = close·(1 + 1.96·σ)`, onde σ é a
volatilidade prevista para 1 dia (fração, não %). Verificação:

| Ativo | close | σ (%) | 1.96·σ·close | close − banda | min do report |
|---|---|---|---|---|---|
| GC=F | 3985.6001 | 1.4950 | 116.789 | 3868.811 | 3868.8110 ✓ |
| ^VIX | 16.7300 | 7.6443 | 2.5066 | 14.2234 | 14.2234 ✓ |
| 6A=F | 0.6992 | 0.4969 | 0.00681 | 0.6924 | 0.6923 ✓ (arredond.) |

Ou seja: **intervalo de 95% assumindo quantil normal (z=1.96)**, aplicado
multiplicativamente sobre o fechamento anterior.

### 1.3 Report 2 — escala da volatilidade
σ é exibido em % com 4 casas (`0.4969`). Compatível com fit de EGARCH(1,1) `dist='t'`
sobre **retornos ×100** (prática padrão do `arch`), com
`sigma = sqrt(forecast.variance[h.1])` já em %. (Alternativa equivalente: fit sem ×100 e
multiplicar σ por 100 na exibição — o dev deve validar contra o report qual das duas
reproduz os dígitos; a primeira é a mais provável.)

### 1.4 Report 1 — grade de modelos testados
Modelos observados nos vencedores: `GARCH(1,1)`, `GARCH(1,2)`, `GARCH(2,1)`,
`EGARCH(1,1,1)`, `EGARCH(1,1,2)`. A legenda menciona também GJR-GARCH. Grade inferida:

- `GARCH(p,q)` para p,q ∈ {1,2}
- `GJR-GARCH(1,1)` (o=1) — testado, nunca venceu nesta amostra
- `EGARCH(p,o,q)` com (1,1,1) e (1,1,2)
- Cada modelo × 4 distribuições: `normal`, `t`, `skewt`, `ged`

Notação exibida: EGARCH mostra os 3 índices `(p,o,q)`; GARCH mostra `(p,q)`.

### 1.5 Report 1 — critério de seleção
Conforme o próprio report declara:
1. Filtrar modelos com **Ljung-Box p > 0.05** (resíduos padronizados sem autocorrelação;
   usar `statsmodels.stats.diagnostic.acorr_ljungbox` sobre `res.std_resid`, lag=10,
   reportando o p-value — coluna `LB`).
2. Entre os válidos, escolher o **menor AIC** (`res.aic`).
3. `Status = "EXCELENTE"` quando LB > 0.05 (todos os vencedores exibem isso; prever
   possíveis níveis inferiores, ex. "BOM"/"RUIM", para LB menor — calibrar se surgir).

### 1.6 Report 1 — colunas de parâmetros
- **Ω** = `omega` do modelo (12 casas decimais).
- **α** = **soma de todos os `alpha[i]`** (8 casas) — a legenda confirma "soma de todos os α[i]".
- **β** = **soma de todos os `beta[i]`** (8 casas).
- **γ** = soma dos `gamma[i]` (8 casas); `0.00000000` para GARCH puro.

### 1.7 Report 1 — regras de interpretação automática (reconstruídas dos dados)
As tags são concatenadas com `" | "` na ordem: **[tag de Ω] | [tag de β] | [tag de α] |
[tag de classe/pânico] | [tag de caudas]**. Regras validadas contra as 33 linhas:

Somente para EGARCH (efeito do Ω log-vol):
- `Ω < -0.5` → `QUEDAS EXPLODEM VOL!`
- `-0.5 ≤ Ω < -0.2` → `Quedas aumentam vol`
- `-0.2 ≤ Ω < 0` → `Leve alavancagem`

Persistência (qualquer modelo):
- `β > 0.98` → `VOL DURA MUITO (CRISES)`
- `0.95 < β ≤ 0.98` → `Vol persistente`

Choques:
- `α > 0.2` → `REAÇÃO FORTE A NOTÍCIAS`
- `0.1 ≤ α ≤ 0.2` → `Choques moderados`

Classe do ativo (exige dict `ticker → classe` no código: FOREX / FUTUROS / AÇÃO):
- `FOREX CLÁSSICO` → FOREX + GARCH + α<0.07 + β>0.90 (USDBRL, EURUSD)
- `VOL TÉCNICA` → FUTUROS + GARCH + α>0.08
- `ACAO MADURA` → AÇÃO + GARCH + α<0.07 (inclui AUDNZD, NZDUSD, DX-Y.NYB → no código
  original esses tickers estão classificados como "AÇÃO"; reproduzir o mesmo mapa)
- `ACAO VOLÁTIL` → AÇÃO + GARCH + α>0.15 (USDX)
- `TECH/PÂNICO` → EGARCH + Ω < -0.3

Caudas (pela distribuição vencedora):
- `Student-t` → `CAUDAS PESADAS (leptocurtose)`
- `Skewed t` → `CAUDAS PESADAS + ASSIMETRIA`
- `GED` → `CAUDAS EXTREMAS`
- `Normal` → sem tag; **se a lista final ficar vazia → `Estável`** (caso 6E).

### 1.8 Universos de ativos
- Report 1 (33 ativos, ordem alfabética case-sensitive com `^` por último):
  `6A, 6B, 6C, 6E, 6J, 6L, 6S, AAPL, AMZN, AUDNZD, USDBRL, BTC-USD, CHF, CL, DIA,
  DX-Y.NYB, EURUSD, EWZ, GC, GOOGL, JPY, RTY, ES, MGC, NQ, YM, NVDA, NZDUSD, TSLA,
  USDX, XAF, ^BVSP, ^VIX, ^VVIX`.
  Os nomes exibidos são **aliases** (ex.: `6A` ↔ `6A=F`, `EURUSD` ↔ `EURUSD=X`,
  `USDBRL` ↔ `BRL=X`, `CHF` ↔ `6S=F`? — manter um dict `alias → ticker_yahoo` e
  calibrar; `USDX`/`XAF` provavelmente `DX=F` e um ETF/futuro a confirmar).
  Obs.: a ordem do report NÃO é alfabética pura (USDBRL após AUDNZD, ES após RTY, YM
  após NQ) → a ordem vem da **ordem de inserção da lista de tickers no código**;
  reproduzir a lista exatamente na ordem acima.
- Report 2 (19 ativos, tickers Yahoo literais): `6A=F, 6B=F, 6C=F, 6E=F, 6J=F, 6S=F,
  BRL=X, DX-Y.NYB, EURBRL=X, GC=F, M2K=F, MES=F, MGC=F, MNQ=F, MYM=F, NZDUSD=X,
  USDBRL=X, ^BVSP, ^VIX` (ordem alfabética; nota: `USDBRL=X` e `BRL=X` retornam a mesma
  série — ambos aparecem com valores idênticos, confirmando).

---

## 2. Arquitetura proposta do código

```
stat01-xtr/
├── config.py            # listas de ativos, aliases, classes (FOREX/FUTUROS/AÇÃO), datas
├── data.py              # download via yfinance + retornos log
├── garch_analyzer.py    # Report 1: grade de modelos, seleção, interpretação, render
├── egarch_forecast.py   # Report 2: EGARCH(1,1)-t, previsão 1d, bandas 95%, render
├── interpretacao.py     # regras da seção 1.7
├── render.py            # formatação fixed-width dos dois reports
└── reports_originais/   # arquivos de referência p/ testes de regressão
```

Dependências (fixar versões — crítico para reproduzir dígitos):
`yfinance`, `arch` (testar 6.x; se dígitos divergirem, tentar 5.x), `statsmodels`,
`pandas`, `numpy`, `scipy`.

## 3. Especificação por módulo

### 3.1 `data.py`
```python
end = date.today()                     # no original: 2026-07-17
start = end - timedelta(days=1460)     # 4 anos corridos
px = yf.download(ticker, start=start, end=end)["Close"].dropna()
ret = np.log(px / px.shift(1)).dropna()   # Report 1: usar ret puro
ret100 = 100 * ret                        # Report 2: usar ret * 100
```

### 3.2 `garch_analyzer.py` (Report 1)
```python
from arch import arch_model
GRID = (
    [("GARCH", p, 0, q) for p in (1, 2) for q in (1, 2)]
    + [("GARCH", 1, 1, 1)]                    # GJR
    + [("EGARCH", 1, 1, 1), ("EGARCH", 1, 1, 2)]
)
DISTS = ["normal", "t", "skewt", "ged"]

for (vol, p, o, q) in GRID:
    for dist in DISTS:
        am = arch_model(ret, mean="Constant", vol=vol, p=p, o=o, q=q,
                        dist=dist, rescale=False)   # rescale=False é essencial
        res = am.fit(disp="off")
        lb = acorr_ljungbox(res.std_resid, lags=[10])["lb_pvalue"].iloc[0]
        candidatos.append((lb, res.aic, ...))
# seleção: filtra lb > 0.05, escolhe min AIC; se nenhum passa, min AIC geral
```
Extração de parâmetros: `omega = params["omega"]`;
`alpha = sum(params[f"alpha[{i}]"] ...)`; idem beta e gamma.

### 3.3 `egarch_forecast.py` (Report 2)
```python
am = arch_model(ret100, mean="Constant", vol="EGARCH", p=1, q=1, dist="t")
res = am.fit(disp="off")
f = res.forecast(horizon=1)
sigma_pct = float(np.sqrt(f.variance.iloc[-1, 0]))      # já em %
close = float(px.iloc[-1])                              # "Fechamento Anterior"
minimo = close * (1 - 1.96 * sigma_pct / 100)
maximo = close * (1 + 1.96 * sigma_pct / 100)
status = "Sucesso"    # em exceção: capturar e escrever "Erro: <msg>" (ou similar)
```

### 3.4 `render.py` — formatos exatos
Report 1 (separador `"=" * 228`):
```python
linha = (f"{alias:<9}{modelo:<21}{dist:<15}{aic:<11.1f}{lb:<10.3f}"
         f"{omega:<19.12f}{alpha:<16.8f}{beta:<18.8f}{gamma:<18.8f}"
         f"{status:<13}{interpretacao:<60}")
```
Cabeçalho fixo:
`Ativo    Modelo               Distribuição     AIC        LB        Ω (Omega)         α (Alpha)       β (Beta)          γ (Gamma)          Status     Interpretação`
Seguido dos blocos estáticos de texto ("NOVO: DISTRIBUIÇÕES...", "CRITÉRIOS...",
"INTERPRETAÇÃO DOS PARÂMETROS GREGOS", "DICAS PARA MT5", "LEGENDA... (v3.9.4)") —
copiar literalmente do arquivo de referência.

Report 2 (separador `"=" * 130`):
```python
linha = (f"{ticker:<14}{close:^19.4f}{vol_pct:^23.4f}"
         f"{minimo:^23.4f}{maximo:^20.4f}   {status:<30}")
```
Cabeçalhos:
`Análise EGARCH(1,1)-t para Ativos Selecionados` / `Data: YYYY-MM-DD HH:MM:SS` /
`Resultados do Modelo EGARCH-t` e a linha de colunas fixa. Calibrar larguras
caractere a caractere contra `reports_originais/` (teste de regressão abaixo).

## 4. Plano de trabalho para o dev

1. **Fase 0 — ambiente**: criar venv, fixar `arch`, `yfinance`, `statsmodels`;
   guardar em cache local (CSV/parquet) os dados baixados de 2022-07-18 a 2026-07-17
   para tornar os testes determinísticos (yfinance pode revisar dados históricos).
2. **Fase 1 — Report 2** (mais simples, valida stack): implementar
   `egarch_forecast.py` + render; comparar as 19 linhas com o original.
3. **Fase 2 — Report 1 núcleo**: grade de modelos + seleção LB/AIC; conferir para 3–4
   ativos (ex.: AAPL, GC, EURUSD, ^VIX) se modelo vencedor, distribuição, AIC (1 casa)
   e parâmetros (8–12 casas) batem. Se α/β não travarem em 0.05/0.93 nos casos GARCH,
   revisar `rescale=False` e versão do `arch`.
4. **Fase 3 — interpretação**: implementar seção 1.7 e o mapa de classes; validar as
   33 strings de interpretação por comparação exata.
5. **Fase 4 — render + regressão**: teste automatizado que gera os dois reports com os
   dados em cache e faz `diff` contra `reports_originais/` ignorando apenas as linhas
   de data/hora. Meta: diff vazio.

## 5. Riscos e pontos de calibração

- **Dados do Yahoo mudam retroativamente** (splits, ajustes) → sem o cache da execução
  original, dígitos podem divergir minimamente; o critério de aceite realista é:
  mesma estrutura, mesmas regras, e igualdade numérica quando alimentado com os mesmos
  dados de entrada.
- **Versão do `arch`** altera valores iniciais/otimizador → testar 6.3, 6.x e 5.6.
- **Aliases de tickers do Report 1** (`CHF`, `JPY`, `USDX`, `XAF`, `ES`, `NQ`, `RTY`,
  `YM`, `CL`, `GC`, `MGC`) → confirmar o mapa Yahoo (`6S=F`? `CHF=X`? `DX=F`, `ES=F`,
  `NQ=F`, `RTY=F`, `YM=F`, `CL=F`, `GC=F`, `MGC=F`); usar o AIC do report como
  impressão digital para validar cada mapeamento.
- **Lag do Ljung-Box** (10 é o default usual; testar 5/10/20 se p-values não baterem) e
  se o teste é sobre resíduos padronizados ou seus quadrados.
- **Fallback quando nenhum modelo passa no LB** — não observável no report (todos
  "EXCELENTE"); implementar min-AIC geral como fallback documentado.
