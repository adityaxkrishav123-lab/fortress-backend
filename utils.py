import re
import logging

logger = logging.getLogger(__name__)

def clean_json_output(raw_string: str) -> str:
    """
    Surgically cleans malformed JSON output from AI models.
    Removes markdown backticks, trailing commas, and leading/trailing whitespace.
    """
    cleaned = raw_string.strip()
    
    # Remove markdown json codeblocks if present
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
        
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
        
    cleaned = cleaned.strip()

    # Regex to fix trailing commas before closing braces/brackets
    # This is the most common reason json.loads() fails on AI output
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)

    return cleaned
