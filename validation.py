"""
validation.py
=============
This module contains PURE VALIDATION functions — functions that check whether
input data meets certain rules and raise errors if not.

WHY a separate validation module?
-----------------------------------
Validation logic is reused in many places:
    - The CLI (main.py) validates user keyboard input.
    - The store manager validates data before creating objects.
    - The Streamlit GUI validates form fields.

By putting all validation in one place, we follow the DRY principle:
"Don't Repeat Yourself." If the SKU format rule changes, we fix it in ONE place.

All functions in this module follow the same contract:
    - Accept a raw value (usually a string from user input).
    - Return a clean, typed Python value if valid.
    - Raise a descriptive exception if invalid.
"""

from exceptions import InvalidSKUError


# ════════════════════════════════════════════════════════════════
# SKU VALIDATION
# ════════════════════════════════════════════════════════════════

def validate_sku(sku: str) -> str:
    """
    Validate and normalise a SKU string.

    Valid SKU format: 2–4 uppercase letters, followed immediately by 3–6 digits.
    The letters must come FIRST, then the digits (no mixing).

    Examples of VALID SKUs : ELEC001, ABC123, PR042, FOOD0099
    Examples of INVALID SKUs: 1AB23 (digits first), AB (no digits), TOOLONG1234567

    Parameters
    ----------
    sku : str
        The raw SKU string from user input.

    Returns
    -------
    str
        The validated, uppercased SKU.

    Raises
    ------
    InvalidSKUError
        If the SKU does not match the required format.
    """
    sku = sku.strip().upper()

    if not sku:
        raise InvalidSKUError(sku, "SKU cannot be empty.")

    # Check for invalid characters
    for char in sku:
        if not char.isalpha() and not char.isdigit():
            raise InvalidSKUError(sku, "SKU can only contain letters and digits.")

    # Find the boundary between letters and digits
    # We walk character by character until we hit the first digit
    split_index = None
    for i, char in enumerate(sku):
        if char.isdigit():
            split_index = i
            break

    # If no digit was ever found, the SKU has no numeric part
    if split_index is None:
        raise InvalidSKUError(sku, "SKU must end with at least 3 digits.")

    # If the very first character is a digit, letters come after — wrong order
    if split_index == 0:
        raise InvalidSKUError(sku, "SKU must start with 2–4 letters, not a digit.")

    letters_part = sku[:split_index]
    digits_part  = sku[split_index:]

    # The letters section must contain ONLY letters (no embedded digits)
    if not letters_part.isalpha():
        raise InvalidSKUError(sku, "Letters and digits must not be mixed.")

    # The digits section must contain ONLY digits
    if not digits_part.isdigit():
        raise InvalidSKUError(sku, "Letters and digits must not be mixed.")

    # Length checks
    if not (2 <= len(letters_part) <= 4):
        raise InvalidSKUError(sku, "SKU must start with 2 to 4 letters.")
    if not (3 <= len(digits_part) <= 6):
        raise InvalidSKUError(sku, "SKU must end with 3 to 6 digits.")

    return sku


# ════════════════════════════════════════════════════════════════
# NUMERIC VALIDATORS
# ════════════════════════════════════════════════════════════════

def validate_price(value, field_name: str = "Price") -> float:
    """
    Parse and validate a price or cost value.

    Prices may be 0 (e.g., a free promotional item) but cannot be negative.

    Parameters
    ----------
    value : any
        The raw value to validate (typically a string from user input).
    field_name : str
        Name of the field, used in the error message.

    Returns
    -------
    float
        The validated, non-negative price.

    Raises
    ------
    ValueError
        If the value is not a valid non-negative number.
    """
    try:
        price = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"'{field_name}' must be a number (e.g. 19.99). Got: '{value}'.")

    if price < 0:
        raise ValueError(f"'{field_name}' cannot be negative. Got: {price}.")

    return price


def validate_quantity(value, field_name: str = "Quantity") -> int:
    """
    Parse and validate a quantity (stock count or reorder level).

    Quantities may be 0 (empty shelf) but cannot be negative.

    Parameters
    ----------
    value : any
        The raw value to validate.
    field_name : str
        Name of the field, used in the error message.

    Returns
    -------
    int
        The validated, non-negative integer quantity.

    Raises
    ------
    ValueError
        If the value is not a valid non-negative whole number.
    """
    try:
        qty = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"'{field_name}' must be a whole number (e.g. 50). Got: '{value}'.")

    if qty < 0:
        raise ValueError(f"'{field_name}' cannot be negative. Got: {qty}.")

    return qty


def validate_positive_quantity(value, field_name: str = "Quantity") -> int:
    """
    Like validate_quantity() but also rejects zero.

    Used when at least 1 unit is required (e.g., units to sell or restock).

    Parameters
    ----------
    value : any
        The raw value to validate.
    field_name : str
        Name of the field, used in the error message.

    Returns
    -------
    int
        The validated, strictly positive integer.

    Raises
    ------
    ValueError
        If the value is zero or negative.
    """
    qty = validate_quantity(value, field_name)
    if qty == 0:
        raise ValueError(f"'{field_name}' must be greater than zero.")
    return qty


# ════════════════════════════════════════════════════════════════
# STRING VALIDATORS
# ════════════════════════════════════════════════════════════════

def validate_non_empty_string(value: str, field_name: str = "Field") -> str:
    """
    Ensure a string is not blank after stripping whitespace.

    Parameters
    ----------
    value : str
        The string to validate.
    field_name : str
        Name of the field, used in the error message.

    Returns
    -------
    str
        The stripped, non-empty string.

    Raises
    ------
    ValueError
        If the string is empty or only whitespace.
    """
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"'{field_name}' cannot be empty.")
    return cleaned


# ════════════════════════════════════════════════════════════════
# DATE VALIDATORS
# ════════════════════════════════════════════════════════════════

def validate_date_string(date_str: str) -> str:
    """
    Validate that a string is a valid date in YYYY-MM-DD format.

    Parameters
    ----------
    date_str : str
        The date string to validate.

    Returns
    -------
    str
        The validated date string (stripped).

    Raises
    ------
    ValueError
        If the format does not match YYYY-MM-DD.
    """
    from datetime import datetime
    date_str = str(date_str).strip()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(
            f"'{date_str}' is not a valid date. Use YYYY-MM-DD format (e.g. 2025-12-31)."
        )
    return date_str
