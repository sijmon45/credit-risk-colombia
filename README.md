# credit-risk-colombia

Estimacion reproducible de indicadores financieros para emisores colombianos
del sector energia e infraestructura.

## Estado actual

La extraccion XBRL esta implementada inicialmente para ISA. El modulo selecciona
facts consolidados sin dimensiones, convierte flujos YTD a valores trimestrales
y conserva caja y deuda como stocks al cierre. Todavia no calcula ratios ni
stress testing.

## Ejecutar la extraccion de ISA 2021

Desde la raiz del repositorio:

```powershell
python src/extract_xbrl.py
```

Tambien puede utilizarse desde Python:

```python
from src.extract_xbrl import build_isa_panel, extract_isa_facts

facts = extract_isa_facts("Data/raw/ISA", pattern="2021Q*.xbrl")
panel = build_isa_panel(facts)
print(panel)
```

El panel resultante contiene:

`emisor`, `periodo`, `ebitda`, `deuda_cp`, `deuda_lp`,
`gastos_financieros`, `caja`, `ingresos`.

## Proximos pasos

1. Validar ISA para todos los archivos historicos disponibles.
2. Incorporar los archivos de ISAGEN, EPM, CELSIA y ENEL Colombia usando el
	mismo contrato de extraccion.
3. Construir los cuatro ratios, normalizacion, indice compuesto y stress testing.
4. Agregar pruebas automatizadas y visualizaciones para el video final.
