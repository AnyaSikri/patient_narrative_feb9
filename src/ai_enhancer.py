"""OpenAI-based comprehensive narrative enhancement with full guide integration."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

LOGGER = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
GUIDE_PATH = BASE_DIR / "configs" / "narrative_guide.txt"


class OpenAINarrativeEnhancer:
    """Enhance narratives using OpenAI with comprehensive narrative guide."""

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.3,
        max_tokens: int = 3000,
        client: Optional[Any] = None,
        guide_path: Optional[Path] = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = client or self._build_client()
        
        # Load narrative guide
        self.guide_path = guide_path or GUIDE_PATH
        self.narrative_guide = self._load_guide()
        
        LOGGER.info(
            "Initialized OpenAINarrativeEnhancer with model=%s, temperature=%.2f, max_tokens=%d",
            model,
            temperature,
            max_tokens,
        )

    def _load_guide(self) -> str:
        """Load the comprehensive narrative writing guide."""
        try:
            if self.guide_path.exists():
                guide_text = self.guide_path.read_text(encoding="utf-8")
                LOGGER.info("Loaded narrative guide from %s (%d chars)", self.guide_path, len(guide_text))
                return guide_text
            else:
                LOGGER.warning("Narrative guide not found at %s", self.guide_path)
                return ""
        except Exception as e:
            LOGGER.error("Failed to load narrative guide: %s", e)
            return ""

    def enhance(
        self,
        field_values: Dict[str, Any],
        template_id: str,
        baseline_text: str,
    ) -> str:
        """
        Generate comprehensive narrative using OpenAI with full guide compliance.
        
        Args:
            field_values: All structured data fields from ADAE/SDTM
            template_id: Template identifier
            baseline_text: Basic template-generated text
            
        Returns:
            Complete, guide-compliant narrative
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_comprehensive_user_prompt(field_values, baseline_text, template_id)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        try:
            LOGGER.info("Calling OpenAI for comprehensive narrative generation...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            content = response.choices[0].message.content or baseline_text
            LOGGER.info("OpenAI enhancement completed successfully.")
            return content.strip()
            
        except Exception as exc:
            LOGGER.warning(
                "OpenAI enhancement failed (%s). Falling back to baseline narrative.",
                exc,
            )
            return baseline_text

    def _build_system_prompt(self) -> str:
        """Build comprehensive system prompt with guide."""
        return f"""You are an expert medical writer specializing in clinical adverse event narratives for regulatory submissions (FDA, EMA). You have deep expertise in:

- Clinical trial safety reporting
- ICH E2B/E2C guidelines
- MedDRA terminology
- Regulatory writing conventions
- Medical terminology and clinical assessment

You write complete, accurate, compliant narratives that follow sponsor-specific writing guides exactly.

**YOUR NARRATIVE WRITING GUIDE:**
{self.narrative_guide}

**CRITICAL RULES:**
1. Follow the guide conventions EXACTLY - this is non-negotiable
2. Never invent data not provided in structured fields
3. Use proper medical terminology and regulatory language
4. Maintain factual accuracy above all else
5. Generate complete narratives with all required paragraphs
6. Apply all formatting rules (dates, capitalization, phrasing)
"""

    def _build_comprehensive_user_prompt(
        self,
        field_values: Dict[str, Any],
        baseline_text: str,
        template_id: str,
    ) -> str:
        """Build detailed user prompt with all available data."""
        
        # Organize fields by category
        demographics = self._extract_category(field_values, [
            "age", "sex", "race", "ethnicity", "subject_id", "site_id", "study_id"
        ])
        
        treatment = self._extract_category(field_values, [
            "actual_treatment", "first_dose_date", "last_dose_date"
        ])
        
        event_details = self._extract_category(field_values, [
            "verbatim_term", "preferred_term", "start_date", "end_date",
            "study_day_start", "study_day_end", "severity_grade", "outcome",
            "action_taken", "causality", "analysis_causality", "hospitalization",
            "life_threatening", "results_in_death", "other_medically_important",
            "serious_event", "soc"
        ])
        
        prompt = f"""Generate a COMPLETE patient safety narrative following the guide conventions exactly.

**TEMPLATE USED:** {template_id}

**BASELINE NARRATIVE (from simple templates):**
{baseline_text}

**ALL AVAILABLE STRUCTURED DATA:**

Demographics:
{self._format_dict(demographics)}

Treatment Information:
{self._format_dict(treatment)}

Event Details:
{self._format_dict(event_details)}

**YOUR TASK:**

1. Generate a COMPREHENSIVE, DETAILED narrative with proper paragraph structure:
   - Paragraph 1: Demographics (age, sex, race, ethnicity, subject ID, site, study) - 2-3 sentences
   - Paragraph 2: Concomitant medications (state "not available" if no data) - 1 sentence
   - Paragraph 3: Study drug dosing leading up to event (use "most recent dose") - 2-3 sentences with specific dates and Study Day numbers
   - Paragraph 4+: Event description (3-5 sentences):
     * Opening sentence with date, Study Day, and event description
     * Clinical presentation and symptoms (if applicable)
     * Laboratory values with reference ranges (if applicable)
     * Clinical course and interventions
     * Outcome with date and Study Day
   - Final: Action taken and causality assessment - 2 sentences

2. Apply ALL guide conventions:
   ✓ Use "year-old" (not "years-old" or "YEARS-old")
   ✓ Proper case for race/ethnicity (e.g., "White Not Hispanic or Latino")
   ✓ Lowercase preferred term after "SAE of"
   ✓ Use "most recent dose" NEVER "last dose"
   ✓ Add Study Day # ONLY for: onset date, stop date, dosing dates
   ✓ Correct hospitalization phrasing per guide
   ✓ Lowercase action_taken and causality in final sentence
   ✓ Format dates as DD-MMM-YYYY
   ✓ Add verbatim term in parentheses if different from PT

3. For liver events (ALT/AST increased):
   - Mention that laboratory values and ULN calculations would be included if baseline data were available
   - Note this is a medically significant event

4. Ensure natural flow while maintaining factual accuracy

5. **IMPORTANT - ADD CLINICAL DETAIL:**
   - For liver events: Include specific AST/ALT values if available in verbatim term
   - Describe clinical significance (e.g., "representing Grade 3 hepatotoxicity")
   - Add context about timing relative to treatment
   - Include any relevant clinical assessments
   - Make each paragraph substantive (not just 1 sentence)

6. **TARGET LENGTH:** Aim for 250-400 words total (not 100 words)

**OUTPUT REQUIREMENTS:**
- Return ONLY the complete narrative text
- Use double line breaks between paragraphs
- No commentary, explanations, or meta-text
- No unresolved placeholders like {{field}}
- Professional regulatory tone throughout
- Each paragraph should be 2-5 sentences (not just 1 sentence)

Generate the comprehensive narrative now:"""

        return prompt

    @staticmethod
    def _extract_category(data: Dict[str, Any], keys: list) -> Dict[str, Any]:
        """Extract subset of fields for a category."""
        return {k: v for k, v in data.items() if k in keys and v is not None}

    @staticmethod
    def _format_dict(data: Dict[str, Any]) -> str:
        """Format dictionary as readable list."""
        if not data:
            return "  (no data available)"
        lines = [f"  - {k}: {v}" for k, v in sorted(data.items())]
        return "\n".join(lines)

    @staticmethod
    def _build_client():
        """Build OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY environment variable is required when --use-openai is set."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "openai package is not installed. Run `pip install -r requirements.txt`."
            ) from exc
        return OpenAI(api_key=api_key)
