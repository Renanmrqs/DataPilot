"""Create the demo quota schema explicitly, without changing managed auth tables."""
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


def main():
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    database_url = os.getenv("NEON_DATABASE_URL", "")
    if not database_url:
        raise SystemExit("NEON_DATABASE_URL is required.")
    try:
        with psycopg.connect(database_url, connect_timeout=15) as connection:
            connection.execute((root / "sql/demo_schema.sql").read_text(encoding="utf-8"))
    except psycopg.Error:
        raise SystemExit("Demo quota schema setup failed. Check the connection and database permissions.") from None
    print("Demo quota schema is ready. Managed authentication tables were not modified.")


if __name__ == "__main__":
    main()
