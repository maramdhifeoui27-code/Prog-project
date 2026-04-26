"""
reporting.py
============
This module generates all textual reports and summaries for RetailTrack.

WHY a separate reporting module?
----------------------------------
Report generation is pure READ-ONLY logic — it never changes any data.
By separating it from the manager (which writes data) and from main.py
(which handles user interaction), we keep each file laser-focused on one job.

All functions return formatted strings. They never call print() directly.
The CALLER (main.py or app.py) decides what to do with the returned string
(print it to the terminal, show it in Streamlit, write it to a file, etc.).
This design makes the functions reusable across both interfaces.
"""

from data_processing import (
    build_full_summary,
    get_profit_margin,
    filter_transactions_by_sku,
    filter_transactions_by_date,
)
from exceptions import ZeroPriceError


# ════════════════════════════════════════════════════════════════
# INVENTORY REPORTS
# ════════════════════════════════════════════════════════════════

def generate_inventory_report(inventory) -> str:
    """
    Generate a formatted table showing all products and their current status.

    Parameters
    ----------
    inventory : Inventory
        The inventory containing all products.

    Returns
    -------
    str
        A multiline string report, ready to print or display.
    """
    lines = []
    lines.append("\n" + "=" * 75)
    lines.append("                    INVENTORY REPORT")
    lines.append("=" * 75)

    products = inventory.get_all_products()

    if not products:
        lines.append("  No products in the inventory yet.")
        lines.append("=" * 75)
        return "\n".join(lines)

    # Column header
    lines.append(
        f"  {'SKU':<12} {'Name':<22} {'Price':>8} {'Cost':>8} "
        f"{'Qty':>6} {'Reorder':>8} {'Margin':>8}  Status"
    )
    lines.append("  " + "-" * 71)

    for product in products:
        try:
            margin = f"{get_profit_margin(product):.1f}%"
        except ZeroPriceError:
            margin = "N/A"

        status = "⚠ LOW STOCK" if product.is_low_stock() else "✅ OK"
        lines.append(
            f"  {product.sku:<12} {product.name:<22} {product.price:>8.2f} "
            f"{product.cost:>8.2f} {product.quantity:>6} {product.reorder_level:>8} "
            f"{margin:>8}  {status}"
        )

    lines.append("=" * 75)
    return "\n".join(lines)


def generate_low_stock_report(inventory) -> str:
    """
    Generate a report listing only products that are below their reorder level.

    Parameters
    ----------
    inventory : Inventory

    Returns
    -------
    str
        A formatted low-stock alert report.
    """
    lines = []
    lines.append("\n" + "=" * 55)
    lines.append("           ⚠  LOW STOCK ALERTS")
    lines.append("=" * 55)

    low = inventory.get_low_stock_products()

    if not low:
        lines.append("  ✅  All products are sufficiently stocked.")
    else:
        lines.append(f"  {'SKU':<12} {'Name':<25} {'Qty':>6}  {'Reorder':>8}")
        lines.append("  " + "-" * 51)
        for product in low:
            out_flag = "  (OUT OF STOCK)" if product.quantity == 0 else ""
            lines.append(
                f"  {product.sku:<12} {product.name:<25} "
                f"{product.quantity:>6}  {product.reorder_level:>8}{out_flag}"
            )

    lines.append("=" * 55)
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════
# TRANSACTION REPORTS
# ════════════════════════════════════════════════════════════════

def generate_transaction_report(transactions: list, title: str = "TRANSACTION HISTORY") -> str:
    """
    Generate a formatted transaction history table.

    Parameters
    ----------
    transactions : list of Transaction
        The transactions to display.
    title : str
        The report title (e.g., "TRANSACTION HISTORY" or "FILTERED RESULTS").

    Returns
    -------
    str
        A formatted multiline report string.
    """
    lines = []
    lines.append("\n" + "=" * 75)
    lines.append(f"  {title}")
    lines.append("=" * 75)

    if not transactions:
        lines.append("  No transactions found.")
        lines.append("=" * 75)
        return "\n".join(lines)

    lines.append(
        f"  {'ID':<12} {'SKU':<12} {'Qty':>5} {'Unit Price':>11} "
        f"{'Total':>10}  Date"
    )
    lines.append("  " + "-" * 65)

    for t in transactions:
        lines.append(
            f"  {t.transaction_id:<12} {t.product_sku:<12} {t.quantity_sold:>5} "
            f"{t.unit_price:>11.2f} {t.calculate_total():>10.2f}  "
            f"{t.timestamp.strftime('%Y-%m-%d %H:%M')}"
        )

    total_amount = sum(t.calculate_total() for t in transactions)
    lines.append("  " + "-" * 65)
    lines.append(f"  {'Total Revenue from these transactions':>50}  {total_amount:>10.2f} TND")
    lines.append("=" * 75)
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════
# PERFORMANCE REPORT
# ════════════════════════════════════════════════════════════════

