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


def diff_report(generated: str, ref_path: Path) -> list[str]:
    if not ref_path.exists():
        return [f"AVISO: arquivo de referência não encontrado: {ref_path}"]
    ref_text = ref_path.read_text(encoding="utf-8")
    gen_lines = _strip(generated)
    ref_lines = _strip(ref_text)
    diffs = []
    for i, (g, r) in enumerate(zip(gen_lines, ref_lines), 1):
        if g != r:
            diffs.append(f"  Linha {i:4d}:")
            diffs.append(f"    GERADO : {repr(g)}")
            diffs.append(f"    REF    : {repr(r)}")
    if len(gen_lines) != len(ref_lines):
        diffs.append(
            f"  AVISO: gerado={len(gen_lines)} linhas, ref={len(ref_lines)} linhas"
        )
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
