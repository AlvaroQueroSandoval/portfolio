# Validación de FacturaApp

Fecha: 15/10/2026. Entorno: Windows, Python 3.12, Streamlit 1.50.0.

## Pruebas automáticas

37 pruebas superadas con pytest:

- Cantidades inválidas, negativas, cero, infinitas y fuera de rango.
- Coma decimal y redondeo monetario; sacos completos como unidad comercial.
- Precio con IVA sin doble imposición en el cálculo.
- Extracción de una oferta del producto correcto y rechazo de moneda, fecha, precio o disponibilidad inválidos.
- Conservación del catálogo anterior si falla la actualización.
- Rollback del historial cuando falla el PDF.
- Idempotencia de la generación y permanencia de los importes históricos.
- Numeración única con ocho escrituras concurrentes.
- PDF de 65 líneas y varias páginas, sin pérdida de líneas ni total.
- Rechazo de IDs, unidades, cantidades y campos de precios incorrectos propuestos por la IA.
- Contrato HTTP de Ollama con una respuesta simulada.
- Creación de un documento y consulta del historial mediante Streamlit AppTest.

## Conexión real

El conector recuperó correctamente las tres referencias de Pochiche el 15/10/2026:

| Referencia | Unidad | Precio publicado, IVA incluido |
|---|---|---:|
| Cemento blanco LAFARGE | Saco de 25 kg | 10,41 EUR |
| Cemento gris CEMEX | Saco de 25 kg | 6,75 EUR |
| Mortero MM30 FASSA | Saco de 25 kg | 2,90 EUR |

Las fuentes, referencias y horas de consulta se conservan en examples/catalog_snapshot.json.
Estos son resultados históricos de la prueba, no una promesa de precios vigentes cuando se lea este documento.

## Revisión visual

PDF de ejemplo renderizado e inspeccionado: tabla legible, totales y trazabilidad, una página.
La interfaz de creación y el catálogo se revisaron en Chrome.

## Pendiente

- Inferencia real con Ollama y evaluación de peticiones ambiguas: el equipo no dispone de Ollama instalado.
- Pruebas en Linux/macOS y pantallas móviles.
- Ampliación de materiales: el conector incluye tres referencias, no todo el catálogo.
- La extracción web puede fallar si cambia la estructura de la tienda; la aplicación conserva el precio anterior y avisa.

Las pruebas de IA simuladas comprueban el contrato y los controles, no la precisión del modelo.
