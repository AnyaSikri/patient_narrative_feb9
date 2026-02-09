"""Generate patient narratives using configured templates."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from string import Formatter
from typing import Any, Dict, List, Optional

from field_mapper import FieldMapper, DEFAULT_DB_PATH as FM_DB_PATH
from ai_enhancer import OpenAINarrativeEnhancer

LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE_PATH = BASE_DIR / "configs" / "narrative_templates.json"


class NarrativeGenerator:
    """Template-driven narrative generator."""

    def __init__(
        self,
        template_config_path: Path | str = DEFAULT_TEMPLATE_PATH,
        field_mapper: Optional[FieldMapper] = None,
        enhancer: Optional[OpenAINarrativeEnhancer] = None,
    ) -> None:
        self.template_config_path = Path(template_config_path)
        self.templates = self._load_templates(self.template_config_path)
        self.field_mapper = field_mapper or FieldMapper(db_path=FM_DB_PATH)
        self.enhancer = enhancer

    @staticmethod
    def _load_templates(path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def select_template(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Select template based on event flags with fallback logic."""
        # Normalize event data - handle None values
        serious = (event_data.get("serious_event") or "").upper()
        hosp = (event_data.get("hospitalization") or "").upper()
        med_imp = (event_data.get("other_medically_important") or "").upper()
        
        # Priority 1: Hospitalization SAE
        if serious == "Y" and hosp == "Y":
            template = self.templates.get("sae_hospitalization")
            if template:
                LOGGER.info("Selected template %s (hospitalization)", template["template_id"])
                return template
        
        # Priority 2: Medically important SAE (no hospitalization)
        if serious == "Y" and hosp == "N" and med_imp == "Y":
            template = self.templates.get("sae_medically_important")
            if template:
                LOGGER.info("Selected template %s (medically important)", template["template_id"])
                return template
        
        # Priority 3: Any SAE without hospitalization (fallback)
        if serious == "Y" and hosp != "Y":
            template = self.templates.get("sae_medically_important")
            if template:
                LOGGER.warning(
                    "Using medically important template as fallback for SAE without clear categorization"
                )
                return template
        
        # Priority 4: Any SAE (ultimate fallback - use generic template)
        if serious == "Y":
            template = self.templates.get("sae_generic")
            if template:
                LOGGER.warning("Using generic SAE template as fallback for uncategorized SAE")
                return template
            # If generic doesn't exist, use hospitalization
            template = self.templates.get("sae_hospitalization")
            if template:
                LOGGER.warning("Using hospitalization template as ultimate fallback")
                return template
        
        # Priority 5: Non-serious AE (also default when serious flag is missing)
        template = self.templates.get("ae_non_serious")
        if template:
            if serious != "N":
                LOGGER.warning(
                    "Serious event flag is '%s' (not Y or N); defaulting to non-serious template",
                    serious or "(empty)",
                )
            else:
                LOGGER.info("Selected template %s (non-serious AE)", template["template_id"])
            return template

        # If we get here, something is wrong
        raise ValueError(
            f"No suitable template found. Event data: serious={serious}, "
            f"hospitalization={hosp}, medically_important={med_imp}. "
            f"Available templates: {list(self.templates.keys())}"
        )

    def fill_template(self, template_text: str, field_values: Dict[str, Any]) -> str:
        """Replace placeholders in template with safe handling of missing values."""
        # Convert None and empty strings to placeholder text
        safe_dict = _SafeDict({
            key: (
                value if value not in (None, "", "nan", "NaN") 
                else "[NOT AVAILABLE]"
            )
            for key, value in field_values.items()
        })
        formatter = Formatter()
        try:
            return formatter.vformat(template_text, (), safe_dict)
        except KeyError as e:
            LOGGER.error("Missing field in template: %s. Available fields: %s", e, list(field_values.keys()))
            raise ValueError(f"Template requires field {e} which is not available in data") from e

    def apply_business_rules(self, text: str) -> str:
        """Apply narrative business rules."""
        # Rule 1: enforce "most recent dose"
        text = re.sub(r"\blast dose\b", "most recent dose", text, flags=re.IGNORECASE)

        # Rule 2: normalize ISO dates to DD-MMM-YYYY
        def _date_repl(match: re.Match[str]) -> str:
            raw = match.group(0)
            try:
                parsed = datetime.strptime(raw, "%Y-%m-%d")
                return parsed.strftime("%d-%b-%Y")
            except ValueError:
                return raw

        text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", _date_repl, text)

        # Rule 3: lowercase action_taken clause
        text = re.sub(
            r"(action taken with study drug was )([^\.]+)",
            lambda m: m.group(1) + m.group(2).lower(),
            text,
            flags=re.IGNORECASE,
        )

        # Rule 4: lowercase causality clause
        text = re.sub(
            r"(assessed the event as )([^\.]+)",
            lambda m: m.group(1) + m.group(2).lower(),
            text,
            flags=re.IGNORECASE,
        )
        
        # Rule 5: Fix age formatting (74-YEARS-old -> 74-year-old)
        text = re.sub(r"(\d+)-YEARS-old", r"\1-year-old", text, flags=re.IGNORECASE)
        
        # Rule 6: Fix race/ethnicity casing (all caps -> Title Case)
        text = re.sub(r"\bWHITE\b", "White", text)
        text = re.sub(r"\bBLACK OR AFRICAN AMERICAN\b", "Black or African American", text)
        text = re.sub(r"\bASIAN\b", "Asian", text)
        text = re.sub(r"\bNOT HISPANIC OR LATINO\b", "Not Hispanic or Latino", text)
        text = re.sub(r"\bHISPANIC OR LATINO\b", "Hispanic or Latino", text)
        
        # Rule 7: Lowercase preferred terms after "SAE of"
        text = re.sub(
            r"(SAE of )([A-Z])",
            lambda m: m.group(1) + m.group(2).lower(),
            text
        )

        return text

    def generate_paragraph(
        self, paragraph_config: Dict[str, Any], field_values: Dict[str, Any]
    ) -> str:
        base_template = paragraph_config["template"]
        variations = paragraph_config.get("variations")
        template_text = base_template
        if variations:
            key = "with_end_date" if field_values.get("end_date") else "without_end_date"
            variation_text = variations.get(key)
            if variation_text:
                template_text = f"{base_template} {variation_text}"
        filled = self.fill_template(template_text, field_values)
        return self.apply_business_rules(filled)

    def generate_narrative(self, subject_id: str, sequence_number: int) -> str:
        field_values = self.field_mapper.map_all_fields(subject_id, sequence_number)
        event_data = self.field_mapper.get_event_data(subject_id, sequence_number) or {}
        template = self.select_template(event_data)
        paragraphs: List[str] = []
        for paragraph in sorted(template["paragraphs"], key=lambda p: p["number"]):
            paragraph_text = self.generate_paragraph(paragraph, field_values)
            paragraphs.append(paragraph_text)
            LOGGER.debug(
                "Generated paragraph %s for subject %s seq %s",
                paragraph["number"],
                subject_id,
                sequence_number,
            )
        narrative_text = "\n\n".join(paragraphs)
        if self.enhancer:
            LOGGER.info(
                "Enhancing narrative for subject %s seq %s via OpenAI.",
                subject_id,
                sequence_number,
            )
            narrative_text = self.enhancer.enhance(
                field_values=field_values,
                template_id=template["template_id"],
                baseline_text=narrative_text,
            )
        return narrative_text

    @staticmethod
    def save_to_database(
        subject_id: str,
        sequence_number: int,
        narrative_text: str,
        template_id: str,
        db_path: Path | str = FM_DB_PATH,
    ) -> int:
        """Persist generated narrative to SQLite."""
        db_path = Path(db_path)
        timestamp = datetime.utcnow().isoformat()
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO narratives (subject_id, sequence_number, narrative_text, generation_date, template_used)
                VALUES (?, ?, ?, ?, ?)
                """,
                (subject_id, sequence_number, narrative_text, timestamp, template_id),
            )
            narrative_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            LOGGER.info(
                "Saved narrative %s for subject %s seq %s",
                narrative_id,
                subject_id,
                sequence_number,
            )
            return narrative_id


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:  # pragma: no cover - simple helper
        return "[NOT AVAILABLE]"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a single narrative.")
    parser.add_argument("--subject", required=True, help="Subject identifier.")
    parser.add_argument("--sequence", required=True, type=int, help="AE sequence number.")
    parser.add_argument(
        "--templates",
        type=Path,
        default=DEFAULT_TEMPLATE_PATH,
        help="Path to narrative template config.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=FM_DB_PATH,
        help="SQLite database path.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    mapper = FieldMapper(db_path=args.db_path)
    generator = NarrativeGenerator(template_config_path=args.templates, field_mapper=mapper)
    narrative = generator.generate_narrative(args.subject, args.sequence)
    print(narrative)


if __name__ == "__main__":
    main()

