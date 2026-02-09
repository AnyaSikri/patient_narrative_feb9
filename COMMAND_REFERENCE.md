# Command Reference Guide

Quick reference for all commands to run the patient narrative automation system.

---

## Initial Setup (One Time)

### 1. Navigate to Project
```bash
cd /Users/anyasikri/Downloads/rigel/patient_demo_new_/narrative_poc
```

### 2. Create Virtual Environment
```bash
python3 -m venv .venv
```

### 3. Activate Virtual Environment
```bash
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Create Database and Load Data
```bash
python src/main.py --setup
```

---

## Set OpenAI API Key (Each Session)

```bash
export OPENAI_API_KEY="sk-your-actual-key-here"
```

**Check if key is set:**
```bash
echo $OPENAI_API_KEY
```

**Or:**
```bash
python -c "import os; print('✅ API key is set' if os.getenv('OPENAI_API_KEY') else '❌ API key NOT set')"
```

---

## Generate Narratives

### Generate Single SAE Narrative

```bash
# ALT increased (liver event)
python src/main.py --generate-single "C-906289-002-0422-001" 14 --use-openai

# AST increased (liver event)
python src/main.py --generate-single "C-906289-002-0422-001" 15 --use-openai

# Upper GI hemorrhage
python src/main.py --generate-single "C-906289-002-0422-001" 17 --use-openai

# Cardiac failure
python src/main.py --generate-single "C-906289-002-0636-002" 8 --use-openai

# COVID-19
python src/main.py --generate-single "C-906289-002-0636-004" 3 --use-openai

# Pneumonia
python src/main.py --generate-single "C-906289-002-0633-006" 5 --use-openai
```

### Generate Single Non-Serious AE

```bash
# Cough (non-serious)
python src/main.py --generate-single "C-906289-002-0422-001" 1 --use-openai

