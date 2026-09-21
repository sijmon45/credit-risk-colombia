# credit-risk-colombia

Estimación reproducible de indicadores financieros y riesgo crediticio relativo para cinco emisores colombianos del sector energía e infraestructura: **ISA, ISAGEN, EPM, CELSIA y ENEL Colombia**.

---

## Objetivo

Construir un índice compuesto de solidez crediticia a partir de ratios financieros extraídos de estados financieros bajo NIIF, y evaluar la resiliencia de cada emisor bajo dos escenarios de estrés. El análisis es completamente reproducible desde los archivos XBRL públicos disponibles en el RNVE de la Superintendencia Financiera de Colombia.

---

## Estructura del repositorio

```
credit-risk-colombia/
├── Data/
│   ├── raw/                   # Archivos XBRL descargados del RNVE por emisor
│   │   ├── ISA/
│   │   ├── ISAGEN/
│   │   ├── EPM/
│   │   ├── CELSIA/
│   │   └── ENEL/
│   └── processed/
|		├── isa_panel.csv      # Panel preliminar de exploración 
│       ├── panel_limpio.csv   # Panel trimestral limpio (insumo del notebook)
│       └── tabla_resumen.csv  # Resultados del último periodo (output)
|
├── src/
│   ├── extract_xbrl.py        # Extracción y construcción del panel desde XBRL
│   └── clean_panel.py         # Correcciones de unidades e imputación de EBITDA
├── notebooks/
|   ├── Exploracion_XBRL_ISA.ipynb        # Primera aproximación a extracción de datos XBRL
│   └── Ratios_Indice_Stress.ipynb  # Ratios, índice compuesto y stress testing
├── outputs/
│   ├── grafico1_evolucion_historica.png
│   ├── grafico2_ranking.png
│   ├── grafico3_stress.png
│   ├── grafico4_heatmap.png
|	└── tabla_resumen.csv
├── Video_explicativo.mp4
└── README.md
```

---

## Cómo reproducir el análisis

### 1. Instalar dependencias

```bash
pip install pandas numpy matplotlib seaborn arelle-release
```

Python 3.10 o superior recomendado.

### 2. Descargar los archivos XBRL

