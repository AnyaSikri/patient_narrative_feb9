"""Load ADAE Excel data into the SQLite database."""

from __future__ import annotations

import argparse
import logging
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = BASE_DIR / "data" / "processed" / "narratives.db"
DEFAULT_EXCEL_PATH = BASE_DIR / "data" / "raw" / "adae.xlsx"


class ADAELoader:
    """Utility class to extract and load ADAE data."""

    COL_SUBJECT_ID = "Subject Identifier for the Study"
    COL_UNIQUE_SUBJECT_ID = "Unique Subject Identifier"

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        LOGGER.debug("ADAELoader initialized with DB path %s", self.db_path)

    @staticmethod
    def load_excel(filepath: Path | str) -> pd.DataFrame:
        """Load ADAE Excel file into a DataFrame."""
        filepath = Path(filepath)
        LOGGER.info("Loading ADAE Excel file from %s", filepath)
        df = pd.read_excel(filepath)
        LOGGER.info("Loaded %d rows from %s", len(df), filepath.name)
        return df

    def extract_subjects(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract unique subjects."""
        subject_rows = df.drop_duplicates(subset=[self.COL_UNIQUE_SUBJECT_ID])
        subjects: List[Dict[str, Any]] = []
        for _, row in subject_rows.iterrows():
            subject = {
                "subject_id": self._clean_string(row.get(self.COL_UNIQUE_SUBJECT_ID)),
                "study_id": self._clean_string(row.get("Study Identifier")),
                "site_id": self._safe_int(row.get("Study Site Identifier")),
                "age": self._safe_int(row.get("Age")),
                "age_units": self._clean_string(row.get("Age Units")),
                "sex": self._clean_string(row.get("Sex")),
                "race": self._clean_string(row.get("Race")),
                "ethnicity": self._clean_string(row.get("Ethnicity")),
            }
            subjects.append(subject)
        LOGGER.info("Extracted %d unique subjects", len(subjects))
        return subjects

    def extract_adverse_events(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract adverse events records with comprehensive fields."""
        events: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            event = {
                "subject_id": self._clean_string(row.get(self.COL_UNIQUE_SUBJECT_ID)),
                "sequence_number": self._safe_int(row.get("Sequence Number")),
                "sponsor_id": self._safe_int(row.get("Sponsor-Defined Identifier")),
                "verbatim_term": self._clean_string(
                    row.get("Reported Term for the Adverse Event")
                ),
                "preferred_term": self._clean_string(
                    row.get("Dictionary-Derived Term")
                ),
                "pt_code": self._clean_string(row.get("Preferred Term Code")),
                "soc": self._clean_string(row.get("Primary System Organ Class")),
                "serious_event": self._clean_string(row.get("Serious Event")),
                "start_date": self._clean_date(row.get("Start Date/Time of Adverse Event")),
                "end_date": self._clean_date(row.get("End Date/Time of Adverse Event")),
                "study_day_start": self._safe_int(row.get("Analysis Start Relative Day")),
                "study_day_end": self._safe_int(row.get("Analysis End Relative Day")),
                "severity_grade": self._safe_int(row.get("Standard Toxicity Grade")),
                "outcome": self._clean_string(row.get("Outcome of Adverse Event")),
                "action_taken": self._clean_string(
                    row.get("Action Taken with Study Treatment")
                ),
                "causality": self._clean_string(row.get("Causality")),
                "analysis_causality": self._clean_string(row.get("Analysis Causality")),
                "hospitalization": self._clean_string(
                    row.get("Requires or Prolongs Hospitalization")
                ),
                "life_threatening": self._clean_string(
                    row.get("Is Life Threatening")
                ),
                "results_in_death": self._clean_string(row.get("Results in Death")),
                "disability": self._clean_string(
                    row.get("Persist or Signif Disability/Incapacity")
                ),
                "other_medically_important": self._clean_string(
                    row.get("Other Medically Important Serious Event")
                ),
                "treatment_emergent": self._clean_string(
                    row.get("Treatment Emergent Analysis Flag")
                ),
            }
            events.append(event)
        LOGGER.info("Extracted %d adverse events", len(events))
        return events

    def extract_treatment_exposure(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract treatment exposure per subject."""
        treatment_rows = df.drop_duplicates(subset=[self.COL_UNIQUE_SUBJECT_ID])
        exposures: List[Dict[str, Any]] = []
        for _, row in treatment_rows.iterrows():
            exposure = {
                "subject_id": self._clean_string(row.get(self.COL_UNIQUE_SUBJECT_ID)),
                "actual_treatment": self._clean_string(row.get("Actual Treatment")),
                "first_dose_date": self._clean_date(
                    row.get("Date of First Exposure to Treatment")
                ),
                "last_dose_date": self._clean_date(
                    row.get("Date of Last Exposure to Treatment")
                ),
            }
            exposures.append(exposure)
        LOGGER.info("Extracted %d treatment exposure records", len(exposures))
        return exposures

    def load_to_database(
        self, db_path: Optional[Path | str] = None, excel_path: Optional[Path | str] = None
    ) -> Dict[str, int]:
        """Load ADAE data into SQLite."""
        db_path = Path(db_path) if db_path else self.db_path
        excel_path = Path(excel_path) if excel_path else DEFAULT_EXCEL_PATH
        df = self.load_excel(excel_path)
        subjects = self.extract_subjects(df)
        events = self.extract_adverse_events(df)
        exposures = self.extract_treatment_exposure(df)

        counts = {"subjects": 0, "adverse_events": 0, "treatment_exposure": 0}

        try:
            with closing(sqlite3.connect(db_path)) as conn:
                conn.execute("PRAGMA foreign_keys = ON;")
                with conn:
                    counts["subjects"] = self._insert_records(
                        conn,
                        "subjects",
                        (
                            "subject_id",
                            "study_id",
                            "site_id",
                            "age",
                            "age_units",
                            "sex",
                            "race",
                            "ethnicity",
                        ),
                        subjects,
                    )
                    counts["adverse_events"] = self._insert_records(
                        conn,
                        "adverse_events",
                        (
                            "subject_id",
                            "sequence_number",
                            "sponsor_id",
                            "verbatim_term",
                            "preferred_term",
                            "pt_code",
                            "soc",
                            "serious_event",
                            "start_date",
                            "end_date",
                            "study_day_start",
                            "study_day_end",
                            "severity_grade",
                            "outcome",
                            "action_taken",
                            "causality",
                            "hospitalization",
                            "life_threatening",
                            "results_in_death",
                            "disability",
                            "other_medically_important",
                            "treatment_emergent",
                        ),
                        events,
                    )
                    counts["treatment_exposure"] = self._insert_records(
                        conn,
                        "treatment_exposure",
                        (
                            "subject_id",
                            "actual_treatment",
                            "first_dose_date",
                            "last_dose_date",
                        ),
                        exposures,
                    )
            LOGGER.info("Data loaded successfully: %s", counts)
            return counts
        except sqlite3.Error as exc:
            LOGGER.exception("Failed to load ADAE data: %s", exc)
            raise

    @staticmethod
    def _insert_records(
        conn: sqlite3.Connection,
        table: str,
        columns: Iterable[str],
        records: List[Dict[str, Any]],
    ) -> int:
        placeholders = ", ".join(["?"] * len(columns))
        column_list = ", ".join(columns)
        sql = f"INSERT OR REPLACE INTO {table} ({column_list}) VALUES ({placeholders})"
        rows = [
            tuple(record.get(column) for column in columns)
            for record in records
        ]
        LOGGER.debug("Inserting %d rows into %s", len(rows), table)
        conn.executemany(sql, rows)
        return len(rows)

    @staticmethod
    def _clean_string(value: Any) -> Optional[str]:
        if pd.isna(value):
            return None
        value = str(value).strip()
        return value or None

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        if pd.isna(value):
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _clean_date(value: Any) -> Optional[str]:
        if value is None or pd.isna(value):
            return None
        if isinstance(value, pd.Timestamp):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        try:
            parsed = pd.to_datetime(value, errors="coerce")
            if pd.isna(parsed):
                return None
            return parsed.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load ADAE Excel into SQLite.")
    parser.add_argument(
        "--excel",
        type=Path,
        default=DEFAULT_EXCEL_PATH,
        help="Path to ADAE Excel file.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to SQLite database.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    loader = ADAELoader(db_path=args.db_path)
    counts = loader.load_to_database(db_path=args.db_path, excel_path=args.excel)
    LOGGER.info(
        "ADAE load complete - Subjects: %(subjects)d, AEs: %(adverse_events)d, Treatment: %(treatment_exposure)d",
        counts,
    )


if __name__ == "__main__":
    main()

