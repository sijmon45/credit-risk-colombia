import pandas as pd
import numpy as np

def clean_panel(path_in: str, path_out: str) -> pd.DataFrame:
    df = pd.read_csv(path_in)
    num_cols = ["ebitda", "deuda_cp", "deuda_lp",
                "gastos_financieros", "caja", "ingresos"]

    # --- Fix 1: normalizar unidades de ISAGEN a miles COP ---
    df.loc[df["emisor"] == "ISAGEN", num_cols] /= 1000

    # --- Fix 2: imputar EPM 2026Q1-Q2 con promedio últimos 4 trimestres ---
    epm_hist = df[(df["emisor"] == "EPM") & (df["ebitda"].notna())]
    epm_mean_ebitda = epm_hist.tail(4)["ebitda"].mean()
    df.loc[(df["emisor"] == "EPM") & (df["ebitda"].isna()), "ebitda"] = epm_mean_ebitda

    # --- Fix 3: imputar EBITDA faltante de ENEL con su propio margen ---
    enel_mask = df["emisor"] == "ENEL"
    enel = df[enel_mask].copy()

    # Margen de los periodos con dato real
    enel_obs = enel[enel["ebitda"].notna()]
    enel_margen = (enel_obs["ebitda"] / enel_obs["ingresos"]).mean()

    print(f"Margen EBITDA propio de ENEL ({len(enel_obs)} periodos observados): {enel_margen:.2%}")

    # Imputar solo donde falta
    df.loc[enel_mask, "ebitda_imputado"] = df.loc[enel_mask, "ebitda"].isna()
    df.loc[enel_mask & df["ebitda"].isna(), "ebitda"] = (
        df.loc[enel_mask & df["ebitda"].isna(), "ingresos"] * enel_margen
    )

    # Para los demás emisores, ebitda_imputado = False
    df["ebitda_imputado"] = df["ebitda_imputado"].fillna(False)
    df.to_csv(path_out, index=False)
    print(f"Panel limpio guardado en: {path_out}")
    return df

if __name__ == "__main__":
    clean_panel(
        "Data/processed/panel_consolidado.csv",
        "Data/processed/panel_limpio.csv"
    )