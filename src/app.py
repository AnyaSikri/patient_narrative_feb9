"""Streamlit demo UI for Patient Narrative Generator."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to path so existing bare imports work
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import sqlite3
import tempfile

import streamlit as st

from field_mapper import FieldMapper
from narrative_generator import NarrativeGenerator
from document_generator import DocumentGenerator

BASE_DIR = SRC_DIR.parent
DB_PATH = BASE_DIR / "data" / "processed" / "narratives.db"

st.set_page_config(
    page_title="Patient Narrative Generator",
    page_icon="\U0001f3e5",
    layout="wide",
)

st.title("Patient Narrative Generator")
st.caption("Rigel Pharmaceuticals \u2014 Study C-935788-061")


# ── Helper queries ──────────────────────────────────────


@st.cache_data
def get_subjects() -> list[str]:
    """Fetch all subject IDs from database."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT DISTINCT subject_id FROM subjects ORDER BY subject_id"
        ).fetchall()
    return [r[0] for r in rows]


@st.cache_data
def get_events(subject_id: str, sae_only: bool) -> list[dict]:
    """Fetch events for a subject."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        if sae_only:
            rows = conn.execute(
                """SELECT sequence_number, preferred_term, serious_event
                   FROM adverse_events
                   WHERE subject_id = ? AND serious_event = 'Y' AND treatment_emergent = 'Y'
                   ORDER BY sequence_number""",
                (subject_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT sequence_number, preferred_term, serious_event
                   FROM adverse_events
                   WHERE subject_id = ? AND treatment_emergent = 'Y'
                   ORDER BY sequence_number""",
                (subject_id,),
            ).fetchall()
    return [
        {"seq": r[0], "preferred_term": r[1] or "Unknown", "serious": r[2]}
        for r in rows
    ]


# ── Sidebar ─────────────────────────────────────────────

with st.sidebar:
    st.header("Controls")

    sae_only = st.checkbox("SAEs only", value=True)

    subjects = get_subjects()
    subject_id = st.selectbox(
        "Subject",
        options=[""] + subjects,
        format_func=lambda x: "Select a subject..." if x == "" else x,
    )

    # Event dropdown (filtered by subject)
    events: list[dict] = []
    selected_event: dict | None = None
    if subject_id:
        events = get_events(subject_id, sae_only)
        event_options = [""] + [
            f"Seq {e['seq']} \u2014 {e['preferred_term']}" for e in events
        ]
        event_choice = st.selectbox(
            "Adverse Event",
            options=event_options,
            format_func=lambda x: "Select an event..." if x == "" else x,
        )
        if event_choice and event_choice != "":
            idx = event_options.index(event_choice) - 1
            selected_event = events[idx]

    st.divider()
    use_openai = st.toggle("OpenAI Enhancement", value=False)

    generate_disabled = not (subject_id and selected_event)
    generate_clicked = st.button(
        "Generate Narrative",
        disabled=generate_disabled,
        type="primary",
        use_container_width=True,
    )

# ── Main area ───────────────────────────────────────────

if subject_id and selected_event:
    seq_num = selected_event["seq"]

    # Query source data
    mapper = FieldMapper(db_path=DB_PATH)
    subject_data = mapper.get_subject_data(subject_id) or {}
    treatment_data = mapper.get_treatment_data(subject_id) or {}
    event_data = mapper.get_event_data(subject_id, seq_num) or {}
    mapper.close()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Source Data")

        with st.expander("Demographics", expanded=True):
            st.markdown(f"""
| Field | Value |
|-------|-------|
| **Subject ID** | {subject_data.get('subject_id', '—')} |
| **Study** | {subject_data.get('study_id', '—')} |
| **Site** | {subject_data.get('site_id', '—')} |
| **Age** | {subject_data.get('age', '—')} {subject_data.get('age_units', '')} |
| **Sex** | {subject_data.get('sex', '—')} |
| **Race** | {subject_data.get('race', '—')} |
| **Ethnicity** | {subject_data.get('ethnicity', '—')} |
""")

        with st.expander("Treatment", expanded=True):
            st.markdown(f"""
| Field | Value |
|-------|-------|
| **Drug** | {treatment_data.get('actual_treatment', '—')} |
| **First Dose** | {treatment_data.get('first_dose_date', '—')} |
| **Last Dose** | {treatment_data.get('last_dose_date', '—')} |
""")

        with st.expander("Event Details", expanded=True):
            st.markdown(f"""
| Field | Value |
|-------|-------|
| **Preferred Term** | {event_data.get('preferred_term', '—')} |
| **Verbatim Term** | {event_data.get('verbatim_term', '—')} |
| **SOC** | {event_data.get('soc', '—')} |
| **Start Date** | {event_data.get('start_date', '—')} |
| **End Date** | {event_data.get('end_date', '—')} |
| **Study Day Start** | {event_data.get('study_day_start', '—')} |
| **Study Day End** | {event_data.get('study_day_end', '—')} |
| **Severity Grade** | {event_data.get('severity_grade', '—')} |
""")

        with st.expander("Seriousness & Outcome", expanded=True):
            st.markdown(f"""
| Field | Value |
|-------|-------|
| **Serious** | {event_data.get('serious_event', '—')} |
| **Hospitalization** | {event_data.get('hospitalization', '—')} |
| **Life Threatening** | {event_data.get('life_threatening', '—')} |
| **Results in Death** | {event_data.get('results_in_death', '—')} |
| **Outcome** | {event_data.get('outcome', '—')} |
| **Action Taken** | {event_data.get('action_taken', '—')} |
| **Causality** | {event_data.get('causality', '—')} |
""")

    with col_right:
        st.subheader("Generated Narrative")

        if generate_clicked:
            with st.spinner("Generating narrative..."):
                enhancer = None
                if use_openai:
                    import os

                    if os.getenv("OPENAI_API_KEY"):
                        from ai_enhancer import OpenAINarrativeEnhancer

                        enhancer = OpenAINarrativeEnhancer()
                    else:
                        st.warning(
                            "OPENAI_API_KEY not set. Using template-only generation."
                        )

                gen_mapper = FieldMapper(db_path=DB_PATH)
                generator = NarrativeGenerator(
                    field_mapper=gen_mapper, enhancer=enhancer
                )
                narrative_text = generator.generate_narrative(subject_id, seq_num)
                gen_mapper.close()

            st.session_state["narrative"] = narrative_text
            st.session_state["narrative_subject"] = subject_id
            st.session_state["narrative_seq"] = seq_num

        # Display narrative from session state
        narrative = st.session_state.get("narrative")
        if narrative:
            st.markdown(narrative)

            # Download button
            doc_gen = DocumentGenerator()
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                doc_gen.create_narrative_document(
                    narrative,
                    st.session_state["narrative_subject"],
                    st.session_state["narrative_seq"],
                    tmp.name,
                )
                docx_bytes = Path(tmp.name).read_bytes()

            st.download_button(
                label="Download as Word",
                data=docx_bytes,
                file_name=f"narrative_{subject_id}_{seq_num}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        else:
            st.markdown(
                "_Click **Generate Narrative** in the sidebar to create a narrative for the selected patient and event._"
            )

else:
    st.info(
        "Select a subject and adverse event from the sidebar to view source data and generate a narrative."
    )
