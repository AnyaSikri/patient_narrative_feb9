"""Test suite for patient narrative automation POC."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from data_loader import DEFAULT_EXCEL_PATH  # noqa: E402
from field_mapper import FieldMapper  # noqa: E402
from main import (  # noqa: E402
    generate_all_saes,
    generate_single_narrative,
    setup_database,
)
from narrative_generator import NarrativeGenerator  # noqa: E402


@pytest.fixture(scope="session")
def temp_environment(tmp_path_factory):
    base_dir = tmp_path_factory.mktemp("narrative_tests")
    db_path = base_dir / "narratives.db"
    output_dir = base_dir / "output"
    counts = setup_database(db_path=db_path, excel_path=DEFAULT_EXCEL_PATH)
    yield {
        "db_path": db_path,
        "output_dir": output_dir,
        "counts": counts,
    }


def test_database_loading(temp_environment):
    """Ensure ADAE data loads fully into SQLite."""
    db_path = temp_environment["db_path"]
    counts = temp_environment["counts"]
    df = pd.read_excel(DEFAULT_EXCEL_PATH)

    expected_subjects = df["Subject Identifier for the Study"].nunique()
    expected_events = len(df)
    expected_saes = (df["Serious Event"] == "Y").sum()

    assert counts["adverse_events"] == expected_events

    with sqlite3.connect(db_path) as conn:
        subjects_in_db = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        events_in_db = conn.execute("SELECT COUNT(*) FROM adverse_events").fetchone()[0]
        saes_in_db = conn.execute(
            "SELECT COUNT(*) FROM adverse_events WHERE serious_event = 'Y'"
        ).fetchone()[0]

    assert subjects_in_db == expected_subjects
    assert events_in_db == expected_events
    assert saes_in_db == expected_saes


def test_field_mapping(temp_environment):
    """Verify field mappings, value transformations, and date formatting."""
    mapper = FieldMapper(db_path=temp_environment["db_path"])
    fields = mapper.map_all_fields("C-906289-002-0422-001", 17)
    mapper.close()

    assert fields["sex"] == "male"
    assert fields["age"] == 74
    assert fields["race"].lower() == "white"
    assert fields["ethnicity"].lower() in {"not hispanic or latino", "not hispanic/latino"}
    assert fields["first_dose_date"] == "20-Dec-2023"
    assert fields["last_dose_date"] == "15-Jan-2024"
    assert fields["start_date"] == "22-Jan-2024"
    assert fields["end_date"] == "25-Jan-2024"


def test_template_selection(temp_environment):
    """Ensure correct templates are selected based on flags."""
    mapper = FieldMapper(db_path=temp_environment["db_path"])
    generator = NarrativeGenerator(field_mapper=mapper)

    hosp_event = mapper.get_event_data("C-906289-002-0422-001", 17)
    hosp_template = generator.select_template(hosp_event)
    assert hosp_template["template_id"] == "SAE_HOSP_V1"

    with sqlite3.connect(temp_environment["db_path"]) as conn:
        med_imp = conn.execute(
            """
            SELECT subject_id, sequence_number FROM adverse_events
            WHERE serious_event = 'Y'
              AND hospitalization = 'N'
              AND other_medically_important = 'Y'
            LIMIT 1
            """
        ).fetchone()

    assert med_imp is not None, "Need at least one medically important SAE in dataset."
    med_event = mapper.get_event_data(med_imp[0], med_imp[1])
    med_template = generator.select_template(med_event)
    assert med_template["template_id"] == "SAE_MED_IMP_V1"
    mapper.close()


def test_narrative_generation(temp_environment):
    """Generate a narrative and ensure structure is correct."""
    mapper = FieldMapper(db_path=temp_environment["db_path"])
    generator = NarrativeGenerator(field_mapper=mapper)
    narrative = generator.generate_narrative("C-906289-002-0422-001", 17)
    mapper.close()

    assert narrative.count("\n\n") >= 4
    assert "{" not in narrative
    assert "most recent dose" in narrative.lower()
    assert "action taken with study drug was" in narrative.lower()


def test_end_to_end(temp_environment):
    """Full workflow: generate narratives, confirm DB + doc outputs."""
    db_path = temp_environment["db_path"]
    output_dir = temp_environment["output_dir"]

    # Clean narratives table to avoid duplicate rows.
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM narratives")

    count = generate_all_saes(db_path=db_path, output_dir=output_dir)
    assert count >= 3

    generated_files = list(output_dir.glob("*_narrative_*.docx"))
    assert len(generated_files) == count

    with sqlite3.connect(db_path) as conn:
        narrative_rows = conn.execute("SELECT COUNT(*) FROM narratives").fetchone()[0]

    assert narrative_rows == count

    # Spot check that single generation still works with existing DB/output.
    text = generate_single_narrative(
        "C-906289-002-0422-001", 17, db_path=db_path, output_dir=output_dir
    )
    assert "upper gastrointestinal" in text.lower()


class DummyEnhancer:
    def __init__(self) -> None:
        self.called = False

    def enhance(self, field_values, template_id, baseline_text):
        self.called = True
        return baseline_text + "\n\n[Enhanced by OpenAI]"


def test_openai_enhancer_hook(temp_environment):
    """Ensure NarrativeGenerator uses the enhancer when provided."""
    mapper = FieldMapper(db_path=temp_environment["db_path"])
    enhancer = DummyEnhancer()
    generator = NarrativeGenerator(field_mapper=mapper, enhancer=enhancer)
    narrative = generator.generate_narrative("C-906289-002-0422-001", 17)
    mapper.close()

    assert enhancer.called is True
    assert narrative.endswith("[Enhanced by OpenAI]")

