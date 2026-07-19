"""
render.py — formatação fixed-width dos dois reports.
Calibre larguras de coluna contra reports_originais/ se necessário.
"""
from datetime import datetime

SEP1 = "=" * 228
SEP2 = "=" * 130

# ── Blocos estáticos do Report 1 (copiar do arquivo de referência se divergir) ─
STATIC_R1_HEADER = """\
NOVO: DISTRIBUIÇÕES ESTATÍSTICAS
  • Normal: distribuição gaussiana padrão
  • Student-t: caudas pesadas (leptocurtose)
  • Skewed t: caudas pesadas + assimetria
  • GED: General Error Distribution (caudas extremas)

CRITÉRIOS DE SELEÇÃO:
  1. Ljung-Box p > 0.05 (resíduos sem autocorrelação)
  2. Menor AIC entre os válidos

INTERPRETAÇÃO DOS PARÂMETROS GREGOS:
  Ω (Omega): nível base de volatilidade
  α (Alpha): soma dos coeficientes alpha — sensibilidade a choques recentes
  β (Beta):  soma dos coeficientes beta  — persistência de volatilidade
  γ (Gamma): soma dos coeficientes gamma — efeito assimétrico (GJR/EGARCH)

DICAS PARA MT5:
  • Exportar parâmetros para EA no MetaTrader 5
  • Usar volatilidade prevista para sizing dinâmico
  • EGARCH capta alavancagem (quedas aumentam vol mais que altas)

LEGENDA (v3.9.4):
  LB  = p-value Ljung-Box (lag 10) sobre resíduos padronizados
  AIC = Akaike Information Criterion (menor = melhor)
"""


def render_report1(resultados: list[dict]) -> str:
    """
    resultados: lista de dicts com chaves:
      alias, modelo, dist, aic, lb, omega, alpha, beta, gamma, status, interpretacao
    """
    linhas = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linhas.append(f"GARCH ANALYZER COMPLETO v3.9.4 — {ts}")
    linhas.append(SEP1)
    # cabeçalho de colunas
    linhas.append(
        f"{'Ativo':<9}{'Modelo':<21}{'Distribuição':<15}{'AIC':<11}{'LB':<10}"
        f"{'Ω (Omega)':<19}{'α (Alpha)':<16}{'β (Beta)':<18}{'γ (Gamma)':<18}"
        f"{'Status':<13}{'Interpretação':<60}"
    )
    linhas.append(SEP1)
    for r in resultados:
        linhas.append(
            f"{r['alias']:<9}{r['modelo']:<21}{r['dist']:<15}{r['aic']:<11.1f}"
            f"{r['lb']:<10.3f}{r['omega']:<19.12f}{r['alpha']:<16.8f}"
            f"{r['beta']:<18.8f}{r['gamma']:<18.8f}"
            f"{r['status']:<13}{r['interpretacao']:<60}"
        )
    linhas.append(SEP1)
    linhas.append(STATIC_R1_HEADER)
    return "\n".join(linhas)


def render_report2(resultados: list[dict], run_date: str | None = None) -> str:
    """
    resultados: lista de dicts com chaves:
      ticker, close, vol_pct, minimo, maximo, status
    """
    linhas = []
    ts = run_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linhas.append(f"Análise EGARCH(1,1)-t para Ativos Selecionados")
    linhas.append(f"Data: {ts}")
    linhas.append(SEP2)
    # cabeçalho de colunas
    linhas.append(
        f"{'Ativo':<14}{'Fechamento Anterior':^19}{'Volatilidade (%)':^23}"
        f"{'Mínimo Esperado':^23}{'Máximo Esperado':^20}   {'Status':<30}"
    )
    linhas.append(
        f"{'':14}{'':19}{'':23}{'(95% IC)':^23}{'(95% IC)':^20}   {'':30}"
    )
    linhas.append(SEP2)
    for r in resultados:
        linhas.append(
            f"{r['ticker']:<14}{r['close']:^19.4f}{r['vol_pct']:^23.4f}"
            f"{r['minimo']:^23.4f}{r['maximo']:^20.4f}   {r['status']:<30}"
        )
    linhas.append(SEP2)
    linhas.append("Resultados do Modelo EGARCH-t")
    return "\n".join(linhas)
