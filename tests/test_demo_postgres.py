"""Opt-in PostgreSQL tests with a unique, disposable schema; no AI or email calls."""
import os
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from fastapi import HTTPException
from psycopg import sql

from src.demo.config import demo_settings
from src.demo.quota import QuotaStore


@unittest.skipUnless(os.getenv("DATAPILOT_TEST_NEON") == "1", "Opt-in Neon integration test")
class PostgresQuotaTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        load_dotenv(root / ".env")
        self.config = demo_settings()
        self.namespace = "datapilot_demo_test_" + uuid.uuid4().hex
        self.now = datetime(2030, 1, 1, tzinfo=timezone.utc)
        script = (root / "sql/demo_schema.sql").read_text(encoding="utf-8").replace("datapilot_demo", self.namespace)
        with psycopg.connect(self.config.database_url, connect_timeout=15) as connection:
            connection.execute(script)
        namespace = self.namespace

        class TestStore(QuotaStore):
            def connect(self):
                connection = super().connect()
                connection.execute(sql.SQL("SET LOCAL search_path = {}, pg_catalog").format(sql.Identifier(namespace)))
                return connection

        self.store = TestStore(replace(self.config, questions_per_user=2, daily_questions=20, cooldown_seconds=1))

    def tearDown(self):
        # Drop only the generated test schema; never touch the application schema.
        if self.namespace.startswith("datapilot_demo_test_") and len(self.namespace) == len("datapilot_demo_test_") + 32:
            with psycopg.connect(self.config.database_url, connect_timeout=15) as connection:
                connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.namespace)))

    def test_third_question_is_rejected_and_reload_preserves_usage(self):
        self.assertEqual(self.store.snapshot("alice", self.now)["remaining"], 2)
        self.store.reserve("alice", self.now)
        self.store.reserve("alice", self.now + timedelta(seconds=2))
        with self.assertRaises(HTTPException) as caught:
            self.store.reserve("alice", self.now + timedelta(seconds=4))
        self.assertEqual(caught.exception.status_code, 429)
        another_store = type(self.store)(self.store.settings)
        self.assertEqual(another_store.snapshot("alice", self.now)["remaining"], 0)
        self.assertEqual(another_store.snapshot("bob", self.now)["remaining"], 2)

    def test_parallel_requests_cannot_spend_the_same_last_question(self):
        self.store.reserve("alice", self.now)

        def attempt(_):
            try:
                self.store.reserve("alice", self.now + timedelta(seconds=2))
                return "reserved"
            except HTTPException as exc:
                return exc.status_code

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(attempt, range(4)))
        self.assertEqual(results.count("reserved"), 1)
        self.assertEqual(results.count(429), 3)
        self.assertEqual(self.store.snapshot("alice", self.now)["used"], 2)

    def test_global_limit_cooldown_override_and_rollback(self):
        self.store.settings = replace(self.store.settings, daily_questions=2)
        self.store.reserve("alice", self.now)
        with self.assertRaises(HTTPException):
            self.store.reserve("alice", self.now)
        with self.store.connect() as connection:
            daily = connection.execute("SELECT used_questions FROM daily_usage").fetchone()
            self.assertEqual(daily["used_questions"], 1)
            connection.execute("UPDATE accounts SET question_limit = 1 WHERE user_id = 'alice'")
        self.assertEqual(self.store.snapshot("alice", self.now)["remaining"], 0)
        self.store.reserve("bob", self.now)
        with self.assertRaises(HTTPException):
            self.store.reserve("carol", self.now)
        self.assertEqual(self.store.snapshot("carol", self.now)["used"], 0)
        self.assertFalse(self.store.snapshot("carol", self.now)["daily_available"])
        self.assertTrue(self.store.snapshot("carol", self.now + timedelta(days=1))["daily_available"])
