from datetime import datetime, timezone
from pathlib import Path
import json
import os
import uuid

import pandas as pd
import streamlit as st

from ai import propose
from core import calculate
from pdf_export import render_pdf
from storage import Store
from supplier import refresh

ROOT = Path(__file__).resolve().parent
store = Store(os.environ.get("FACTURA_DB", str(ROOT / "data/factura.sqlite3")))
st.set_page_config(page_title="FacturaApp · Materiales de obra", page_icon="🏗️", layout="wide")
st.markdown("""<style>
.stApp {background:#f5f7f8}
.block-container {max-width:1180px;padding-top:2rem}
h1,h2,h3 {color:#193c47}
[data-testid="stMetric"] {background:white;border:1px solid #dae3e7;border-radius:12px;padding:18px}
[data-testid="stSidebar"] {background:#eaf1f2}
[data-testid="stAlert"] {background:#e8f2f5;color:#193c47}
[data-testid="stAlert"] p {color:#193c47}
</style>""", unsafe_allow_html=True)

if not store.catalog():
    snapshot = json.loads((ROOT / "examples/catalog_snapshot.json").read_text(encoding="utf-8"))
    store.update_catalog(snapshot, {})
    # El snapshot conserva su fecha real, no se presenta como una consulta nueva.
    with store.connect() as db:
        db.execute("DELETE FROM metadata WHERE key='last_attempt'")

with st.sidebar:
    st.title("FacturaApp")
    st.caption("Materiales, precios y documentos")
    page = st.radio("Navegación", ["Nuevo documento", "Catálogo y precios", "Historial"])
    auto = st.toggle("Actualizar tarifas automáticamente", value=True)
    st.caption("Consulta al abrir o interactuar si han pasado 24 h. No se ejecuta con la aplicación cerrada.")
    refresh_now = st.button("Actualizar precios ahora", use_container_width=True)
    meta = store.metadata()
    last = meta.get("last_attempt")
    due = not last or (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() >= 86400
    if refresh_now or (auto and due):
        with st.spinner("Consultando Pochiche…"):
            products, errors = refresh()
            store.update_catalog(products, errors)
        if products:
            st.success(f"{len(products)} referencias actualizadas.")
        if errors:
            st.warning("Hay tarifas que no se han podido actualizar. Conservan su fecha anterior.")
    st.divider()
    st.caption("Aplicación local · Sin API de pago")
    st.caption("Los precios son referencias de un proveedor, no una media del mercado.")

catalog = store.catalog()
metadata = store.metadata()
errors = json.loads(metadata.get("refresh_errors", "{}"))
st.title("Materiales claros. Documentos ordenados.")
st.caption("Prepara el documento, revisa los importes y guarda una copia en PDF.")
if errors:
    st.warning("La última consulta no pudo actualizar todas las referencias. Revisa las fechas del catálogo antes de usar sus precios.")

if page == "Catálogo y precios":
    st.subheader("Tarifas publicadas por Pochiche")
    st.info("Precios por saco de 25 kg, IVA incluido. No incluyen transporte ni descuentos negociados. "
            "El desglose de esta demo usa un IVA del 21 %. Confirma las condiciones de la operación con el proveedor.")
    rows = [{"Material": p["name"], "Unidad": p["unit"], "Precio con IVA (€)": p["price_gross"],
             "Consultado (UTC)": p["checked_at"], "Validez publicada": p.get("price_valid_until"),
             "Fuente": p["source"]} for p in catalog.values()]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
                 column_config={"Fuente": st.column_config.LinkColumn("Ficha del proveedor", display_text="Abrir ficha")})
    st.caption("Conexión mediante las fichas públicas de producto. No existe afiliación ni una API oficial contratada.")

elif page == "Historial":
    st.subheader("Documentos guardados")
    query = st.text_input("Buscar por número, destinatario u obra")
    records = store.history()
    selected = [r for r in records if query.casefold() in (r["number"] + r["body"]).casefold()]
    if not selected:
        st.info("Todavía no hay documentos que coincidan con la búsqueda.")
    for row in selected:
        doc = json.loads(row["body"])
        with st.expander(f"{row['number']} · {doc['recipient']} · {doc['total']} EUR"):
            st.write(f"Obra: {doc['worksite']}")
            st.caption("Se conserva el precio y el PDF de la fecha de generación.")
            st.dataframe(pd.DataFrame(doc["lines"])[["name", "quantity", "unit_gross", "gross"]], hide_index=True)
            st.download_button("Descargar PDF", store.pdf(row["id"]), file_name=row["number"] + ".pdf",
                               mime="application/pdf", key=f"download_{row['id']}")
