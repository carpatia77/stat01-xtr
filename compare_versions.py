import os
import shutil
import subprocess
import re
import pandas as pd
from pathlib import Path
from glob import glob

def parse_garch_report(filepath: str) -> dict:
    """Parse o relatório ANALISE_GARCH_COMPLETO em dict estruturado."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    results = {}
    pattern = r'^(\S+)\s+(GARCH\([^)]+\)|EGARCH\([^)]+\)|GJR-GARCH\([^)]+\))\s+([\w\s-]+?)\s+(-?\d+\.?\d*)\s+(\d+\.?\d*)\s+(-?\d+\.?\d+(?:e[+-]?\d+)?)\s+(-?\d+\.?\d+)\s+(-?\d+\.?\d+)\s+(-?\d+\.?\d+)\s+(EXCELENTE|BOM|RUIM)\s+(.*?)$'
    for line in content.split('\n'):
        line = line.strip()
        match = re.match(pattern, line)
        if match:
            asset = match.group(1)
            results[asset] = {
                'model': match.group(2),
                'distribution': match.group(3).strip(),
                'aic': float(match.group(4)),
                'lb': float(match.group(5)),
                'omega': float(match.group(6)),
                'alpha': float(match.group(7)),
                'beta': float(match.group(8)),
                'gamma': float(match.group(9)),
                'status': match.group(10),
            }
    return results

def parse_forecast_report(filepath: str) -> dict:
    """Parse o relatório EGARCH-TSTUDENT diário."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    results = {}
    pattern = r'^(\S+)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\w+)$'
    for line in content.split('\n'):
        line = line.strip()
        match = re.match(pattern, line)
        if match:
            asset = match.group(1)
            results[asset] = {
                'close': float(match.group(2)),
                'vol_pct': float(match.group(3)),
                'min_95': float(match.group(4)),
                'max_95': float(match.group(5)),
                'status': match.group(6),
            }
    return results

def compare_r1(original: dict, computed: dict) -> pd.DataFrame:
    tolerances = {'aic': 0.03, 'omega': 0.20, 'alpha': 0.10, 'beta': 0.05, 'gamma': 0.25}
    rows = []
    all_assets = set(original.keys()) | set(computed.keys())
    for asset in sorted(all_assets):
        if asset not in original or asset not in computed:
            rows.append({'Ativo': asset, 'Status': 'FALTANDO NO OUTRO', 'Mudou Modelo': '-', 'Mudou Dist': '-', 'dAIC': '-'})
            continue
        orig, comp = original[asset], computed[asset]
        row = {'Ativo': asset}
        model_match = orig['model'] == comp['model']
        dist_match = orig['distribution'] == comp['distribution']
        aic_diff = comp['aic'] - orig['aic']
        aic_err = abs(aic_diff) / abs(orig['aic']) if orig['aic'] != 0 else 0
        lb_match = (orig['lb'] > 0.05) == (comp['lb'] > 0.05)
        
        all_ok = all([model_match, dist_match, aic_err < tolerances['aic'], lb_match])
        row['Status'] = 'PASSOU' if all_ok else 'FALHOU'
        row['Mudou Modelo'] = 'NAO' if model_match else f"{orig['model']} -> {comp['model']}"
        row['Mudou Dist'] = 'NAO' if dist_match else f"{orig['distribution']} -> {comp['distribution']}"
        row['dAIC'] = round(aic_diff, 2)
        row['Orig_LB'] = orig['lb']
        row['Comp_LB'] = comp['lb']
        rows.append(row)
    return pd.DataFrame(rows)

