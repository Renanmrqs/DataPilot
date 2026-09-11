import pandas as pd

from pathlib import Path

sales_path = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "raw"
    / "3 - Aprofundando em Qlik_Sales.csv"
)

sales = pd.read_csv(
    sales_path,
    sep=None,
    engine="python",
)

print("\nPrimeiras linhas:")
print(sales.head().to_string(index=False))

print("\nValores monetários:")
print(
    sales[
        [
            "Unit Price",
            "Extended Amount",
            "Product Standard Cost",
            "Total Product Cost",
            "Sales Amount",
        ]
    ].head(10).to_string(index=False)
)

print("\nDatas:")
print(
    sales[
        ["OrderDateKey", "DueDateKey", "ShipDateKey"]
    ].head(10).to_string(index=False)
)