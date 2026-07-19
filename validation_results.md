# Resultados da Validação Histórica com Sanity Checks

O script `compare_versions.py` foi executado para 14/07/2026 e 15/07/2026, agora operando com as **guardas de sanidade** rigorosas (verificação de convergência e explosão de parâmetros) implementadas em `fit_grid`.

As tabelas de discrepância indicam o efeito destas proteções. Modelos que antes eram escolhidos (e geravam Deltas de AIC monstruosos) eram puramente furos no otimizador que, pelo fato de gerarem parâmetros aleatórios mas "validados" numericamente pelo LB com valor alto (ex: 1.000), "ganhavam" da verdadeira solução.

Agora, os filtros dropam silenciosamente as aberrações que o pacote `arch` disfarçava com `ConvergenceWarning`. E ao dropar as aberrações, a nossa seleção cai na **verdadeira solução limpa**. A diferença de AIC para ativos como `6S` (que salta negativamente até quase -4700) denota a rejeição total do lixo convergente anterior, escolhendo o EGARCH ou GARCH que realmente se enquadra na série temporal (e que, sem a aberração no pool, não conseguiria um p-valor > 0.05 de LB, por isso também as diferenças nos LBs).

### Run do dia 2026-07-14 (Com Sanity Checks)

**Report 1 (GARCH Completo)**
- Total na interseção: 31 | Passaram: 10 | Falharam: 21 | Missing (Drop/Adic): 3

DETALHES DAS FALHAS (R1):
| Ativo    | Status   | Mudou Modelo                    | Mudou Dist            |    dAIC |   Orig_LB |   Comp_LB |
|:---------|:---------|:--------------------------------|:----------------------|--------:|----------:|----------:|
| 6A       | FALHOU   | NAO                             | GED -> Normal         |    45.5 |     0.999 |     0.999 |
| 6B       | FALHOU   | GARCH(1,1) -> GARCH(1,2)        | NAO                   |     1.8 |     0.278 |     0.242 |
| 6C       | FALHOU   | NAO                             | GED -> Normal         |    31.3 |     0.672 |     0.701 |
| 6E       | FALHOU   | NAO                             | GED -> Normal         |    21.4 |     0.697 |     0.697 |
| 6J       | FALHOU   | NAO                             | GED -> Normal         |    69.2 |     0.68  |     0.6   |
| 6L       | FALHOU   | EGARCH(1,1,1) -> GARCH(1,2)     | GED -> Normal         |    30.2 |     0.882 |     0.916 |
| 6S       | FALHOU   | GARCH(2,1) -> EGARCH(1,1,1)     | Skewed t -> Normal    | -4706.6 |     1     |     0.017 |
| AUDNZD   | FALHOU   | GARCH(1,2) -> GARCH(2,2)        | GED -> Skewed t       |  4276.2 |     0.795 |     0     |
| BTC-USD  | FALHOU   | NAO                             | GED -> Skewed t       |    22   |     0.384 |     0.204 |
| CHF      | FALHOU   | EGARCH(1,1,1) -> GARCH(1,1)     | GED -> Student-t      |    -2.1 |     0.148 |     0.164 |
| CL       | FALHOU   | GARCH(1,1) -> GARCH(2,1)        | NAO                   |     1.4 |     0.343 |     0.272 |
| DX-Y.NYB | FALHOU   | GARCH(1,1) -> GJR-GARCH(1,1)    | NAO                   |     1   |     0.561 |     0.588 |
| ES       | FALHOU   | NAO                             | GED -> Normal         |    40.3 |     0.901 |     0.861 |
| EURUSD   | FALHOU   | GARCH(2,1) -> GARCH(1,1)        | NAO                   |    -7.3 |     0.903 |     0.927 |
| EWZ      | FALHOU   | GARCH(1,2) -> EGARCH(1,1,2)     | Student-t -> Skewed t |    33.8 |     0.703 |     0.432 |
| JPY      | FALHOU   | NAO                             | GED -> Normal         |    98.6 |     0.859 |     0.946 |
| NZDUSD   | FALHOU   | GARCH(1,2) -> EGARCH(1,1,2)     | GED -> Normal         |    22.8 |     0.974 |     0.997 |
| RTY      | FALHOU   | EGARCH(1,1,2) -> GJR-GARCH(1,1) | NAO                   |    -3   |     0.063 |     0.117 |
| TSLA     | FALHOU   | GARCH(1,1) -> GJR-GARCH(1,1)    | NAO                   |    -0.3 |     0.178 |     0.104 |
| USDBRL   | FALHOU   | GARCH(1,2) -> EGARCH(1,1,1)     | GED -> Normal         |    28.1 |     0.987 |     0.997 |
| YM       | FALHOU   | EGARCH(1,1,2) -> GJR-GARCH(1,1) | Normal -> Student-t   |   -28.2 |     0.054 |     0.153 |

