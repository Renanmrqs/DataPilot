"""Persist and reserve question allowances atomically in PostgreSQL."""
from datetime import datetime, timezone

import psycopg
from fastapi import HTTPException
from psycopg.rows import dict_row


class QuotaStore:
    def __init__(self, settings):
        self.settings = settings

    def connect(self):
        connection = psycopg.connect(
            self.settings.database_url, connect_timeout=10, row_factory=dict_row,
        )
        try:
            # Neon pooling rejects search_path as a startup option. SET LOCAL
            # applies only to this transaction and cannot leak to another user.
            connection.execute("SET LOCAL statement_timeout = '10s'")
            connection.execute("SET LOCAL lock_timeout = '5s'")
            connection.execute("SET LOCAL search_path = datapilot_demo, pg_catalog")
        except psycopg.Error:
            connection.close()
            raise
        return connection

    def snapshot(self, user_id, now=None):
        now = now or datetime.now(timezone.utc)
        with self.connect() as connection:
            account = connection.execute(
                "SELECT used_questions, question_limit, last_question_at "
                "FROM accounts WHERE user_id = %s", (user_id,),
            ).fetchone()
            day = connection.execute(
                "SELECT used_questions FROM daily_usage WHERE usage_date = %s", (now.date(),),
            ).fetchone()
        return self.describe(account, day, now)

    def describe(self, account, day, now):
        account = account or {"used_questions": 0, "question_limit": None, "last_question_at": None}
        limit = account["question_limit"]
        if limit is None:
            limit = self.settings.questions_per_user
        retry_after = 0
        if account["last_question_at"]:
            elapsed = (now - account["last_question_at"]).total_seconds()
            retry_after = max(0, int(self.settings.cooldown_seconds - elapsed + 0.999))
        return {
            "limit": limit,
            "used": account["used_questions"],
            "remaining": max(0, limit - account["used_questions"]),
            "daily_available": (day or {}).get("used_questions", 0) < self.settings.daily_questions,
            "retry_after_seconds": retry_after,
        }

    def reserve(self, user_id, now=None):
        now = now or datetime.now(timezone.utc)
        # Every reservation locks the day before the user, always in this order.
        # The short transaction ends before any slow AI request starts.
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO daily_usage (usage_date) VALUES (%s) ON CONFLICT DO NOTHING",
                (now.date(),),
            )
            day = connection.execute(
                "SELECT used_questions FROM daily_usage WHERE usage_date = %s FOR UPDATE",
                (now.date(),),
            ).fetchone()
            connection.execute(
                "INSERT INTO accounts (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,),
            )
            account = connection.execute(
                "SELECT used_questions, question_limit, last_question_at FROM accounts "
                "WHERE user_id = %s FOR UPDATE", (user_id,),
            ).fetchone()
            allowance = self.describe(account, day, now)
            if allowance["remaining"] == 0:
                raise HTTPException(429, "Você usou as perguntas disponíveis nesta demonstração. Continue explorando o painel e os filtros.")
            if not allowance["daily_available"]:
                raise HTTPException(429, "A cota de IA da demonstração terminou por hoje. O painel continua disponível.")
            if allowance["retry_after_seconds"]:
                raise HTTPException(
                    429, "Aguarde alguns segundos antes de enviar outra pergunta.",
                    headers={"Retry-After": str(allowance["retry_after_seconds"])},
                )
            connection.execute(
                "UPDATE accounts SET used_questions = used_questions + 1, last_question_at = %s "
                "WHERE user_id = %s", (now, user_id),
            )
            connection.execute(
                "UPDATE daily_usage SET used_questions = used_questions + 1 WHERE usage_date = %s",
                (now.date(),),
            )
        allowance["used"] += 1
        allowance["remaining"] -= 1
        return allowance
