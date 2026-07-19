"""
validate.py — Teste de regressão: gera os dois reports e faz diff contra
reports_originais/, ignorando linhas de data/hora.

Uso:
    python validate.py [--phase 1|2]

Fase 1: valida apenas o Report 2 (EGARCH forecast, mais rápido)
Fase 2: valida o Report 1 completo (GARCH grade — demorado)
"""
import argparse
import re
from pathlib import Path

REF_DIR = Path("reports_originais")

# Padrão de linhas a ignorar no diff (datas, timestamps)
IGNORE_PATTERN = re.compile(
    r"Data:|\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}|GARCH ANALYZER.*v\d"
)


def _strip(text: str) -> list[str]:
    """Remove linhas de data/hora para comparação estável."""
    return [ln for ln in text.splitlines() if not IGNORE_PATTERN.search(ln)]


# Linha de dado = começa com token não-vazio e tem colunas suficientes.
# Ignora separadores (===), bullets (•) e blocos de texto estático.
_DATA_ROW = re.compile(r"^\S+\s+\S.*\s+(EXCELENTE|BOM|RUIM|Sucesso|Erro)")


def _index_by_key(lines: list[str]) -> dict[str, str]:
    """Indexa linhas de dado pelo 1º token (ativo/ticker)."""
    d = {}
    for ln in lines:
        if _DATA_ROW.search(ln):
            d[ln.split()[0]] = ln
    return d


def diff_report(generated: str, ref_path: Path) -> list[str]:
    """
    Compara chaveando por ativo (robusto a linhas faltando/reordenadas), em vez
    de zip() posicional — uma linha ausente não cascateia para todas as
    seguintes. Reporta ativos só-no-ref, só-no-gerado e valores divergentes.
    """
    if not ref_path.exists():
        return [f"AVISO: arquivo de referência não encontrado: {ref_path}"]
    ref_text = ref_path.read_text(encoding="utf-8")
    gen = _index_by_key(_strip(generated))
    ref = _index_by_key(_strip(ref_text))

    diffs = []
    faltando = sorted(set(ref) - set(gen))
    sobrando = sorted(set(gen) - set(ref))
    if faltando:
        diffs.append(f"  AUSENTES no gerado ({len(faltando)}): {', '.join(faltando)}")
    if sobrando:
        diffs.append(f"  EXTRAS no gerado ({len(sobrando)}): {', '.join(sobrando)}")

    for key in ref:
        if key in gen and gen[key] != ref[key]:
            diffs.append(f"  [{key}]")
            diffs.append(f"    GERADO : {gen[key]!r}")
            diffs.append(f"    REF    : {ref[key]!r}")
    return diffs


def validate_report2():
    print("\n=== FASE 1: Report 2 (EGARCH forecast) ===")
    from egarch_forecast import run
    generated = run()
    diffs = diff_report(
        generated,
        REF_DIR / "EGARCHTSTUDENT1.1t_20260717_ORIGINAL.txt",
    )
    if diffs:
        print(f"DIVERGÊNCIAS ({len(diffs)} linhas diferentes):")
        print("\n".join(diffs))
    else:
        print("OK — Report 2 idêntico ao original (exceto data/hora).")
    return not diffs


def validate_report1():
    print("\n=== FASE 2: Report 1 (GARCH Analyzer) ===")
    from garch_analyzer import run
    generated = run()
    diffs = diff_report(
        generated,
        REF_DIR / "ANALISE_GARCH_COMPLETO_ORIGINAL.txt",
    )
    if diffs:
        print(f"DIVERGÊNCIAS ({len(diffs)} linhas diferentes):")
        print("\n".join(diffs))
    else:
        print("OK — Report 1 idêntico ao original (exceto data/hora).")
    return not diffs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validação por regressão")
    parser.add_argument("--phase", type=int, choices=[1, 2], default=1,
                        help="1 = Report 2 (rápido), 2 = Report 1 (demorado)")
    args = parser.parse_args()
    if args.phase == 1:
        validate_report2()
    else:
        validate_report1()
