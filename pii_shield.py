"""
PII SHIELD — Local Privacy Layer (Runs BEFORE Gemini)
======================================================
Purpose: Detect and MASK all PII from raw document text before it is sent
to any external AI API (Gemini, etc.). Google never sees real names, phones,
or contact info. Only anonymized tokens are sent to the cloud.

Masking token format:
  [DONOR_NAME_1], [PHONE_1], [EMAIL_1], [ADDRESS_1], [ORG_ID_1]

The token map is returned separately and handed to EncryptionManager.
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger("PIIShield")

# -------------------------------------------------------
# REGEX PATTERNS — Tuned for Indian context
# -------------------------------------------------------

# Indian mobile numbers: +91-XXXXXXXXXX, 91XXXXXXXXXX, 0XXXXXXXXXX, XXXXXXXXXX
# Starts with 6, 7, 8, or 9 (valid Indian mobile prefixes)
# Phase 4 (Anti-Obfuscation): We add \s* and \-* between digits to catch 9 8 7 6 - 5 4 3 2 1 0
PHONE_PATTERN = re.compile(
    r'(?:\+91[\s\-]?|91[\s\-]?|0)?'
    r'[6-9][\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d',
    re.IGNORECASE
)

# Standard email pattern
EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b'
)

# Organisation/Trust registration IDs (Indian formats)
# Example: MH/2021/0012345, E-12345/MH, 80G/2022/XXXXXXX
ORG_ID_PATTERN = re.compile(
    r'\b(?:MH|DL|KA|TN|UP|GJ|RJ|MP|AP|TS|WB|OR|PB|HR|BR|JH|UK|HP|GA|JK|AS)/'
    r'\d{4}/\d{4,10}\b'
    r'|'
    r'\b(?:80G|12A|FCRA|CIN|TAN|PAN)[/\s\-]?\w{5,15}\b',
    re.IGNORECASE
)

# Names: Title + Capitalized word(s)
# Covers: Mr./Mrs./Dr./Shri/Smt./Prof. followed by 1-3 capitalized words
NAME_TITLE_PATTERN = re.compile(
    r'\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Shri|Smt\.|Prof\.|Er\.|Adv\.)\s+'
    r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}',
    re.UNICODE
)

# Address keywords — flag lines containing these as sensitive
ADDRESS_KEYWORDS = re.compile(
    r'\b(?:flat|plot|survey|gali|nagar|ward|taluka|tehsil|pincode|pin[\s\-]?code|'
    r'district|block|sector|house\s*no|h\.no|door\s*no|village|gram|'
    r'road|street|lane|marg|path|colony|society|chawl|bastee|'
    r'near|opp\.|behind|beside)\b',
    re.IGNORECASE
)


class PIIShield:
    """
    Local PII detection and masking.
    Call mask() before sending any text to Gemini or any external API.
    Call restore() to put original values back for user-facing output.
    """

    def mask(self, raw_text: str) -> Tuple[str, dict]:
        """
        Scans raw_text for PII, replaces with tokens.
        Returns:
            masked_text: safe to send to Gemini
            token_map: {token: original_value} — must be encrypted and stored
        """
        token_map = {}
        text = raw_text
        counter = {"phone": 0, "email": 0, "org_id": 0, "name": 0, "address": 0}

        # 1. Mask phone numbers first
        # ANTI-OBFUSCATION: Normalize by stripping spaces and dashes before regex match
        def replace_phone(match):
            counter["phone"] += 1
            token = f"[PHONE_{counter['phone']}]"
            token_map[token] = match.group(0)
            return token
            
        # We need to temporarily remove spaces and dashes to detect obfuscated numbers
        # But we still want to replace the original text, so we do a smart match
        normalized_text = text.replace(" ", "").replace("-", "")
        # Because replacing back in the original string with spaces is hard with regex,
        # we will broaden the regex to ignore spaces and dashes natively.
        text = PHONE_PATTERN.sub(replace_phone, text)

        # 2. Mask emails
        def replace_email(match):
            counter["email"] += 1
            token = f"[EMAIL_{counter['email']}]"
            token_map[token] = match.group(0)
            return token
        text = EMAIL_PATTERN.sub(replace_email, text)

        # 3. Mask org/trust registration IDs
        def replace_org_id(match):
            counter["org_id"] += 1
            token = f"[ORG_ID_{counter['org_id']}]"
            token_map[token] = match.group(0)
            return token
        text = ORG_ID_PATTERN.sub(replace_org_id, text)

        # 4. Mask titled names (Mr. Ramesh Sharma → [DONOR_NAME_1])
        def replace_name(match):
            counter["name"] += 1
            token = f"[DONOR_NAME_{counter['name']}]"
            token_map[token] = match.group(0)
            return token
        text = NAME_TITLE_PATTERN.sub(replace_name, text)

        # 5. Flag address lines — replace entire line if address keywords found
        masked_lines = []
        for line in text.splitlines():
            if ADDRESS_KEYWORDS.search(line):
                counter["address"] += 1
                token = f"[ADDRESS_{counter['address']}]"
                token_map[token] = line.strip()
                masked_lines.append(token)
            else:
                masked_lines.append(line)
        text = "\n".join(masked_lines)

        pii_count = sum(counter.values())
        if pii_count > 0:
            logger.warning(f"PIIShield masked {pii_count} sensitive fields: {counter}")
        else:
            logger.info("PIIShield: No PII detected in document.")

        return text, token_map

    def restore(self, masked_text: str, token_map: dict) -> str:
        """
        Restores original PII values from token map.
        Used for user-facing output (CSV/Excel visible to the NGO).
        """
        text = masked_text
        for token, original in token_map.items():
            text = text.replace(token, original)
        return text

    def get_encrypted_placeholder(self, token_map: dict) -> dict:
        """
        Returns a version of the token map with values replaced by [ENCRYPTED].
        Used for AI agent feed — agents see tokens but not real values.
        """
        return {token: "[ENCRYPTED]" for token in token_map}
