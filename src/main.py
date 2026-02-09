"""CLI orchestration for the patient narrative POC."""

from __future__ import annotations

import argparse
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from ai_enhancer import OpenAINarrativeEnhancer
from data_loader import (
    ADAELoader,
    DEFAULT_DB_PATH as LOADER_DB_PATH,
    DEFAULT_EXCEL_PATH as ADAE_EXCEL_PATH,
)
from database_setup import create_tables
from document_generator import DocumentGenerator
from field_mapper import FieldMapper, DEFAULT_DB_PATH as MAPPER_DB_PATH
from narrative_generator import NarrativeGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
LOGGER = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "output" / "narratives"


def setup_database(
    db_path: Path | str = LOADER_DB_PATH,
    excel_path: Path | str = ADAE_EXCEL_PATH,
) -> Dict[str, int]:
    """Create tables and load ADAE data."""
    LOGGER.info("Setting up database and loading ADAE data.")
    create_tables(Path(db_path))
    loader = ADAELoader(db_path=db_path)
    counts = loader.load_to_database(db_path=db_path, excel_path=excel_path)
    LOGGER.info("Database setup complete: %s", counts)
    return counts


def generate_single_narrative(
    subject_id: str,
    sequence_number: int,
    db_path: Path | str = MAPPER_DB_PATH,
    output_dir: Path | str = OUTPUT_DIR,
    enhancer: OpenAINarrativeEnhancer | None = None,
) -> str:
    """Generate, persist, and export a single narrative."""
    mapper = FieldMapper(db_path=db_path)
    generator = NarrativeGenerator(field_mapper=mapper, enhancer=enhancer)
    doc_gen = DocumentGenerator()

    narrative_text = generator.generate_narrative(subject_id, sequence_number)
    template = generator.select_template(
        mapper.get_event_data(subject_id, sequence_number) or {}
    )
    NarrativeGenerator.save_to_database(
        subject_id,
        sequence_number,
        narrative_text,
        template["template_id"],
        db_path=db_path,
    )
    output_dir = Path(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d")
    doc_path = output_dir / f"{timestamp}_narrative_{subject_id}_{sequence_number}.docx"
    doc_gen.create_narrative_document(
        narrative_text, subject_id, sequence_number, doc_path
    )
    print(narrative_text)
    mapper.close()
    return narrative_text


def generate_all_saes(
    db_path: Path | str = MAPPER_DB_PATH,
    output_dir: Path | str = OUTPUT_DIR,
    enhancer: OpenAINarrativeEnhancer | None = None,
    include_non_serious: bool = False,
) -> int:
    """Generate narratives for all SAEs (or all AEs if include_non_serious=True)."""
    mapper = FieldMapper(db_path=db_path)
    generator = NarrativeGenerator(field_mapper=mapper, enhancer=enhancer)
    doc_gen = DocumentGenerator()
    sae_events = _fetch_sae_events(db_path, include_non_serious=include_non_serious)
    narratives_list: List[Dict[str, str | int]] = []
    output_dir = Path(output_dir)

    for idx, (subject_id, sequence_number) in enumerate(sae_events, start=1):
        LOGGER.info(
            "Generating narrative %d/%d for subject %s seq %s",
            idx,
            len(sae_events),
            subject_id,
            sequence_number,
        )
        narrative = generator.generate_narrative(subject_id, sequence_number)
        template = generator.select_template(
            mapper.get_event_data(subject_id, sequence_number) or {}
        )
        NarrativeGenerator.save_to_database(
            subject_id,
            sequence_number,
            narrative,
            template["template_id"],
            db_path=db_path,
        )
        timestamp = datetime.now().strftime("%Y%m%d")
        doc_path = output_dir / f"{timestamp}_narrative_{subject_id}_{sequence_number}.docx"
        doc_gen.create_narrative_document(
            narrative, subject_id, sequence_number, doc_path
        )
        narratives_list.append(
            {
                "subject_id": subject_id,
                "sequence_number": sequence_number,
                "narrative_text": narrative,
            }
        )

    timestamp = datetime.now().strftime("%Y%m%d")
    batch_path = output_dir / f"{timestamp}_batch_report.docx"
    doc_gen.create_batch_document(narratives_list, batch_path)
    mapper.close()
    LOGGER.info("Generated %d SAE narratives.", len(sae_events))
    return len(sae_events)


def _fetch_sae_events(db_path: Path | str, include_non_serious: bool = False) -> List[Tuple[str, int]]:
    """Fetch SAE events (or all AEs if include_non_serious=True)."""
    with sqlite3.connect(db_path) as conn:
        if include_non_serious:
            # Get all treatment-emergent AEs (serious and non-serious)
            rows = conn.execute(
                """
                SELECT subject_id, sequence_number
                FROM adverse_events
                WHERE treatment_emergent = 'Y'
                ORDER BY subject_id, sequence_number
                """
            ).fetchall()
        else:
            # Get only SAEs
            rows = conn.execute(
                """
                SELECT subject_id, sequence_number
                FROM adverse_events
                WHERE serious_event = 'Y' AND treatment_emergent = 'Y'
                ORDER BY subject_id, sequence_number
                """
            ).fetchall()
    return [(row[0], row[1]) for row in rows]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Patient Narrative Automation CLI")
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Create tables and load ADAE data.",
    )
    parser.add_argument(
        "--generate-single",
        nargs=2,
        metavar=("SUBJECT_ID", "SEQUENCE"),
        help="Generate a single narrative for subject and sequence.",
    )
    parser.add_argument(
        "--generate-all",
        action="store_true",
        help="Generate narratives for all SAEs (or all AEs if --include-non-serious is set).",
    )
    parser.add_argument(
        "--include-non-serious",
        action="store_true",
        help="Include non-serious AEs when using --generate-all.",
    )
    parser.add_argument(
        "--use-openai",
        action="store_true",
        help="Pass generated narratives to OpenAI for refinement.",
    )
    parser.add_argument(
        "--openai-model",
        default="gpt-4o-mini",
        help="OpenAI model to use when --use-openai is set.",
    )
    parser.add_argument(
        "--openai-temperature",
        type=float,
        default=0.2,
        help="Sampling temperature for OpenAI enhancement.",
    )
    parser.add_argument(
        "--openai-max-tokens",
        type=int,
        default=2500,
        help="Max tokens for OpenAI responses.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    enhancer = None
    if args.use_openai:
        enhancer = _build_openai_enhancer(
            model=args.openai_model,
            temperature=args.openai_temperature,
            max_tokens=args.openai_max_tokens,
        )
    if args.setup:
        setup_database()
    elif args.generate_single:
        subject_id, sequence = args.generate_single
        generate_single_narrative(subject_id, int(sequence), enhancer=enhancer)
    elif args.generate_all:
        count = generate_all_saes(enhancer=enhancer, include_non_serious=args.include_non_serious)
        event_type = "AE" if args.include_non_serious else "SAE"
        print(f"Generated {count} {event_type} narratives.")
    else:
        print("No action specified. Use --help for options.")


def _build_openai_enhancer(
    model: str,
    temperature: float,
    max_tokens: int,
) -> OpenAINarrativeEnhancer:
    LOGGER.info("OpenAI enhancement enabled using model %s.", model)
    return OpenAINarrativeEnhancer(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


if __name__ == "__main__":
    main()