else:
    if "items" not in st.session_state:
        st.session_state["items"] = [{"Material": catalog["cemento_gris"]["name"], "Cantidad": "1"}]
        st.session_state["editor_version"] = 0
    with st.expander("Preparar materiales con IA local", expanded=False):
        st.caption("Requiere Ollama y un modelo instalado en tu equipo. La IA interpreta el texto; no inventa precios.")
        text = st.text_area("Describe los materiales", placeholder="20 sacos de cemento gris y 10 sacos de mortero", max_chars=4000)
        model = st.text_input("Modelo de Ollama", value=os.environ.get("OLLAMA_MODEL", "qwen2.5:3b"))
        if st.button("Proponer materiales con IA"):
            try:
                with st.spinner("Interpretando la petición…"):
                    items, unmatched = propose(text, catalog, model=model)
                st.session_state["proposal"] = items
                st.session_state["unmatched"] = unmatched
            except ValueError as exc:
                st.error(str(exc))
        if st.session_state.get("proposal"):
            proposal = st.session_state["proposal"]
            st.dataframe([{"Material": catalog[x["id"]]["name"], "Cantidad": x["quantity"],
                           "Unidad": catalog[x["id"]]["unit"]} for x in proposal], hide_index=True)
            for missing in st.session_state.get("unmatched", []):
                st.warning("Sin identificar: " + missing[:300])
            st.caption("Revisa materiales, cantidades y cualquier elemento sin identificar antes de usar la propuesta.")
            if st.button("Usar estas líneas en el documento"):
                st.session_state["items"] = [{"Material": catalog[x["id"]]["name"], "Cantidad": x["quantity"]} for x in proposal]
                st.session_state["editor_version"] += 1
                st.rerun()

    left, right = st.columns([1, 1])
    with left:
        st.subheader("1. Datos del documento")
        kind = st.selectbox("Documento", ["Presupuesto de materiales", "Factura de demostración"])
        issuer = st.text_input("Emisor", placeholder="Nombre de tu empresa")
        recipient = st.text_input("Destinatario", placeholder="Cliente o empresa destinataria")
        worksite = st.text_input("Obra / destino", placeholder="Nombre o dirección de la obra")
    with right:
        st.subheader("2. Materiales")
        st.caption("Elige la referencia exacta. Las cantidades se expresan en sacos completos de 25 kg.")
        names = {p["name"]: key for key, p in catalog.items()}
        edited = st.data_editor(pd.DataFrame(st.session_state["items"]), num_rows="dynamic", hide_index=True,
            use_container_width=True, key=f"lines_{st.session_state['editor_version']}",
            column_config={"Material": st.column_config.SelectboxColumn(options=list(names), required=True),
                           "Cantidad": st.column_config.TextColumn(required=True)})
        st.caption("Puedes añadir o eliminar filas en la tabla. Los importes proceden del catálogo.")
    notes = st.text_area("Observaciones", max_chars=1000, placeholder="Condiciones, referencia de la obra…")
    items, valid = [], True
    for row in edited.to_dict("records"):
        if row.get("Material") not in names:
            valid = False
            break
        items.append({"id": names[row["Material"]], "quantity": row.get("Cantidad")})
    totals = None
    try:
        if not valid:
            raise ValueError("Selecciona un material válido en todas las filas.")
        totals = calculate(items, catalog)
    except ValueError as exc:
        st.warning(str(exc))
    if totals:
        st.subheader("3. Revisión")
        st.dataframe([{"Material": r["name"], "Cantidad": r["quantity"], "Precio con IVA (€)": r["unit_gross"],
                       "Base (€)": r["net"], "IVA (€)": r["tax"], "Total (€)": r["gross"]} for r in totals["lines"]],
                     hide_index=True, use_container_width=True)
        a, b, c = st.columns(3)
        a.metric("Base", totals["subtotal"] + " €")
        b.metric("IVA", totals["tax"] + " €")
        c.metric("Total", totals["total"] + " €")
        oldest = min(line["checked_at"] for line in totals["lines"])
        st.caption(f"Tarifa más antigua utilizada: {oldest}. Precios de referencia; transporte y descuentos no incluidos.")
    st.info("La factura de demostración no acredita una compra. Para compras reales se utiliza la factura emitida por el proveedor.")
    details = dict(kind=kind, issuer=issuer, recipient=recipient, worksite=worksite, notes=notes)
    fingerprint = json.dumps({"details": details, "items": items, "totals": totals}, sort_keys=True, ensure_ascii=False)
    if fingerprint != st.session_state.get("fingerprint"):
        st.session_state["fingerprint"] = fingerprint
        st.session_state["request_key"] = uuid.uuid4().hex
        st.session_state.pop("result", None)
    if st.button("Generar y guardar PDF", type="primary", disabled=totals is None):
        try:
            result = store.save_document(details, items, catalog, st.session_state["request_key"], render_pdf)
            st.session_state["result"] = result
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error("No se ha podido guardar el documento. Comprueba el acceso a la carpeta de datos.")
    if st.session_state.get("result"):
        result = st.session_state["result"]
        st.success("Documento guardado: " + result["number"])
        st.download_button("Descargar PDF", bytes(result["pdf"]), file_name=result["number"] + ".pdf", mime="application/pdf")
