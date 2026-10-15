from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import sys
import uuid

import pytest
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core import calculate, number
from storage import Store
from supplier import parse_product, refresh
from ai import validate_proposal, propose
from pdf_export import render_pdf

CATALOG = json.loads((ROOT / "examples/catalog_snapshot.json").read_text(encoding="utf-8"))
DETAILS = {"kind": "Presupuesto de materiales", "issuer": "Constructora de ejemplo",
           "recipient": "Cliente de ejemplo", "worksite": "Obra de ejemplo", "notes": ""}


@pytest.mark.parametrize("value", ["", "abc", "-1", "NaN", "Infinity", "1e9999", True, None, "1000001"])
def test_invalid_numbers(value):
    with pytest.raises(ValueError):
        number(value)


def test_comma_decimal_and_rounding():
    cat = deepcopy(CATALOG)
    cat["cemento_gris"].update(price_gross="6.75", whole_units=False)
    result = calculate([{"id": "cemento_gris", "quantity": "1,5"}], cat)
    assert (result["subtotal"], result["tax"], result["total"]) == ("8.37", "1.76", "10.13")


@pytest.mark.parametrize("items", [[], [{"id": "unknown", "quantity": "1"}],
    [{"id": "mortero", "quantity": "0"}], [{"id": "mortero", "quantity": "-2"}],
    [{"id": "mortero", "quantity": "1.5"}], [{"id": "mortero", "quantity": "nan"}]])
def test_invalid_lines(items):
    with pytest.raises(ValueError):
        calculate(items, CATALOG)


def test_gross_price_is_not_taxed_twice():
    cat = deepcopy(CATALOG)
    cat["cemento_gris"]["price_gross"] = "6.75"
    result = calculate([{"id": "cemento_gris", "quantity": "20"}], cat)
    assert result["total"] == "135.00"
    assert result["subtotal"] == "111.57"
    assert result["tax"] == "23.43"


def html_fixture(**overrides):
    offer = {"url": CATALOG["cemento_gris"]["source"], "priceCurrency": "EUR",
             "availability": "https://schema.org/InStock", "price": "6.75", "priceValidUntil": "2099-01-01"}
    offer.update(overrides)
    obj = {"@type": "Product", "name": "Cemento gris 25 kg", "sku": "test", "offers": offer}
    return '<p>Precios con IVA incluido.</p><script type="application/ld+json">' + json.dumps(obj) + "</script>"


def test_supplier_parses_exact_product():
    product = parse_product(html_fixture(), "cemento_gris")
    assert product["price_gross"] == "6.75"
    assert product["unit"] == "saco de 25 kg"
    assert product["source"] == CATALOG["cemento_gris"]["source"]


@pytest.mark.parametrize("override", [{"price": "-1"}, {"price": "NaN"}, {"priceCurrency": "USD"},
    {"availability": "https://schema.org/OutOfStock"}, {"priceValidUntil": "2000-01-01"},
    {"url": "https://other.example/product"}])
def test_supplier_rejects_ambiguous_or_invalid_offer(override):
    with pytest.raises(ValueError):
        parse_product(html_fixture(**override), "cemento_gris")


def test_no_iva_or_no_json_fails():
    for html in ["<html>12 euros</html>", html_fixture().replace("Precios con IVA incluido.", "")]:
        with pytest.raises(ValueError):
            parse_product(html, "cemento_gris")


def test_supplier_failure_keeps_previous_price(tmp_path, monkeypatch):
    import supplier
    store = Store(tmp_path / "db.sqlite3")
    store.update_catalog(CATALOG, {})
    def fail(*args, **kwargs):
        raise ValueError("Offline")
    monkeypatch.setattr(supplier, "fetch_product", fail)
    products, errors = refresh()
    store.update_catalog(products, errors)
    assert store.catalog() == CATALOG and len(errors) == 3


