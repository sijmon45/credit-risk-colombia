# src/build_panel.py
from pathlib import Path

import pandas as pd
from extract_xbrl import extract_issuer_facts, build_panel

# Configura un emisor por entrada: nombre → carpeta de archivos XBRL
ISSUERS = {
    "ISA":        "Data/raw/ISA",
    "ISAGEN":     "Data/raw/ISAGEN",
    "EPM":        "Data/raw/EPM",
    "CELSIA":     "Data/raw/CELSIA",
    "ENEL":       "Data/raw/ENEL",
}

def main():
    all_records = []

    for issuer, folder in ISSUERS.items():
        if not Path(folder).exists():
            print(f"Omitiendo {issuer}: carpeta no encontrada")
            continue
        print(f"Extrayendo {issuer}...")
        records = extract_issuer_facts(folder, issuer)
        if records.empty:
            print(f"  → sin archivos XBRL válidos; se omite")
            continue
        print(f"  → {len(records)} periodos encontrados")
        expected_variables = {
            "ingresos", "gastos_financieros", "resultado_operativo",
            "d_and_a", "caja", "deuda_cp", "deuda_lp",
        }
        available = records.groupby(["emisor", "periodo"])["variable"].agg(set)
        missing = {
            f"{issuer} {period}: {sorted(expected_variables - variables)}"
            for (issuer_name, period), variables in available.items()
            if (expected_variables - variables)
        }
        if missing:
            print("  → faltantes (se conservarán como NaN):")
            for item in sorted(missing):
                print(f"     {item}")
        all_records.append(records)

    panel = build_panel(pd.concat(all_records, ignore_index=True))

    # Reporte rápido de calidad
    print("\n--- Resumen del panel ---")
    print(panel.groupby("emisor")["periodo"].agg(["count", "min", "max"]))
    print("\n--- NaNs por columna ---")
    print(panel.isnull().sum())

    # Guarda
    panel.to_csv("Data/processed/panel_consolidado.csv", index=False)
    print("\nGuardado en Data/processed/panel_consolidado.csv")

if __name__ == "__main__":
    main()