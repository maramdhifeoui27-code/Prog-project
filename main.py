"""
main.py
=======
The Command-Line Interface (CLI) entry point for RetailTrack.

IMPORTANT DESIGN RULE — Zero Business Logic Here
-------------------------------------------------
This file is ONLY responsible for:
  1. Displaying menus to the user.
  2. Collecting user input via input().
  3. Calling the appropriate StoreManager method.
  4. Displaying results or error messages.

ALL business logic (stock checks, margin calculations, transaction creation)
lives inside the StoreManager and the domain classes. This keeps main.py
clean, short, and easy to read.

If you find yourself writing an if/else that isn't about menu navigation,
that logic belongs in store_manager.py or the classes — not here.
"""

import sys

from store_manager import StoreManager
from reporting import (
    generate_inventory_report,
    generate_low_stock_report,
    generate_transaction_report,
    generate_performance_report,
    generate_product_detail,
    generate_sale_receipt,
)
from exceptions import RetailTrackError
from validation import (
    validate_sku,
    validate_price,
    validate_quantity,
    validate_positive_quantity,
    validate_non_empty_string,
    validate_date_string,
)
from data_processing import filter_transactions_by_sku, filter_transactions_by_date


# ════════════════════════════════════════════════════════════════
# HELPER UTILITIES (pure I/O helpers — no business logic)
# ════════════════════════════════════════════════════════════════

def print_header(title: str):
    """Print a formatted section header."""
    print("\n" + "─" * 55)
    print(f"  {title}")
    print("─" * 55)


def prompt(label: str) -> str:
    """
    Prompt the user for input and return the stripped result.

    WHY strip()?
    ------------
    Users often accidentally add spaces around their input.
    .strip() removes that whitespace so "ELEC001 " and "ELEC001" are the same.
    """
    return input(f"  {label}: ").strip()


def confirm(message: str) -> bool:
    """Ask the user a yes/no question. Returns True if they answer 'y'."""
    answer = input(f"  {message} (y/n): ").strip().lower()
    return answer == "y"


# ════════════════════════════════════════════════════════════════
# PRODUCT MENU HANDLERS
# ════════════════════════════════════════════════════════════════

def menu_add_product(manager: StoreManager):
    """Handle the 'Add Product' workflow."""
    print_header("ADD NEW PRODUCT")
    try:
        sku           = validate_sku(prompt("SKU (e.g. ELEC001)"))
        name          = validate_non_empty_string(prompt("Product name"), "Name")
        price         = validate_price(prompt("Selling price (TND)"), "Selling Price")
        cost          = validate_price(prompt("Cost price (TND)"), "Cost Price")
        quantity      = validate_quantity(prompt("Initial quantity"), "Quantity")
        reorder_level = validate_quantity(prompt("Reorder level"), "Reorder Level")

        product = manager.add_product(sku, name, price, cost, quantity, reorder_level)
        print(f"\n  ✅ Product added successfully!")
        print(generate_product_detail(product))

    except RetailTrackError as e:
        print(f"\n  ❌ {e}")
    except ValueError as e:
        print(f"\n  ❌ Invalid input: {e}")


def menu_update_product(manager: StoreManager):
    """Handle the 'Update Product' workflow."""
    print_header("UPDATE PRODUCT")
    try:
        sku     = validate_sku(prompt("SKU of product to update"))
        product = manager.get_product(sku)
        print(generate_product_detail(product))

        print("  What would you like to update?")
        print("  [1] Selling price")
        print("  [2] Cost price")
        print("  [3] Reorder level")
        print("  [4] Restock (add quantity)")

        choice = prompt("Choice")

        if choice == "1":
            new_price = validate_price(prompt("New selling price"), "Selling Price")
            manager.update_price(sku, new_price)
            print(f"\n  ✅ Selling price updated to {new_price:.2f} TND.")

        elif choice == "2":
            new_cost = validate_price(prompt("New cost price"), "Cost Price")
            manager.update_cost(sku, new_cost)
            print(f"\n  ✅ Cost price updated to {new_cost:.2f} TND.")

        elif choice == "3":
            new_level = validate_quantity(prompt("New reorder level"), "Reorder Level")
            manager.update_reorder_level(sku, new_level)
            print(f"\n  ✅ Reorder level updated to {new_level}.")

        elif choice == "4":
            amount = validate_positive_quantity(prompt("Units to add"), "Restock Amount")
            product = manager.restock_product(sku, amount)
            print(f"\n  ✅ Restocked {amount} units. New stock: {product.quantity}.")

        else:
            print("\n  ⚠️  Invalid choice. No changes made.")

    except RetailTrackError as e:
        print(f"\n  ❌ {e}")
    except ValueError as e:
        print(f"\n  ❌ Invalid input: {e}")


