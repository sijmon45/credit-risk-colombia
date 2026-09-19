"""Extraccion reproducible de variables financieras desde XBRL de ISA.

La seleccion se basa en los contextos validados en la exploracion:
- flujos: fact consolidado sin dimensiones, acumulado desde el 1 de enero;
- stocks: fact consolidado sin dimensiones, instantaneo al cierre del trimestre.

Este modulo no calcula ratios ni modelos de riesgo.
"""

from __future__ import annotations

import collections
import collections.abc
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


# Arelle versions used by some XBRL files still import these names from collections.
for _name in (
    "MutableSet",
    "MutableMapping",
    "Mapping",
    "Sequence",
    "Callable",
    "Iterable",
    "Container",
    "Hashable",
    "Sized",
    "Set",
    "MutableSequence",
):
    if not hasattr(collections, _name) and hasattr(collections.abc, _name):
        setattr(collections, _name, getattr(collections.abc, _name))

from arelle import Cntlr


FLOW_TAGS = {
    "ifrs:Revenue": "ingresos",
    "ifrs:FinanceCosts": "gastos_financieros",
    "ifrs:InterestExpenseOnBorrowings": "intereses_deuda",
    "ifrs:ProfitLossFromOperatingActivities": "resultado_operativo",
    "ifrs:DepreciationExpense": "depreciacion",
    "ifrs:AmortisationExpense": "amortizacion",
    "ifrs:DepreciationAndAmortisationExpense": "d_and_a",
}

STOCK_TAGS = {
    "ifrs:CashAndCashEquivalents": "caja",
    "ifrs:ShorttermBorrowings": "deuda_cp",
    "ifrs:LongtermBorrowings": "deuda_lp",
    "ifrs:Borrowings": "deuda_total",
}

TAG_ALIASES = {
    "ifrs:CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings": "deuda_cp",
    "co-sfc-core:ObligacionesFinancierasCorrientes": "deuda_cp",
    "co-sfc-core:ObligacionesFinancierasNoCorrientes": "deuda_lp",
}

PREFERRED_TAGS = {
    "deuda_cp": "co-sfc-core:ObligacionesFinancierasCorrientes",
    "deuda_lp": "ifrs:LongtermBorrowings",
}

TAG_TO_VARIABLE = {**FLOW_TAGS, **STOCK_TAGS, **TAG_ALIASES}
ALL_TAGS = set(TAG_TO_VARIABLE)

_FLOW_CONTEXT = "TrimestreAcumuladoActual"
_STOCK_CONTEXT = "CierreTrimestreActual"
_PERIOD_PATTERN = re.compile(r"^(?P<year>\d{4})Q(?P<quarter>[1-4])_")
_DATE_PATTERN = re.compile(r"_(?P<date>\d{4}-\d{2}-\d{2})\.xbrl$")


def _context_dimensions(context: Any) -> str:
    return "; ".join(
        f"{dimension}={dimension_value.memberQname}"
        for dimension, dimension_value in context.qnameDims.items()
    )


def _period_from_path(path: Path) -> str:
    match = _PERIOD_PATTERN.match(path.name)
    if match is None:
        raise ValueError(
            f"Nombre de archivo no compatible: {path.name}. "
            "Se esperaba, por ejemplo, 2021Q1_2021-03-31.xbrl."
        )
    return f"{match.group('year')}Q{match.group('quarter')}"


def _is_valid_period_path(path: Path) -> bool:
    try:
        _period_from_path(path)
    except ValueError:
        return False
    return True


def _expected_end_date(path: Path) -> datetime:
    match = _DATE_PATTERN.search(path.name)
    if match is None:
        raise ValueError(
            f"Nombre de archivo sin fecha de cierre: {path.name}."
        )
    reported_date = datetime.strptime(match.group("date"), "%Y-%m-%d")
    return reported_date + timedelta(days=1)


def _fact_row(
    fact: Any,
    period: str,
    source_file: Path,
    issuer: str,
) -> dict[str, Any]:
    context = fact.context
    return {
        "emisor": issuer,
        "periodo": period,
        "tag": str(fact.concept.qname),
        "variable": TAG_TO_VARIABLE[str(fact.concept.qname)],
        "valor_ytd_o_stock": float(fact.value),
        "unitID": fact.unitID,
        "contextID": fact.contextID,
        "startDate": context.startDatetime,
        "endDate": context.endDatetime,
        "isInstant": context.isInstantPeriod,
        "dimensiones": _context_dimensions(context) or "sin dimensiones",
        "source_file": source_file.name,
    }