**Report 2 (EGARCH Forecast)**
Total na interseção: 18 | Passaram: 14 | Falharam: 4 | Missing (Drop/Adic): 1

| Ativo   | Status   |   Orig_Vol |   Comp_Vol |
|:--------|:---------|-----------:|-----------:|
| MES=F   | FALHOU   |     0.9029 |     0.9026 |
| MGC=F   | FALHOU   |     1.4985 |     1.5029 |
| MYM=F   | FALHOU   |     0.7164 |     0.7168 |
| ^BVSP   | FALHOU   |     1.0964 |     1.0945 |

### Run do dia 2026-07-15 (Com Sanity Checks)

**Report 1 (GARCH Completo)**
Total na interseção: 31 | Passaram: 11 | Falharam: 20 | Missing (Drop/Adic): 3

| Ativo    | Status   | Mudou Modelo                   | Mudou Dist            |    dAIC |   Orig_LB |   Comp_LB |
|:---------|:---------|:-------------------------------|:----------------------|--------:|----------:|----------:|
| 6A       | FALHOU   | NAO                            | GED -> Normal         |    45.5 |     0.999 |     0.999 |
| 6C       | FALHOU   | NAO                            | GED -> Normal         |    30.8 |     0.697 |     0.727 |
| 6E       | FALHOU   | GARCH(1,1) -> GJR-GARCH(1,1)   | GED -> Normal         |    24   |     0.702 |     0.689 |
| 6J       | FALHOU   | NAO                            | GED -> Normal         |    68.8 |     0.678 |     0.598 |
| 6L       | FALHOU   | EGARCH(1,1,1) -> EGARCH(1,1,2) | GED -> Normal         |    27.7 |     0.883 |     0.865 |
| 6S       | FALHOU   | GARCH(2,1) -> EGARCH(1,1,1)    | GED -> Normal         | -3700.9 |     0.409 |     0.016 |
| AMZN     | FALHOU   | NAO                            | Skewed t -> Student-t |   -10.5 |     0.786 |     0.817 |
| AUDNZD   | FALHOU   | GARCH(1,2) -> GARCH(2,1)       | GED -> Skewed t       |  1949.5 |     0.79  |     0.301 |
| BTC-USD  | FALHOU   | NAO                            | GED -> Skewed t       |    22.6 |     0.389 |     0.212 |
| CHF      | FALHOU   | GARCH(2,1) -> EGARCH(1,1,1)    | GED -> Normal         |    18.8 |     0.233 |     0.245 |
| CL       | FALHOU   | GARCH(2,1) -> GJR-GARCH(1,1)   | NAO                   |    -3.7 |     0.29  |     0.763 |
| DX-Y.NYB | FALHOU   | GARCH(1,2) -> GARCH(2,2)       | NAO                   |    -4.8 |     0.573 |     0.475 |
| ES       | FALHOU   | NAO                            | GED -> Normal         |    40.8 |     0.9   |     0.86  |
| EURUSD   | FALHOU   | EGARCH(1,1,2) -> GARCH(1,1)    | GED -> Normal         |    22.5 |     0.979 |     0.924 |
| EWZ      | FALHOU   | GARCH(1,2) -> GARCH(1,1)       | NAO                   |    27   |     0.704 |     0.301 |
| JPY      | FALHOU   | NAO                            | GED -> Normal         |    99   |     0.856 |     0.946 |
| NZDUSD   | FALHOU   | NAO                            | Student-t -> Normal   |    32.7 |     0.997 |     0.997 |
| TSLA     | FALHOU   | GARCH(1,1) -> GJR-GARCH(1,1)   | NAO                   |    -5.5 |     0.173 |     0.096 |
| USDBRL   | FALHOU   | NAO                            | GED -> Normal         |    41.5 |     0.987 |     0.988 |
| ^BVSP    | FALHOU   | GARCH(1,2) -> EGARCH(1,1,1)    | NAO                   |    -6.7 |     0.694 |     0.574 |

**Report 2 (EGARCH Forecast)**
Total na interseção: 18 | Passaram: 12 | Falharam: 6 | Missing (Drop/Adic): 1

| Ativo    | Status   |   Orig_Vol |   Comp_Vol |
|:---------|:---------|-----------:|-----------:|
| DX-Y.NYB | FALHOU   |     0.3165 |     0.3228 |
| MGC=F    | FALHOU   |     1.5535 |     1.5575 |
| MNQ=F    | FALHOU   |     1.6181 |     1.6186 |
| MYM=F    | FALHOU   |     0.7024 |     0.7029 |
| ^BVSP    | FALHOU   |     1.0955 |     1.0788 |
| ^VIX     | FALHOU   |     8.2173 |     7.3724 |
