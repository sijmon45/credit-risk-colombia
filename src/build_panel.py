"""Construye el panel consolidado a partir de los archivos XBRL por emisor."""

from pathlib import Path

import pandas as pd

from extract_xbrl import build_panel, extract_issuer_facts

# Cada entrada relaciona el nombre del emisor con su carpeta de archivos XBRL.
ISSUERS = {
    "ISA": "Data/raw/ISA",
    "ISAGEN": "Data/raw/ISAGEN",
    "EPM": "Data/raw/EPM",
    "CELSIA": "Data/raw/CELSIA",
    "ENEL": "Data/raw/ENEL",
}


def main() -> None:
    """Extrae los emisores disponibles y guarda el panel consolidado."""

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
            "ingresos",
            "gastos_financieros",
            "resultado_operativo",
            "d_and_a",
            "caja",
            "deuda_cp",
            "deuda_lp",
        }
        available = records.groupby(["emisor", "periodo"])["variable"].agg(set)
        missing = {
            f"{issuer} {period}: {sorted(expected_variables - variables)}"
            for (_, period), variables in available.items()
            if (expected_variables - variables)
        }
        if missing:
            print("  → faltantes (se conservarán como NaN):")
            for item in sorted(missing):
                print(f"     {item}")
        all_records.append(records)

    panel = build_panel(pd.concat(all_records, ignore_index=True))

    # Reporte rapido de calidad del panel construido.
    print("\n--- Resumen del panel ---")
    print(panel.groupby("emisor")["periodo"].agg(["count", "min", "max"]))
    print("\n--- NaNs por columna ---")
    print(panel.isnull().sum())

    # Guarda el resultado en la ruta usada por las etapas posteriores.
    panel.to_csv("Data/processed/panel_consolidado.csv", index=False)
    print("\nGuardado en Data/processed/panel_consolidado.csv")

if __name__ == "__main__":
    main()