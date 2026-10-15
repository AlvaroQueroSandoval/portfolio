"""Consulta pública de tres referencias de Pochiche. No es una API concertada."""
from datetime import datetime, timezone, date
from html import unescape
from html.parser import HTMLParser
import json
from urllib.parse import urlsplit

import requests
from core import number, money

BASE = "https://pochiche.com"
PRODUCTS = {
    "cemento_blanco": {"slug": "cemento-blanco-iial-425-r", "unit": "saco de 25 kg"},
    "cemento_gris": {"slug": "cem-ii-bm-sll-425-r", "unit": "saco de 25 kg"},
    "mortero": {"slug": "mortero-cementoso-mamposteria-mm30", "unit": "saco de 25 kg"},
}


class StructuredData(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.buffer = []
        self.blocks = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("type", "").lower() == "application/ld+json":
            self.active = True
            self.buffer = []

    def handle_endtag(self, tag):
        if tag == "script" and self.active:
            self.blocks.append("".join(self.buffer))
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.buffer.append(data)
        else:
            self.text.append(data)


def nodes(value):
    if isinstance(value, list):
        for item in value:
            yield from nodes(item)
    elif isinstance(value, dict):
        yield value
        if "@graph" in value:
            yield from nodes(value["@graph"])


def parse_product(html, product_id):
    spec = PRODUCTS[product_id]
    url = BASE + "/materiales-construccion/" + spec["slug"]
    parser = StructuredData()
    parser.feed(html)
    products = []
    for block in parser.blocks:
        try:
            products.extend(n for n in nodes(json.loads(block)) if n.get("@type") == "Product")
        except (json.JSONDecodeError, TypeError):
            continue
    matching = []
    for product in products:
        offers = product.get("offers")
        if isinstance(offers, dict) and offers.get("url", "").rstrip("/") == url:
            matching.append((product, offers))
    if len(matching) != 1:
        raise ValueError("No se ha encontrado una oferta única para esta referencia.")
    product, offer = matching[0]
    if offer.get("priceCurrency") != "EUR":
        raise ValueError("La oferta no está expresada en euros.")
    if not str(offer.get("availability", "")).endswith("/InStock"):
        raise ValueError("El proveedor no indica disponibilidad.")
    valid_until = offer.get("priceValidUntil")
    if valid_until and date.fromisoformat(valid_until) < datetime.now(timezone.utc).date():
        raise ValueError("La fecha de validez publicada por el proveedor ha vencido.")
    visible = unescape(" ".join(parser.text)).casefold()
    if "precios con iva incluido" not in visible:
        raise ValueError("No se puede confirmar si el precio incluye IVA.")
    # Comprobar la presentación comercial, no asumir que la cifra es precio por kg.
    name = unescape(product.get("name", "")).strip()
    if "25" not in name or "kg" not in name.casefold():
        raise ValueError("La presentación del producto ha cambiado; revisa su unidad.")
    return {
        "id": product_id, "name": name, "unit": spec["unit"], "whole_units": True,
        "price_gross": money(number(offer.get("price"), positive=True)),
        "vat": "21", "supplier": "Pochiche", "source": url,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sku": str(product.get("sku", "")), "price_valid_until": valid_until,
        "reference": True,
    }


def fetch_product(product_id, session=None):
    client = session or requests.Session()
    url = BASE + "/materiales-construccion/" + PRODUCTS[product_id]["slug"]
    with client.get(url, timeout=(8, 20), stream=True, allow_redirects=False,
                    headers={"User-Agent": "FacturaApp/1.0 (consulta de precios de referencia)"}) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("La ficha ha cambiado de dirección.")
        if "text/html" not in response.headers.get("Content-Type", ""):
            raise ValueError("El proveedor no ha devuelto una ficha HTML.")
        chunks, size = [], 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > 2_000_000:
                raise ValueError("La ficha supera el tamaño permitido.")
            chunks.append(chunk)
        html = b"".join(chunks).decode("utf-8")
    return parse_product(html, product_id)


def refresh():
    updated, errors = {}, {}
    with requests.Session() as session:
        for key in PRODUCTS:
            try:
                updated[key] = fetch_product(key, session)
            except (requests.RequestException, ValueError, UnicodeError) as exc:
                errors[key] = f"No se pudo actualizar: {type(exc).__name__}. Se conserva el precio anterior."
    return updated, errors
