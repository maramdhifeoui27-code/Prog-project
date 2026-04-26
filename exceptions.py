"""
exceptions.py
=============
This module defines ALL custom exceptions used by RetailTrack.

WHY a dedicated exceptions file?
---------------------------------
Instead of raising generic Python errors (like plain `Exception`), we create
our own error types that are specific to the retail domain. This makes it
crystal-clear WHAT went wrong and WHERE — both for the developer reading the
code and for the `except` clauses that catch them.

Think of it like this: a fire alarm (generic) vs. a "Low Stock" alarm
(specific). The specific one tells you exactly what to do next.

All custom exceptions inherit from a single base class (RetailTrackError),
which means you can catch ALL retail errors with one `except RetailTrackError`
or catch specific ones individually for finer control.
"""


# ─────────────────────────────────────────────────────────────
# BASE (PARENT) EXCEPTION
# ─────────────────────────────────────────────────────────────

class RetailTrackError(Exception):
    """
    The base class for all RetailTrack-specific errors.

    Every custom exception in this project inherits from this class.
    This is useful because you can catch ALL retail errors with a single
    `except RetailTrackError` clause, or catch specific ones individually.

    Parameters
    ----------
    message : str
        A human-readable description of what went wrong.
    """

    def __init__(self, message: str = "An unexpected retail system error occurred."):
        super().__init__(message)
        self.message = message

    def __str__(self):
        """Return a clean string when this error is printed."""
        return f"[RetailTrack Error] {self.message}"


# ─────────────────────────────────────────────────────────────
# PRODUCT-RELATED EXCEPTIONS
# ─────────────────────────────────────────────────────────────

class DuplicateSKUError(RetailTrackError):
    """
    Raised when someone tries to add a product with a SKU that already exists.

    Example scenario: Product 'ELEC001' is already in the inventory.
    Someone tries to add another product with the same SKU.

    Parameters
    ----------
    sku : str
        The duplicate SKU that caused the conflict.
    """

    def __init__(self, sku: str):
        message = (
            f"SKU '{sku}' already exists in the inventory. "
            "Each product must have a unique SKU."
        )
        super().__init__(message)
        self.sku = sku


class ProductNotFoundError(RetailTrackError):
    """
    Raised when a product lookup fails because the SKU does not exist.

    Parameters
    ----------
    sku : str
        The SKU that could not be found.
    """

    def __init__(self, sku: str):
        message = f"No product with SKU '{sku}' was found in the inventory."
        super().__init__(message)
        self.sku = sku


class InsufficientStockError(RetailTrackError):
    """
    Raised when a sale is attempted for more units than are in stock.

    Example scenario: Only 5 units of 'ELEC001' remain, but someone
    tries to sell 10.

    Parameters
    ----------
    sku : str
        The product SKU with insufficient stock.
    requested : int
        How many units were requested.
    available : int
        How many units are actually in stock.
    """

    def __init__(self, sku: str, requested: int, available: int):
        message = (
            f"Cannot sell {requested} unit(s) of '{sku}'. "
            f"Only {available} unit(s) available in stock."
        )
        super().__init__(message)
        self.sku = sku
        self.requested = requested
        self.available = available


# ─────────────────────────────────────────────────────────────
# SKU VALIDATION EXCEPTION
# ─────────────────────────────────────────────────────────────

class InvalidSKUError(RetailTrackError):
    """
    Raised when a SKU string does not match the required format.

    Valid SKU format: 2–4 uppercase letters followed by 3–6 digits.
    Examples of valid SKUs: ABC123, ELEC001, PR042X (invalid — mixed).

    Parameters
    ----------
    sku : str
        The invalid SKU string that was provided.
    reason : str
        A short explanation of what is wrong with the format.
    """

    def __init__(self, sku: str, reason: str = ""):
        message = (
            f"'{sku}' is not a valid SKU format. "
            f"Expected 2–4 letters followed by 3–6 digits (e.g. ELEC001). "
            f"{reason}"
        )
        super().__init__(message)
        self.sku = sku


# ─────────────────────────────────────────────────────────────
# MARGIN CALCULATION EXCEPTION
# ─────────────────────────────────────────────────────────────

class ZeroPriceError(RetailTrackError):
    """
    Raised when a profit margin calculation is attempted on a product
    whose selling price is zero, which would cause a division by zero.

    Parameters
    ----------
    sku : str
        The product SKU with a zero price.
    """

    def __init__(self, sku: str):
        message = (
            f"Cannot calculate profit margin for '{sku}': "
            "selling price is 0. Please update the product price."
        )
        super().__init__(message)
        self.sku = sku


# ─────────────────────────────────────────────────────────────
# FILE-RELATED EXCEPTION
# ─────────────────────────────────────────────────────────────

class DataLoadError(RetailTrackError):
    """
    Raised when a data file cannot be loaded correctly due to bad formatting.

    Parameters
    ----------
    filename : str
        The file that caused the problem.
    detail : str
        Extra context about what was malformed.
    """

    def __init__(self, filename: str, detail: str = ""):
        message = f"Could not load data from '{filename}'. {detail}"
        super().__init__(message)
        self.filename = filename