def extract_selected_facts(
    file_path: str | Path,
    controller: Any | None = None,
    issuer: str = "ISA",
    strict: bool = True,
) -> pd.DataFrame:
    """Extrae un fact consolidado seleccionable por tag desde un archivo.

    Los facts dimensionales se excluyen. Para flujos se requiere un contexto
    de duracion que empiece el 1 de enero; para stocks, un contexto instantaneo
    con ``CierreTrimestreActual``.
    """

    path = Path(file_path)
    own_controller = controller is None
    active_controller: Any = controller if controller is not None else Cntlr.Cntlr()
    model = active_controller.modelManager.load(str(path))
    period = _period_from_path(path)
    expected_end_date = _expected_end_date(path)
    rows: list[dict[str, Any]] = []

    try:
        for fact in model.facts:
            if fact.concept is None:
                continue
            tag = str(fact.concept.qname)
            if tag not in ALL_TAGS:
                continue

            context = fact.context
            if _context_dimensions(context):
                continue

            if tag in FLOW_TAGS:
                is_selected = (
                    not context.isInstantPeriod
                    and context.startDatetime is not None
                    and context.startDatetime.month == 1
                    and context.startDatetime.day == 1
                    and context.endDatetime == expected_end_date
                )
            else:
                is_selected = (
                    context.isInstantPeriod
                    and context.endDatetime == expected_end_date
                )

            if is_selected:
                rows.append(_fact_row(fact, period, path, issuer))
    finally:
        active_controller.modelManager.close(model)
        if own_controller:
            active_controller.close()

    facts = pd.DataFrame(rows)
    if facts.empty:
        raise ValueError(f"No se encontraron facts seleccionables en {path.name}.")

    duplicate_keys = [
        "tag",
        "contextID",
        "unitID",
        "startDate",
        "endDate",
    ]
    deduplicated_rows = []
    for _, duplicate_group in facts.groupby(duplicate_keys, dropna=False, sort=False):
        if len(duplicate_group) == 1:
            deduplicated_rows.append(duplicate_group.iloc[0])
            continue

        non_zero = duplicate_group[duplicate_group["valor_ytd_o_stock"] != 0]
        if len(non_zero) == 1:
            deduplicated_rows.append(non_zero.iloc[0])
        elif duplicate_group["valor_ytd_o_stock"].nunique() == 1:
            deduplicated_rows.append(duplicate_group.iloc[0])
        else:
            raise ValueError(
                f"Facts duplicados ambiguos en {path.name}: "
                f"tag={duplicate_group.iloc[0]['tag']}, "
                f"contextID={duplicate_group.iloc[0]['contextID']}, "
                f"valores={duplicate_group['valor_ytd_o_stock'].tolist()}"
            )

    facts = pd.DataFrame(deduplicated_rows)

    for variable, preferred_tag in PREFERRED_TAGS.items():
        variable_facts = facts[facts["variable"] == variable]
        if preferred_tag in set(variable_facts["tag"]):
            facts = facts[
                (facts["variable"] != variable)
                | (facts["tag"] == preferred_tag)
            ]

    if "d_and_a" not in set(facts["variable"]):
        components = facts[facts["variable"].isin(["depreciacion", "amortizacion"])]
        if set(components["variable"]) == {"depreciacion", "amortizacion"}:
            depreciation = components[components["variable"] == "depreciacion"]
            amortisation = components[components["variable"] == "amortizacion"]
            if len(depreciation) == 1 and len(amortisation) == 1:
                derived = depreciation.iloc[0].copy()
                derived["tag"] = "derived:DepreciationAndAmortisationExpense"
                derived["variable"] = "d_and_a"
                derived["valor_ytd_o_stock"] = (
                    depreciation.iloc[0]["valor_ytd_o_stock"]
                    + amortisation.iloc[0]["valor_ytd_o_stock"]
                )
                facts = pd.concat([facts, pd.DataFrame([derived])], ignore_index=True)

    counts = facts.groupby("variable").size()
    required_variables = (
        set(FLOW_TAGS.values())
        | {"caja", "deuda_cp", "deuda_lp"}
    )
    missing = sorted(required_variables - set(counts.index))
    duplicated = sorted(counts[counts != 1].index.tolist())
    if strict and (missing or duplicated):
        raise ValueError(
            f"Seleccion invalida en {path.name}: missing={missing}, duplicated={duplicated}."
        )

    return facts.sort_values("tag").reset_index(drop=True)


