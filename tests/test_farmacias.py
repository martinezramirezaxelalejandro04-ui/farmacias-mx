import pandas as pd
import pytest

from farmacias import analysis
from farmacias.analysis import basket_cost, chain_index, clean, spread_by_medicine

COLUMNS = ["producto", "presentacion", "precio", "cadena_comercial", "giro",
           "nombre_comercial", "estado", "municipio"]


def raw(rows):
    """rows: (product, price, chain, store)"""
    return pd.DataFrame(
        [[product, "Caja con 10 Tabletas", str(price), chain, "Farmacias", store, "Jalisco",
          "Guadalajara"] for product, price, chain, store in rows], columns=COLUMNS, dtype=str)


@pytest.fixture(autouse=True)
def small_thresholds(monkeypatch):
    monkeypatch.setattr(analysis, "MIN_STORES_PER_ITEM", 4)
    monkeypatch.setattr(analysis, "MIN_STORES_PER_CHAIN", 2)
    monkeypatch.setattr(analysis, "MIN_ITEMS_PER_CHAIN", 1)
    monkeypatch.setattr(analysis, "BASKET_SIZE", 2)


def two_chains():
    rows = []
    for product, cheap, pricey in [("Tempra", 80, 120), ("Aspirina", 40, 60)]:
        rows += [(product, cheap, "Barata", f"Barata {n}") for n in range(2)]
        rows += [(product, pricey, "Cara", f"Cara {n}") for n in range(2)]
    return raw(rows)


def test_repeated_visits_become_one_median_price_per_store():
    prices = clean(raw([("Tempra", 90, "A", "Tienda 1"), ("Tempra", 100, "A", "Tienda 1"),
                        ("Tempra", 110, "A", "Tienda 1")]))
    assert list(prices["price"]) == [100]


def test_spelling_differences_do_not_split_a_medicine():
    data = raw([("Losartán", 50, "A", "Tienda 1"), ("LOSARTAN ", 50, "A", "Tienda 2")])
    assert clean(data)["item_key"].nunique() == 1


def test_typing_errors_and_zero_prices_are_removed():
    rows = [("Tempra", 100, "A", f"Tienda {n}") for n in range(8)]
    prices = clean(raw(rows + [("Tempra", 10000, "A", "Error"), ("Tempra", 0, "A", "Cero")]))
    assert len(prices) == 8 and prices["price"].max() == 100


def test_spread_compares_pricey_and_cheap_stores():
    table = spread_by_medicine(clean(two_chains())).set_index("medicine")
    tempra = table.loc["Tempra, Caja con 10 Tabletas"]
    assert tempra["stores"] == 4
    assert tempra["cheap_store_price"] == 80 and tempra["pricey_store_price"] == 120
    assert tempra["spread_pct"] == 50.0
    assert tempra["pesos_between_stores"] == 40


def test_chain_index_is_relative_to_the_typical_price_of_each_medicine():
    table = chain_index(clean(two_chains())).set_index("chain")["price_index"]
    assert table["Barata"] == 80.0      # 80/100 and 40/50
    assert table["Cara"] == 120.0


def test_basket_only_compares_chains_that_carry_every_medicine():
    data = pd.concat([two_chains(),
                      raw([("Tempra", 70, "Incompleta", f"Incompleta {n}") for n in range(2)])])
    table = basket_cost(clean(data)).set_index("chain")["basket_cost_mxn"]
    assert dict(table) == {"Barata": 120, "Cara": 180}
