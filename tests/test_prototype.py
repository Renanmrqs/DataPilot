import sqlite3
from contextlib import closing
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import create_app, ROOT
from src.etl.build_database import money_cents, date_key


class TransformationTests(unittest.TestCase):
    def test_exact_money_and_invalid_amounts(self):
        self.assertEqual(money_cents("$1,234.56"), 123456)
        for value in ("NaN", "Infinity", "12.345", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                money_cents(value)

    def test_missing_shipping_date_is_allowed_but_invalid_dates_fail(self):
        self.assertIsNone(date_key("", optional=True))
        self.assertEqual(date_key("20240229"), "2024-02-29")
        for value in ("", "20230229", "2024011"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                date_key(value)


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "test.db"
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.executescript((ROOT / "sql/schema.sql").read_text())
            connection.executescript("""
                INSERT INTO product VALUES (1,'Bike','Bikes'),(2,'Helmet','Accessories');
                INSERT INTO customer VALUES (-1,NULL);
                INSERT INTO reseller VALUES (-1,NULL);
                INSERT INTO territory VALUES (1,'North','Sample');
                INSERT INTO order_line VALUES (1,'SO1','Internet'),(2,'SO1','Internet'),(3,'SO2','Reseller');
                INSERT INTO sales VALUES
                (1,1,-1,-1,1,'2024-01-01','2024-01-05',NULL,1,10000,6000),
                (2,2,-1,-1,1,'2024-01-01','2024-01-05',NULL,2,2000,1000),
                (3,1,-1,-1,1,'2024-02-01','2024-02-05',NULL,1,8000,5000);
            """)
        self.client = TestClient(create_app(self.database))

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def test_metrics_count_orders_not_lines_and_use_weighted_margin(self):
        response = self.client.get("/api/dashboard")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["summary"]["orders"], 2)
        self.assertEqual(result["summary"]["line_count"], 3)
        self.assertEqual(result["summary"]["revenue_cents"], 20000)
        self.assertEqual(result["summary"]["gross_profit_cents"], 8000)
        self.assertEqual(result["summary"]["gross_margin_pct"], 40)
        self.assertEqual(result["summary"]["average_order_value_cents"], 10000)
        self.assertEqual(sum(row["revenue_cents"] for row in result["monthly"]), 20000)

    def test_filters_apply_to_every_aggregation_and_include_endpoints(self):
        response = self.client.get("/api/dashboard", params={
            "start_date":"2024-01-01", "end_date":"2024-01-01", "category":"Accessories", "channel":"Internet"})
        data = response.json()
        self.assertEqual(response.status_code,200)
        self.assertEqual(data["summary"]["revenue_cents"],2000)
        self.assertEqual(data["summary"]["orders"],1)
        self.assertEqual(data["categories"],[{"category":"Accessories","revenue_cents":2000}])
        self.assertEqual(data["monthly"],[{"month":"2024-01","revenue_cents":2000}])

    def test_empty_selection_has_no_fabricated_ratios(self):
        result=self.client.get("/api/dashboard?start_date=2030-01-01").json()
        self.assertEqual(result["summary"]["orders"],0)
        self.assertIsNone(result["summary"]["gross_margin_pct"])
        self.assertIsNone(result["summary"]["average_order_value_cents"])
        self.assertEqual(result["monthly"],[])

    def test_invalid_filters(self):
        for query in ("start_date=bad", "start_date=2025-01-01&end_date=2024-01-01",
                      "category=unknown", "channel=%27%20OR%201=1--"):
            with self.subTest(query=query):
                self.assertEqual(self.client.get("/api/dashboard?"+query).status_code,422)

    def test_database_constraints_reject_duplicates_and_orphans(self):
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("PRAGMA foreign_keys=ON")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO product VALUES (1,'Duplicate','Bikes')")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE sales SET product_key=999 WHERE order_line_key=1")

    def test_copilot_receives_server_metrics_for_selected_filters(self):
        with patch("src.api.main.explain", return_value={"answer": "test"}) as mocked:
            response = self.client.post("/api/copilot", json={
                "provider": "deepseek", "model": "test-model", "question": "Explain",
                "category": "Accessories",
            })
        self.assertEqual(response.status_code, 200)
        snapshot = mocked.call_args.args[3]
        self.assertEqual(snapshot["summary"]["revenue_cents"], 2000)
        self.assertEqual(snapshot["summary"]["orders"], 1)
        self.assertEqual(snapshot["filters"]["category"], "Accessories")

    def test_page_and_assets_are_served(self):
        for path in ("/", "/static/app.js", "/static/style.css", "/docs"):
            self.assertEqual(self.client.get(path).status_code,200)

    def test_missing_database_returns_actionable_error(self):
        with TestClient(create_app(Path(self.temp.name)/"absent.db")) as client:
            self.assertEqual(client.get("/api/dashboard").status_code,503)


if __name__ == "__main__":
    unittest.main()
