"""Download medicine prices from PROFECO's "Quien es Quien en los Precios" open data.

Source: datos.gob.mx (CKAN DataStore API), published by PROFECO under CC BY 4.0.
Only the "Medicamentos" category of the second fortnight of July 2026 is used.

    python -m farmacias.data
"""
from __future__ import annotations

import csv
import io
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

API = "https://www.datos.gob.mx/api/3/action/datastore_search"
USER_AGENT = "farmacias-mx/0.1 (open-data price analysis)"
RESOURCE = "40f64926-bd6b-4642-8e04-e767d9775d4d"      # July 2026, second fortnight
FIELDS = ["producto", "presentacion", "precio", "cadena_comercial", "giro",
          "nombre_comercial", "estado", "municipio"]
PAGE_SIZE = 32000
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "medicamentos_2026-07-q2.csv.gz"


def fetch_page(offset: int, limit: int = PAGE_SIZE) -> list[list[str]]:
    """One page of medicine rows; the category filter is applied by the server."""
    query = urllib.parse.urlencode({
        "resource_id": RESOURCE, "fields": ",".join(FIELDS), "limit": limit, "offset": offset,
        "filters": json.dumps({"categoria": "Medicamentos"}), "sort": "_id",
        "records_format": "csv", "include_total": "false",
    })
    request = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.load(response)
    return list(csv.reader(io.StringIO(payload["result"]["records"])))


def download() -> None:
    rows: list[list[str]] = []
    while True:
        page = fetch_page(offset=len(rows))
        rows += page
        if len(page) < PAGE_SIZE:
            break
        time.sleep(0.5)
    DATA_FILE.parent.mkdir(exist_ok=True)
    pd.DataFrame(rows, columns=FIELDS).to_csv(DATA_FILE, index=False)
    print(f"{len(rows):,} rows saved to {DATA_FILE.name}")


def load() -> pd.DataFrame:
    return pd.read_csv(DATA_FILE, dtype=str)


if __name__ == "__main__":
    download()
