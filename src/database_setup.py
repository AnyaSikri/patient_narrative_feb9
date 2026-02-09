"""Database schema utilities for the narrative proof of concept."""

from __future__ import annotations

import argparse
import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
LOGGER = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "processed" / "narratives.db"

CREATE_TABLE_STATEMENTS: Iterable[str] = (
    """
    CREATE TABLE IF NOT EXISTS subjects (
        subject_id TEXT PRIMARY KEY,
        study_id TEXT,
        site_id INTEGER,
        age INTEGER,
        age_units TEXT,
        sex TEXT,
        race TEXT,
        ethnicity TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS adverse_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id TEXT,
        sequence_number INTEGER,
        sponsor_id INTEGER,
        verbatim_term TEXT,
        preferred_term TEXT,
        pt_code TEXT,
        soc TEXT,
        serious_event TEXT,
        start_date TEXT,
        end_date TEXT,
        study_day_start INTEGER,
        study_day_end INTEGER,
        severity_grade INTEGER,
        outcome TEXT,
            action_taken TEXT,
            causality TEXT,
            analysis_causality TEXT,
            hospitalization TEXT,
        life_threatening TEXT,
        results_in_death TEXT,
        disability TEXT,
        other_medically_important TEXT,
        treatment_emergent TEXT,
        FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
        UNIQUE(subject_id, sequence_number)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS treatment_exposure (
        subject_id TEXT PRIMARY KEY,
        actual_treatment TEXT,
        first_dose_date TEXT,
        last_dose_date TEXT,
        FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS narratives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id TEXT,
        sequence_number INTEGER,
        narrative_text TEXT,
        generation_date TEXT,
        template_used TEXT,
        FOREIGN KEY (subject_id, sequence_number)
            REFERENCES adverse_events(subject_id, sequence_number)
    );
    """,
)

TABLE_NAMES = (
    "narratives",
    "treatment_exposure",
    "adverse_events",
    "subjects",
)


def _connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def create_tables(db_path: Path = DB_PATH) -> None:
    """Create all database tables."""
    try:
        with closing(_connect(db_path)) as conn, conn:
            for statement in CREATE_TABLE_STATEMENTS:
                LOGGER.debug("Executing SQL: %s", statement.strip().splitlines()[0])
                conn.execute(statement)
        LOGGER.info("Tables created successfully at %s", db_path)
    except sqlite3.Error as exc:
        LOGGER.exception("Failed to create tables: %s", exc)
        raise


def reset_database(db_path: Path = DB_PATH) -> None:
    """Drop all tables then recreate schema."""
    try:
        with closing(_connect(db_path)) as conn, conn:
            for table in TABLE_NAMES:
                LOGGER.debug("Dropping table if exists: %s", table)
                conn.execute(f"DROP TABLE IF EXISTS {table};")
        LOGGER.info("Existing tables dropped.")
        create_tables(db_path)
    except sqlite3.Error as exc:
        LOGGER.exception("Failed to reset database: %s", exc)
        raise


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SQLite schema setup utility.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop existing tables before recreating the schema.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DB_PATH,
        help="Optional override for database path.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    db_path = args.db_path
    if args.reset:
        LOGGER.info("Resetting database at %s", db_path)
        reset_database(db_path)
    else:
        LOGGER.info("Creating database tables at %s", db_path)
        create_tables(db_path)


if __name__ == "__main__":
    main()

