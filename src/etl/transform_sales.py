from pathlib import Path

import pandas as pd


project_root = Path(__file__).resolve().parents[2]
sales_path = project_root / "data" / "raw" / "3 - Aprofundando em Qlik_Sales.csv"

sales = pd.read_csv(
    sales_path,
    sep=None,
    engine="python",
)


money_columns = [
    "Unit Price",
    "Extended Amount",
    "Product Standard Cost",
    "Total Product Cost",
    "Sales Amount",
]

for column in money_columns:
    sales[column] = (
        sales[column]
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .astype("float64")
    )


sales["Unit Price Discount Pct"] = (
    sales["Unit Price Discount Pct"]
    .str.replace("%", "", regex=False)
    .astype("float64")
    .div(100)
)


date_columns = [
    "OrderDateKey",
    "DueDateKey",
    "ShipDateKey",
]

for column in date_columns:
    sales[column] = pd.to_datetime(
        sales[column].astype("Int64").astype("string"),
        format="%Y%m%d",
        errors="coerce",
    )


print(sales.head().to_string(index=False))

print("\nTipos após a transformação:")
print(sales.dtypes)

# Salva uma copia tratada, mantendo o CSV original em data/raw.
output_directory = project_root / "data" / "processed"
output_directory.mkdir(parents=True, exist_ok=True)
output_path = output_directory / "sales.csv"

sales.to_csv(output_path, index=False, date_format="%Y-%m-%d")
print(f"\nSales salva em: {output_path} ({len(sales)} linhas)")
