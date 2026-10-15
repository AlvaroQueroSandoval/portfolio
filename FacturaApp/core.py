"""Cálculos reproducibles: la IA nunca establece precios ni importes."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")


def number(value, *, positive=False, maximum="1000000"):
    if isinstance(value, bool):
        raise ValueError("Introduce un número válido.")
    try:
        result = Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError("Introduce un número sin separadores de miles; admite coma decimal.") from exc
    if not result.is_finite() or result < 0 or result > Decimal(maximum):
        raise ValueError("El número debe ser finito, positivo o cero, y estar dentro del límite.")
    if positive and result == 0:
        raise ValueError("La cantidad y el precio deben ser mayores que cero.")
    return result


def money(value):
    return format(value.quantize(CENT, rounding=ROUND_HALF_UP), ".2f")


def calculate(items, catalog):
    if not items or len(items) > 100:
        raise ValueError("Añade entre 1 y 100 líneas.")
    lines = []
    subtotal = tax = Decimal(0)
    for item in items:
        product = catalog.get(item.get("id"))
        if not product:
            raise ValueError("Uno de los materiales no existe en el catálogo.")
        quantity = number(item.get("quantity"), positive=True, maximum="100000")
        if quantity.as_tuple().exponent < -3:
            raise ValueError("Las cantidades admiten como máximo tres decimales.")
        if product.get("whole_units", False) and quantity != quantity.to_integral_value():
            raise ValueError(f"{product['name']}: introduce unidades completas.")
        rate = number(product["vat"], maximum="100")
        # La tarifa pública incluye IVA. Mantener el bruto evita redondearlo dos veces.
        gross_price = number(product["price_gross"], positive=True)
        gross = (quantity * gross_price).quantize(CENT, rounding=ROUND_HALF_UP)
        net = (gross / (1 + rate / 100)).quantize(CENT, rounding=ROUND_HALF_UP)
        line_tax = gross - net
        lines.append({
            "id": item["id"], "name": product["name"], "unit": product["unit"],
            "quantity": str(quantity), "unit_gross": money(gross_price),
            "vat": str(rate), "net": money(net), "tax": money(line_tax), "gross": money(gross),
            "source": product.get("source", ""), "checked_at": product.get("checked_at", ""),
            "supplier": product.get("supplier", ""), "reference": True,
        })
        subtotal += net
        tax += line_tax
    return {"lines": lines, "subtotal": money(subtotal), "tax": money(tax),
            "total": money(subtotal + tax), "currency": "EUR"}


def validate_details(details):
    clean = {}
    for key in ("issuer", "recipient", "worksite"):
        value = str(details.get(key, "")).strip()
        if not value or len(value) > 180:
            raise ValueError("Completa emisor, destinatario y obra (máximo 180 caracteres cada uno).")
        clean[key] = value
    kind = details.get("kind")
    if kind not in {"Presupuesto de materiales", "Factura de demostración"}:
        raise ValueError("Tipo de documento no válido.")
    clean["kind"] = kind
    clean["notes"] = str(details.get("notes", ""))[:1000]
    return clean
