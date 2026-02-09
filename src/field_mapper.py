"""Map database fields into template-ready values."""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = BASE_DIR / "data" / "processed" / "narratives.db"
DEFAULT_CONFIG_PATH = BASE_DIR / "configs" / "field_mappings.json"


class FieldMapper:
    """Lookup and transform subject, treatment, and event fields."""

    def __init__(
        self,
        config_path: Path | str = DEFAULT_CONFIG_PATH,
        db_path: Path | str = DEFAULT_DB_PATH,
    ) -> None:
        self.config_path = Path(config_path)
        self.db_path = Path(db_path)
        self.config = self._load_config(self.config_path)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        LOGGER.debug(
            "FieldMapper initialized with config=%s, db=%s",
            self.config_path,
            self.db_path,
        )

    @staticmethod
    def _load_config(path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
        return config

    def get_subject_data(self, subject_id: str) -> Optional[Dict[str, Any]]:
        return self._fetch_one(
            "SELECT * FROM subjects WHERE subject_id = ?",
            (subject_id,),
            not_found_log=f"Subject {subject_id} not found.",
        )

    def get_treatment_data(self, subject_id: str) -> Optional[Dict[str, Any]]:
        return self._fetch_one(
            "SELECT * FROM treatment_exposure WHERE subject_id = ?",
            (subject_id,),
            not_found_log=f"Treatment exposure for {subject_id} not found.",
        )

    def get_event_data(
        self, subject_id: str, sequence_number: int
    ) -> Optional[Dict[str, Any]]:
        return self._fetch_one(
            """
            SELECT * FROM adverse_events
            WHERE subject_id = ? AND sequence_number = ?
            """,
            (subject_id, sequence_number),
            not_found_log=(
                f"Adverse event not found for subject {subject_id} "
                f"sequence {sequence_number}."
            ),
        )

    def apply_value_mapping(
        self, field_name: str, value: Any, config: Dict[str, Any]
    ) -> Any:
        """Apply configured value_map transforms."""
        value_map = config.get("value_map")
        if value is None or not value_map:
            return value
        mapped_value = value_map.get(str(value).upper()) or value_map.get(value)
        if mapped_value is None:
            return value
        LOGGER.debug("Value mapping applied for %s: %s -> %s", field_name, value, mapped_value)
        return mapped_value

    def format_field(self, field_name: str, value: Any, config: Dict[str, Any]) -> Any:
        """Apply formatting rules such as date conversions."""
        if value is None:
            return None
        formatter = config.get("format")
        if formatter == "date":
            parsed = self._parse_date(value)
            if parsed:
                formatted = parsed.strftime("%d-%b-%Y")
                LOGGER.debug(
                    "Date formatted for %s: %s -> %s", field_name, value, formatted
                )
                return formatted
        return value

    def map_all_fields(self, subject_id: str, sequence_number: int) -> Dict[str, Any]:
        """Combine subject, treatment, and event fields into a single dict."""
        LOGGER.info(
            "Mapping fields for subject %s sequence %s", subject_id, sequence_number
        )
        subject_data = self.get_subject_data(subject_id)
        event_data = self.get_event_data(subject_id, sequence_number)
        treatment_data = self.get_treatment_data(subject_id)

        data_sources = {
            "subjects": subject_data or {},
            "adverse_events": event_data or {},
            "treatment_exposure": treatment_data or {},
        }

        if not subject_data:
            LOGGER.warning("Subject data missing for %s", subject_id)
        if not event_data:
            LOGGER.warning("Event data missing for %s seq %s", subject_id, sequence_number)
        if not treatment_data:
            LOGGER.warning("Treatment data missing for %s", subject_id)

        mapped_fields: Dict[str, Any] = {}
        for section_name, section in self.config.items():
            for field in section.get("fields", []):
                table = field["db_table"]
                column = field["db_column"]
                raw_value = data_sources.get(table, {}).get(column)
                value = self.apply_value_mapping(field["name"], raw_value, field)
                value = self.format_field(field["name"], value, field)
                mapped_fields[field["name"]] = value
                LOGGER.debug(
                    "Mapped %s.%s (%s) -> %s",
                    table,
                    column,
                    field["name"],
                    value,
                )
        return mapped_fields

    def close(self) -> None:
        """Close the database connection."""
        self.connection.close()

    def _fetch_one(
        self,
        query: str,
        params: tuple[Any, ...],
        not_found_log: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            cursor = self.connection.execute(query, params)
            row = cursor.fetchone()
        except sqlite3.Error as exc:
            LOGGER.exception("Database query failed: %s", exc)
            raise
        if row is None:
            if not_found_log:
                LOGGER.warning(not_found_log)
            return None
        return dict(row)

    @staticmethod
    def _parse_date(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d")
            return parsed
        except (ValueError, TypeError):
            try:
                parsed = datetime.strptime(value, "%d-%b-%Y")
                return parsed
            except (ValueError, TypeError):
                return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test FieldMapper mappings.")
    parser.add_argument("--subject", required=True, help="Subject identifier.")
    parser.add_argument(
        "--sequence",
        required=True,
        type=int,
        help="Adverse event sequence number.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Field mapping config path.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="SQLite database path.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    mapper = FieldMapper(config_path=args.config, db_path=args.db_path)
    try:
        fields = mapper.map_all_fields(args.subject, args.sequence)
        for key, value in fields.items():
            print(f"{key}: {value}")
    finally:
        mapper.close()


if __name__ == "__main__":
    main()

