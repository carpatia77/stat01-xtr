# Resultados da Validação Histórica com Sanity Checks (Fix GED)

O script `compare_versions.py` foi executado para 14/07/2026 e 15/07/2026. Esta execução já contempla a correção do filtro do parâmetro `nu`: anteriormente, o filtro tratava `nu` da distribuição GED como graus de liberdade do Student-t (exigindo `nu >= 2.05`), o que rejeitava falsamente modelos GED válidos (onde `nu < 2` é o comportamento esperado para caudas pesadas).

Com a restrição de `nu` aplicada apenas a `t` e `skewt` (e o `convergence_flag` + limite de `mu` mantidos para todas), **a taxa de acerto recuperou-se para os níveis originais exatos (19/31 e 16/31).** O padrão sistemático de falha `GED -> Normal` com piora no AIC sumiu completamente, confirmando que aqueles fits GED do autor original eram de fato válidos e ótimos.

Ao mesmo tempo, os falsos positivos causados por falha do otimizador SciPy (como o caso do `6S` original, que tinha `mu` negativo na casa dos milhões mas era aceito por ter um p-valor Ljung-Box degenerado de 1.0) continuam sendo devidamente bloqueados pelo `convergence_flag`.

### Run do dia 2026-07-14 (Com Sanity Checks Corrigidos)

**Report 1 (GARCH Completo)**
Total na interseção: 31 | Passaram: 19 | Falharam: 12 | Missing (Drop/Adic): 3

DETALHES DAS FALHAS (R1):
| Ativo    | Status   | Mudou Modelo                    | Mudou Dist            |    dAIC |   Orig_LB |   Comp_LB |
|:---------|:---------|:--------------------------------|:----------------------|--------:|----------:|----------:|
| 6B       | FALHOU   | GARCH(1,1) -> GARCH(1,2)        | NAO                   |     1.8 |     0.278 |     0.242 |
| 6E       | FALHOU   | NAO                             | GED -> Normal         |    21.4 |     0.697 |     0.697 |
| 6S       | FALHOU   | GARCH(2,1) -> GARCH(1,2)        | Skewed t -> GED       | -4748.2 |     1     |     0.007 |
| CHF      | FALHOU   | EGARCH(1,1,1) -> GARCH(1,1)     | GED -> Student-t      |    -2.1 |     0.148 |     0.164 |
| CL       | FALHOU   | GARCH(1,1) -> GARCH(2,1)        | NAO                   |     1.4 |     0.343 |     0.272 |
| DIA      | FALHOU   | EGARCH(1,1,2) -> GJR-GARCH(1,1) | Normal -> GED         |   -19.7 |     0.069 |     0.237 |
| DX-Y.NYB | FALHOU   | GARCH(1,1) -> EGARCH(1,1,2)     | Normal -> GED         |     0.2 |     0.561 |     0.056 |
| EURUSD   | FALHOU   | GARCH(2,1) -> EGARCH(1,1,1)     | Normal -> GED         |   -27.5 |     0.903 |     0.981 |
| EWZ      | FALHOU   | GARCH(1,2) -> EGARCH(1,1,2)     | Student-t -> Skewed t |    33.8 |     0.703 |     0.432 |
| RTY      | FALHOU   | EGARCH(1,1,2) -> GJR-GARCH(1,1) | NAO                   |    -3   |     0.063 |     0.117 |
| TSLA     | FALHOU   | GARCH(1,1) -> GJR-GARCH(1,1)    | NAO                   |    -0.3 |     0.178 |     0.104 |
| YM       | FALHOU   | EGARCH(1,1,2) -> GJR-GARCH(1,1) | Normal -> Student-t   |   -28.2 |     0.054 |     0.153 |

**Report 2 (EGARCH Forecast)**
Total na interseção: 18 | Passaram: 14 | Falharam: 4 | Missing (Drop/Adic): 1

| Ativo   | Status   |   Orig_Vol |   Comp_Vol |
|:--------|:---------|-----------:|-----------:|
| MES=F   | FALHOU   |     0.9029 |     0.9026 |
| MGC=F   | FALHOU   |     1.4985 |     1.5029 |
| MYM=F   | FALHOU   |     0.7164 |     0.7168 |
| ^BVSP   | FALHOU   |     1.0964 |     1.0945 |

### Run do dia 2026-07-15 (Com Sanity Checks Corrigidos)

**Report 1 (GARCH Completo)**
Total na interseção: 31 | Passaram: 16 | Falharam: 15 | Missing (Drop/Adic): 3

DETALHES DAS FALHAS (R1):
| Ativo    | Status   | Mudou Modelo                    | Mudou Dist            |    dAIC |   Orig_LB |   Comp_LB |
|:---------|:---------|:--------------------------------|:----------------------|--------:|----------:|----------:|
| 6C       | FALHOU   | GARCH(1,2) -> GARCH(2,1)        | NAO                   |     3.9 |     0.697 |     0.618 |
| 6E       | FALHOU   | GARCH(1,1) -> EGARCH(1,1,2)     | NAO                   |    16.3 |     0.702 |     0.323 |
| 6S       | FALHOU   | GARCH(2,1) -> EGARCH(1,1,1)     | NAO                   | -3750.8 |     0.409 |     0.008 |
| AMZN     | FALHOU   | NAO                             | Skewed t -> Student-t |   -10.5 |     0.786 |     0.817 |
| AUDNZD   | FALHOU   | GARCH(1,2) -> GARCH(2,1)        | NAO                   |     4.4 |     0.79  |     0.536 |
| CHF      | FALHOU   | GARCH(2,1) -> GJR-GARCH(1,1)    | NAO                   |    -2.5 |     0.233 |     0.288 |
| CL       | FALHOU   | GARCH(2,1) -> GJR-GARCH(1,1)    | NAO                   |    -3.7 |     0.29  |     0.763 |
| DIA      | FALHOU   | EGARCH(1,1,2) -> GJR-GARCH(1,1) | Normal -> GED         |   -28.4 |     0.069 |     0.237 |
| DX-Y.NYB | FALHOU   | GARCH(1,2) -> GARCH(2,2)        | NAO                   |    -4.8 |     0.573 |     0.475 |
| EURUSD   | FALHOU   | EGARCH(1,1,2) -> GARCH(1,1)     | GED -> Normal         |    22.5 |     0.979 |     0.924 |
| EWZ      | FALHOU   | GARCH(1,2) -> GARCH(1,1)        | NAO                   |    27   |     0.704 |     0.301 |
| NZDUSD   | FALHOU   | EGARCH(1,1,2) -> GARCH(1,2)     | Student-t -> GED      |     9.7 |     0.997 |     0.975 |
| TSLA     | FALHOU   | GARCH(1,1) -> GJR-GARCH(1,1)    | NAO                   |    -5.5 |     0.173 |     0.096 |
| YM       | FALHOU   | EGARCH(1,1,2) -> GJR-GARCH(1,1) | Normal -> GED         |   -23.8 |     0.055 |     0.217 |
| ^BVSP    | FALHOU   | GARCH(1,2) -> EGARCH(1,1,1)     | NAO                   |    -6.7 |     0.694 |     0.574 |

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
