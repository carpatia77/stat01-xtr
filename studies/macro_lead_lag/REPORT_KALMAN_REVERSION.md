# Dossiê: O Alfa da Reversão (Ajuste + Kalman + EGARCH Geométrico)

## A Tese do "Edge Contra-Intuitivo"
A pesquisa comprovou que a aplicação estrita do modelo EGARCH com Bandas Geométricas falha em conter o preço (como provado no relatório de percentil), resultando em rompimentos falsos frequentes. O *Edge Contra-Intuitivo* baseia-se em explorar exatamente a **perda de energia cinética** nesses rompimentos, apostando na reversão imediata à média.

O modelo final de "Ponto de Repouso" é uma trindade:
1. **Âncora Macro (Confirmação):** XAUUSD apontando divergência no fluxo livre de notícias.
2. **Média Dinâmica Instantânea:** Filtro de Kalman 1D.
3. **Memória Institucional:** Ajuste da B3 (VWAP das 17:00 às 17:15).

## Fita de Execução (O Custo do Pedágio)
Ao testarmos a regra de saída cega em T+1 (Time-Stop):
- O modelo apresentou um **Win Rate Bruto de 51.7%** e um Sharpe Anualizado massivo (+1.85).
- **Stress Test de Fricção (Renaissance-Level):** Ao adicionarmos 1.0 bps de custo por trade (spread + corretagem), o *Edge* evapora, tornando o saldo líquido negativo. A janela de T+1 (5 minutos) é muito curta para cobrir a taxa transacional da bolsa.

## Simulador Event-Driven (Cenário Multi-Candle)
Para esticar o *Payoff*, substituímos o *Time-Stop* por **Take Profits** reais na Média de Kalman e no Ajuste, protegidos por um **Stop Técnico de 1 Candle** (Máxima/Mínima + 20 pontos).

**Conclusão Matemática Final:**
O Payoff dobrou (Ganho Médio saltou de +6.78 para +13.89 bps). No entanto, o ruído HFT do M5 (wicks/violinos) esmagou o Win Rate de 51% para 33.2%.
A pesquisa conclui que o direcional existe e os alvos híbridos funcionam, mas operar essa reversão exige **Stops de Volatilidade (ATR/Sigma)**; Stops baseados em máximas rígidas de M5 não sobrevivem à liquidez institucional varrendo o *book*.
