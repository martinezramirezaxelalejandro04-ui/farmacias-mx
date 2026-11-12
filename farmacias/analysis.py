"""How much the same box of medicine costs depending on where you buy it.

A "medicine" here is a product name plus its exact presentation (for example
"Tempra, box of 20 tablets of 500 mg"). For brand-name products that is the
identical box. For generics listed by active ingredient ("Losartan, 30 tablets
of 50 mg") it is the same drug, dose and pack size, possibly from different
laboratories.
"""
from __future__ import annotations

import pandas as pd

OUTLIER_FACTOR = 3        # a price 3x above or below the medicine's median is a typing error
MIN_STORES_PER_ITEM = 30
MIN_STORES_PER_CHAIN = 8
MIN_ITEMS_PER_CHAIN = 100
BASKET_SIZE = 20


def text_key(series: pd.Series) -> pd.Series:
    """Lower case, no accents, single spaces."""
    return (series.astype("string").str.normalize("NFKD").str.encode("ascii", "ignore")
            .str.decode("ascii").str.lower().str.strip().str.replace(r"\s+", " ", regex=True))


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """One price per medicine per store, typing errors removed."""
    df = pd.DataFrame({
        "medicine": raw["producto"].str.strip() + ", " + raw["presentacion"].str.strip(),
        "item_key": text_key(raw["producto"]) + " | " + text_key(raw["presentacion"]),
        "store_key": text_key(raw["nombre_comercial"]) + " @ " + text_key(raw["municipio"]),
        "chain": raw["cadena_comercial"].str.strip(),
        "price": pd.to_numeric(raw["precio"], errors="coerce"),
    })
    df = df[df["price"] > 0]
    stores = df.groupby(["item_key", "store_key"], as_index=False).agg(
        medicine=("medicine", "first"), chain=("chain", "first"), price=("price", "median"))
    typical = stores.groupby("item_key")["price"].transform("median")
    keep = stores["price"].between(typical / OUTLIER_FACTOR, typical * OUTLIER_FACTOR)
    return stores[keep].reset_index(drop=True)


def _comparable(prices: pd.DataFrame) -> pd.DataFrame:
    """Only medicines found in enough stores, with their national median price attached."""
    stats = prices.groupby("item_key")["price"].agg(stores="count", median_price="median")
    merged = prices.merge(stats[stats["stores"] >= MIN_STORES_PER_ITEM], on="item_key")
    return merged.assign(relative_price=merged["price"] / merged["median_price"])


def spread_by_medicine(prices: pd.DataFrame) -> pd.DataFrame:
    """Cheap store (10th percentile) vs pricey store (90th percentile) for each medicine."""
    comparable = _comparable(prices)
    grouped = comparable.groupby(["item_key", "medicine"])["price"]
    table = grouped.agg(stores="count", cheap_store_price=lambda s: s.quantile(0.10),
                        typical_price="median",
                        pricey_store_price=lambda s: s.quantile(0.90)).reset_index()
    table["spread_pct"] = (100 * (table["pricey_store_price"] / table["cheap_store_price"] - 1)
                           ).round(1)
    table["pesos_between_stores"] = (table["pricey_store_price"]
                                     - table["cheap_store_price"]).round(2)
    return table.drop(columns="item_key").sort_values("spread_pct", ascending=False
                                                      ).reset_index(drop=True)


def chain_index(prices: pd.DataFrame) -> pd.DataFrame:
    """Price level of each chain for identical medicines. 100 = typical national price."""
    comparable = _comparable(prices)
    per_item = comparable.groupby(["chain", "item_key"], as_index=False)["relative_price"].mean()
    table = per_item.groupby("chain", as_index=False).agg(
        medicines_compared=("item_key", "count"), price_index=("relative_price", "mean"))
    sizes = comparable.groupby("chain")["store_key"].nunique().rename("stores")
    table = table.merge(sizes, on="chain")
    table = table[(table["stores"] >= MIN_STORES_PER_CHAIN)
                  & (table["medicines_compared"] >= MIN_ITEMS_PER_CHAIN)]
    table["price_index"] = (100 * table["price_index"]).round(1)
    return table.sort_values("price_index").reset_index(drop=True)[
        ["chain", "stores", "medicines_compared", "price_index"]]


def _chain_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Median price of each medicine (rows) in each large chain (columns)."""
    stores = prices.groupby("chain")["store_key"].nunique()
    large = stores[stores >= MIN_STORES_PER_CHAIN].index
    return (prices[prices["chain"].isin(large)]
            .groupby(["medicine", "chain"])["price"].median().unstack())


def basket_medicines(prices: pd.DataFrame) -> list[str]:
    """The medicines carried by the largest number of chains."""
    return list(_chain_prices(prices).notna().sum(axis=1).nlargest(BASKET_SIZE).index)


def basket_cost(prices: pd.DataFrame) -> pd.DataFrame:
    """Cost of the same basket of widely sold medicines in each chain that carries all of it."""
    basket = basket_medicines(prices)
    complete = _chain_prices(prices).loc[basket].dropna(axis=1)
    table = complete.sum().round(0).rename("basket_cost_mxn").reset_index()
    table["medicines_in_basket"] = len(basket)
    return table.sort_values("basket_cost_mxn").reset_index(drop=True)
