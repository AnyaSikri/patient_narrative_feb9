"""Comprehensive test: attempt narrative generation for EVERY AE in adae.xlsx."""

from __future__ import annotations

import sqlite3
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from data_loader import DEFAULT_EXCEL_PATH
from database_setup import create_tables
from data_loader import ADAELoader
from field_mapper import FieldMapper
from narrative_generator import NarrativeGenerator
from document_generator import DocumentGenerator

import tempfile


def run_full_patient_audit():
    """Try to generate a narrative for every AE in adae.xlsx and report issues."""

    # Setup a fresh temp database
    tmp_dir = Path(tempfile.mkdtemp(prefix="narrative_audit_"))
    db_path = tmp_dir / "narratives.db"
    output_dir = tmp_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Working directory: {tmp_dir}")
    print(f"Excel source: {DEFAULT_EXCEL_PATH}\n")

    # 1. Setup database
    create_tables(db_path)
    loader = ADAELoader(db_path=db_path)
    counts = loader.load_to_database(db_path=db_path, excel_path=DEFAULT_EXCEL_PATH)
    print(f"Database loaded: {counts}\n")

    # 2. Get ALL adverse events
    with sqlite3.connect(db_path) as conn:
        all_events = conn.execute(
            "SELECT subject_id, sequence_number, preferred_term, serious_event, "
            "hospitalization, other_medically_important, treatment_emergent "
            "FROM adverse_events ORDER BY subject_id, sequence_number"
        ).fetchall()

    total = len(all_events)
    print(f"Total adverse events to process: {total}")
    print("=" * 100)

    # 3. Try generating narratives for each
    mapper = FieldMapper(db_path=db_path)
    generator = NarrativeGenerator(field_mapper=mapper)
    doc_gen = DocumentGenerator()

    successes = []
    failures = []
    warnings = []  # Narratives that generate but have quality issues

    for idx, (subject_id, seq, pt, serious, hosp, med_imp, te) in enumerate(all_events, 1):
        result = {
            "subject_id": subject_id,
            "sequence_number": seq,
            "preferred_term": pt,
            "serious_event": serious,
            "hospitalization": hosp,
            "other_medically_important": med_imp,
            "treatment_emergent": te,
        }

        try:
            # Step A: Field mapping
            fields = mapper.map_all_fields(subject_id, seq)

            # Step B: Check for critical missing fields
            missing_fields = []
            for key in ["age", "sex", "race", "ethnicity", "first_dose_date",
                        "last_dose_date", "start_date", "preferred_term",
                        "outcome", "action_taken", "causality"]:
                val = fields.get(key)
                if val is None or str(val).strip() == "" or str(val) == "nan":
                    missing_fields.append(key)

            # Step C: Generate narrative
            narrative = generator.generate_narrative(subject_id, seq)

            # Step D: Quality checks
            issues = []

            # Check for unresolved placeholders
            if "{" in narrative:
                issues.append("UNRESOLVED_PLACEHOLDERS: narrative contains '{' characters")

            # Check for [NOT AVAILABLE] markers
            not_avail_count = narrative.count("[NOT AVAILABLE]")
            if not_avail_count > 0:
                issues.append(f"NOT_AVAILABLE: {not_avail_count} fields show [NOT AVAILABLE]")

            # Check minimum paragraph count
            para_count = narrative.count("\n\n") + 1
            if para_count < 4:
                issues.append(f"LOW_PARAGRAPH_COUNT: only {para_count} paragraphs (expected >= 5)")

            # Check for "most recent dose" (business rule)
            if "most recent dose" not in narrative.lower() and "last dose" in narrative.lower():
                issues.append("BUSINESS_RULE: 'last dose' used instead of 'most recent dose'")

            # Check narrative length (should be meaningful)
            word_count = len(narrative.split())
            if word_count < 50:
                issues.append(f"TOO_SHORT: only {word_count} words")

            # Check for None/nan appearing literally in text
            if "None" in narrative or "nan" in narrative.lower().split():
                issues.append("LITERAL_NONE_OR_NAN: 'None' or 'nan' appears in narrative text")

            # Step E: Try generating Word document
            doc_path = output_dir / f"narrative_{subject_id}_{seq}.docx"
            doc_gen.create_narrative_document(narrative, subject_id, seq, doc_path)

            if not doc_path.exists():
                issues.append("DOC_GENERATION_FAILED: Word document not created")

            # Record result
            result["narrative_length"] = word_count
            result["paragraph_count"] = para_count
            result["missing_fields"] = missing_fields
            result["not_available_count"] = not_avail_count

            if issues:
                result["issues"] = issues
                warnings.append(result)
            else:
                successes.append(result)

        except Exception as e:
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()
            failures.append(result)

    mapper.close()

    # 4. Print report
    print("\n" + "=" * 100)
    print("NARRATIVE GENERATION AUDIT REPORT")
    print("=" * 100)

    print(f"\nTotal AEs: {total}")
    print(f"  Successes (clean):     {len(successes)}")
    print(f"  Warnings (generated but issues): {len(warnings)}")
    print(f"  Failures (exceptions): {len(failures)}")

    # --- Failures ---
    if failures:
        print("\n" + "-" * 100)
        print(f"FAILURES ({len(failures)}):")
        print("-" * 100)
        for f in failures:
            print(f"\n  Subject: {f['subject_id']}, Seq: {f['sequence_number']}, "
                  f"PT: {f['preferred_term']}")
            print(f"  Serious: {f['serious_event']}, Hosp: {f['hospitalization']}, "
                  f"Med Imp: {f['other_medically_important']}")
            print(f"  ERROR: {f['error']}")
            # Print just the last few lines of traceback
            tb_lines = f['traceback'].strip().split('\n')
            for line in tb_lines[-4:]:
                print(f"    {line}")

    # --- Warnings ---
    if warnings:
        print("\n" + "-" * 100)
        print(f"WARNINGS ({len(warnings)}):")
        print("-" * 100)

        # Group warnings by issue type
        issue_counts = {}
        for w in warnings:
            for issue in w["issues"]:
                issue_type = issue.split(":")[0]
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1

        print("\n  Issue type summary:")
        for issue_type, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
            print(f"    {issue_type}: {count} events")

        print("\n  Detailed warnings:")
        for w in warnings:
            print(f"\n  Subject: {w['subject_id']}, Seq: {w['sequence_number']}, "
                  f"PT: {w['preferred_term']}")
            print(f"  Serious: {w['serious_event']}, Hosp: {w['hospitalization']}, "
                  f"Med Imp: {w['other_medically_important']}, TE: {w['treatment_emergent']}")
            print(f"  Words: {w['narrative_length']}, Paragraphs: {w['paragraph_count']}")
            if w['missing_fields']:
                print(f"  Missing DB fields: {w['missing_fields']}")
            for issue in w['issues']:
                print(f"    -> {issue}")

    # --- Success sample ---
    if successes:
        print("\n" + "-" * 100)
        print(f"SUCCESSES ({len(successes)}) - Sample:")
        print("-" * 100)
        for s in successes[:5]:
            print(f"  Subject: {s['subject_id']}, Seq: {s['sequence_number']}, "
                  f"PT: {s['preferred_term']}, Words: {s['narrative_length']}, "
                  f"Paragraphs: {s['paragraph_count']}")

    # --- Per-patient summary ---
    print("\n" + "-" * 100)
    print("PER-PATIENT SUMMARY:")
    print("-" * 100)

    # Group by subject
    from collections import defaultdict
    patient_stats = defaultdict(lambda: {"total": 0, "success": 0, "warning": 0, "failure": 0})
    for s in successes:
        patient_stats[s["subject_id"]]["total"] += 1
        patient_stats[s["subject_id"]]["success"] += 1
    for w in warnings:
        patient_stats[w["subject_id"]]["total"] += 1
        patient_stats[w["subject_id"]]["warning"] += 1
    for f in failures:
        patient_stats[f["subject_id"]]["total"] += 1
        patient_stats[f["subject_id"]]["failure"] += 1

    print(f"\n  {'Subject ID':<35} {'Total':>6} {'OK':>6} {'Warn':>6} {'Fail':>6}")
    print(f"  {'-'*35} {'-'*6} {'-'*6} {'-'*6} {'-'*6}")
    for subj in sorted(patient_stats.keys()):
        stats = patient_stats[subj]
        print(f"  {subj:<35} {stats['total']:>6} {stats['success']:>6} "
              f"{stats['warning']:>6} {stats['failure']:>6}")

    # --- Generated docs count ---
    generated_docs = list(output_dir.glob("narrative_*.docx"))
    print(f"\n  Word documents generated: {len(generated_docs)} / {total}")

    print("\n" + "=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    run_full_patient_audit()
