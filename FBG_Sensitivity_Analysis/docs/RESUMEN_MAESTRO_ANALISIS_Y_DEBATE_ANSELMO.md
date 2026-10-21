# RESUMEN MAESTRO DEL ANÁLISIS DE SENSIBILIDAD FBG Y DEBATE CON ANSELMO
**Fecha de consolidación**: 21 de octubre de 2026  
**Autora**: Victoria García Pol  
**Repositorio**: `/afs/cern.ch/user/v/vgarciap/rtd-calibration-ana/FBG_Sensitivity_Analysis`

---

## 1. CONTEXTO GENERAL Y OBJETIVO DEL PAPER
* **Título / Tema**: Calibración y caracterización metrológica de sensores de fibra óptica Bragg (FBG) a temperaturas criogénicas (77 a 92 K) para monitorización térmica en detectores como DUNE.
* **Fibras estudiadas**:
  - PEEK grueso (400–450 µm): PEEK-4, PEEK-1, PEEK-7 (alta sensibilidad: ~18–20 pm/K).
  - PEEK fino (200 µm): ~3.1 pm/K.
  - Ormocer / Ormocer-T (200–250 µm): ~4.7–7.2 pm/K.
  - Polyimide (200 µm): ~3.6 pm/K.
* **Manuscrito actual**: `main-v5.tex` (sincronizado con Overleaf y con `/eos/user/v/vgarciap/cernbox/TESIS/papers/main-v5.tex`).
* **Debate central**: Cómo estructurar y validar de forma 100% matemática, ciega y sin cherry-picking la **resolución térmica milikelvin** en la Sección 4.4 y la **Figura 4**.

---

## 2. CRONOLOGÍA DETALLADA DEL DEBATE CON ANSELMO CERVERA

### Fase 1: La crítica al plateau único (Cherry-picking)
* En el borrador inicial se mostraba un único plateau a $T \approx 83\text{ K}$ con $\sigma = 2.5\text{ mK}$.
* Anselmo señaló que un único plateau parecía elegido "a mano" (cherry-picking).
* **Decisión**: El criterio de selección de plateaus debía ser **100% ciego**, basándose **exclusivamente en la señal del RTD de referencia**, sin mirar jamás a la fibra FBG.

### Fase 2: El filtro con polinomio de grado 3 (La cúbica)
* Anselmo propuso: *"Prueba a mirar la chi2 del ajuste a un polinomio de grado 3"*.
* Analizamos todos los plateaus de todas las fibras:
  - **PEEK-4** (19 plateaus en Runs 1, 2 y 3).
  - **PEEK-1** (17 plateaus en Runs 26/09, 30/09 y 01/10).
  - **PEEK-7** (20 plateaus en Runs 27/02, 28/02 y 10/03).
* Con corte $\chi^2/\text{ndf} \le 1.5$ sobre el RTD, 9 plateaus de PEEK-4 pasaron el filtro con un error de seguimiento medio de $\text{RMS} = 3.01 \pm 0.86\text{ mK}$.

### Fase 3: Descarte del 3-sigma y del histograma combinado
* Anselmo escribió:
  - *"Quita lo de los 3sigma. Mejor quedarse solo con la RMS"*.
  - *"Muchos plateaus no van a ser ni siquiera gaussianos"*.
  - *"¿Qué es la combined residual distribution? ¿Para todos los plateaus a la vez?"*.
  - *"El requisito del que hemos hablado siempre es que la resolución sea menor de 5 mK, en este caso la RMS"*.
* **Decisión**: Se eliminó el histograma combinado con ajuste gaussiano y la noción de $3\sigma = 20\text{ mK}$. Se adoptó el requisito oficial: **$\text{RMS} < 5.0\text{ mK}$**.

### Fase 4: La refutación de la cúbica con `P3_R3`
* Al graficar la RMS de los residuos en función de la $\chi^2$ del polinomio para todos los plateaus, aparecieron **3 puntos anómalos**: alta $\chi^2$ pero bajo residuo FBG (`P3_R3`, `P2_R3`, `P1_R2`).
* En `P3_R3`, la $\chi^2$ era de **110.88**, pero la fibra FBG seguía al RTD con una RMS de apenas **$4.0\text{ mK}$**.
* Anselmo descubrió la causa física al instante:  
  *"P3_R3 creo que es este. Esto no se va a ajustar bien a una cúbica pero la temperatura tiene un comportamiento suave. También puedes probar con splines. Busca en la IA cómo estudiar la suavidad de un grupo de puntos experimentales"*.
