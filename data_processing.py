"""
data_processing.py
==================
This module contains PURE functions that analyse inventory and sales data.

WHY a separate data processing module?
----------------------------------------
Analysis logic is completely separate from:
    - HOW data is displayed (that's reporting.py's job).
    - HOW data is stored (that's file_handler.py's job).
    - HOW business operations are managed (that's store_manager.py's job).

All functions here are PURE: they accept data as arguments, perform
calculations, and return results. They never print anything, never modify
any object, and have no side effects. This makes them:
    - Easy to test (just call with data, check the return value).
    - Reusable in both the CLI and the Streamlit GUI.
    - Safe to call without worrying about unintended changes.
"""

from datetime import datetime
from exceptions import ZeroPriceError


# ════════════════════════════════════════════════════════════════
# REVENUE & PROFIT FUNCTIONS
# ════════════════════════════════════════════════════════════════

def get_total_revenue(inventory) -> float:
    """
    Calculate the total revenue from all transactions.

    Parameters
    ----------
    inventory : Inventory
        The Inventory object containing all transactions.

    Returns
    -------
    float
        Sum of (quantity_sold × unit_price) for every transaction.
    """
    total = 0.0
    for t in inventory.transactions:
        total += t.calculate_total()
    return total


def get_revenue_by_product(inventory) -> dict:
    """
    Break down total revenue by product SKU.

    Parameters
    ----------
    inventory : Inventory

    Returns
    -------
    dict
        Mapping of {sku: total_revenue_float}.
        Only products that have been sold appear in the result.
    """
    result = {}
    for t in inventory.transactions:
        result[t.product_sku] = result.get(t.product_sku, 0.0) + t.calculate_total()
    return result


def get_units_sold_per_product(inventory) -> dict:
    """
    Count total units sold for each product SKU.

    Parameters
    ----------
    inventory : Inventory

    Returns
    -------
    dict
        Mapping of {sku: total_units_sold_int}.
    """
    result = {}
    for t in inventory.transactions:
        result[t.product_sku] = result.get(t.product_sku, 0) + t.quantity_sold
    return result


def get_most_sold_products(inventory, n: int = 5) -> list:
    """
    Return the top-n products sorted by units sold (descending).

    Parameters
    ----------
    inventory : Inventory
    n : int
        Number of top products to return. Default is 5.

    Returns
    -------
    list of tuple (str, int)
        Each tuple is (sku, units_sold), sorted highest to lowest.
        Returns an empty list if no sales have been recorded.
    """
    units = get_units_sold_per_product(inventory)

    # sorted() with reverse=True gives us highest first
    sorted_items = sorted(units.items(), key=lambda item: item[1], reverse=True)
    return sorted_items[:n]


def get_profit_margin(product) -> float:
    """
    Calculate the profit margin percentage for a single product.

    Formula: ((price - cost) / price) × 100

    Parameters
    ----------
    product : Product
        The product to calculate the margin for.

    Returns
    -------
    float
        Profit margin as a percentage (e.g., 52.3 means 52.3%).

    Raises
    ------
    ZeroPriceError
        If the product's selling price is zero.
    """
    if product.price == 0:
        raise ZeroPriceError(product.sku)
    return ((product.price - product.cost) / product.price) * 100


def get_inventory_value(inventory) -> float:
    """
    Calculate the total value of all stock at cost price.

    This tells the store owner how much capital is tied up in inventory.
    Formula: sum of (cost × quantity) for every product.

    Parameters
    ----------
    inventory : Inventory

    Returns
    -------
    float
        Total stock value at cost price.
    """
    total = 0.0
    for product in inventory.products.values():
        total += product.cost * product.quantity
    return total


# ════════════════════════════════════════════════════════════════
# TRANSACTION FILTERING FUNCTIONS
# ════════════════════════════════════════════════════════════════

def filter_transactions_by_sku(inventory, sku: str) -> list:
    """
    Return all transactions for a specific product SKU.

    Parameters
    ----------
    inventory : Inventory
    sku : str
        The SKU to filter by (case-insensitive).

    Returns
    -------
    list of Transaction
        All transactions where product_sku matches.
    """
    sku = sku.strip().upper()
    return [t for t in inventory.transactions if t.product_sku == sku]


def filter_transactions_by_date(inventory, start_date: str, end_date: str) -> list:
    """
    Return transactions whose timestamp falls within [start_date, end_date].

    The end date is inclusive: a transaction at 23:59 on the end date IS included.

    Parameters
    ----------
    inventory : Inventory
    start_date : str
        Start date in YYYY-MM-DD format.
    end_date : str
        End date in YYYY-MM-DD format (inclusive, until 23:59:59).

    Returns
    -------
    list of Transaction
        All matching transactions, in chronological order.

    Raises
    ------
    ValueError
        If either date string is not in YYYY-MM-DD format.
    """
    try:
        start = datetime.strptime(start_date.strip(), "%Y-%m-%d")
        # Set end to 23:59:59 so the full end day is included
        end   = datetime.strptime(end_date.strip(), "%Y-%m-%d").replace(
            hour=23, minute=59, second=59
        )
    except ValueError:
        raise ValueError(
            "Dates must be in YYYY-MM-DD format (e.g. 2025-12-31)."
        )

    return [t for t in inventory.transactions if start <= t.timestamp <= end]


# ════════════════════════════════════════════════════════════════
# SUMMARY BUILDER
# ════════════════════════════════════════════════════════════════

def build_full_summary(inventory) -> dict:
    """
    Aggregate all key business metrics into a single summary dictionary.

    WHY a summary function?
    -----------------------
    The reporting module and Streamlit GUI both need the same set of
    metrics. Instead of each computing them independently, they both call
    this function. Single source of truth.

    Parameters
    ----------
    inventory : Inventory

    Returns
    -------
    dict
        Keys:
            total_revenue       (float)
            total_transactions  (int)
            inventory_value     (float)
            top_sellers         (list of (sku, units_sold) tuples)
            low_stock_count     (int)
            margins             (dict {sku: margin_float})
    """
    # Compute margins for every product, with fallback for zero-price items
    margins = {}
    for sku, product in inventory.products.items():
        try:
            margins[sku] = get_profit_margin(product)
        except ZeroPriceError:
            margins[sku] = 0.0   # report 0% margin rather than crashing

    return {
        "total_revenue":      get_total_revenue(inventory),
        "total_transactions": len(inventory.transactions),
        "inventory_value":    get_inventory_value(inventory),
        "top_sellers":        get_most_sold_products(inventory, n=5),
        "low_stock_count":    len(inventory.get_low_stock_products()),
        "margins":            margins,
    }
