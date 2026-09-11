from pathlib import Path

import pandas as pd


data_directory = Path(__file__).resolve().parent.parent / "data" / "raw"

for csv_path in data_directory.glob("*.csv"):
    dataframe = pd.read_csv(
        csv_path,
        sep=None,
        engine="python",
    )

    print(f"\nArquivo: {csv_path.name}")
    print(f"Linhas: {dataframe.shape[0]}")
    print(f"Colunas: {dataframe.shape[1]}")
    print("Campos:")

    for column in dataframe.columns:
        nulls = dataframe[column].isna().sum()
        unique_values = dataframe[column].nunique(dropna=True)

        print(
            f"  {column} | "
            f"tipo: {dataframe[column].dtype} | "
            f"nulos: {nulls} | "
            f"únicos: {unique_values}"
        )