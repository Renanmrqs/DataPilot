# DataPilot

Projeto de estudo de BI + IA, desenvolvido aos poucos a partir de CSVs exportados de um modelo de teste do Qlik.

## Estado atual

- CSVs originais em `data/raw/`.
- Scripts para inspecionar os dados em `scripts/`.
- Transformacao de Sales em `src/etl/transform_sales.py`.
- Sales tratada salva em `data/processed/sales.csv` ao executar o transformador.
- Pastas `sql/` e `tests/` reservadas para etapas futuras.
- Calendar ainda pendente, para uma proxima etapa.

## Modelo de dados

Sales e a tabela fato: cada linha representa um item de pedido, identificado por `SalesOrderLineKey`.
Customer, Product, Reseller e Sales-Territory sao dimensoes.
Sales-Order tem uma relacao 1:1 com Sales por `SalesOrderLineKey`.

## Executar no PowerShell

Na pasta raiz do projeto, usando o ambiente virtual existente com pandas:

```powershell
# Inspecionar todos os CSVs originais
.\.venv\Scripts\python.exe scripts/inspect_all_date.py

# Ver uma amostra de Sales
.\.venv\Scripts\python.exe scripts/inspect_sales.py

# Transformar e salvar Sales
.\.venv\Scripts\python.exe src/etl/transform_sales.py
```

## O que a transformacao faz

1. Le o CSV de Sales em `data/raw/`.
2. Remove os simbolos de moeda e separadores de milhar e converte os valores para numeros decimais.
3. Converte percentuais para fracao: por exemplo, `5%` vira `0.05`.
4. Converte OrderDateKey, DueDateKey e ShipDateKey para datas.
5. Salva o resultado em `data/processed/sales.csv`, sem adicionar uma coluna de indice.

Os originais ficam preservados. Executar novamente substitui apenas o CSV tratado.
Datas ausentes continuam vazias; datas invalidas tambem sao convertidas em valores ausentes pelo script atual.
O CSV salva as datas como `AAAA-MM-DD`, mas nao guarda os tipos do pandas: ao reler, e preciso converter as colunas de data novamente.

## Proxima sessao

Revisar juntos a Sales salva e escolher um pequeno proximo passo. A dimensao Calendar fica para depois.
