"""Run the protected demo locally without changing the normal local profile."""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
import uvicorn


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    os.environ["DEMO_MODE"] = "true"
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
