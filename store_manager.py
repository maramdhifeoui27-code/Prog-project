"""
store_manager.py
================
This module contains the StoreManager class — the single source of truth for
all retail data and cross-entity business logic.

WHAT is a "Manager" class?
----------------------------
A manager class is a pattern that acts as a coordinator for a group of related
objects. Instead of having floating functions scattered across files, ALL
operations that involve multiple classes (e.g., "process a sale that links a
Product to a Transaction") live here.

Think of StoreManager as the store's supervisor: it knows about all products
and all transactions, and it makes sure that operations are valid before
carrying them out.

This class replaces standalone utility functions and keeps main.py clean.
"""

from classes import Inventory, Product, Transaction
from exceptions import (
    RetailTrackError,
    DuplicateSKUError,
    ProductNotFoundError,
    InsufficientStockError,
)
from file_handler import (
    load_products,
    load_transactions,
    save_products,
    save_transactions,
    export_daily_report,
)


class StoreManager:
    """
    Central coordinator for all RetailTrack data and operations.

    Holds a single Inventory instance and exposes clean methods for:
        - Adding / updating / removing products
        - Processing sales
        - Accessing reports

    All data is persisted to CSV files automatically after every operation.

    Attributes
    ----------
    _inventory : Inventory
        The single Inventory object holding all products and transactions.
    """

    def __init__(self):
        """
        Initialise the manager and load any existing data from CSV files.

        WHY load on __init__?
        ----------------------
        When the program starts (either CLI or Streamlit), the manager is
        created once and immediately populated with saved data. Every session
        continues exactly where the last one left off.
        """
        self._inventory = Inventory()
        self._load_all_data()

    # ════════════════════════════════════════════════════════════════
    # DATA LOADING (called once at startup)
    # ════════════════════════════════════════════════════════════════

    def _load_all_data(self):
        """
        Load products and transactions from CSV files and rebuild objects.

        WHY rebuild objects instead of storing raw dicts?
        --------------------------------------------------
        Our system depends on having REAL Product and Transaction objects with
        methods. CSV files only store raw text. This method bridges that gap
        by reading the text and reconstructing proper Python objects.
        """
        # ── Load Products ──
        for row in load_products():
            try:
                product = Product(
                    sku           = row["sku"],
                    name          = row["name"],
                    price         = float(row["price"]),
                    cost          = float(row["cost"]),
                    quantity      = int(row["quantity"]),
                    reorder_level = int(row["reorder_level"]),
                )
                self._inventory.add_product(product)
            except (ValueError, KeyError, RetailTrackError) as e:
                print(f"[Warning] Skipping invalid product data: {e}")

        # ── Load Transactions ──
        # We also need to restore the Transaction._counter so new IDs don't
        # start from TXN00001 and clash with existing saved transactions.
        max_id = 0
        for row in load_transactions():
            try:
                # Restore the counter by finding the highest existing ID number
                txn_id_str = row["transaction_id"]
                id_number  = int(txn_id_str.replace("TXN", ""))
                if id_number > max_id:
                    max_id = id_number
            except (ValueError, KeyError):
                pass

        # Set the class counter so new transactions continue from the last ID
        if max_id > 0:
            Transaction._counter = max_id
            print(f"[Info] Transaction counter restored to {max_id}. "
                  f"Next transaction will be TXN{max_id + 1:05d}.")

    # ════════════════════════════════════════════════════════════════
    # PRODUCT OPERATIONS
    # ════════════════════════════════════════════════════════════════

    def add_product(
        self,
        sku: str,
        name: str,
        price: float,
        cost: float,
        quantity: int,
        reorder_level: int,
    ) -> Product:
        """
        Add a new product to the inventory and save to disk.

        Parameters
        ----------
        sku : str
        name : str
        price : float
        cost : float
        quantity : int
        reorder_level : int

        Returns
        -------
        Product
            The newly created Product object.

        Raises
        ------
        DuplicateSKUError
            If a product with this SKU already exists.
        ValueError
            If any numeric value is invalid.
        """
        product = Product(sku, name, price, cost, quantity, reorder_level)
        self._inventory.add_product(product)

        # Immediately persist to disk after every change
        save_products(list(self._inventory.products.values()))
        return product

    def get_product(self, sku: str) -> Product:
        """
        Retrieve a product by SKU.

        Raises
        ------
        ProductNotFoundError
            If no product with that SKU exists.
        """
        return self._inventory.find_product(sku)

    def get_all_products(self) -> list:
        """Return all products sorted by SKU."""
        return self._inventory.get_all_products()

    def get_low_stock_products(self) -> list:
        """Return all products at or below their reorder level."""
        return self._inventory.get_low_stock_products()

    def update_price(self, sku: str, new_price: float) -> Product:
        """
        Update the selling price of a product and save.

        Raises
        ------
        ProductNotFoundError
        ValueError : If new_price is negative.
        """
        product = self._inventory.find_product(sku)
        if new_price < 0:
            raise ValueError("Selling price cannot be negative.")
        product.price = float(new_price)
        save_products(list(self._inventory.products.values()))
        return product

    def update_cost(self, sku: str, new_cost: float) -> Product:
        """
        Update the cost price of a product and save.

        Raises
        ------
        ProductNotFoundError
        ValueError : If new_cost is negative.
        """
        product = self._inventory.find_product(sku)
        if new_cost < 0:
            raise ValueError("Cost price cannot be negative.")
        product.cost = float(new_cost)
        save_products(list(self._inventory.products.values()))
        return product

    def update_reorder_level(self, sku: str, new_level: int) -> Product:
        """
        Update the reorder level of a product and save.

        Raises
        ------
        ProductNotFoundError
        ValueError : If new_level is negative.
        """
        product = self._inventory.find_product(sku)
        if new_level < 0:
            raise ValueError("Reorder level cannot be negative.")
        product.reorder_level = int(new_level)
        save_products(list(self._inventory.products.values()))
        return product

    def restock_product(self, sku: str, amount: int) -> Product:
        """
        Add units to a product's stock and save.

        Parameters
        ----------
        sku : str
        amount : int
            Number of units to add (must be positive).

        Raises
        ------
        ProductNotFoundError
        ValueError : If amount is not positive.
        """
        product = self._inventory.find_product(sku)
        product.restock(amount)
        save_products(list(self._inventory.products.values()))
        return product

    def remove_product(self, sku: str):
        """
        Remove a product from the inventory and save.

        Raises
        ------
        ProductNotFoundError
            If no product with that SKU exists.
        """
        self._inventory.remove_product(sku)
        save_products(list(self._inventory.products.values()))

    # ════════════════════════════════════════════════════════════════
    # SALES OPERATIONS
    # ════════════════════════════════════════════════════════════════

    def process_sale(self, sku: str, quantity: int) -> Transaction:
        """
        Process a sale: deduct stock and record a Transaction.

        This is the key cross-entity operation. It delegates all the
        complex logic to Inventory.sell_item(), then persists both the
        updated products and the new transaction to disk.

        Parameters
        ----------
        sku : str
            The SKU of the product to sell.
        quantity : int
            Number of units to sell.

        Returns
        -------
        Transaction
            The newly created Transaction object.

        Raises
        ------
        ProductNotFoundError
            If the SKU does not exist.
        InsufficientStockError
            If requested quantity exceeds available stock.
        """
        # Delegate the actual sale to the Inventory — it handles both
        # the stock deduction and the Transaction creation in one step
        txn = self._inventory.sell_item(sku, quantity)

        # Persist both updated products and the new transaction
        save_products(list(self._inventory.products.values()))
        save_transactions(list(self._inventory.transactions))
        return txn

    def get_all_transactions(self) -> list:
        """Return the full list of transactions."""
        return list(self._inventory.transactions)

    # ════════════════════════════════════════════════════════════════
    # REPORTING
    # ════════════════════════════════════════════════════════════════

    def export_report(self) -> str:
        """
        Generate and save the daily report to a text file.

        Returns
        -------
        str
            The report content (also written to data/daily_report.txt).
        """
        return export_daily_report(self._inventory)

    @property
    def inventory(self) -> Inventory:
        """
        Read-only access to the underlying Inventory object.

        WHY expose this?
        -----------------
        The data_processing and reporting modules work directly with the
        Inventory object. The manager exposes it via a property so those
        modules can access it without bypassing the manager's save logic.
        """
        return self._inventory
