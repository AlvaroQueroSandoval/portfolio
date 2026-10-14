# Modelo de reconocimiento

- Archivo: sudoku_digit_model.h5.
- Procedencia: modelo ya incluido en el proyecto Sudoku original.
- SHA-256: 052a20c427367db78a58c9d2e97f2030c970cace4eca38c023cc29017ca2c4e8.
- Entrada: imagen de una cifra, 28 × 28 × 1, intensidad normalizada a [0, 1].
- Salida: diez puntuaciones de clase, de 0 a 9.
- Carga: TensorFlow 2.20.0 / Keras 3.11.3, sin compilar para entrenamiento.
- No se ha reentrenado ni cambiado el archivo de pesos.

El repositorio original no contiene el conjunto de entrenamiento, su división, las métricas ni una licencia específica del modelo. No se presupone su origen ni se publican métricas de entrenamiento.

La clase 0 no es una pista válida. Una predicción 0 queda vacía y marcada como dudosa para revisión. Las puntuaciones inferiores a 0,95 también se señalan; este umbral es orientativo y no está calibrado estadísticamente.

Las métricas de docs/PRUEBAS.md evalúan el flujo completo sobre imágenes concretas. No equivalen a una evaluación independiente del clasificador ni a una garantía sobre imágenes de cualquier procedencia.
