"""
LabelIntel — NLP Normalizers
Deterministic normalization routines for price, quantity, dates, and contact information.
"""

import re
from datetime import datetime
from typing import Optional, Tuple
from engines.nlp_engine.schemas import (
    NormalizedContact,
    NormalizedDate,
    NormalizedFSSAI,
    NormalizedMRP,
    NormalizedNetQuantity,
)

# Month Name Mapping for Textual Dates
MONTH_NAMES = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def normalize_mrp(raw_text: str) -> Optional[NormalizedMRP]:
    """
    Parses MRP / Retail Sale Price declarations.
    Examples:
      'MRP Rs. 150.00 (incl. of all taxes)'
      'M.R.P. ₹ 85.50'
      'Rs 45'
      '₹ 120 (Rs. 1.20/g)'
    """
    cleaned = raw_text.replace(",", "")
    # Check for taxes inclusion
    tax_pattern = re.compile(r"(?:incl\w*\.?|inclusive)\s*(?:of)?\s*(?:all)?\s*tax\w*", re.IGNORECASE)
    is_inclusive = bool(tax_pattern.search(cleaned))

    # Match amount: matches ₹, Rs, Rs., INR followed by optional spaces and number
    # Also handles trailing currency markers or bare numeric following MRP/Price
    mrp_pattern = re.compile(
        r"(?:m\.?r\.?p\.?|max(?:imum)?\s*retail\s*price|price|rs\.?|inr|₹)\s*[:.]?\s*(?:rs\.?|inr|₹)?\s*([0-9]+(?:\.[0-9]{1,2})?)",
        re.IGNORECASE
    )
    match = mrp_pattern.search(cleaned)
    if not match:
        # Fallback: find any currency sign followed by digits
        curr_match = re.search(r"(?:₹|rs\.?)\s*([0-9]+(?:\.[0-9]{1,2})?)", cleaned, re.IGNORECASE)
        if curr_match:
            match = curr_match

    if not match:
        return None

    try:
        amount = float(match.group(1))
    except ValueError:
        return None

    # Check for unit sale price (e.g. Rs. 0.50 / g)
    unit_price = None
    unit_match = re.search(r"(?:unit\s*sale\s*price|usp|rs\.?|₹)\s*[:.]?\s*([0-9]+(?:\.[0-9]{1,2})?)\s*(?:/|per)\s*(?:g|ml|kg|l|unit)", cleaned, re.IGNORECASE)
    if unit_match:
        try:
            unit_price = float(unit_match.group(1))
        except ValueError:
            pass

    return NormalizedMRP(
        amount=amount,
        currency="INR",
        is_inclusive_of_taxes=is_inclusive,
        unit_price=unit_price,
        raw_text=raw_text.strip(),
    )


def normalize_net_quantity(raw_text: str) -> Optional[NormalizedNetQuantity]:
    """
    Parses net weight, volume, or count declarations.
    Examples:
      'Net Qty: 500 g'
      'Net Wt: 1 kg'
      'Net Volume: 750 ml'
      '1 Litre'
      '100 N' / '10 Units'
    """
    cleaned = raw_text.replace(",", " ").strip()

    # Pattern matching value and unit
    # Units: kg, g, gm, gms, grams, ml, l, ltr, litre, litres, n, pcs, units
    qty_pattern = re.compile(
        r"(?:net\s*(?:wt\.?|weight|qty\.?|quantity|vol\.?|volume)?\s*[:.]?\s*)?"
        r"([0-9]+(?:\.[0-9]+)?)\s*"
        r"(kg|kilograms?|g|gms?|grams?|ml|millilitres?|l|ltrs?|litres?|n|units?|pcs|pieces?)\b",
        re.IGNORECASE
    )
    match = qty_pattern.search(cleaned)
    if not match:
        return None

    val_str, unit_raw = match.group(1), match.group(2).lower()
    try:
        value = float(val_str)
    except ValueError:
        return None

    # Standardize units
    if unit_raw in ("kg", "kilogram", "kilograms"):
        unit = "kg"
        standard_unit = "g"
        standard_value = value * 1000.0
    elif unit_raw in ("g", "gm", "gms", "gram", "grams"):
        unit = "g"
        standard_unit = "g"
        standard_value = value
    elif unit_raw in ("l", "ltr", "ltrs", "litre", "litres"):
        unit = "l"
        standard_unit = "ml"
        standard_value = value * 1000.0
    elif unit_raw in ("ml", "millilitre", "millilitres"):
        unit = "ml"
        standard_unit = "ml"
        standard_value = value
    elif unit_raw in ("n", "unit", "units", "pc", "pcs", "piece", "pieces"):
        unit = "units"
        standard_unit = "units"
        standard_value = value
    else:
        unit = unit_raw
        standard_unit = unit_raw
        standard_value = value

    return NormalizedNetQuantity(
        value=value,
        unit=unit,
        standard_value=standard_value,
        standard_unit=standard_unit,
        raw_text=raw_text.strip(),
    )


