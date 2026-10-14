# Informe de pruebas

Fecha: 14 de octubre de 2026. Ejecución local en Windows, Python 3.12.15, TensorFlow 2.20.0 y Chrome en modo automatizado. No se ha medido el servicio en un alojamiento público.

## 1. Cinco sudokus y variaciones significativas

Se generaron cinco tableros diferentes con semillas 1103, 2207, 3301, 4409 y 5501. Cada uno tiene 32 pistas y solución única. El generador construye primero una solución completa mediante búsqueda aleatoria y después retira pistas conservando unicidad.

Se comparan las **81 casillas detectadas**, incluidas las vacías, contra el tablero esperado, teniendo en cuenta la orientación. No basta con que el solucionador encuentre alguna solución: también se compara esa solución con la original.

| Variante, aplicada a cada tablero | Lectura exacta | Rechazo |
|---|---:|---:|
| Imagen normal, Arial | 5/5 | 0 |
| Reducción a 300 × 300 | 5/5 | 0 |
| Reducción extrema a 144 × 144 | 0 | 5/5 |
| Giro de 90° | 5/5 | 0 |
| Inclinación de 10° | 5/5 | 0 |
| Deformación de perspectiva | 5/5 | 0 |
| Sombra gradual del 25 % al 100 % | 5/5 | 0 |
| Desenfoque gaussiano intenso, sigma 4 | 0 | 5/5 |
| Ruido y compresión JPEG de calidad 35 | 5/5 | 0 |
| Cambio de tipografía a Georgia | 5/5 | 0 |
| **Total** | **40/50** | **10/50** |

En las 40 imágenes aceptadas, el tablero completo se leyó sin corrección y la solución coincidió con la esperada. Las diez rechazadas devolvieron un error explicado, sin producir un tablero resuelto. No se contabilizan los rechazos como aciertos de OCR.

Este conjunto se utilizó durante el ajuste del preprocesamiento. Es una prueba de desarrollo y regresión, no una estimación independiente de generalización.

Detalle: [benchmark.json](benchmark.json). Imágenes y respuestas esperadas: tests/fixtures/manifest.json.

## 2. Conjunto adicional, sin ajustar después el reconocimiento

Cinco nuevos tableros, semillas 6043, 7043, 8043, 9043 y 10043. Fuentes Times New Roman, Verdana, Calibri, Tahoma y Courier New. Cuatro variantes: normal, giro de 90°, sombra del 35 % al 100 % y reducción a 300 × 300.

**20/20 lecturas completas exactas y 20/20 soluciones esperadas**, sin correcciones ni rechazos.

Detalle: [holdout-results.json](holdout-results.json). Imágenes y respuestas esperadas: tests/fixtures/holdout.json.

Aunque cambia tableros y tipografías, este conjunto comparte el generador y el estilo de cuadrícula. No sustituye a un conjunto amplio de fotos reales obtenidas de forma independiente.

## 3. Validación de lógica y API

**26 pruebas superadas** en tests/test_app.py:

- Soluciones correctas de cinco tableros, conservando las pistas de entrada.
- Rechazo de estructuras incorrectas, booleanos, decimales y cifras fuera de rango.
- Detección de duplicados, incluida una cuadrícula completa inválida.
- Tablero vacío, varias soluciones, contradicción sin duplicados inmediatos y límite de cálculo.
- Resolución directa sin casilla de confirmación, con validación de entrada.
- Archivo inválido, imagen vacía, rectángulo sin cuadrícula, cuadrícula sin cifras y tamaño insuficiente.
- Límites de carga, resolución, concurrencia y frecuencia.
- Página, cabeceras y ruta de salud.

## 4. Navegador

Cinco subidas reales mediante el formulario de Chrome:

| Sudoku | Imagen utilizada | Resultado |
|---|---|---|
| 1 | Normal | Pistas y solución correctas |
| 2 | Perspectiva | Pistas y solución correctas |
| 3 | Sombra | Pistas y solución correctas |
| 4 | Giro de 90° | Pistas y solución correctas |
| 5 | Ruido/JPEG | Pistas y solución correctas |

También se comprobaron: resolución sin casilla de confirmación, recuperación de pistas originales, modo manual, conflictos visibles, edición de pistas sin bloqueo adicional, reinicio, rechazo de imagen pequeña y botón de ejemplo.

Vista móvil de 390 píxeles de ancho sin desbordamiento horizontal. Sin errores de JavaScript durante el recorrido. Capturas: [escritorio](demo-desktop.png) y [móvil](demo-mobile.png). Resultado: [browser-check.json](browser-check.json).

## Interpretación

La aplicación resuelve los casos ensayados y ofrece un recorrido de corrección cuando el reconocimiento no es fiable. **Se recomienda revisar siempre las pistas**: una predicción de alta confianza puede estar equivocada y un tablero mal transcrito podría tener otra solución única.

No se ha validado exhaustivamente escritura manual, fotografías de papel curvado, reflejos, fondos oscuros, anotaciones de candidatos ni múltiples sudokus en una imagen.

Las cifras de rendimiento y disponibilidad de una demo pública deberán medirse en el alojamiento elegido. El contenedor Linux está preparado, pero su ejecución no forma parte de estas pruebas.