Los archivos se obtienen del [RNVE de la Superfinanciera](https://www.superfinanciera.gov.co/SIMEV2/rnve).

Por cada emisor, buscar "Informes financieros bajo NIIF y anexos", seleccionar el formato XBRL y descargar los reportes trimestrales disponibles. Guardarlos en la carpeta `Data/raw/<EMISOR>/` con el formato de nombre `<AÑO>Q<TRIMESTRE>_<FECHA-CIERRE>.xbrl` (por ejemplo, `2023Q2_2023-06-30.xbrl`).

### 3. Construir el panel

```bash
python src/extract_xbrl.py      # Extrae variables desde XBRL para todos los emisores
python src/clean_panel.py       # Corrige unidades e imputa EBITDA faltante
```

El resultado se guarda en `Data/processed/panel_limpio.csv`.

### 4. Correr el notebook

```bash
jupyter notebook notebooks/Ratios_Indice_Stress.ipynb
```

Ejecutar todas las celdas en orden (Kernel → Restart & Run All). Los gráficos y la tabla resumen se guardan automáticamente en `outputs/`.

---

## Metodología

### Datos

- **Fuente:** RNVE — Superintendencia Financiera de Colombia
- **Formato:** XBRL bajo taxonomía NIIF (IFRS)
- **Periodo:** 2021Q1 – 2026Q2 (entre 18 y 19 observaciones TTM por emisor)
- **Variables base extraídas:** ingresos operacionales, resultado operativo, depreciación y amortización, gastos financieros, caja y equivalentes, deuda financiera de corto y largo plazo

### Ventana TTM

Los flujos (EBITDA, gastos financieros, ingresos) se anualizan sumando los cuatro trimestres más recientes disponibles para cada observación. Los stocks (caja, deuda) conservan el saldo puntual del trimestre de cierre. Esto elimina la estacionalidad y hace comparables los ratios a lo largo del tiempo.

### Cuatro ratios

| Ratio | Fórmula | Interpretación |
|:---|:---|:---|
| Deuda / EBITDA | (Deuda CP + Deuda LP) / EBITDA TTM | Años de generación para cubrir deuda. Más alto = más riesgo. |
| Cobertura de intereses | EBITDA TTM / Gastos financieros TTM | Veces que el EBITDA cubre intereses. Más alto = más seguro. |
| Liquidez CP | Caja / Deuda CP | Cobertura de vencimientos de corto plazo con caja. Más alto = más seguro. |
| Margen EBITDA | EBITDA TTM / Ingresos TTM | Eficiencia operativa. Más alto = más seguro. |

### Índice compuesto

Cada ratio se normaliza como z-score dentro del panel TTM completo. El signo de Deuda/EBITDA se invierte para que todos los z-scores apunten en la misma dirección (valor más alto = menor riesgo). El índice es un promedio ponderado:

| Dimensión | Peso |
|:---|---:|
| Deuda / EBITDA | 30% |
| Cobertura de intereses | 30% |
| Liquidez CP | 20% |
| Margen EBITDA | 20% |

Un índice positivo indica una posición por encima del promedio histórico del panel; negativo, por debajo.

### Escenarios de estrés

Los choques se aplican sobre el último periodo disponible de cada emisor usando los mismos parámetros de normalización del panel histórico.

**Choque 1 — Caída de EBITDA del 20%:** simula un año con fenómeno de El Niño fuerte que reduce la disponibilidad hídrica y contrae los márgenes operativos de las generadoras. Afecta simultáneamente Deuda/EBITDA, Cobertura de intereses y Margen EBITDA.

**Choque 2 — Alza de gastos financieros del 15%:** simula una subida de tasas de interés o una devaluación del peso que encarece la deuda denominada en USD. Afecta únicamente la Cobertura de intereses.

---

## Resultados principales

### Ratios promedio (ventana TTM completa)

| Emisor | Deuda/EBITDA | Cobertura int. | Liquidez CP | Margen EBITDA |
|:---|---:|---:|---:|---:|
| ENEL | 1.33x | 6.45x | 0.99x | 46% |
| EPM | 2.20x | 3.04x | 1.12x | 24% |
| ISA | 4.27x | 3.21x | 2.13x | 54% |
| CELSIA | 4.35x | 1.98x | 0.31x | 21% |
| ISAGEN | 4.82x | 1.86x | 0.59x | 54% |

### Índice compuesto — último periodo

| Emisor | Índice base | Choque EBITDA −20% | Colchón | Choque Gastos fin. +15% | Colchón |
|:---|---:|---:|---:|---:|---:|
| ENEL | +1.175 | +0.799 | 0.376 | +1.051 | 0.124 |
| ISA | +0.455 | +0.022 | 0.433 | +0.396 | 0.059 |
| EPM | +0.280 | +0.026 | 0.254 | +0.218 | 0.062 |
| ISAGEN | −0.689 | −1.132 | 0.443 | −0.717 | 0.028 |
| CELSIA | −1.087 | −1.441 | 0.354 | −1.120 | 0.033 |

**Hallazgo principal:** el choque de EBITDA es entre 4 y 8 veces más severo que el choque de tasas para todos los emisores, lo que indica que el riesgo operativo es el canal de transmisión dominante en este grupo. ISA presenta la segunda mayor pérdida de índice bajo estrés de EBITDA (0.433) a pesar de tener el segundo mejor índice base, revelando que su fortaleza está impulsada por liquidez y margen, no por bajo apalancamiento.

---

## Limitaciones

- **Índice relativo, no absoluto:** el índice mide posición dentro del grupo de cinco emisores. No equivale a una probabilidad de incumplimiento ni a una calificación crediticia.
- **EBITDA de ENEL parcialmente imputado:** los trimestres Q2–Q4 de cada año se estimaron con el margen EBITDA promedio de los cinco periodos Q1 con dato real. Los movimientos interanuales reflejan ingresos observados; la variación estacional dentro del año es artificial.
- **Universo reducido:** con cinco emisores, la normalización por z-score es sensible a los valores extremos de cualquier empresa. La incorporación de un universo más amplio (segunda fase) mejoraría la robustez del índice.

---

## Próximos pasos (fase 2)

- Modelo logístico con universo ampliado de emisores colombianos, usando cambios de calificación de BRC Investor Services y Fitch Ratings Colombia como variable dependiente proxy de estrés crediticio.
- Métodos predictivos de machine learning para predecir comportamiento crediticio futuro (Random Forest - XGBoost)
---

## Fuentes

- Superintendencia Financiera de Colombia — [RNVE](https://www.superfinanciera.gov.co)

## Presentación del video

[Claude Artifact](https://claude.ai/artifact/Uutxdg4qytPqpHBvhMwq4H)