def extract_isa_facts(
    data_dir: str | Path,
    pattern: str = "*Q[1-4]_*.xbrl",
) -> pd.DataFrame:
    """Extrae los facts seleccionados de todos los archivos ISA del directorio."""

    paths = [
        path
        for path in sorted(Path(data_dir).glob(pattern))
        if _is_valid_period_path(path)
    ]
    if not paths:
        raise FileNotFoundError(f"No hay archivos XBRL en {Path(data_dir)} con {pattern}.")

    controller = Cntlr.Cntlr()
    try:
        frames = [extract_selected_facts(path, controller) for path in paths]
    finally:
        controller.close()

    return pd.concat(frames, ignore_index=True).sort_values(
        ["periodo", "tag"]
    ).reset_index(drop=True)


def extract_issuer_facts(
    data_dir: str | Path,
    issuer: str,
    pattern: str = "*.xbrl",
    strict: bool = False,
) -> pd.DataFrame:
    """Extrae los facts seleccionados de un emisor con la configuracion comun."""

    paths = [
        path
        for path in sorted(Path(data_dir).glob(pattern))
        if _is_valid_period_path(path)
    ]
    if not paths:
        return pd.DataFrame()

    controller = Cntlr.Cntlr()
    try:
        frames = [
            extract_selected_facts(path, controller, issuer, strict=strict)
            for path in paths
        ]
    finally:
        controller.close()

    return pd.concat(frames, ignore_index=True).sort_values(
        ["periodo", "tag"]
    ).reset_index(drop=True)


def build_panel(facts: pd.DataFrame) -> pd.DataFrame:
    """Construye el panel base: flujos trimestrales y stocks al cierre.

    Los flujos se convierten de YTD a trimestre mediante diferencias dentro de
    ISA. EBITDA usa el concepto agregado D&A validado en la exploracion.
    """

    required = {"periodo", "variable", "valor_ytd_o_stock"}
    missing = required - set(facts.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {sorted(missing)}")

    ytd = facts.pivot(
        index=["emisor", "periodo"],
        columns="variable",
        values="valor_ytd_o_stock",
    ).sort_index()
    panel = pd.DataFrame(index=ytd.index)

    flow_variables = [
        "ingresos",
        "gastos_financieros",
        "resultado_operativo",
        "d_and_a",
    ]
    for variable in flow_variables:
        if variable not in ytd:
            raise ValueError(f"Falta el flujo requerido: {variable}")
        years = ytd.index.get_level_values("periodo").str[:4]
        issuers = ytd.index.get_level_values("emisor")
        panel[variable] = ytd[variable].groupby(
            [issuers, years],
        ).diff()
        group_keys = pd.MultiIndex.from_arrays([issuers, years])
        first_positions = (
            pd.Series(range(len(ytd)), index=group_keys)
            .groupby(level=[0, 1])
            .first()
        )
        for first_position in first_positions.astype(int):
            first_period = ytd.index[first_position]
            panel.loc[first_period, variable] = ytd.loc[first_period, variable]

    for variable in ["caja", "deuda_cp", "deuda_lp"]:
        if variable not in ytd:
            raise ValueError(f"Falta el stock requerido: {variable}")
        panel[variable] = ytd[variable]

    panel["ebitda"] = panel["resultado_operativo"] + panel["d_and_a"]
    panel = panel.reset_index()
    return panel[
        [
            "emisor",
            "periodo",
            "ebitda",
            "deuda_cp",
            "deuda_lp",
            "gastos_financieros",
            "caja",
            "ingresos",
        ]
    ]


def build_isa_panel(facts: pd.DataFrame) -> pd.DataFrame:
    """Compatibilidad con el nombre historico de la funcion para ISA."""

    return build_panel(facts)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    isa_dir = project_root / "Data" / "raw" / "ISA"
    all_files = sorted(isa_dir.glob("*.xbrl"))
    valid_files = [
        file for file in all_files if _is_valid_period_path(file)
    ]
    excluded_files = sorted(set(all_files) - set(valid_files))

    if excluded_files:
        print("Archivos excluidos por nombre de periodo no valido:")
        for file in excluded_files:
            print(f"- {file.name}")

    isa_facts = extract_isa_facts(isa_dir, pattern="*.xbrl")
    isa_panel = build_isa_panel(isa_facts)
    output_path = project_root / "Data" / "processed" / "isa_panel.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    isa_panel.to_csv(output_path, index=False)
    print(isa_panel.to_string(index=False))
    print(f"Panel guardado en: {output_path}")