def generate_performance_report(inventory) -> str:
    """
    Generate a comprehensive business performance report.

    Includes: total revenue, transaction count, inventory value,
    top-selling products, and profit margins for all products.

    Parameters
    ----------
    inventory : Inventory

    Returns
    -------
    str
        A formatted multiline performance report.
    """
    summary = build_full_summary(inventory)
    lines   = []

    lines.append("\n" + "=" * 65)
    lines.append("             PERFORMANCE REPORT")
    lines.append("=" * 65)

    # ── Key metrics ──
    lines.append(f"  Total Revenue       : {summary['total_revenue']:>10.2f} TND")
    lines.append(f"  Total Transactions  : {summary['total_transactions']:>10}")
    lines.append(f"  Inventory Value     : {summary['inventory_value']:>10.2f} TND")
    lines.append(f"  Low-Stock Products  : {summary['low_stock_count']:>10}")

    # ── Top sellers ──
    lines.append("")
    lines.append("  TOP SELLING PRODUCTS (by units sold)")
    lines.append("  " + "-" * 50)
    top = summary["top_sellers"]
    if not top:
        lines.append("  No sales recorded yet.")
    else:
        for rank, (sku, units) in enumerate(top, start=1):
            name = inventory.products[sku].name if sku in inventory.products else sku
            lines.append(f"  #{rank}  {sku:<12} {name:<25} {units:>6} units")

    # ── Profit margins ──
    lines.append("")
    lines.append("  PROFIT MARGINS BY PRODUCT")
    lines.append("  " + "-" * 50)
    if not summary["margins"]:
        lines.append("  No products in inventory.")
    else:
        for sku, margin in summary["margins"].items():
            name = inventory.products[sku].name if sku in inventory.products else sku
            # ASCII progress bar: each █ represents 5%
            bar = "█" * int(margin / 5)
            lines.append(f"  {sku:<12} {name:<22} {margin:>6.1f}%  {bar}")

    lines.append("=" * 65)
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════
# SINGLE-PRODUCT DETAIL
# ════════════════════════════════════════════════════════════════

def generate_product_detail(product) -> str:
    """
    Generate a detailed information card for a single product.

    Parameters
    ----------
    product : Product

    Returns
    -------
    str
        A formatted product detail card.
    """
    try:
        margin = f"{get_profit_margin(product):.1f}%"
    except ZeroPriceError:
        margin = "N/A (price is 0)"

    status = "⚠ LOW STOCK" if product.is_low_stock() else "✅ OK"

    lines = []
    lines.append("\n" + "=" * 50)
    lines.append(f"  PRODUCT DETAIL — {product.sku}")
    lines.append("=" * 50)
    lines.append(f"  Name          : {product.name}")
    lines.append(f"  SKU           : {product.sku}")
    lines.append(f"  Selling Price : {product.price:.2f} TND")
    lines.append(f"  Cost Price    : {product.cost:.2f} TND")
    lines.append(f"  Profit Margin : {margin}")
    lines.append(f"  Stock Level   : {product.quantity} units")
    lines.append(f"  Reorder Level : {product.reorder_level} units")
    lines.append(f"  Stock Status  : {status}")
    lines.append("=" * 50)
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════
# BILLING / RECEIPT
# ════════════════════════════════════════════════════════════════

def generate_sale_receipt(transaction, product_name: str = "") -> str:
    """
    Generate a receipt for a completed sale transaction.

    Parameters
    ----------
    transaction : Transaction
        The transaction to generate a receipt for.
    product_name : str
        Optional product name for a more readable receipt.

    Returns
    -------
    str
        A formatted receipt string.
    """
    lines = []
    lines.append("\n" + "=" * 45)
    lines.append("      RETAILTRACK — SALE RECEIPT")
    lines.append("=" * 45)
    lines.append(f"  Transaction ID : {transaction.transaction_id}")
    lines.append(f"  Product SKU    : {transaction.product_sku}")
    if product_name:
        lines.append(f"  Product Name   : {product_name}")
    lines.append(f"  Quantity Sold  : {transaction.quantity_sold} units")
    lines.append(f"  Unit Price     : {transaction.unit_price:.2f} TND")
    lines.append(f"  ─────────────────────────────────────")
    lines.append(f"  TOTAL          : {transaction.calculate_total():.2f} TND")
    lines.append(f"  Date & Time    : {transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 45)
    return "\n".join(lines)