def menu_remove_product(manager: StoreManager):
    """Handle the 'Remove Product' workflow."""
    print_header("REMOVE PRODUCT")
    try:
        sku     = validate_sku(prompt("SKU of product to remove"))
        product = manager.get_product(sku)
        print(f"\n  Product to remove: {product}")

        if confirm("Are you sure you want to remove this product?"):
            manager.remove_product(sku)
            print(f"\n  ✅ Product '{sku}' has been removed from the inventory.")
        else:
            print("\n  Removal cancelled.")

    except RetailTrackError as e:
        print(f"\n  ❌ {e}")
    except ValueError as e:
        print(f"\n  ❌ Invalid input: {e}")


def menu_view_product(manager: StoreManager):
    """Display detailed info for a single product."""
    print_header("VIEW PRODUCT DETAIL")
    try:
        sku     = validate_sku(prompt("SKU"))
        product = manager.get_product(sku)
        print(generate_product_detail(product))
    except RetailTrackError as e:
        print(f"\n  ❌ {e}")
    except ValueError as e:
        print(f"\n  ❌ Invalid input: {e}")


# ════════════════════════════════════════════════════════════════
# SALES MENU HANDLERS
# ════════════════════════════════════════════════════════════════

def menu_process_sale(manager: StoreManager):
    """Handle the 'Process Sale' workflow."""
    print_header("PROCESS SALE")
    try:
        sku     = validate_sku(prompt("Product SKU"))
        product = manager.get_product(sku)
        print(f"\n  Product: {product.name} | Price: {product.price:.2f} TND | In stock: {product.quantity}")

        quantity = validate_positive_quantity(prompt("Quantity to sell"), "Quantity")
        txn      = manager.process_sale(sku, quantity)

        print(f"\n  ✅ Sale processed successfully!")
        print(generate_sale_receipt(txn, product.name))

        # Immediate low-stock warning after the sale
        if product.is_low_stock():
            print(f"\n  ⚠️  WARNING: '{product.name}' is now low on stock! "
                  f"(Qty: {product.quantity}, Reorder Level: {product.reorder_level})")

    except RetailTrackError as e:
        print(f"\n  ❌ {e}")
    except ValueError as e:
        print(f"\n  ❌ Invalid input: {e}")


# ════════════════════════════════════════════════════════════════
# TRANSACTION HISTORY HANDLERS
# ════════════════════════════════════════════════════════════════

def menu_view_transactions(manager: StoreManager):
    """Handle the 'View Transactions' workflow with optional filtering."""
    print_header("TRANSACTION HISTORY")
    print("  Filter options:")
    print("  [1] All transactions")
    print("  [2] Filter by product SKU")
    print("  [3] Filter by date range")

    choice = prompt("Choice")

    if choice == "1":
        txns = manager.get_all_transactions()
        print(generate_transaction_report(txns))

    elif choice == "2":
        try:
            sku  = validate_sku(prompt("Product SKU"))
            txns = filter_transactions_by_sku(manager.inventory, sku)
            print(generate_transaction_report(txns, f"TRANSACTIONS FOR {sku}"))
        except (RetailTrackError, ValueError) as e:
            print(f"\n  ❌ {e}")

    elif choice == "3":
        try:
            start = validate_date_string(prompt("Start date (YYYY-MM-DD)"))
            end   = validate_date_string(prompt("End date   (YYYY-MM-DD)"))
            txns  = filter_transactions_by_date(manager.inventory, start, end)
            print(generate_transaction_report(txns, f"TRANSACTIONS FROM {start} TO {end}"))
        except ValueError as e:
            print(f"\n  ❌ {e}")

    else:
        print("\n  ⚠️  Invalid option.")


