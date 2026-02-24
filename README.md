# Patient Narrative Automation - Proof of Concept

## Overview
Automated generation of patient safety narratives from ADAE data.

## Quick Start

1. **Create virtual environment** (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Setup database and load data:**
   ```bash
   python src/main.py --setup
   ```

4. **Set OpenAI API key** (for comprehensive narratives):
   ```bash
   export OPENAI_API_KEY="sk-your-key-here"
   ```

5. **Generate comprehensive SAE narratives with OpenAI:**
   ```bash
   python src/main.py --generate-all --use-openai
   ```

6. **Generate single narrative:**
   ```bash
   # With OpenAI enhancement (recommended):
   python src/main.py --generate-single "C-906289-002-0422-001" 15 --use-openai
   
   # Template-only (basic):
   python src/main.py --generate-single "C-906289-002-0422-001" 15
   ```

7. **Quick test:**
   ```bash
   python test_openai_narrative.py
   ```

5. (Optional) Refine with OpenAI:
   ```bash
   export OPENAI_API_KEY=sk-...
   python src/main.py --generate-all --use-openai --openai-model gpt-4o-mini
   ```

## Output

Narratives are saved to:
- Database: `data/processed/narratives.db`
- Word docs: `output/narratives/narrative_[subject]_[seq].docx`

## Configuration

Edit these files to customize:
- `configs/field_mappings.json` - field mappings
- `configs/narrative_templates.json` - narrative templates

## OpenAI Enhancement (Recommended)

The system uses OpenAI to generate comprehensive, guide-compliant narratives. The AI enhancer:

- Follows the complete narrative writing guide (configs/narrative_guide.txt)
- Applies all regulatory conventions and formatting rules
- Generates complete narratives with proper paragraph structure
- Ensures medical terminology accuracy
- Maintains factual accuracy while improving flow

**The OpenAI enhancement is strongly recommended for production-quality narratives.**

- Install requirements (includes `openai` SDK).
- Set `OPENAI_API_KEY` in your environment; never commit it to source control.
- Run any CLI command with `--use-openai` to route template output through the selected model.
- Tunable flags: `--openai-model`, `--openai-temperature`, `--openai-max-tokens`.
- If the API call fails, the script falls back to the deterministic template output.

## Testing

Run tests:
```bash
python test_narratives.py
```

## Data Scope

- Total AEs: 162
- SAEs: 12
- Subjects with SAEs: 7

## Generated Narratives

This POC generates narratives for:
1. Subject C-906289-002-0422-001, Seq 14 (ALT increased)
2. Subject C-906289-002-0422-001, Seq 15 (AST increased)
3. Subject C-906289-002-0422-001, Seq 17 (GI hemorrhage)
... and 9 more SAEs

## Streamlit Demo UI

The project includes a web-based demo UI built with [Streamlit](https://streamlit.io/), an open-source Python framework that turns Python scripts into interactive web apps with no frontend code required. Streamlit runs locally on your machine — all data stays on your computer and nothing is sent to Streamlit's servers, so it is safe to use with sensitive clinical data.

To launch the demo:
```bash
export OPENAI_API_KEY="sk-your-key-here"  # optional, for AI-enhanced narratives
streamlit run src/app.py
```

The UI lets you select a patient and adverse event, view the source data (demographics, treatment, event details), generate a narrative live, and download it as a Word document.

## Adverse Event Dataset

The source data (`data/raw/adae.xlsx`) is an ADAE (Analysis Dataset for Adverse Events) file from Study C-935788-061. It contains 162 treatment-emergent adverse events across 16 subjects, including 12 serious adverse events (SAEs) across 7 subjects. Fields include demographics, treatment exposure dates, MedDRA-coded event terms, severity grades, seriousness criteria (hospitalization, life-threatening, death), outcomes, actions taken, and causality assessments.

## Architecture

- Database: SQLite
- Templates: JSON configuration
- Output: Word documents (.docx)
- UI: Streamlit (Python)
- No external APIs required (OpenAI enhancement optional)

