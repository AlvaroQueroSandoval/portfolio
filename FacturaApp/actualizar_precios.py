"""Consulta manual o programable: python actualizar_precios.py."""
from pathlib import Path
import json
import os
from storage import Store
from supplier import refresh

if __name__ == "__main__":
    store = Store(os.environ.get("FACTURA_DB", str(Path(__file__).resolve().parent / "data/factura.sqlite3")))
    products, errors = refresh()
    store.update_catalog(products, errors)
    print(json.dumps({"actualizados": list(products), "errores": errors}, ensure_ascii=True, indent=2))
    raise SystemExit(1 if errors else 0)
