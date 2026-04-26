"""
file_handler.py
===============
This module handles ALL file reading and writing for RetailTrack.

WHY isolate file I/O here?
----------------------------
File operations are inherently risky:
  - Files might not exist (FileNotFoundError).
  - Files might be empty or malformed (ValueError, KeyError).
  - Disk could be full or permissions denied (OSError).

By keeping all this risk in ONE module, we:
  1. Contain all the try-except boilerplate in one place.
  2. Let the rest of the application assume clean data objects.
  3. Make it easy to swap CSV storage for a database later (just change this file).

This module has NO awareness of the menu, GUI, or manager's logic.
It only knows how to read/write files and return raw data structures.
"""

import csv
import os
from datetime import datetime

from exceptions import DataLoadError

# ── File paths (constants — easy to change in one place) ──
DATA_DIR          = "data"
PRODUCTS_FILE     = "data/products.csv"
TRANSACTIONS_FILE = "data/transactions.csv"
REPORT_FILE       = "data/daily_report.txt"

# ── CSV column headers ──
PRODUCT_FIELDS     = ["sku", "name", "price", "cost", "quantity", "reorder_level"]
TRANSACTION_FIELDS = ["transaction_id", "product_sku", "quantity_sold",
                      "unit_price", "total", "timestamp"]


def _ensure_data_directory():
    """
    Create the 'data/' folder if it doesn't exist yet.

    WHY? We don't want the program to crash if the data folder is missing.
    This runs silently before any file operation.
    """
    os.makedirs(DATA_DIR, exist_ok=True)   # exist_ok=True: don't error if already exists


# ════════════════════════════════════════════════════════════════
# LOADING FUNCTIONS (Reading from disk)
# ════════════════════════════════════════════════════════════════

