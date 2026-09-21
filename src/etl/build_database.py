"""Build the local demo database from original CSVs, publishing only valid loads."""
import csv
import json
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "data" / "processed" / "datapilot.db"


def money_cents(value):
    try:
        amount = Decimal(value.replace("$", "").replace(",", ""))
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"Invalid monetary value: {value!r}") from exc
    if not amount.is_finite() or amount * 100 != (amount * 100).to_integral_value():
        raise ValueError(f"Expected a finite monetary value with at most two decimals: {value!r}")
    return int(amount * 100)


def date_key(value, optional=False):
    if not value and optional:
        return None
    if len(value) != 8 or not value.isdigit():
        raise ValueError(f"Invalid date key: {value!r}")
    return datetime.strptime(value, "%Y%m%d").date().isoformat()


def source_rows(name, raw_directory):
    path = raw_directory / f"3 - Aprofundando em Qlik_{name}.csv"
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def build_database(raw_directory=ROOT / "data" / "raw", destination=DATABASE):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(suffix=".db", dir=destination.parent)
    os.close(handle)
    connection = sqlite3.connect(temp_name)
    try:
        connection.executescript((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
        dimensions = [
            ("Product", "product", ("ProductKey", "Product", "Category")),
            ("Customer", "customer", ("CustomerKey", "Customer")),
            ("Reseller", "reseller", ("ResellerKey", "Reseller")),
            ("Sales-Territory", "territory", ("SalesTerritoryKey", "Region", "Country")),
            ("Sales-Order", "order_line", ("SalesOrderLineKey", "Sales Order", "Channel")),
        ]
        counts = {}
        with connection:
            for source, table, columns in dimensions:
                rows = source_rows(source, raw_directory)
                values = [(int(row[columns[0]]), *(row[col] or None for col in columns[1:])) for row in rows]
                connection.executemany(
                    f"INSERT INTO {table} VALUES ({','.join('?' for _ in columns)})", values
                )
                counts[table] = len(rows)
            rows = source_rows("Sales", raw_directory)
            records = []
            monetary_columns = ("Unit Price", "Extended Amount", "Product Standard Cost", "Total Product Cost", "Sales Amount")
            for row in rows:
                amounts = {column: money_cents(row[column]) for column in monetary_columns}
                discount_text = row["Unit Price Discount Pct"]
                if not discount_text.endswith("%"):
                    raise ValueError("Expected a discount percentage ending in %")
                discount = Decimal(discount_text[:-1]) / 100
                if not discount.is_finite() or not 0 <= discount <= 1:
                    raise ValueError("Discount must be between zero and one")
                records.append((
                    int(row["SalesOrderLineKey"]), int(row["ProductKey"]),
                    int(row["CustomerKey"]), int(row["ResellerKey"]),
                    int(row["SalesTerritoryKey"]),
                    date_key(row["OrderDateKey"]), date_key(row["DueDateKey"]),
                    date_key(row["ShipDateKey"], optional=True),
                    int(row["Order Quantity"]), amounts["Sales Amount"], amounts["Total Product Cost"],
                ))
            connection.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?,?,?,?,?,?)", records)
            counts["sales"] = len(records)
            loaded = connection.execute("SELECT COUNT(*), SUM(revenue_cents), SUM(cost_cents) FROM sales_detail").fetchone()
            expected = (len(records), sum(row[9] for row in records), sum(row[10] for row in records))
            if loaded != expected:
                raise ValueError(f"Reconciliation failed: loaded={loaded}, expected={expected}")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("Foreign key validation failed")
            report = {
                "loaded_at": datetime.now(timezone.utc).isoformat(),
                "row_counts": counts,
                "orders": connection.execute("SELECT COUNT(DISTINCT order_number) FROM sales_detail").fetchone()[0],
                "revenue_cents": expected[1], "cost_cents": expected[2],
                "missing_ship_dates": sum(row[7] is None for row in records),
                "checks": ["Unique primary keys", "Required foreign keys", "Valid source dates",
                           "Finite monetary values in cents", "Discount range",
                           "Positive quantities", "Joined row count and amount reconciliation"],
            }
            connection.execute("CREATE TABLE load_report (report_json TEXT NOT NULL)")
            connection.execute("INSERT INTO load_report VALUES (?)", (json.dumps(report),))
        connection.close()
        os.replace(temp_name, destination)
        return report
    finally:
        connection.close()
        if os.path.exists(temp_name):
            os.unlink(temp_name)


if __name__ == "__main__":
    print(json.dumps(build_database(), indent=2))
