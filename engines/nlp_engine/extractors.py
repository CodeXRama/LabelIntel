"""
LabelIntel — NLP Extractors
Pattern matchers and classification heuristics to identify packaging declarations.
"""

import re
from typing import List, Optional, Tuple
from engines.nlp_engine.normalizers import (
    normalize_consumer_contact,
    normalize_date,
    normalize_fssai,
    normalize_mrp,
    normalize_net_quantity,
)
from engines.nlp_engine.schemas import DeclarationType, ExtractedEntity

# Keyword Triggers for Declaration Classification
DECLARATION_PATTERNS = [
    (
        DeclarationType.MRP,
        re.compile(r"(?:m\.?r\.?p\.?|max(?:imum)?\s*retail\s*price|incl\w*\s*of\s*all\s*taxes|₹\s*[0-9]|rs\.?\s*[0-9])", re.IGNORECASE),
    ),
    (
        DeclarationType.NET_QUANTITY,
        re.compile(r"(?:net\s*(?:wt\.?|weight|qty\.?|quantity|vol\.?|volume)|\b[0-9]+\s*[x×]\s*[0-9]+(?:\.[0-9]+)?\s*(?:kg|kilogram|g|gm|grams|ml|ltr|litre|litres)\s*=\s*[0-9]+(?:\.[0-9]+)?\s*(?:kg|kilogram|g|gm|grams|ml|ltr|litre|litres)\b|[0-9]+(?:\.[0-9]+)?\s*(?:kg|kilogram|g|gm|grams|ml|ltr|litre|litres|pcs|units)\b)", re.IGNORECASE),
    ),
    (
        DeclarationType.MFG_DATE,
        re.compile(r"\b(?:mfg|pkd|packed|mfd|manufactur(?:ed|ing)\s*date|date\s*of\s*pack(?:ing|aged)?)\b", re.IGNORECASE),
    ),
    (
        DeclarationType.EXPIRY_DATE,
        re.compile(r"\b(?:exp(?:iry)?|use\s*by|expiration\s*date)\b", re.IGNORECASE),
    ),
    (
        DeclarationType.BEST_BEFORE,
        re.compile(r"\b(?:best\s*before|use\s*within)\b", re.IGNORECASE),
    ),
    (
        DeclarationType.BATCH_NUMBER,
        re.compile(r"\b(?:batch\s*(?:no\.?|code|num)?|lot\s*(?:no\.?|code)?)\b", re.IGNORECASE),
    ),
    (
        DeclarationType.FSSAI_LICENSE,
        re.compile(r"(?:fssai|lic(?:ense)?\.?(?:\s*no\.?)?\s*[:.]?\s*[0-9]{14})", re.IGNORECASE),
    ),
    (
        DeclarationType.CONSUMER_CARE,
        re.compile(r"(?:consumer\s*care|customer\s*care|toll\s*free|helpline|care@|feedback@|email\s*[:.]?)", re.IGNORECASE),
    ),
    (
        DeclarationType.MANUFACTURER,
        re.compile(r"(?:mfg\.?\s*by|manufactured\s*by|marketed\s*by|produced\s*by|packed\s*by)", re.IGNORECASE),
    ),
    (
        DeclarationType.COUNTRY_OF_ORIGIN,
        re.compile(r"(?:country\s*of\s*origin|made\s*in\s*india|product\s*of\s*india|made\s*in)", re.IGNORECASE),
    ),
    (
        DeclarationType.INGREDIENTS,
        re.compile(r"(?:ingredients?|contains\s*(?:milk|wheat|soya|nuts|gluten))", re.IGNORECASE),
    ),
    (
        DeclarationType.NUTRITION,
        re.compile(r"(?:nutritio(?:n|nal)\s*(?:facts|information|values)?|energy|carbohydrate|protein|added\s*sugar|fat\b)", re.IGNORECASE),
    ),
    (
        DeclarationType.CAUTION_WARNING,
        re.compile(r"(?:caution|warning|keep\s*out\s*of\s*reach|corrosive|poison|flammable)", re.IGNORECASE),
    ),
]


def classify_text_declaration(text: str) -> DeclarationType:
    """Classifies a textline into a DeclarationType based on prioritized patterns."""
    text_clean = text.strip()
    if not text_clean:
        return DeclarationType.OTHER

    # Nutrition panels commonly repeat serving bases as "Per100g"; this is not
    # the package's declared net quantity even though it contains a mass unit.
    if re.match(r"^per\s*100\s*(?:g|gm|grams?|ml)\b", text_clean, re.IGNORECASE):
        return DeclarationType.NUTRITION

    for decl_type, pattern in DECLARATION_PATTERNS:
        if pattern.search(text_clean):
            return decl_type

    return DeclarationType.OTHER


def extract_entity_from_ocr_block(
    block_id: str,
    text: str,
    confidence: float,
    entity_index: int,
) -> Optional[ExtractedEntity]:
    """
    Attempts to extract and normalize a structured declaration entity from an OCR block.
    """
    decl_type = classify_text_declaration(text)
    if decl_type == DeclarationType.OTHER:
        return None

    normalized_data = None
    parsing_notes = []

    # Execute specific normalizer depending on classified declaration
    if decl_type == DeclarationType.MRP:
        norm_mrp = normalize_mrp(text)
        if norm_mrp:
            normalized_data = norm_mrp.model_dump()
            parsing_notes.append("Parsed monetary amount and tax inclusion status.")
        else:
            parsing_notes.append("MRP keyword detected, but numeric price could not be isolated.")

    elif decl_type == DeclarationType.NET_QUANTITY:
        norm_qty = normalize_net_quantity(text)
        if norm_qty:
            normalized_data = norm_qty.model_dump()
            parsing_notes.append(f"Standardized to base SI unit: {norm_qty.standard_value} {norm_qty.standard_unit}.")
        else:
            return None

    elif decl_type in (DeclarationType.MFG_DATE, DeclarationType.EXPIRY_DATE, DeclarationType.BEST_BEFORE):
        date_ctx = "mfg" if decl_type == DeclarationType.MFG_DATE else ("expiry" if decl_type == DeclarationType.EXPIRY_DATE else "best_before")
        norm_dt = normalize_date(text, context_type=date_ctx)
        if norm_dt:
            normalized_data = norm_dt.model_dump()
            parsing_notes.append("Parsed calendar date or shelf life duration.")
        else:
            parsing_notes.append("Date keyword found, but format did not match expected DD/MM/YYYY or duration.")

    elif decl_type == DeclarationType.FSSAI_LICENSE:
        norm_fssai = normalize_fssai(text)
        if norm_fssai:
            normalized_data = norm_fssai.model_dump()
            parsing_notes.append(f"14-digit FSSAI format verified: {norm_fssai.is_valid_format}.")
        else:
            parsing_notes.append("FSSAI reference present, but 14-digit number not found.")

    elif decl_type == DeclarationType.CONSUMER_CARE:
        norm_contact = normalize_consumer_contact(text)
        if norm_contact:
            normalized_data = norm_contact.model_dump()
            parsing_notes.append(f"Extracted contact {norm_contact.contact_type}: {norm_contact.value}")
        else:
            parsing_notes.append("Consumer care keyword detected.")

    return ExtractedEntity(
        entity_id=f"ent_{entity_index:03d}",
        declaration_type=decl_type,
        raw_text=text.strip(),
        confidence=confidence,
        source_ocr_block_ids=[block_id],
        normalized_data=normalized_data,
        parsing_notes=parsing_notes,
    )
