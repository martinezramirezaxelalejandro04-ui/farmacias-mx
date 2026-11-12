"""Run the whole analysis:  python -m farmacias"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .analysis import (basket_cost, basket_medicines, chain_index, clean,
                       spread_by_medicine)
from .data import load

OUTPUT = Path(__file__).resolve().parent.parent / "output"
SURFACE, INK, INK_SECONDARY, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
AXIS, BLUE, RED = "#c3c2b7", "#2a78d6", "#e34948"
SOURCE = "Fuente: PROFECO, Quién es Quién en los Precios (datos.gob.mx, CC BY 4.0). Julio 2026."


def _figure(title: str, subtitle: str, height: float):
    fig, ax = plt.subplots(figsize=(8, height), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    fig.text(0.02, 1 - 0.22 / height, title, fontsize=13, fontweight="bold", color=INK, va="top")
    fig.text(0.02, 1 - 0.55 / height, subtitle, fontsize=9.5, color=INK_SECONDARY, va="top")
    fig.text(0.02, 0.12 / height, SOURCE, fontsize=8, color=MUTED, va="bottom")
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(colors=MUTED, length=0, labelsize=9.5, labelcolor=INK_SECONDARY)
    ax.xaxis.set_visible(False)
    return fig, ax


def chart_chain_index(table: pd.DataFrame, path: Path) -> None:
    height = 0.36 * len(table) + 1.5
    fig, ax = _figure("Los mismos medicamentos cuestan distinto según la cadena",
                      "Precio de medicamentos iguales frente al precio típico nacional.", height)
    values = (table["price_index"] - 100).to_numpy()
    labels = [f"{row.chain}  ({row.stores} tiendas)" for row in table.itertuples()]
    bars = ax.barh(labels, values, height=0.62, color=[BLUE if v < 0 else RED for v in values])
    reach = abs(values).max()
    for bar, value in zip(bars, values):
        ax.text(value + reach * 0.02 * (1 if value >= 0 else -1),
                bar.get_y() + bar.get_height() / 2, f"{value:+.1f}%", va="center",
                ha="left" if value >= 0 else "right", fontsize=9, color=INK)
    ax.axvline(0, color=AXIS, linewidth=1)
    ax.set_xlim(-reach * 1.4, reach * 1.4)
    ax.invert_yaxis()
    fig.subplots_adjust(left=0.36, right=0.97, top=1 - 0.9 / height, bottom=0.45 / height)
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def chart_basket(table: pd.DataFrame, path: Path) -> None:
    height = 0.36 * len(table) + 1.5
    size = int(table["medicines_in_basket"].iloc[0])
    fig, ax = _figure(f"La misma lista de {size} medicamentos: de "
                      f"\\${table['basket_cost_mxn'].min():,.0f} a "
                      f"\\${table['basket_cost_mxn'].max():,.0f}",
                      "Costo de comprar los mismos medicamentos comunes en cada cadena.", height)
    bars = ax.barh(table["chain"], table["basket_cost_mxn"], height=0.62, color=BLUE)
    for bar, value in zip(bars, table["basket_cost_mxn"]):
        ax.text(value + table["basket_cost_mxn"].max() * 0.012,
                bar.get_y() + bar.get_height() / 2, f"${value:,.0f}", va="center",
                fontsize=9, color=INK)
    ax.set_xlim(0, table["basket_cost_mxn"].max() * 1.12)
    ax.invert_yaxis()
    fig.subplots_adjust(left=0.27, right=0.97, top=1 - 0.9 / height, bottom=0.45 / height)
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    (OUTPUT / "charts").mkdir(parents=True, exist_ok=True)
    raw = load()
    prices = clean(raw)
    spread, chains, basket = spread_by_medicine(prices), chain_index(prices), basket_cost(prices)
    spread.to_csv(OUTPUT / "spread_by_medicine.csv", index=False, encoding="utf-8-sig")
    chains.to_csv(OUTPUT / "chain_index.csv", index=False, encoding="utf-8-sig")
    basket.to_csv(OUTPUT / "basket_cost.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"medicine": basket_medicines(prices)}).to_csv(
        OUTPUT / "basket_medicines.csv", index=False, encoding="utf-8-sig")
    chart_chain_index(chains, OUTPUT / "charts" / "chain_index.png")
    chart_basket(basket, OUTPUT / "charts" / "basket_cost.png")
    print(f"{len(raw):,} raw rows -> {len(prices):,} store prices, "
          f"{prices['item_key'].nunique()} medicines, {prices['store_key'].nunique()} stores")
    print(f"spread: {len(spread)} medicines, median {spread['spread_pct'].median()}%, "
          f"share >= 30%: {(spread['spread_pct'] >= 30).mean():.0%}, "
          f"median pesos {spread['pesos_between_stores'].median()}")
    print(chains.to_string(index=False).encode("ascii", "replace").decode())
    print(basket.to_string(index=False).encode("ascii", "replace").decode())


if __name__ == "__main__":
    main()