# Fatigue (non-serious)
python src/main.py --generate-single "C-906289-002-0422-001" 2 --use-openai
```

### Generate All SAEs (12 narratives)

```bash
python src/main.py --generate-all --use-openai
```

### Generate All AEs (162 narratives - includes non-serious)

```bash
python src/main.py --generate-all --include-non-serious --use-openai
```

---

## View Output

### Open Output Folder
```bash
open output/narratives/
```

### List Generated Files
```bash
ls -la output/narratives/
```

### Count Generated Files
```bash
ls output/narratives/*.docx | wc -l
```

---

## Advanced Options

### Use Different OpenAI Model

```bash
# GPT-4o (more expensive, higher quality)
python src/main.py --generate-all --use-openai --openai-model gpt-4o

# GPT-4o-mini (cheaper, faster - default)
python src/main.py --generate-all --use-openai --openai-model gpt-4o-mini
```

### Adjust Temperature (Creativity)

```bash
# More creative/varied (higher temperature)
python src/main.py --generate-all --use-openai --openai-temperature 0.5

# More deterministic/consistent (lower temperature)
python src/main.py --generate-all --use-openai --openai-temperature 0.1
```

### Adjust Max Tokens (Narrative Length)

```bash
# Longer narratives
python src/main.py --generate-all --use-openai --openai-max-tokens 3000

# Shorter narratives
python src/main.py --generate-all --use-openai --openai-max-tokens 1500
```

### Combine Options

```bash
python src/main.py --generate-all --use-openai \
  --openai-model gpt-4o \
  --openai-temperature 0.3 \
  --openai-max-tokens 2500
```

---

## Testing

### Run Unit Tests
```bash
python -m pytest test_narratives.py
```

### Run Quick Test Script
```bash
python test_openai_narrative.py
```

---

## Database Operations

### View All SAEs in Database
```bash
sqlite3 data/processed/narratives.db "SELECT subject_id, sequence_number, preferred_term FROM adverse_events WHERE serious_event='Y' ORDER BY subject_id, sequence_number;"
```

### View All AEs for a Subject
```bash
sqlite3 data/processed/narratives.db "SELECT subject_id, sequence_number, preferred_term, serious_event FROM adverse_events WHERE subject_id='C-906289-002-0422-001' ORDER BY sequence_number;"
```

### Count Total AEs
```bash
sqlite3 data/processed/narratives.db "SELECT COUNT(*) FROM adverse_events;"
```

### Count SAEs Only
```bash
sqlite3 data/processed/narratives.db "SELECT COUNT(*) FROM adverse_events WHERE serious_event='Y';"
```

### View Generated Narratives
```bash
sqlite3 data/processed/narratives.db "SELECT id, subject_id, sequence_number, generation_date FROM narratives ORDER BY generation_date DESC LIMIT 10;"
```

### Reset Database (Delete and Recreate)
```bash
rm data/processed/narratives.db
python src/main.py --setup
```

---

## Git Operations

### Check Status
```bash
git status
```

### Add and Commit Changes
```bash
git add .
git commit -m "Your commit message here"
```

### Push to GitHub
```bash
git push origin main
```

### Pull Latest Changes
```bash
git pull origin main
```

### View Commit History
```bash
git log --oneline -10
```

---

## Virtual Environment Management

### Activate Virtual Environment
```bash
source .venv/bin/activate
```

### Deactivate Virtual Environment
```bash
deactivate
```

### Check Active Python
```bash
which python
```

### Check Installed Packages
```bash
pip list
```

### Check Specific Package Version
```bash
pip show openai
```

---

## Troubleshooting Commands

### Check Python Version
```bash
python --version
```

### Check if Database Exists
```bash
ls -la data/processed/
```

### Check OpenAI Package Version
```bash
pip show openai
```

### Reinstall OpenAI Package
```bash
pip uninstall openai -y
pip install openai==1.12.0
```

### Clear Python Cache
```bash
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

### View Recent Log Output
```bash
# If you're logging to a file
tail -f logs/narrative_generation.log
```

---

## Quick Start (Daily Workflow)

```bash
# 1. Navigate to project
cd /Users/anyasikri/Downloads/rigel/patient_demo_new_/narrative_poc

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Set API key
export OPENAI_API_KEY="sk-your-key-here"

# 4. Generate narratives
python src/main.py --generate-all --use-openai

# 5. View output
open output/narratives/

# 6. When done
deactivate
```

---

## Complete Example Session

```bash
# Start fresh session
cd /Users/anyasikri/Downloads/rigel/patient_demo_new_/narrative_poc
source .venv/bin/activate
export OPENAI_API_KEY="sk-your-key-here"

# Verify setup
echo $OPENAI_API_KEY
python --version
pip show openai

# Generate a test narrative
python src/main.py --generate-single "C-906289-002-0422-001" 14 --use-openai

# If successful, generate all SAEs
python src/main.py --generate-all --use-openai

# Check output
ls -la output/narratives/
open output/narratives/

# Commit and push changes
git add .
git commit -m "Generated narratives for all SAEs"
git push origin main

# Clean up
deactivate
```

---

## File Locations

- **Source code:** `src/`
- **Configuration:** `configs/`
- **Raw data:** `data/raw/`
- **Database:** `data/processed/narratives.db`
- **Output:** `output/narratives/`
- **Tests:** `test_narratives.py`, `test_openai_narrative.py`
- **Documentation:** `README.md`, `IMPLEMENTATION_SUMMARY.md`

---

## Common Issues & Solutions

### Issue: "No such file or directory"
**Solution:** Make sure you're in the `narrative_poc` directory
```bash
cd /Users/anyasikri/Downloads/rigel/patient_demo_new_/narrative_poc
```

### Issue: "OPENAI_API_KEY not set"
**Solution:** Set the environment variable
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

### Issue: "No module named 'openai'"
**Solution:** Activate venv and install dependencies
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Issue: "No suitable template found"
**Solution:** The event might not be a serious AE. Check with:
```bash
sqlite3 data/processed/narratives.db "SELECT serious_event FROM adverse_events WHERE subject_id='SUBJECT' AND sequence_number=N;"
```

### Issue: Python version incompatibility
**Solution:** Use Python 3.11 or upgrade openai package
```bash
pip install --upgrade openai
```

---

## Tips & Best Practices

1. **Always activate the virtual environment** before running commands
2. **Set the API key** at the start of each session
3. **Test with a single narrative** before generating all
4. **Check output files** after generation
5. **Commit changes regularly** to Git
6. **Use descriptive commit messages**
7. **Keep your API key secure** (never commit it)
8. **Monitor OpenAI API usage** to control costs

---

*Last Updated: December 2025*

