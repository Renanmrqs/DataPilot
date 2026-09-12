from pathlib import Path

import pandas as pd

project_root = Path(__file__).resolve().parents[1]

original = pd.read_csv(
    project_root / "data/raw/3 - Aprofundando em Qlik_Sales.csv",
    sep=None,
    engine="python",
)

tratado = pd.read_csv(project_root / "data/processed/sales.csv")

chave = "SalesOrderLineKey"

print("QUANTIDADE DE LINHAS")
print("Original:", len(original))
print("Tratado:", len(tratado))

print("\nCHAVES VAZIAS")
print("Original:", original[chave].isna().sum())
print("Tratado:", tratado[chave].isna().sum())

print("\nCHAVES REPETIDAS — ocorrências além da primeira")
print("Original:", original[chave].duplicated().sum())
print("Tratado:", tratado[chave].duplicated().sum())

print("\nCHAVES E ORDEM PRESERVADAS")
print(original[chave].equals(tratado[chave]))

print("\nDATAS")
for coluna in ["OrderDateKey", "DueDateKey", "ShipDateKey"]:
    datas = pd.to_datetime(
        tratado[coluna],
        format="%Y-%m-%d",
        errors="coerce",
    )

    print(f"\n{coluna}")
    print("Vazias no original:", original[coluna].isna().sum())
    print("Vazias no tratado:", tratado[coluna].isna().sum())
    print(
        "Preenchidas, mas inválidas no tratado:",
        (tratado[coluna].notna() & datas.isna()).sum(),
    )

print("\nVALORES MONETÁRIOS E DESCONTOS")

print("\nCONFERÊNCIA DE SALES AMOUNT")

# Converte os valores originais para o formato numérico esperado.
valor_esperado = (
    original["Sales Amount"]
    .str.replace("$", "", regex=False)
    .str.replace(",", "", regex=False)
    .astype(float)
)

valor_tratado = tratado["Sales Amount"]

# Uma pequena tolerância evita diferenças irrelevantes de ponto flutuante.
iguais = (valor_esperado - valor_tratado).abs() < 0.000001

print("Valores diferentes:", (~iguais).sum())

print("\nAmostra para conferir visualmente:")
print(pd.DataFrame({
    "original": original["Sales Amount"],
    "esperado": valor_esperado,
    "tratado": valor_tratado,
}).head(10))