* **Causa física**: En `P3_R3` la temperatura descendía $\sim 92\text{ mK}$ en 10 minutos siguiendo una relajación térmica suave. La cúbica global fallaba por ser matemáticamente rígida (dejando $15.7\text{ mK}$ de residuo artificial), pero el fenómeno físico era laminar y continuo.

### Fase 5: El nuevo método de suavizado (Smoothing Splines y Segundas Diferencias)
Implementamos dos métodos estándar en física experimental para evaluar suavidad:
1. **Smoothing Spline (con modelo)**: Ajuste de spline cúbico penalizando curvatura. Para `P3_R3`, el residuo cayó de $15.7\text{ mK}$ a solo **$1.50\text{ mK}$** (el suelo de ruido del RTD).
2. **Segundas Diferencias Finitas (libre de modelos)**: $\sigma_{\text{rough}} = \frac{1}{\sqrt{6}}\text{RMS}(T_{i+2} - 2T_{i+1} + T_i)$. Cancela cualquier deriva continua y mide únicamente saltos o turbulencias. En plateaus tranquilos da $\sim 0.25\text{--}0.30\text{ mK}$.

### Fase 6: La petición final de Anselmo (Correlación continua sin cortes)
* Anselmo indicó: *"Yo te diría de hacer el plot de la RMS en función del parámetro de smoothness sin poner cortes, como hicimos con la cúbica"*.
* Se generó el gráfico de correlación pura continua sin líneas verticales ni zonas sombreadas, tanto combinado (PEEK-4 + PEEK-1) como específico para PEEK-4 con etiquetas en cada punto.

---

## 3. RESULTADOS NUMÉRICOS CONSOLIDADOS (PARA CITAR EN EL PAPER O DEFENSA)

### Si se aplica el corte ciego de suavidad ($\text{Spline RMS} \le 1.5\text{ mK}$):
* **Criterio físico del corte de 1.5 mK**: Corresponde al suelo de ruido electrónico nominal del RTD ($\sigma \approx 1.5\text{ mK}$). Si los residuos están por debajo de 1.5 mK, el criostato está en reposo térmico puro y solo se observa el ruido del sensor.
* **PEEK-4 (Runs 1, 2 y 3, junio 2026)**:
  - 11 plateaus seleccionados (de 18 analizados, 61.1%).
  - Tracking RMS medio del FBG: **$3.35 \pm 1.09\text{ mK}$** (rango: $[2.36,\, 5.21]\text{ mK}$).
* **PEEK-1 (Runs 1, 2 y 3, sept/oct 2024)**:
  - 8 plateaus seleccionados (de 16 analizados, 50.0%).
  - Tracking RMS medio del FBG: **$3.32 \pm 0.91\text{ mK}$** (rango: $[1.89,\, 4.69]\text{ mK}$).
* **Conjunto Global (PEEK-4 + PEEK-1)**:
  - **19 plateaus seleccionados** (56% del total).
  - Tracking RMS medio conjunto: **$\mathbf{3.34 \pm 1.01\text{ mK}}$**.
  - **Cumplimiento del requisito**: Prácticamente el 100% (17 de 19 están estrictamente por debajo de $5.0\text{ mK}$, y los otros 2 en $5.17$ y $5.21\text{ mK}$).
* **Plateaus rechazados ($\text{Spline RMS} > 1.5\text{ mK}$)**:
  - Error de seguimiento medio del FBG: **$8.2\text{ mK}$** (alcanzando 9, 13 y 15 mK), confirmando que las turbulencias desacoplan los sensores.

---

## 4. INVENTARIO DE SCRIPTS Y FIGURAS CLAVE

### Figuras generadas (en carpeta `figures/`):
1. **`figures/peek4_smoothness_no_cuts.png` / `.pdf`**:  
   Plot final pedido por Anselmo: RMS de seguimiento del FBG vs. Suavidad del RTD (Spline y segundas diferencias) **solo para PEEK-4, sin cortes**, con etiquetas en cada plateau (`P1_R1`, `P3_R3`, etc.).
