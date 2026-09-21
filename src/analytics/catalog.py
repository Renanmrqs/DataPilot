"""Approved metrics and analysis layouts. This is the extension point for new topics."""

METRICS = {
    "revenue_cents": ("Receita", "money"),
    "orders": ("Pedidos", "number"),
    "units": ("Unidades vendidas", "number"),
    "average_order_value_cents": ("Ticket médio", "money"),
    "units_per_order": ("Unidades por pedido", "decimal"),
    "gross_profit_cents": ("Resultado bruto", "money"),
    "cost_cents": ("Custo dos produtos", "money"),
    "gross_margin_pct": ("Margem bruta", "percent"),
    "products": ("Produtos vendidos", "number"),
}

RECIPES = {
    "sales": {
        "title": "Análise de vendas",
        "kpis": ["revenue_cents", "orders", "units"],
        "trend": "revenue_cents",
        "breakdown": "revenue_cents",
        "support": "orders",
    },
    "ticket": {
        "title": "Análise do ticket médio",
        "kpis": ["average_order_value_cents", "revenue_cents", "orders", "units_per_order"],
        "trend": "average_order_value_cents",
        "breakdown": "average_order_value_cents",
        "support": "units_per_order",
    },
    "margin": {
        "title": "Análise de margem",
        "kpis": ["gross_margin_pct", "gross_profit_cents", "revenue_cents", "cost_cents"],
        "trend": "gross_margin_pct",
        "breakdown": "gross_margin_pct",
        "support": "gross_profit_cents",
    },
    "products": {
        "title": "Análise de produtos",
        "kpis": ["units", "revenue_cents", "products"],
        "trend": "units",
        "breakdown": "revenue_cents",
        "support": "revenue_cents",
    },
}

DIMENSIONS = {
    "category": ("category", "categoria"),
    "channel": ("channel", "canal"),
    "country": ("country", "país"),
}