def load_products() -> list:
    """
    Load all products from the products CSV file.

    Returns a list of dictionaries (one per row). The store manager will
    then convert these dicts into Product objects.

    Returns
    -------
    list of dict
        Each dict has keys matching PRODUCT_FIELDS.
        Returns an empty list if the file doesn't exist or is empty.
    """
    _ensure_data_directory()

    # Graceful startup: if no file, return empty (not a crash)
    if not os.path.exists(PRODUCTS_FILE):
        print(f"[Info] '{PRODUCTS_FILE}' not found. Starting with an empty product catalogue.")
        return []

    products = []
    try:
        with open(PRODUCTS_FILE, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_number, row in enumerate(reader, start=2):   # row 1 is the header
                try:
                    _check_row_fields(row, PRODUCT_FIELDS, PRODUCTS_FILE, row_number)
                    products.append(dict(row))
                except DataLoadError as e:
                    # Log the bad row and skip it — don't crash the whole startup
                    print(f"[Warning] Skipping malformed row {row_number} in products file: {e}")
    except OSError as e:
        print(f"[Warning] Could not read '{PRODUCTS_FILE}': {e}. Starting with no products.")

    return products


def load_transactions() -> list:
    """
    Load all saved transactions from the transactions CSV file.

    WHY load transactions?
    ----------------------
    We need to restore the Transaction._counter so that new transaction IDs
    continue from where the last session left off (e.g., TXN00006 after TXN00005).
    Without this, every restart would reset IDs to TXN00001, causing duplicates.

    Returns
    -------
    list of dict
        Each dict has keys matching TRANSACTION_FIELDS.
        Returns an empty list if the file doesn't exist.
    """
    _ensure_data_directory()

    if not os.path.exists(TRANSACTIONS_FILE):
        print(f"[Info] '{TRANSACTIONS_FILE}' not found. Starting with no transaction history.")
        return []

    transactions = []
    try:
        with open(TRANSACTIONS_FILE, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_number, row in enumerate(reader, start=2):
                try:
                    _check_row_fields(row, TRANSACTION_FIELDS, TRANSACTIONS_FILE, row_number)
                    transactions.append(dict(row))
                except DataLoadError as e:
                    print(f"[Warning] Skipping malformed row {row_number} in transactions file: {e}")
    except OSError as e:
        print(f"[Warning] Could not read '{TRANSACTIONS_FILE}': {e}.")

    return transactions


# ════════════════════════════════════════════════════════════════
# SAVING FUNCTIONS (Writing to disk)
# ════════════════════════════════════════════════════════════════

def save_products(products: list):
    """
    Overwrite the products CSV with the current list of Product objects.

    Parameters
    ----------
    products : list of Product
        All Product objects from the store manager.
    """
    _ensure_data_directory()
    _write_csv(
        filepath   = PRODUCTS_FILE,
        fieldnames = PRODUCT_FIELDS,
        rows       = [product.to_dict() for product in products],
    )


def save_transactions(transactions: list):
    """
    Overwrite the transactions CSV with all current Transaction objects.

    Parameters
    ----------
    transactions : list of Transaction
        All Transaction objects from the inventory.
    """
    _ensure_data_directory()
    _write_csv(
        filepath   = TRANSACTIONS_FILE,
        fieldnames = TRANSACTION_FIELDS,
        rows       = [txn.to_dict() for txn in transactions],
    )


def export_daily_report(inventory) -> str:
    """
    Write a human-readable daily report to a .txt file and return its content.

    This gives the store owner a snapshot they can print or share.

    Parameters
    ----------
    inventory : Inventory
        The Inventory object containing products and transactions.

    Returns
    -------
    str
        The full report content (also saved to REPORT_FILE).
    """
    _ensure_data_directory()

    from data_processing import get_total_revenue, get_most_sold_products

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []

    # ── Header ──
    lines.append("=" * 60)
    lines.append("       RETAILTRACK — DAILY INVENTORY REPORT")
    lines.append(f"       Generated: {now}")
    lines.append("=" * 60)
    lines.append("")

    # ── Summary numbers ──
    total_revenue = get_total_revenue(inventory)
    low_stock     = inventory.get_low_stock_products()

    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"  Total Products    : {len(inventory.products)}")
    lines.append(f"  Total Transactions: {len(inventory.transactions)}")
    lines.append(f"  Total Revenue     : {round(total_revenue, 2)} TND")
    lines.append(f"  Low Stock Items   : {len(low_stock)}")
    lines.append("")

    # ── Top sellers ──
    lines.append("TOP SELLING PRODUCTS")
    lines.append("-" * 40)
    top = get_most_sold_products(inventory, n=5)
    if not top:
        lines.append("  No sales recorded yet.")
    else:
        for rank, (sku, units) in enumerate(top, start=1):
            name = inventory.products[sku].name if sku in inventory.products else sku
            lines.append(f"  {rank}. {name} ({sku}) — {units} units sold")
    lines.append("")

    # ── Low stock alerts ──
    lines.append("LOW STOCK ALERTS")
    lines.append("-" * 40)
    if not low_stock:
        lines.append("  All products are adequately stocked.")
    else:
        for product in low_stock:
            lines.append(
                f"  ⚠  {product.name} ({product.sku}) | "
                f"Qty: {product.quantity} | Reorder Level: {product.reorder_level}"
            )
    lines.append("")

    # ── Full inventory ──
    lines.append("FULL INVENTORY")
    lines.append("-" * 40)
    for product in inventory.get_all_products():
        lines.append(
            f"  {product.sku:<12} {product.name:<25} "
            f"Qty: {product.quantity:<6} Price: {product.price} TND"
        )
    lines.append("")
    lines.append("=" * 60)
    lines.append("End of Report")

    report_content = "\n".join(lines)

    # ── Write to file ──
    try:
        with open(REPORT_FILE, mode="w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"[Success] Daily report saved to '{REPORT_FILE}'.")
    except OSError as e:
        print(f"[Error] Could not write report: {e}")

    return report_content


# ════════════════════════════════════════════════════════════════
# PRIVATE HELPERS (not meant to be called from outside this module)
# ════════════════════════════════════════════════════════════════

def _write_csv(filepath: str, fieldnames: list, rows: list):
    """
    Generic helper: write a list of dicts to a CSV file.

    Parameters
    ----------
    filepath : str
        Path to write the file.
    fieldnames : list of str
        Column headers.
    rows : list of dict
        Data rows to write.
    """
    try:
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    except OSError as e:
        # Log but don't crash — data is still in memory even if save fails
        print(f"[Error] Could not save to '{filepath}': {e}")


def _check_row_fields(row: dict, required_fields: list, filename: str, row_num: int):
    """
    Verify that a CSV row contains all required fields (non-empty).

    Parameters
    ----------
    row : dict
        The row from csv.DictReader.
    required_fields : list
        Expected column names.
    filename : str
        Used in the error message.
    row_num : int
        Used in the error message.

    Raises
    ------
    DataLoadError
        If any required field is missing or empty.
    """
    for field in required_fields:
        if field not in row or not str(row[field]).strip():
            raise DataLoadError(
                filename=filename,
                detail=f"Row {row_num} is missing or has empty field '{field}'.",
            )