def normalize_date(raw_text: str, context_type: str = "mfg") -> Optional[NormalizedDate]:
    """
    Parses manufacturing dates, expiry dates, or best-before periods.
    Examples:
      'Mfg Date: 12/2026'
      'PKD: 15/08/2026'
      'EXPIRY: 11-2027'
      'Best Before 12 Months from packaging'
    """
    cleaned = raw_text.strip()

    # Check for duration-based "Best Before X Months"
    shelf_match = re.search(r"best\s*before\s*([0-9]{1,2})\s*months?", cleaned, re.IGNORECASE)
    if shelf_match:
        months = int(shelf_match.group(1))
        return NormalizedDate(
            date_type="best_before",
            shelf_life_months=months,
            raw_text=raw_text.strip(),
        )

    # 1. Full Date: DD/MM/YYYY or DD-MM-YYYY
    full_pattern = re.compile(r"\b([0-3]?[0-9])[/-]([0-1]?[0-9])[/-](20[2-3][0-9])\b")
    match_full = full_pattern.search(cleaned)
    if match_full:
        d, m, y = int(match_full.group(1)), int(match_full.group(2)), int(match_full.group(3))
        if 1 <= m <= 12 and 1 <= d <= 31:
            return NormalizedDate(
                date_type=context_type,
                day=d,
                month=m,
                year=y,
                iso_date=f"{y:04d}-{m:02d}-{d:02d}",
                raw_text=raw_text.strip(),
            )

    # 2. Month-Year: MM/YYYY or MM-YYYY
    my_pattern = re.compile(r"\b([0-1]?[0-9])[/-](20[2-3][0-9])\b")
    match_my = my_pattern.search(cleaned)
    if match_my:
        m, y = int(match_my.group(1)), int(match_my.group(2))
        if 1 <= m <= 12:
            return NormalizedDate(
                date_type=context_type,
                month=m,
                year=y,
                iso_date=f"{y:04d}-{m:02d}",
                raw_text=raw_text.strip(),
            )

    # 3. Month Name Year: 'OCT 2026' or 'October 2026'
    for m_name, m_num in MONTH_NAMES.items():
        named_pat = re.compile(rf"\b{m_name}\.?\s*(?:20)?([2-3][0-9])\b", re.IGNORECASE)
        match_named = named_pat.search(cleaned)
        if match_named:
            yr_short = int(match_named.group(1))
            yr = 2000 + yr_short if yr_short < 100 else yr_short
            return NormalizedDate(
                date_type=context_type,
                month=m_num,
                year=yr,
                iso_date=f"{yr:04d}-{m_num:02d}",
                raw_text=raw_text.strip(),
            )

    return None


def normalize_fssai(raw_text: str) -> Optional[NormalizedFSSAI]:
    """
    Parses and validates 14-digit FSSAI license numbers.
    Examples:
      'fssai Lic. No. 10012022000277'
      'Lic No: 11521018000456'
    """
    cleaned = raw_text.replace(" ", "").replace("-", "")
    match = re.search(r"(?:fssai|lic(?:ense)?\.?(?:no\.?)?)\s*[:.]?\s*([0-9]{14})\b", cleaned, re.IGNORECASE)
    if not match:
        # Bare 14-digit number if fssai keyword is nearby
        if "fssai" in raw_text.lower():
            bare = re.search(r"\b([0-9]{14})\b", cleaned)
            if bare:
                match = bare

    if not match:
        return None

    lic_num = match.group(1)
    return NormalizedFSSAI(
        license_number=lic_num,
        is_valid_format=len(lic_num) == 14 and lic_num.isdigit(),
        raw_text=raw_text.strip(),
    )


def normalize_consumer_contact(raw_text: str) -> Optional[NormalizedContact]:
    """
    Parses consumer care phone numbers, email addresses, or postal references.
    """
    # 1. Email
    email_pat = re.search(r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b", raw_text)
    if email_pat:
        return NormalizedContact(
            contact_type="email",
            value=email_pat.group(1).lower(),
            raw_text=raw_text.strip(),
        )

    # 2. Phone / Toll-free
    phone_pat = re.search(r"(?:toll\s*free|tel|phone|contact|care)?\s*[:.]?\s*(1800[- ]?[0-9]{3}[- ]?[0-9]{3,4}|\+?91[- ]?[0-9]{10})\b", raw_text, re.IGNORECASE)
    if phone_pat:
        return NormalizedContact(
            contact_type="phone",
            value=phone_pat.group(1).replace(" ", "").replace("-", ""),
            raw_text=raw_text.strip(),
        )

    return None
