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

## Architecture

- Database: SQLite
- Templates: JSON configuration
- Output: Word documents (.docx)
- No external APIs (fully local)

