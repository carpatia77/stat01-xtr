"""
render.py — formatação fixed-width dos dois reports.
Larguras e blocos estáticos calibrados byte a byte contra reports_originais/.
"""
from datetime import datetime

SEP1 = "=" * 260
SEP2 = "=" * 130

# ── Cabeçalho de colunas do Report 1 (copiado literalmente do original) ───────
HEADER_R1 = (
    "Ativo    Modelo               Distribuição     AIC        LB        "
    "Ω (Omega)         α (Alpha)       β (Beta)          γ (Gamma)          "
    "Status     Interpretação                                               "
)

# ── Blocos estáticos do Report 1 (copiados literalmente do original) ──────────
STATIC_R1_FOOTER = """\
NOVO: DISTRIBUIÇÕES TESTADAS AUTOMATICAMENTE
• Normal     → Padrão, mas raramente melhor em finanças
• Student-t  → Captura caudas pesadas → quase sempre melhora o AIC
• Skewed t   → + assimetria nos retornos → ótima para ações/tech
• GED        → Flexível para caudas muito pesadas

CRITÉRIOS DE SELEÇÃO DO MELHOR MODELO + DISTRIBUIÇÃO
• Primeiro: Ljung-Box p > 0.05 (resíduos sem estrutura)
• Depois: Menor AIC entre os válidos

INTERPRETAÇÃO DOS PARÂMETROS GREGOS
""" + SEP1 + """
Ω (Omega)   → Volatilidade de longo prazo
            • GARCH/GJR: sempre positivo
            • EGARCH: pode ser NEGATIVO → quedas aumentam vol mais que subidas
            • Ex: Ω = -0.645 → quedas geram PÂNICO de vol

α (Alpha)   → Impacto total de choques recentes (soma de todos os α[i])
            • α alto → volatilidade reage forte a eventos
            • Ex: α = 0.341 → 34.1% do choque entra na vol

β (Beta)    → Persistência total da volatilidade (soma de todos os β[i])
            • β próximo de 1 → vol dura MUITO tempo
            • Ex: β = 0.991 → vol dura ~30 dias
            • α + β ≈ 0.98 → vol de hoje explica 98% da vol amanhã

γ (Gamma)   → Assimetria (efeito alavancagem)
            • Presente em: EGARCH e GJR-GARCH
            • γ > 0 → más notícias aumentam vol mais que boas
            • γ = 0 → sem assimetria (GARCH)
            • Se γ ≠ 0 → use EGARCH ou GJR no EA!

DICAS PARA MT5:
• EGARCH: use log(vol) → exp() no MQL5
• GJR: use (retorno < 0) ? (alpha + gamma) : alpha
• Para GARCH(p,q): some todos os α[i] e β[i]
• Atualize todo dia com novos dados
""" + SEP1 + """

LEGENDA DAS INTERPRETAÇÕES AUTOMÁTICAS (v3.9.4)
""" + SEP1 + """
FOREX CLÁSSICO     → FOREX + GARCH + α<0.07 + β>0.90
VOL TÉCNICA        → FUTUROS + GARCH + α>0.08
ACAO MADURA        → AÇÃO + GARCH + α<0.07
ACAO VOLÁTIL       → AÇÃO + GARCH + α>0.15
QUEDAS EXPLODEM VOL! → EGARCH + Ω < -0.5
VOL DURA MUITO     → β > 0.98
TECH/PÂNICO        → EGARCH + Ω < -0.3
""" + SEP1


def render_report1(resultados: list[dict], analysis_ts: str | None = None) -> str:
    """
    resultados: lista de dicts com chaves:
      alias, modelo, dist, aic, lb, omega, alpha, beta, gamma, status, interpretacao
    """
    from config import START_DATE, END_DATE

    linhas = []
    ts = analysis_ts or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dias_corridos = (END_DATE - START_DATE).days
    dias_uteis = len(resultados[0]["_index"]) if resultados and "_index" in resultados[0] else None

    linhas.append("GARCH ANALYZER COMPLETO – MELHOR MODELO + DISTRIBUIÇÃO AUTOMÁTICA")
    linhas.append(f"Data da análise: {ts}")
    linhas.append(f"Período analisado: {START_DATE.isoformat()} → {END_DATE.isoformat()}")
    if dias_uteis is not None:
        anos = dias_corridos / 365.25
        linhas.append(
            f"Dias corridos: {dias_corridos} | Dias úteis: {dias_uteis} (≈ {anos:.2f} anos)"
        )
    linhas.append("")
    linhas.append("RESULTADOS DOS MODELOS VENCEDORES + INTERPRETAÇÃO AUTOMÁTICA")
    linhas.append(SEP1)
    linhas.append(HEADER_R1)
    linhas.append(SEP1)
    for r in resultados:
        # Ω: largura do campo cresce com o comprimento do valor (sinal negativo
        # "rouba" 1 espaço do campo LB anterior). Não afeta os números, só o
        # alinhamento visual — deixado como está (nunca desalinha os valores em
        # si, apenas desloca 1 espaço em linhas com Ω negativo).
        omega_field = f"{r['omega']:.12f}" + " " * 5
        linhas.append(
            f"{r['alias']:<9}{r['modelo']:<21}{r['dist']:<15}{r['aic']:<11.1f}"
            f"{r['lb']:<10.3f}{omega_field}{r['alpha']:<16.8f}"
            f"{r['beta']:<18.8f}{r['gamma']:<18.8f}"
            f"{r['status']:<13}{r['interpretacao']:<60}"
        )
    linhas.append(SEP1)
    linhas.append("")
    linhas.append(STATIC_R1_FOOTER)
    return "\n".join(linhas)


def render_report2(resultados: list[dict], run_date: str | None = None) -> str:
    """
    resultados: lista de dicts com chaves:
      ticker, close, vol_pct, minimo, maximo, status
    """
    linhas = []
    ts = run_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linhas.append("Análise EGARCH(1,1)-t para Ativos Selecionados")
    linhas.append(f"Data: {ts}")
    linhas.append("")
    linhas.append("Resultados do Modelo EGARCH-t")
    linhas.append(SEP2)
    linhas.append(
        f"{'Ativo':<11}{'Fechamento Anterior':^26}{'Volatilidade (%)':^20}"
        f"{'Mínimo Previsto':^26}{'Máximo Previsto':^20}  {'Status':<30}"
    )
    linhas.append(SEP2)
    for r in resultados:
        linhas.append(
            f"{r['ticker']:<11}{r['close']:^26.4f}{r['vol_pct']:^20.4f}"
            f"{r['minimo']:^26.4f}{r['maximo']:^20.4f}  {r['status']:<30}"
        )
    linhas.append(SEP2)
    return "\n".join(linhas)