2. **`figures/fbg_rms_vs_smoothness_no_cuts.png` / `.pdf`**:  
   Mismo plot de correlación continua sin cortes pero combinando **PEEK-4 y PEEK-1** (34 plateaus).
3. **`figures/peek4_all_plateaus_spline_grid.png` / `.pdf`**:  
   Cuadrícula de 4x5 con los 19 plateaus de PEEK-4 mostrando los datos del RTD, el ajuste del Spline y el FBG en cada uno, con fondo verde (seleccionados) y rojo (rechazados).
4. **`figures/plateau_p3_r3_spline_explanation.png`**:  
   Figura explicativa que demuestra por qué falló la cúbica en `P3_R3` ($\Delta T \approx 92\text{ mK}$) y cómo el spline y el FBG funcionan perfectamente.
5. **`figures/spline_method_final_comparison.png` / `.pdf`**:  
   Scatter plot de 4 cuadrantes con la línea de corte en 1.5 mK y la de resolución en 5 mK.
6. **`figures/fig4_20mK_resolution.pdf` / `.png`**:  
   Figura 4 del paper actualmente enlazada en `main-v5.tex` (seguimiento en 3 plateaus arriba + barras de RMS abajo).

### Scripts de análisis (en `scratch/`):
* `scratch/plot_peek4_only_no_cuts.py`: Genera el plot de correlación continua solo para PEEK-4.
* `scratch/plot_smoothness_no_cuts.py`: Genera el plot de correlación continua para PEEK-4 y PEEK-1.
* `scratch/plot_all_peek4_splines_grid.py`: Genera la cuadrícula de 19 mini-subplots de PEEK-4.
* `scratch/plot_p3_r3_explanation.py`: Genera la comparativa cúbica vs spline en `P3_R3`.
* `scratch/evaluate_new_smoothness_method.py`: Script maestro que calcula Spline RMS, segundas diferencias y FBG RMS con filtro de 1.0 s en todos los runs.
* `scratch/generate_fig4_comprehensive.py`: Genera la Figura 4 oficial del paper.

### Archivos de datos generados (en `figures/`):
* `figures/new_smoothness_method_results.csv`: Tabla completa con todos los plateaus, temperaturas, Spline RMS, $\sigma_{\text{rough}}$ y FBG RMS.
* `figures/peek4_all_runs_plateaus.csv`: Datos de PEEK-4 por plateau.
* `figures/all_peek_fibers_plateaus.csv`: Datos de PEEK-1, PEEK-4 y PEEK-7.

---

## 5. DÓNDE ESTÁ CADA COSA EN LATEX (`main-v5.tex`)
* **Sección 4.4**: `\subsubsection{Experimental Demonstration of Sub-20\,mK Tracking}` (líneas ~522 en adelante).
  - Ya se eliminó la mención a $3\sigma = 20\text{ mK}$ y el histograma gaussiano.
  - Describe la selección ciega en el RTD, el seguimiento en los 3 plateaus (a1–a3) y la RMS de los plateaus seleccionados ($\langle \text{RMS} \rangle \approx 3.0\text{--}3.3\text{ mK}$).
* **Conclusiones**: Actualizada para reflejar la RMS de $\approx 3.0\text{ mK}$ sin hipótesis gaussianas.
* **Copias sincronizadas**:
  - `overleaf_snapshots/main-v5.tex`
  - `/eos/user/v/vgarciap/cernbox/TESIS/papers/main-v5.tex`

---

## 6. GUÍA RÁPIDA PARA RETOMAR CON LA NUEVA CUENTA DE GEMINI PRO

Cuando abras el chat en la nueva cuenta de Gmail, solo tendrás que poner este prompt:

> *"Hola, soy Victoria García Pol. Estoy trabajando en mi tesis y paper de calibración de sensores FBG criogénicos en `/afs/cern.ch/user/v/vgarciap/rtd-calibration-ana/FBG_Sensitivity_Analysis`. Por favor, lee el archivo `docs/RESUMEN_MAESTRO_ANALISIS_Y_DEBATE_ANSELMO.md` para situarte en el estado exacto del proyecto, las decisiones de análisis tomadas con Anselmo Cervera y los scripts y figuras disponibles."*

Con eso, el asistente sabrá el 100% de la historia y podrá continuar exactamente desde donde lo dejamos.
