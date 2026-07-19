"""
interpretacao.py — regras de interpretação automática (seção 1.7 do plano)
"""


def interpretar(vol_type: str, omega: float, alpha: float, beta: float,
                classe: str, dist: str) -> str:
    """
    Gera a string de interpretação no formato:
      [tag Ω] | [tag β] | [tag α] | [tag classe/pânico] | [tag caudas]
    Tags vazias são omitidas; separador ' | ' entre as presentes.
    Se a lista final ficar vazia → 'Estável'.
    """
    tags = []

    # ── Efeito de alavancagem (apenas EGARCH, usa omega direto = log-vol) ──────
    if vol_type.upper() == "EGARCH":
        if omega < -0.5:
            tags.append("QUEDAS EXPLODEM VOL!")
        elif -0.5 <= omega < -0.2:
            tags.append("Quedas aumentam vol")
        elif -0.2 <= omega < 0:
            tags.append("Leve alavancagem")

    # ── Persistência ──────────────────────────────────────────────────────────
    if beta > 0.98:
        tags.append("VOL DURA MUITO (CRISES)")
    elif 0.95 < beta <= 0.98:
        tags.append("Vol persistente")

    # ── Choques ───────────────────────────────────────────────────────────────
    if alpha > 0.2:
        tags.append("REAÇÃO FORTE A NOTÍCIAS")
    elif 0.1 <= alpha <= 0.2:
        tags.append("Choques moderados")

    # ── Classe do ativo / pânico ───────────────────────────────────────────────
    vt = vol_type.upper()
    if vt == "EGARCH" and omega < -0.3:
        tags.append("TECH/PÂNICO")
    elif classe == "FOREX" and vt == "GARCH" and alpha < 0.07 and beta > 0.90:
        tags.append("FOREX CLÁSSICO")
    elif classe == "FUTUROS" and vt == "GARCH" and alpha > 0.08:
        tags.append("VOL TÉCNICA")
    elif classe == "AÇÃO" and vt == "GARCH" and alpha < 0.07:
        tags.append("ACAO MADURA")
    elif classe == "AÇÃO" and vt == "GARCH" and alpha > 0.15:
        tags.append("ACAO VOLÁTIL")

    # ── Caudas ────────────────────────────────────────────────────────────────
    CAUDA = {
        "t":     "CAUDAS PESADAS (leptocurtose)",
        "skewt": "CAUDAS PESADAS + ASSIMETRIA",
        "ged":   "CAUDAS EXTREMAS",
        "normal": "",
    }
    c = CAUDA.get(dist, "")
    if c:
        tags.append(c)

    return " | ".join(tags) if tags else "Estável"
