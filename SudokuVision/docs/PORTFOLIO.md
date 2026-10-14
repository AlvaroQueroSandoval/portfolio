# SudokuVision — lector y solucionador de Sudokus

**Categoría:** Visión artificial / Desarrollo web  
**Tecnologías:** Python, Flask, OpenCV, TensorFlow, JavaScript  
**Estado:** Demo local validada; publicación web pendiente

Aplicación web que transforma una imagen de un Sudoku en un tablero editable. El usuario puede subir su propia imagen, revisar las cifras detectadas y obtener una solución cuya unicidad se comprueba.

## El problema

Reconocer una cuadrícula no basta: una cifra mal leída puede cambiar el problema. El flujo separa la lectura de imágenes de la validación de las pistas y permite corregir errores antes de resolver.

## Funcionalidades

- Subida de PNG/JPG y dos ejemplos incorporados.
- Detección del tablero, corrección de perspectiva y orientación.
- Revisión manual con casillas dudosas y conflictos señalados.
- Comprobación de solución única, contradicciones y ambigüedad.
- Diseño adaptable a escritorio y móvil.

## Validación

10 tableros y 70 imágenes generadas: 60 lecturas completas correctas y 10 rechazos explícitos por baja resolución o desenfoque intenso. Cinco recorridos completos de subida y resolución comprobados en Chrome.

La evaluación incluye variaciones de escala, giro, perspectiva, iluminación, ruido y tipografía. No demuestra un reconocimiento perfecto en fotografías reales: el usuario debe revisar siempre las pistas.

## Qué demuestra el proyecto

Integración de procesamiento de imágenes, inferencia con un modelo existente, lógica de resolución, una API y una interfaz usable. El proyecto incluye pruebas reproducibles y documentación de sus limitaciones.

---

Para preparar la ficha de Notion:

1. Usa docs/demo-desktop.png como captura y portada.
2. Copia la descripción y las funcionalidades de esta página.
3. Añade el enlace al repositorio en la propiedad GitHub.
4. Cuando esté desplegado, añade su URL HTTPS en Demo.
5. Usa el texto de enlace «Probar SudokuVision» para que el visitante suba su propia imagen.

No presentes la aplicación como un modelo entrenado desde cero ni como un lector infalible de cualquier Sudoku.
