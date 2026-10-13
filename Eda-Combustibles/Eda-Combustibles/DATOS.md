# Datos y procedencia

`gasolina.csv` es el archivo entregado originalmente como `gasofa.csv`.
Solo se ha cambiado el nombre: su contenido se conserva byte a byte.

- SHA-256: `402b844a57f272a1096019b6f3ea01d5620ec8de955787b064b7a1cccadded86`.
- 1.134 registros, desde 2002 semana 2 hasta 2024 semana 44.
- Codificación UTF-8 con BOM, separador coma, campos entrecomillados y coma decimal.
- Columnas: año, periodo declarado y precios de gasolina 95 y diésel.
- Un precio de diésel ausente en 2020 semana 17. No se imputa.
- Sin duplicados por año y semana. Cobertura desigual entre años.
- Semana 53 en 2022: convención de calendario pendiente de verificar.

## Qué no se ha podido recuperar

El autor no recuerda la web de descarga y el archivo original no contiene una referencia.
Por tanto, la fuente, fecha de extracción, licencia de los datos, representatividad nacional,
unidad exacta y tratamiento de impuestos/descuentos no están verificados.
La descripción académica original indicaba España y euros. No se atribuye el CSV a un
organismo ni se confirma que sean medias nacionales en euros por litro.

No se sustituye este conjunto por otro aparentemente similar. Una futura recuperación de
la fuente debe contrastar tanto los valores como su calendario y definición.
La revisión del código no resuelve la procedencia ni las condiciones de redistribución del CSV.
