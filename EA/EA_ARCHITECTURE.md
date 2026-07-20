
# Arquitetura do Expert Advisor (Kalman Reversion)

Este documento define as regras lógicas validadas quantitativamente para o robô institucional MQL5, baseado no estudo estatístico do "Edge Invertido" e análise de ruído HFT no WIN (M5).

## 1. Módulos de Cálculo (A Trindade)
1. **Filtro de Kalman 1D:** Média dinâmica instantânea que atua como ímã de atração imediata.
2. **Ajuste B3 (VWAP Institucional):** Calculado das 17:00 às 17:15. Atua como âncora macro de longo alcance.
3. **Bandas Geométricas EGARCH:** Baseadas no desvio padrão (Sigma = 0.67) e comprimidas pelo fator geométrico (`f = 0.35`). Elas são desenhadas para *falhar* e absorver a exaustão cinética.

## 2. Condição de Entrada (Gatilho + Confirmação)
- **Fase 1 (Stop Hunt):** Preço rompe a banda superior/inferior.
- **Fase 2 (Caos HFT):** O preço passa de 2 a 4 candles (10 a 20 min) vibrando acima/abaixo da banda. 
- **Fase 3 (Gatilho):** O robô **apenas entra a mercado** no momento em que o candle fecha *de volta para dentro* da zona (Confirmation Entry). 
- **Macro Filtro (XAUUSD):** A entrada só é autorizada se o Ouro (XAUUSD) estiver apontando divergência (ex: índice engolfou para baixo, mas ouro está subindo).

## 3. Gestão de Risco (Sobrevivência ao Ruído)
- **Stop Loss Inicial (Largo):** Baseado no Percentil 90 da análise de excursão, o stop é posicionado de forma cara, a **~550 pontos** da linha da banda geométrica. Isso garante a sobrevivência a 90% das "violinadas" da mesa proprietária.
- **Breakeven e Trailing:** Assim que o "elástico solta" e o preço derrete/dispara a favor da operação, o Stop Loss é agressivamente movido para a zona de empate (*Breakeven*). 
- A partir daí, o robô sufoca a operação protegendo lucros (*Trailing Stop*), deixando o risco virtual no zero absoluto.

## 4. Alvos Institucionais (Take Profit Híbrido)
O robô terá saídas parciais ou totais nos seguintes alvos gravitacionais:
- **Alvo Curto (Scalp Seguro):** A linha central do EGARCH ou o Filtro de Kalman Dinâmico.
- **Alvo Longo (Zone to Zone / Home Run):** A Banda Oposta ou a linha do Ajuste Institucional do dia anterior.

