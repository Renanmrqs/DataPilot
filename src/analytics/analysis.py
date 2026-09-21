"""Calculate all cards and chart points using approved SQL and validated filters."""
from fastapi import HTTPException

from src.analytics.catalog import DIMENSIONS, METRICS, RECIPES

AGGREGATES = """
    COUNT(*) AS line_count,
    COUNT(DISTINCT order_number) AS orders,
    COUNT(DISTINCT product_key) AS products,
    COALESCE(SUM(quantity), 0) AS units,
    COALESCE(SUM(revenue_cents), 0) AS revenue_cents,
    COALESCE(SUM(cost_cents), 0) AS cost_cents
"""


def available_values(connection):
    result = {}
    for column in DIMENSIONS:
        result[column] = [
            row[0] for row in connection.execute(
                f"SELECT DISTINCT {column} FROM sales_detail ORDER BY {column}"
            )
        ]
    dates = connection.execute("SELECT MIN(order_date), MAX(order_date) FROM sales").fetchone()
    result["date_range"] = {"start_date": dates[0], "end_date": dates[1]}
    return result


def add_ratios(row):
    values = dict(row)
    revenue, cost = values["revenue_cents"], values["cost_cents"]
    orders = values["orders"]
    values["gross_profit_cents"] = revenue - cost
    values["gross_margin_pct"] = 100 * (revenue - cost) / revenue if revenue else None
    values["average_order_value_cents"] = revenue / orders if orders else None
    values["units_per_order"] = values["units"] / orders if orders else None
    return values


def filter_sql(filters, options):
    start = filters.get("start_date")
    end = filters.get("end_date")
    if start and end and start > end:
        raise HTTPException(422, "A data inicial não pode ser posterior à data final.")

    clauses, parameters = [], []
    for column in DIMENSIONS:
        value = filters.get(column)
        if value is not None:
            if value not in options[column]:
                raise HTTPException(422, f"Filtro de {DIMENSIONS[column][1]} não encontrado na base.")
            clauses.append(f"{column} = ?")
            parameters.append(value)
    for value, operator in ((start, ">="), (end, "<=")):
        if value:
            clauses.append(f"order_date {operator} ?")
            parameters.append(value)
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), parameters


def make_chart(title, metric, rows, kind, dimension):
    label, value_format = METRICS[metric]
    return {
        "title": title,
        "metric": metric,
        "metric_label": label,
        "format": value_format,
        "kind": kind,
        "dimension": dimension,
        "points": [{"label": row["label"], "value": row[metric]} for row in rows],
    }


def build_analysis(connection, plan, current_filters):
    options = available_values(connection)
    filters = dict(current_filters)
    filters.update(plan.filters.model_dump(mode="json", exclude_unset=True))
    filters["start_date"] = filters.get("start_date") or options["date_range"]["start_date"]
    filters["end_date"] = filters.get("end_date") or options["date_range"]["end_date"]
    where, parameters = filter_sql(filters, options)
    recipe = RECIPES[plan.topic]

    summary = add_ratios(connection.execute(
        "SELECT " + AGGREGATES + " FROM sales_detail" + where, parameters
    ).fetchone())
    monthly = [
        add_ratios(row) for row in connection.execute(
            "SELECT substr(order_date, 1, 7) AS label, " + AGGREGATES
            + " FROM sales_detail" + where + " GROUP BY label ORDER BY label",
            parameters,
        )
    ]
    column, dimension_label = DIMENSIONS[plan.breakdown]
    groups = [
        add_ratios(row) for row in connection.execute(
            f"SELECT {column} AS label, " + AGGREGATES
            + " FROM sales_detail" + where + f" GROUP BY {column} ORDER BY revenue_cents DESC",
            parameters,
        )
    ]
    charts = [
        make_chart(
            METRICS[recipe["trend"]][0] + " por mês",
            recipe["trend"], monthly, "line", "month",
        ),
        make_chart(
            METRICS[recipe["breakdown"]][0] + " por " + dimension_label,
            recipe["breakdown"], groups, "bar", plan.breakdown,
        ),
    ]
    if plan.topic == "products":
        ranking_metric = "units" if plan.ranking == "units" else "revenue_cents"
        ranking_label = "unidades vendidas" if plan.ranking == "units" else "receita"
        top_products = [
            add_ratios(row) for row in connection.execute(
                "SELECT product AS label, " + AGGREGATES
                + " FROM sales_detail" + where
                + f" GROUP BY product_key, product ORDER BY {ranking_metric} DESC, product_key LIMIT 10",
                parameters,
            )
        ]
        charts.append(make_chart(
            "Até 10 produtos por " + ranking_label, ranking_metric, top_products, "bar", "product"
        ))
    else:
        charts.append(make_chart(
            METRICS[recipe["support"]][0] + " por mês",
            recipe["support"], monthly, "line", "month",
        ))

    notes = [
        "O painel analisa o período e os filtros indicados abaixo; o painel principal continua com sua seleção original.",
        "Os gráficos ajudam a investigar padrões, mas não comprovam causas nem definem se um valor é alto ou baixo.",
        "Meses sem vendas são omitidos; o primeiro e o último mês podem estar incompletos.",
    ]
    if filters.get("category"):
        notes.append("O ticket considera apenas os itens da categoria selecionada, não o pedido completo.")
    if plan.topic == "margin":
        notes.append("Resultado bruto desconta somente o custo dos produtos; não representa lucro líquido.")
    if plan.topic == "products":
        notes.append(f"O ranking mostra até 10 produtos por {ranking_label}; os indicadores consideram todos os produtos selecionados.")

    panel = {
        "topic": plan.topic,
        "title": recipe["title"],
        "filters": filters,
        "notes": notes,
        "empty": summary["line_count"] == 0,
        "kpis": [
            {"label": METRICS[key][0], "format": METRICS[key][1], "value": summary[key]}
            for key in recipe["kpis"]
        ],
        "charts": charts,
    }
    # Metric names preserve the cents suffix for the existing AI serialization.
    context = {
        "topic": panel["title"],
        "summary": summary,
        "filters": filters,
        "notes": notes,
        "charts": [
            {
                "title": chart["title"],
                "rows": [{"label": point["label"], chart["metric"]: point["value"]}
                         for point in chart["points"]],
            }
            for chart in charts
        ],
    }
    return panel, context
