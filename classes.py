"""
classes.py
==========
This module defines the three core domain classes for RetailTrack:

    - Product     → Represents a store product with stock and pricing info.
    - Transaction → Represents a single completed sales transaction.
    - Inventory   → Manages the collection of products and transaction history.

WHY are all three classes in one file?
---------------------------------------
They are tightly related domain objects. Product is used by Transaction, and
Inventory holds both. Keeping them here prevents circular import issues and
keeps domain logic in one readable place.

All business logic lives inside the class methods — NOT in main.py.
This is the core principle of Object-Oriented Programming: data and the
functions that operate on that data belong together.
"""

from datetime import datetime

# Import our custom exceptions so classes can raise meaningful domain errors
from exceptions import (
    DuplicateSKUError,
    ProductNotFoundError,
    InsufficientStockError,
    ZeroPriceError,
)


# ════════════════════════════════════════════════════════════════
# CLASS 1: PRODUCT
# ════════════════════════════════════════════════════════════════

class Product:
    """
    Represents a single retail product with stock and pricing information.

    Attributes (public)
    -------------------
    sku           : str   — Stock Keeping Unit, unique identifier (e.g. 'ELEC001').
    name          : str   — Human-readable product name.
    price         : float — Selling price per unit (what the customer pays).
    cost          : float — Cost price per unit (what the store paid).
    quantity      : int   — Current stock level.
    reorder_level : int   — Minimum stock before a low-stock alert is triggered.

    Design Note
    -----------
    We store both `price` and `cost` on the product so that the profit_margin()
    method can operate on self-contained data without external lookups.
    This keeps the class fully encapsulated — it knows everything about itself.
    """

    def __init__(
        self,
        sku: str,
        name: str,
        price: float,
        cost: float,
        quantity: int,
        reorder_level: int,
    ):
        """
        Create a new Product instance.

        Parameters
        ----------
        sku : str
            The product's unique identifier (e.g., 'ELEC001').
        name : str
            The product's display name.
        price : float
            The selling price per unit. Must be >= 0.
        cost : float
            The cost price per unit. Must be >= 0.
        quantity : int
            Starting stock level. Must be >= 0.
        reorder_level : int
            The stock threshold that triggers a low-stock alert.

        Raises
        ------
        ValueError
            If price, cost, or quantity are negative.
        """
        # Validate price and cost (they can be 0, but not negative)
        if float(price) < 0:
            raise ValueError("Selling price cannot be negative.")
        if float(cost) < 0:
            raise ValueError("Cost price cannot be negative.")
        if int(quantity) < 0:
            raise ValueError("Quantity cannot be negative.")

        self.sku           = sku.strip().upper()
        self.name          = name.strip()
        self.price         = float(price)
        self.cost          = float(cost)
        self.quantity      = int(quantity)
        self.reorder_level = int(reorder_level)

    # ── MUTATING METHODS ────────────────────────────────────────

    def apply_sale(self, units: int):
        """
        Deduct *units* from stock when a sale is processed.

        WHY check here instead of in Inventory?
        ----------------------------------------
        The Product owns its own quantity, so it should be responsible for
        validating that a sale is possible. This is the Single Responsibility
        Principle: the object that owns the data enforces the rules on it.

        Parameters
        ----------
        units : int
            Number of units to deduct. Must be a positive integer.

        Raises
        ------
        InsufficientStockError
            If requested units exceed current stock.
        ValueError
            If units is not a positive integer.
        """
        if units <= 0:
            raise ValueError("Units sold must be a positive integer.")

        # Guard clause: check stock before deducting
        if units > self.quantity:
            raise InsufficientStockError(
                sku=self.sku,
                requested=units,
                available=self.quantity,
            )

        self.quantity -= units

    def restock(self, amount: int):
        """
        Add stock to the product (e.g., after a new shipment arrives).

        Parameters
        ----------
        amount : int
            Number of units to add. Must be a positive integer.

        Raises
        ------
        ValueError
            If amount is not a positive integer.
        """
        if amount <= 0:
            raise ValueError("Restock amount must be a positive integer.")
        self.quantity += amount

    # ── QUERY METHODS ───────────────────────────────────────────

    def is_low_stock(self) -> bool:
        """
        Return True when current stock is at or below the reorder level.

        WHY a method instead of a property?
        ------------------------------------
        A method name like is_low_stock() reads as a question, making the
        code in main.py more expressive: `if product.is_low_stock(): ...`
        This is a common Python convention for boolean checks.
        """
        return self.quantity <= self.reorder_level

    def profit_margin(self) -> float:
        """
        Calculate the profit margin as a percentage.

        Formula: ((price - cost) / price) × 100

        Returns
        -------
        float
            The profit margin percentage (e.g., 52.3 means 52.3%).

        Raises
        ------
        ZeroPriceError
            If the selling price is zero (would cause division by zero).
        """
        if self.price == 0:
            raise ZeroPriceError(self.sku)
        return ((self.price - self.cost) / self.price) * 100

    def to_dict(self) -> dict:
        """
        Serialise the product to a plain dictionary.

        WHY to_dict()?
        --------------
        Used when saving product data to a CSV file. The file_handler module
        calls product.to_dict() and writes those key-value pairs as a CSV row.
        It keeps the serialisation logic inside the class (encapsulation).

        Returns
        -------
        dict
            All product attributes as a flat dictionary.
        """
        return {
            "sku":           self.sku,
            "name":          self.name,
            "price":         self.price,
            "cost":          self.cost,
            "quantity":      self.quantity,
            "reorder_level": self.reorder_level,
        }

    def __repr__(self) -> str:
        """Developer-friendly string representation (shown in debugger/REPL)."""
        return (
            f"Product(sku={self.sku!r}, name={self.name!r}, "
            f"price={self.price}, qty={self.quantity})"
        )

    def __str__(self) -> str:
        """User-friendly string representation (shown when you print a Product)."""
        low_flag = " ⚠ LOW STOCK" if self.is_low_stock() else ""
        return (
            f"[{self.sku}] {self.name} | "
            f"Price: {self.price:.2f} TND | "
            f"Stock: {self.quantity}{low_flag}"
        )


