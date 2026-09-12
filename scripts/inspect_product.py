import pandas as pd

from pathlib import Path

product_path = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "raw"
    / "3 - Aprofundando em Qlik_Product.csv"
)

product = pd.read_csv(
    product_path,
    sep=None,
    engine="python",
)

print("\nPrimeiras linhas:")
print(product.head().to_string(index=False))

print("\nValores monetários:")
print(
    product[
        [
            "ProductKey",
            "SKU",
            "Product",
            "Standard Cost",
            "Color",
            "List Price",
            "Model",
            "Subcategory",
            "Category"
        ]
    ].head(10).to_string(index=False)
)

print("\nTipos das colunas:")
print(product.dtypes)

print("\nVazios por coluna:")
print(product.isna().sum())

print("\nChaves repetidas:")
print(product["ProductKey"].duplicated().sum())

print("\nSKUs repetidos:")
print(product["SKU"].duplicated().sum())

print("\nProdutos sem cor:")
print(
    product.loc[
        product["Color"].isna(),
        ["ProductKey", "Product", "Color", "Subcategory"],
    ].head(20).to_string(index=False)
)