def test_pdf_failure_does_not_create_history(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    def broken(_doc):
        raise RuntimeError("PDF failed")
    with pytest.raises(RuntimeError):
        store.save_document(DETAILS, [{"id": "mortero", "quantity": "1"}], CATALOG, "one", broken)
    assert store.history() == []


def test_snapshot_and_idempotency(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    items = [{"id": "mortero", "quantity": "10"}]
    first = store.save_document(DETAILS, items, CATALOG, "same", render_pdf)
    again = store.save_document(DETAILS, items, CATALOG, "same", render_pdf)
    assert first["id"] == again["id"]
    changed = deepcopy(CATALOG)
    changed["mortero"]["price_gross"] = "999"
    store.update_catalog(changed, {})
    assert store.pdf(first["id"]) == first["pdf"]
    assert json.loads(store.history()[0]["body"])["lines"][0]["unit_gross"] == CATALOG["mortero"]["price_gross"]
    assert len(store.history()) == 1


def test_concurrent_numbering(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    def save(_):
        return store.save_document(DETAILS, [{"id": "mortero", "quantity": "1"}], CATALOG,
                                   uuid.uuid4().hex, lambda _doc: b"%PDF-test")["number"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        numbers = list(pool.map(save, range(8)))
    assert len(set(numbers)) == 8


def test_pdf_multiple_pages_and_totals():
    totals = calculate([{"id": "mortero", "quantity": "1"}] * 65, CATALOG)
    doc = dict(DETAILS, **totals, number="PRE-TEST-000001", created_at="2026-10-15")
    pdf = render_pdf(doc)
    reader = PdfReader(BytesIO(pdf))
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert len(reader.pages) >= 2
    assert totals["total"] in text
    assert "PRE-TEST-000001" in text
    assert text.count("Mortero Cementoso") == 65
    assert all("Página" in page.extract_text() for page in reader.pages)


def test_ai_valid_proposal():
    result, unmatched = validate_proposal({"items": [{"id": "mortero", "quantity": "2", "unit": "saco de 25 kg"}],
                                            "unmatched": ["ladrillos"]}, CATALOG)
    assert result == [{"id": "mortero", "quantity": "2"}]
    assert unmatched == ["ladrillos"]


@pytest.mark.parametrize("item", [
    {"id": "inventado", "quantity": "1", "unit": "saco de 25 kg"},
    {"id": "mortero", "quantity": "-1", "unit": "saco de 25 kg"},
    {"id": "mortero", "quantity": "2", "unit": "kg"},
    {"id": "mortero", "quantity": "2", "unit": "saco de 25 kg", "price": "0.01"}])
def test_ai_cannot_introduce_invalid_data(item):
    with pytest.raises(ValueError):
        validate_proposal({"items": [item], "unmatched": []}, CATALOG)


def test_ollama_http_contract(monkeypatch):
    import ai
    def post(url, **kwargs):
        assert url == "http://127.0.0.1:11434/api/chat"
        assert kwargs["json"]["stream"] is False
        assert "price_gross" not in kwargs["json"]["messages"][1]["content"]
        class Response:
            def raise_for_status(self): pass
            def json(self):
                return {"message": {"content": json.dumps({"items": [
                    {"id": "mortero", "quantity": "2", "unit": "saco de 25 kg"}], "unmatched": []})}}
        return Response()
    monkeypatch.setattr(ai.requests, "post", post)
    assert propose("Dos sacos de mortero", CATALOG)[0][0]["quantity"] == "2"


def test_app_flow(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    db = tmp_path / "app.sqlite3"
    store = Store(db)
    store.update_catalog(CATALOG, {})
    monkeypatch.setenv("FACTURA_DB", str(db))
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
    assert not app.exception
    for label, value in [("Emisor", "Empresa de ejemplo"), ("Destinatario", "Cliente de ejemplo"), ("Obra / destino", "Obra de ejemplo")]:
        next(x for x in app.text_input if x.label == label).set_value(value)
    next(x for x in app.button if x.label == "Generar y guardar PDF").click()
    app.run(timeout=30)
    assert not app.exception
    assert len(store.history()) == 1
    app.sidebar.radio[0].set_value("Historial").run()
    assert not app.exception
