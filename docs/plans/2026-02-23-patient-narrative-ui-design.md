# Patient Narrative UI Design

## Purpose
Demo UI for clinical/regulatory audience. Single-page Streamlit app that showcases live narrative generation from structured adverse event data.

## Tech Stack
- **Streamlit** (Python-only, no frontend build step)
- Integrates directly with existing Python modules

## Layout

```
┌─────────────────────────────────────────────────────────┐
│  Patient Narrative Generator                            │
├──────────┬──────────────────────────────────────────────┤
│ SIDEBAR  │                MAIN AREA                     │
│          │  ┌─────────────┐  ┌───────────────────────┐ │
│ Subject  │  │ SOURCE DATA │  │ GENERATED NARRATIVE   │ │
│ dropdown │  │ cards       │  │                       │ │
│          │  │             │  │                       │ │
│ Event    │  │ Demographics│  │                       │ │
│ dropdown │  │ Treatment   │  │                       │ │
│          │  │ Event Info  │  │                       │ │
│ OpenAI   │  │ Seriousness │  │                       │ │
│ toggle   │  │             │  │                       │ │
│          │  └─────────────┘  └───────────────────────┘ │
│[Generate]│  ┌──────────────────────────────────────────┐│
│          │  │ Download as Word                         ││
│          │  └──────────────────────────────────────────┘│
└──────────┴──────────────────────────────────────────────┘
```

## Sidebar Controls
- **Subject dropdown**: All 16 subject IDs. Default: none selected.
- **Event dropdown**: Filtered by subject. Shows "Seq N — Preferred Term". Appears after subject selected.
- **SAEs only checkbox**: Default checked. Filters events to 12 SAEs only.
- **OpenAI Enhancement toggle**: Default on. When off, template-only generation.
- **Generate button**: Disabled until subject + event selected.

## Interaction Flow
1. Select subject -> event dropdown populates
2. Select event -> source data cards populate (left column)
3. Click Generate -> spinner ("Generating narrative...") -> narrative appears (right column)
4. Click Download -> Word doc downloads

## Source Data Cards (left column)
Four `st.expander` sections, all expanded by default:

| Card | Fields |
|------|--------|
| Demographics | Age, sex, race, ethnicity, subject ID, site ID, study ID |
| Treatment | Drug name, first dose date, last dose date |
| Event Details | Preferred term, verbatim term, start/end date, study days, severity grade |
| Seriousness & Outcome | Serious (Y/N), hospitalization, life-threatening, outcome, action taken, causality |

## Narrative Display (right column)
- Empty state with placeholder text before generation
- After generation: formatted narrative text
- Uses `st.markdown` for rendering

## Download
- "Download as Word" button appears after narrative generation
- Uses existing `document_generator.py` to create .docx
- Streamlit `st.download_button` for browser download

## File Structure
```
patient_narrative_feb9/
├── src/
│   ├── app.py              <- New Streamlit app (single file)
│   ├── main.py             (existing)
│   ├── data_loader.py      (existing)
│   ├── database_setup.py   (existing)
│   ├── field_mapper.py     (existing)
│   ├── narrative_generator.py (existing)
│   ├── ai_enhancer.py      (existing)
│   └── document_generator.py  (existing)
└── requirements.txt        <- Add streamlit
```

## Dependencies
- Add `streamlit` to requirements.txt
- All other dependencies already present

## Run Command
```bash
streamlit run src/app.py
```
