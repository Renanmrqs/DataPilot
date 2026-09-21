"""Read-only analytics API and local dashboard."""
from contextlib import closing
from datetime import date
from pathlib import Path
import sqlite3
import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv
from src.ai.copilot import explain, list_providers
from src.api.analysis import create_analysis_router
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "data" / "processed" / "datapilot.db"
load_dotenv(ROOT / ".env", override=False)


class CopilotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    provider: str = Field(min_length=1, max_length=50)
    model: str = Field(min_length=1, max_length=150)
    question: str = Field(min_length=1, max_length=2000)
    start_date: date | None = None
    end_date: date | None = None
    channel: str | None = None
    category: str | None = None



def connect(database):
    try:
        connection = sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection
    except sqlite3.OperationalError as exc:
        raise HTTPException(503, "Banco de dados indisponível. Execute python -m src.etl.build_database primeiro.") from exc


def create_app(database=DATABASE):
    app = FastAPI(title="DataPilot", version="0.1.0")
    app.mount("/static", StaticFiles(directory=ROOT / "src" / "web"), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(ROOT / "src" / "web" / "index.html")

    @app.get("/api/metadata")
    def metadata():
        with closing(connect(database)) as connection:
            dates = connection.execute("SELECT MIN(order_date), MAX(order_date) FROM sales").fetchone()
            return {
                "start_date": dates[0], "end_date": dates[1],
                "channels": [row[0] for row in connection.execute("SELECT DISTINCT channel FROM sales_detail ORDER BY channel")],
                "categories": [row[0] for row in connection.execute("SELECT DISTINCT category FROM sales_detail ORDER BY category")],
                "quality": json.loads(connection.execute("SELECT report_json FROM load_report").fetchone()[0]),
            }

    @app.get("/api/dashboard")
    def dashboard(start_date: date | None = None, end_date: date | None = None,
                  channel: str | None = None, category: str | None = None):
        if start_date and end_date and start_date > end_date:
            raise HTTPException(422, "A data inicial não pode ser posterior à data final.")
        clauses, parameters = [], []
        for column, operator, value in (
            ("order_date", ">=", start_date), ("order_date", "<=", end_date),
            ("channel", "=", channel), ("category", "=", category),
        ):
            if value is not None:
                clauses.append(f"{column} {operator} ?")
                parameters.append(value.isoformat() if isinstance(value, date) else value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with closing(connect(database)) as connection:
            for column, value in (("channel", channel), ("category", category)):
                if value is not None and not connection.execute(
                    f"SELECT 1 FROM sales_detail WHERE {column} = ? LIMIT 1", (value,)
                ).fetchone():
                    raise HTTPException(422, "Canal desconhecido." if column == "channel" else "Categoria desconhecida.")
            summary = dict(connection.execute(
                "SELECT COUNT(*) AS line_count, COUNT(DISTINCT order_number) AS orders, "
                "COALESCE(SUM(quantity),0) AS units, COALESCE(SUM(revenue_cents),0) AS revenue_cents, "
                "COALESCE(SUM(cost_cents),0) AS cost_cents FROM sales_detail" + where, parameters
            ).fetchone())
            summary["gross_profit_cents"] = summary["revenue_cents"] - summary["cost_cents"]
            summary["gross_margin_pct"] = (
                100 * summary["gross_profit_cents"] / summary["revenue_cents"]
                if summary["revenue_cents"] else None
            )
            summary["average_order_value_cents"] = (
                summary["revenue_cents"] / summary["orders"] if summary["orders"] else None
            )
            monthly = [dict(row) for row in connection.execute(
                "SELECT substr(order_date,1,7) AS month, SUM(revenue_cents) AS revenue_cents "
                "FROM sales_detail" + where + " GROUP BY month ORDER BY month", parameters
            )]
            categories = [dict(row) for row in connection.execute(
                "SELECT category, SUM(revenue_cents) AS revenue_cents FROM sales_detail"
                + where + " GROUP BY category ORDER BY revenue_cents DESC, category", parameters
            )]
        return {"summary": summary, "monthly": monthly, "categories": categories,
                "filters": {"start_date": start_date, "end_date": end_date, "channel": channel, "category": category}}

    @app.get("/api/providers")
    def providers():
        return {"providers": list_providers()}

    @app.post("/api/copilot")
    def copilot(request: CopilotRequest):
        snapshot = dashboard(request.start_date, request.end_date, request.channel, request.category)
        return explain(request.provider, request.model, request.question, snapshot)

    app.include_router(create_analysis_router(lambda: connect(database)))
    return app


app = create_app()
