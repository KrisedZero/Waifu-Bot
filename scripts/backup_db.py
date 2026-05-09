from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def default_output_dir() -> Path:
    return Path("backups")


def default_filename(db_name: str) -> str:
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{db_name}_{timestamp}.sql"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a PostgreSQL backup for the waifu bot database."
    )
    parser.add_argument(
        "--output-dir",
        default=str(default_output_dir()),
        help="Directory for backup files.",
    )
    parser.add_argument(
        "--filename",
        default=None,
        help="Optional backup filename. If omitted, a timestamped one is used.",
    )
    args = parser.parse_args()

    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME")

    if not db_user or not db_name:
        print("DB_USER and DB_NAME must be set in environment variables.", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / (args.filename or default_filename(db_name))

    cmd = [
        "pg_dump",
        "-h", db_host,
        "-p", str(db_port),
        "-U", db_user,
        "-F", "p",
        "-f", str(output_path),
        db_name,
    ]

    env = os.environ.copy()
    if db_password:
        env["PGPASSWORD"] = db_password

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    except FileNotFoundError:
        print(
            "pg_dump was not found. Install PostgreSQL client tools and add pg_dump to PATH.",
            file=sys.stderr,
        )
        return 3

    if result.returncode != 0:
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode

    print(f"Backup created: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