def compare_r2(original: dict, computed: dict) -> pd.DataFrame:
    rows = []
    all_assets = set(original.keys()) | set(computed.keys())
    for asset in sorted(all_assets):
        if asset not in original or asset not in computed:
            rows.append({'Ativo': asset, 'Status': 'FALTANDO NO OUTRO'})
            continue
        orig, comp = original[asset], computed[asset]
        row = {'Ativo': asset}
        vol_err = abs(comp['vol_pct'] - orig['vol_pct'])
        min_err = abs(comp['min_95'] - orig['min_95'])
        max_err = abs(comp['max_95'] - orig['max_95'])
        
        # Tolerância apertada para predição
        all_ok = (vol_err < 0.05) and (min_err < 0.05) and (max_err < 0.05)
        row['Status'] = 'PASSOU' if all_ok else 'FALHOU'
        row['Orig_Vol'] = orig['vol_pct']
        row['Comp_Vol'] = comp['vol_pct']
        rows.append(row)
    return pd.DataFrame(rows)

def main():
    dates = ["2026-07-14", "2026-07-15"]
    orig_dir = Path("C:/Users/aidea/Documents")
    
    for dt in dates:
        print(f"\n{'='*80}\nPROCESSANDO DATA: {dt}\n{'='*80}")
        
        # Limpar cache
        if os.path.exists("cache"):
            shutil.rmtree("cache")
            print("[✓] Cache apagado para forçar janela histórica exata")
        
        # Rodar R1
        import sys
        print("[ ] Rodando garch_analyzer.py...")
        env = os.environ.copy()
        env["GARCH_REPORT_DATE"] = dt
        subprocess.run([sys.executable, "garch_analyzer.py", "--save"], env=env, check=True)
        
        # Rodar R2
        print("[ ] Rodando egarch_forecast.py...")
        subprocess.run([sys.executable, "egarch_forecast.py", "--save"], env=env, check=True)
        
        # Comparar R1
        orig_r1 = orig_dir / f"ANALISE_GARCH_COMPLETO_{dt}.txt"
        comp_r1 = Path(f"ANALISE_GARCH_COMPLETO_{dt}.txt")
        if orig_r1.exists() and comp_r1.exists():
            df1 = compare_r1(parse_garch_report(str(orig_r1)), parse_garch_report(str(comp_r1)))
            pass_r1 = (df1['Status'] == 'PASSOU').sum()
            fail_r1 = (df1['Status'] == 'FALHOU').sum()
            missing_r1 = (df1['Status'] == 'FALTANDO NO OUTRO').sum()
            print(f"\n[REPORT 1 - {dt}]")
            print(f"Total na interseção: {len(df1) - missing_r1} | Passaram: {pass_r1} | Falharam: {fail_r1} | Missing (Drop/Adic): {missing_r1}")
            if fail_r1 > 0:
                print("\nDETALHES DAS FALHAS (R1):")
                print(df1[df1['Status'] == 'FALHOU'].to_markdown(index=False))
        
        # Comparar R2
        # Tentar achar o arquivo R2 original que tem "_082239" no final, por exemplo: EGARCH-TSTUDENT(1.1)-t_2026-07-14_082239.txt
        orig_r2_matches = glob(str(orig_dir / f"EGARCH-TSTUDENT(1.1)-t_{dt}*.txt"))
        comp_r2 = Path(f"EGARCH-TSTUDENT(1.1)-t_{dt}.txt")
        if orig_r2_matches and comp_r2.exists():
            orig_r2 = orig_r2_matches[0]
            df2 = compare_r2(parse_forecast_report(orig_r2), parse_forecast_report(str(comp_r2)))
            pass_r2 = (df2['Status'] == 'PASSOU').sum()
            fail_r2 = (df2['Status'] == 'FALHOU').sum()
            missing_r2 = (df2['Status'] == 'FALTANDO NO OUTRO').sum()
            print(f"\n[REPORT 2 - {dt}]")
            print(f"Total na interseção: {len(df2) - missing_r2} | Passaram: {pass_r2} | Falharam: {fail_r2} | Missing (Drop/Adic): {missing_r2}")
            if fail_r2 > 0:
                print("\nDETALHES DAS FALHAS (R2):")
                print(df2[df2['Status'] == 'FALHOU'].to_markdown(index=False))

if __name__ == "__main__":
    main()
