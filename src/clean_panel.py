"""Aplica ajustes de unidades e imputaciones al panel consolidado."""

import pandas as pd


def clean_panel(path_in: str, path_out: str) -> pd.DataFrame:
    """Limpia el panel y guarda una copia lista para el analisis.

    Los ajustes conservan la logica historica del proyecto: ISAGEN se escala
    a miles de COP, EPM completa EBITDA faltante con su media reciente y ENEL
    completa EBITDA usando su margen observado.
    """

    df = pd.read_csv(path_in)
    numeric_columns = [
        "ebitda",
        "deuda_cp",
        "deuda_lp",
        "gastos_financieros",
        "caja",
        "ingresos",
    ]

    # ISAGEN reporta estas magnitudes en unidades distintas al resto del panel.
    df.loc[df["emisor"] == "ISAGEN", numeric_columns] /= 1000

    # Completa EBITDA faltante de EPM con la media de sus cuatro datos previos.
    epm_hist = df[(df["emisor"] == "EPM") & (df["ebitda"].notna())]
    epm_mean_ebitda = epm_hist.tail(4)["ebitda"].mean()
    df.loc[(df["emisor"] == "EPM") & (df["ebitda"].isna()), "ebitda"] = epm_mean_ebitda

    # Completa EBITDA faltante de ENEL con su margen EBITDA medio observado.
    enel_mask = df["emisor"] == "ENEL"
    enel = df[enel_mask].copy()

    enel_obs = enel[enel["ebitda"].notna()]
    enel_margen = (enel_obs["ebitda"] / enel_obs["ingresos"]).mean()

    print(f"Margen EBITDA propio de ENEL ({len(enel_obs)} periodos observados): {enel_margen:.2%}")

    # Marca unicamente los valores de EBITDA que se completan en esta etapa.
    df.loc[enel_mask, "ebitda_imputado"] = df.loc[enel_mask, "ebitda"].isna()
    df.loc[enel_mask & df["ebitda"].isna(), "ebitda"] = (
        df.loc[enel_mask & df["ebitda"].isna(), "ingresos"] * enel_margen
    )

    # Para los demas emisores, no se ha aplicado imputacion en esta etapa.
    df["ebitda_imputado"] = df["ebitda_imputado"].fillna(False)
    df.to_csv(path_out, index=False)
    print(f"Panel limpio guardado en: {path_out}")
    return df

if __name__ == "__main__":
    clean_panel(
        "Data/processed/panel_consolidado.csv",
        "Data/processed/panel_limpio.csv"
    )