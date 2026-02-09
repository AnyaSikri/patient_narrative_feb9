"""Quick test script for OpenAI-enhanced narrative generation."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from field_mapper import FieldMapper
from narrative_generator import NarrativeGenerator
from ai_enhancer import OpenAINarrativeEnhancer

# Configuration
DB_PATH = Path(__file__).parent / "data" / "processed" / "narratives.db"
CONFIG_PATH = Path(__file__).parent / "configs" / "field_mappings.json"
TEMPLATE_PATH = Path(__file__).parent / "configs" / "narrative_templates.json"

# Test subject: C-906289-002-0422-001, Sequence 15 (AST increased - liver event)
TEST_SUBJECT = "C-906289-002-0422-001"
TEST_SEQUENCE = 15

def main():
    """Generate a test narrative with OpenAI enhancement."""
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set.")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    
    print(f"Generating narrative for Subject {TEST_SUBJECT}, Sequence {TEST_SEQUENCE}")
    print("=" * 80)
    
    # Initialize components
    field_mapper = FieldMapper(CONFIG_PATH, DB_PATH)
    enhancer = OpenAINarrativeEnhancer(model="gpt-4o", temperature=0.3, max_tokens=3000)
    generator = NarrativeGenerator(TEMPLATE_PATH, field_mapper, enhancer=enhancer)
    
    # Generate narrative
    print("\n1. Generating baseline narrative from templates...")
    narrative = generator.generate_narrative(TEST_SUBJECT, TEST_SEQUENCE)
    
    print("\n2. FINAL NARRATIVE:")
    print("-" * 80)
    print(narrative)
    print("-" * 80)
    
    print("\n3. Saving to database...")
    narrative_id = generator.save_to_database(
        TEST_SUBJECT,
        TEST_SEQUENCE,
        narrative,
        "SAE_MED_IMP_V1_OPENAI",
        DB_PATH
    )
    print(f"Saved with ID: {narrative_id}")
    
    print("\n✅ Test complete!")

if __name__ == "__main__":
    main()