# ════════════════════════════════════════════════════════════════
# CLASS 2: TRANSACTION
# ════════════════════════════════════════════════════════════════

class Transaction:
    """
    Records a single completed sales transaction.

    This is an IMMUTABLE record — once created, its data should not change.
    It captures the state of a sale at the exact moment it happened (price
    at time of sale, timestamp, quantity).

    Attributes
    ----------
    transaction_id : str      — Unique ID (auto-generated, e.g. 'TXN00001').
    product_sku    : str      — SKU of the product sold.
    quantity_sold  : int      — Number of units sold.
    unit_price     : float    — Price per unit at the time of sale.
    timestamp      : datetime — Exact date and time the transaction occurred.

    Design Note on unit_price
    --------------------------
    We store the price AT THE TIME OF SALE, not a reference to the product's
    current price. This is important because product prices can change later,
    but historical transaction records should always reflect what was charged.
    """

    # Class-level counter to generate unique IDs
    # WHY class-level? It's shared across ALL Transaction instances, so each
    # new transaction gets the next number in the sequence.
    _counter: int = 0

    def __init__(self, product_sku: str, quantity_sold: int, unit_price: float):
        """
        Create a new Transaction record.

        The transaction ID and timestamp are set automatically — the caller
        does not need to provide them.

        Parameters
        ----------
        product_sku : str
            The SKU of the product that was sold.
        quantity_sold : int
            Number of units sold in this transaction.
        unit_price : float
            The selling price per unit at the time of the sale.
        """
        # Auto-increment the class counter and format as TXN00001, TXN00002, ...
        Transaction._counter += 1
        self.transaction_id = f"TXN{Transaction._counter:05d}"

        self.product_sku  = product_sku.strip().upper()
        self.quantity_sold = int(quantity_sold)
        self.unit_price    = float(unit_price)

        # Capture the exact moment this transaction was created
        self.timestamp = datetime.now()

    def calculate_total(self) -> float:
        """
        Return the total revenue for this transaction.

        WHY a method instead of storing the total?
        -------------------------------------------
        The total is always derivable from quantity_sold × unit_price.
        Storing it separately would risk inconsistency if either value
        were ever updated. Computing on-demand guarantees correctness.

        Returns
        -------
        float
            Total amount: quantity_sold × unit_price.
        """
        return self.quantity_sold * self.unit_price

    def to_dict(self) -> dict:
        """
        Serialise the transaction to a plain dictionary.

        Returns
        -------
        dict
            All transaction attributes as a flat dictionary.
        """
        return {
            "transaction_id": self.transaction_id,
            "product_sku":    self.product_sku,
            "quantity_sold":  self.quantity_sold,
            "unit_price":     self.unit_price,
            "total":          round(self.calculate_total(), 2),
            "timestamp":      self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def __repr__(self) -> str:
        return (
            f"Transaction(id={self.transaction_id}, sku={self.product_sku}, "
            f"qty={self.quantity_sold}, total={self.calculate_total():.2f})"
        )

    def __str__(self) -> str:
        return (
            f"[{self.transaction_id}] {self.product_sku} × {self.quantity_sold} "
            f"@ {self.unit_price:.2f} TND = {self.calculate_total():.2f} TND "
            f"| {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
        )


# ════════════════════════════════════════════════════════════════
# CLASS 3: INVENTORY
# ════════════════════════════════════════════════════════════════

class Inventory:
    """
    Central store manager that holds all products and transaction history.

    Think of Inventory as the store's back-office: it knows about every
    product and every sale, and it coordinates operations that involve
    both (like processing a sale, which touches a product AND creates a
    transaction).

    Attributes
    ----------
    _products    : dict {sku: Product}       — Private. Products keyed by SKU.
    _transactions: list [Transaction]        — Ordered list of all sales.

    WHY a dict for products?
    -------------------------
    Dictionaries give O(1) lookup by SKU. find_product('ELEC001') is instant
    regardless of how many products exist. A list would require looping through
    every product to find a match — much slower as the catalogue grows.

    WHY private attributes (_products, _transactions)?
    ---------------------------------------------------
    We control all access through methods (add_product, find_product, etc.)
    so we can enforce rules. If products were public, external code could
    add items directly without our validation checks.
    """

    def __init__(self):
        """
        Initialise an empty inventory.

        The store manager will populate this with data from CSV files
        immediately after creation.
        """
        self._products     = {}   # {sku: Product}
        self._transactions = []   # [Transaction, ...]

    # ── PRODUCT MANAGEMENT ──────────────────────────────────────

    def add_product(self, product: Product):
        """
        Register a new product in the inventory.

        Parameters
        ----------
        product : Product
            The Product object to add.

        Raises
        ------
        DuplicateSKUError
            If a product with the same SKU already exists.
        """
        if product.sku in self._products:
            raise DuplicateSKUError(product.sku)
        self._products[product.sku] = product

    def find_product(self, sku: str) -> Product:
        """
        Retrieve a Product by its SKU.

        Parameters
        ----------
        sku : str
            The SKU to look up (case-insensitive).

        Returns
        -------
        Product
            The matching Product object.

        Raises
        ------
        ProductNotFoundError
            If no product with that SKU exists.
        """
        sku = sku.strip().upper()
        if sku not in self._products:
            raise ProductNotFoundError(sku)
        return self._products[sku]

    def remove_product(self, sku: str):
        """
        Remove a product from the inventory.

        Parameters
        ----------
        sku : str
            The SKU of the product to remove.

        Raises
        ------
        ProductNotFoundError
            If the SKU does not exist.
        """
        sku = sku.strip().upper()
        if sku not in self._products:
            raise ProductNotFoundError(sku)
        del self._products[sku]

    def get_all_products(self) -> list:
        """Return all products as a sorted list (sorted by SKU)."""
        return sorted(self._products.values(), key=lambda p: p.sku)

    def get_low_stock_products(self) -> list:
        """Return a list of all products that are at or below their reorder level."""
        return [p for p in self._products.values() if p.is_low_stock()]

    # ── SALES ───────────────────────────────────────────────────

    def sell_item(self, sku: str, quantity: int) -> Transaction:
        """
        Process a sale: deduct stock from the product and record a Transaction.

        This is the key cross-entity operation: it touches both a Product
        (to deduct stock) and creates a Transaction (to record the sale).

        WHY does Inventory own this method?
        ------------------------------------
        Because it involves TWO entities (Product + Transaction) and
        coordinating them is Inventory's job — just like a cashier's job is
        to scan items AND issue receipts in one step.

        Parameters
        ----------
        sku : str
            The SKU of the product being sold.
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
        product = self.find_product(sku)         # raises ProductNotFoundError if missing
        product.apply_sale(quantity)              # raises InsufficientStockError if short

        # Create the transaction record with the price AT THIS MOMENT
        txn = Transaction(product.sku, quantity, product.price)
        self._transactions.append(txn)
        return txn

    # ── READ-ONLY ACCESSORS ──────────────────────────────────────

    @property
    def products(self) -> dict:
        """Read-only access to the internal products dictionary."""
        return self._products

    @property
    def transactions(self) -> list:
        """Read-only access to the internal transactions list."""
        return self._transactions

    def generate_report(self) -> dict:
        """
        Build a high-level summary of inventory and sales data.

        Returns
        -------
        dict
            Keys: total_revenue, total_transactions, units_by_sku.
        """
        total_revenue = sum(t.calculate_total() for t in self._transactions)

        units_by_sku: dict = {}
        for t in self._transactions:
            units_by_sku[t.product_sku] = (
                units_by_sku.get(t.product_sku, 0) + t.quantity_sold
            )

        return {
            "total_revenue":      total_revenue,
            "total_transactions": len(self._transactions),
            "units_by_sku":       units_by_sku,
        }