# ════════════════════════════════════════════════════════════════
# REPORTING MENU HANDLERS
# ════════════════════════════════════════════════════════════════

def menu_inventory_report(manager: StoreManager):
    """Display the full inventory report."""
    print(generate_inventory_report(manager.inventory))


def menu_low_stock_report(manager: StoreManager):
    """Display the low-stock alerts report."""
    print(generate_low_stock_report(manager.inventory))


def menu_performance_report(manager: StoreManager):
    """Display the full performance report."""
    print(generate_performance_report(manager.inventory))


def menu_export_report(manager: StoreManager):
    """Export the daily report to a text file."""
    print_header("EXPORT DAILY REPORT")
    manager.export_report()


# ════════════════════════════════════════════════════════════════
# MAIN MENU DISPLAY
# ════════════════════════════════════════════════════════════════

def display_main_menu():
    """Print the main menu options to the terminal."""
    print("""
╔══════════════════════════════════════════════════════╗
║         RETAILTRACK — INVENTORY & SALES MANAGER      ║
╠══════════════════════════════════════════════════════╣
║  PRODUCTS                                            ║
║   1.  Add a new product                              ║
║   2.  Update a product                               ║
║   3.  Remove a product                               ║
║   4.  View product detail                            ║
║   5.  View full inventory                            ║
╠══════════════════════════════════════════════════════╣
║  SALES                                               ║
║   6.  Process a sale                                 ║
║   7.  View transaction history                       ║
╠══════════════════════════════════════════════════════╣
║  REPORTS                                             ║
║   8.  Low-stock alerts                               ║
║   9.  Performance report                             ║
║   10. Export daily report to file                    ║
╠══════════════════════════════════════════════════════╣
║   0.  Exit                                           ║
╚══════════════════════════════════════════════════════╝""")


# ════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ════════════════════════════════════════════════════════════════

def main():
    """
    The main function — entry point of the CLI application.

    Creates a StoreManager (which loads all saved data) and runs
    the menu loop until the user chooses to exit.

    WHY while True?
    ---------------
    We want the menu to keep reappearing after each action until the user
    explicitly chooses to quit. `while True` with a `break` on exit is
    the standard pattern for interactive CLI loops.
    """
    print("\n" + "═" * 55)
    print("   Welcome to RetailTrack — Inventory & Sales Manager")
    print("═" * 55)
    print("  Loading saved data, please wait...")

    # Create the manager — this triggers data loading from CSV files
    manager = StoreManager()

    print("  ✅ System ready!\n")

    # Menu dispatch table: maps choice strings to handler functions.
    # WHY a dictionary instead of a giant if/elif chain?
    # A dict is cleaner, easier to extend, and avoids deeply nested conditionals.
    menu_actions = {
        "1":  menu_add_product,
        "2":  menu_update_product,
        "3":  menu_remove_product,
        "4":  menu_view_product,
        "5":  menu_inventory_report,
        "6":  menu_process_sale,
        "7":  menu_view_transactions,
        "8":  menu_low_stock_report,
        "9":  menu_performance_report,
        "10": menu_export_report,
    }

    # ── Main menu loop ──
    while True:
        display_main_menu()

        try:
            choice = input("\n  Enter your choice: ").strip()
        except (KeyboardInterrupt, EOFError):
            # Handle Ctrl+C gracefully
            print("\n\n  Goodbye! Thank you for using RetailTrack. 🛒")
            sys.exit(0)

        if choice == "0":
            print("\n  Goodbye! Thank you for using RetailTrack. 🛒\n")
            break

        elif choice in menu_actions:
            # Look up and call the matching handler function
            # We pass `manager` as an argument — the handler does the work
            menu_actions[choice](manager)
            input("\n  Press Enter to return to the main menu...")

        else:
            print(f"\n  ⚠️  '{choice}' is not a valid option. Please choose 0–10.")


# ── Standard Python guard: only run main() if this file is executed directly ──
if __name__ == "__main__":
    main()
