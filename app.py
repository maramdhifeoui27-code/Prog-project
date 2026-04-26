"""
app.py
======
The Streamlit Graphical User Interface (GUI) for RetailTrack.

HOW TO RUN:
    streamlit run app.py

WHY a separate GUI file?
--------------------------
The GUI is completely separate from the CLI (main.py). Both import the same
StoreManager backend, but they present it differently. This means:
  - The backend logic never changes based on how the user accesses it.
  - We can add a web interface without touching any business logic.
  - If Streamlit is not installed, the CLI still works fine.

HOW Streamlit works (beginner note):
--------------------------------------
Streamlit re-runs the entire script from top to bottom every time a user
interacts with any widget. To preserve state between re-runs, we use
`st.session_state`, which is a dictionary that persists across runs.
"""

import streamlit as st
import pandas as pd

# Import our backend
from store_manager import StoreManager
from reporting import generate_sale_receipt, generate_performance_report
from exceptions import RetailTrackError
from validation import validate_sku, validate_price, validate_quantity, validate_positive_quantity, validate_non_empty_string
from data_processing import get_profit_margin, get_most_sold_products, filter_transactions_by_sku
from exceptions import ZeroPriceError

# ── Streamlit page configuration (must be the FIRST Streamlit command) ──
st.set_page_config(
    page_title         = "RetailTrack",
    page_icon          = "🛒",
    layout             = "wide",
    initial_sidebar_state = "expanded",
)

# ════════════════════════════════════════════════════════════════
# SESSION STATE: Initialise the StoreManager once per session
# ════════════════════════════════════════════════════════════════

# WHY session_state?
# ------------------
# Streamlit re-runs the script on every user interaction.
# Without session_state, we'd create a new StoreManager every time,
# losing all in-memory changes. session_state persists for the browser tab.

if "manager" not in st.session_state:
    st.session_state.manager = StoreManager()

# Shortcut reference — makes the code below less verbose
manager: StoreManager = st.session_state.manager


# ════════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ════════════════════════════════════════════════════════════════

with st.sidebar:
    st.title("🛒 RetailTrack")
    st.caption("Inventory & Sales Management System")
    st.divider()

    page = st.radio(
        "Navigate to:",
        options=[
            "📊 Dashboard",
            "📦 Product Management",
            "💰 Process Sale",
            "📋 Transaction History",
            "📈 Reports",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption("RetailTrack v1.0 — Built with Streamlit")


# ════════════════════════════════════════════════════════════════
# PAGE 1: DASHBOARD
# ════════════════════════════════════════════════════════════════

if page == "📊 Dashboard":
    st.title("📊 Dashboard")
    st.caption("Live overview of current store status")

    products     = manager.get_all_products()
    transactions = manager.get_all_transactions()
    low_stock    = manager.get_low_stock_products()

    # ── KPI Cards ──
    col1, col2, col3, col4 = st.columns(4)
    total_revenue = sum(t.calculate_total() for t in transactions)

    with col1:
        st.metric("📦 Total Products", len(products))
    with col2:
        st.metric("💰 Total Revenue", f"{total_revenue:,.2f} TND")
    with col3:
        st.metric("🧾 Transactions", len(transactions))
    with col4:
        st.metric("⚠️ Low Stock Items", len(low_stock))

    st.divider()

    # ── Top 5 Bar Chart ──
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("🏆 Top 5 Selling Products")
        top = get_most_sold_products(manager.inventory, n=5)
        if not top:
            st.info("No sales recorded yet. Process a sale to see the chart.")
        else:
            labels = []
            values = []
            for sku, units in top:
                name = manager.inventory.products[sku].name if sku in manager.inventory.products else sku
                labels.append(name)
                values.append(units)
            chart_df = pd.DataFrame({"Product": labels, "Units Sold": values}).set_index("Product")
            st.bar_chart(chart_df)

    with col_right:
        st.subheader("📊 Profit Margins")
        if not products:
            st.info("No products yet.")
        else:
            margin_data = []
            for product in products:
                try:
                    margin = round(get_profit_margin(product), 1)
                except ZeroPriceError:
                    margin = 0.0
                margin_data.append({"Product": product.name, "Margin (%)": margin})
            margin_df = pd.DataFrame(margin_data).set_index("Product")
            st.bar_chart(margin_df)

    st.divider()

    # ── Inventory Table with red-highlighted low stock ──
    st.subheader("📦 Inventory Overview")
    if not products:
        st.info("No products in the inventory yet. Add products using the Product Management page.")
    else:
        rows = []
        for product in products:
            try:
                margin = f"{get_profit_margin(product):.1f}%"
            except ZeroPriceError:
                margin = "N/A"

            rows.append({
                "SKU":           product.sku,
                "Name":          product.name,
                "Price (TND)":   product.price,
                "Cost (TND)":    product.cost,
                "Qty":           product.quantity,
                "Reorder Level": product.reorder_level,
                "Margin":        margin,
                "Status":        "⚠️ LOW STOCK" if product.is_low_stock() else "✅ OK",
            })

        df = pd.DataFrame(rows)

        # Highlight low-stock rows in red
        def highlight_low_stock(row):
            if row["Status"] == "⚠️ LOW STOCK":
                return ["background-color: #ffcccc"] * len(row)
            return [""] * len(row)

        styled_df = df.style.apply(highlight_low_stock, axis=1)
        st.dataframe(styled_df, use_container_width=True)


# ════════════════════════════════════════════════════════════════
# PAGE 2: PRODUCT MANAGEMENT
# ════════════════════════════════════════════════════════════════

elif page == "📦 Product Management":
    st.title("📦 Product Management")

    tab1, tab2, tab3 = st.tabs(["➕ Add Product", "✏️ Update / Restock", "🗑️ Remove Product"])

    # ── Tab 1: Add Product ──
    with tab1:
        st.subheader("Add a New Product")
        with st.form("add_product_form"):
            col1, col2 = st.columns(2)
            with col1:
                sku_input    = st.text_input("SKU", placeholder="e.g. ELEC001")
                name_input   = st.text_input("Product Name", placeholder="e.g. Wireless Headphones")
                price_input  = st.number_input("Selling Price (TND)", min_value=0.0, value=0.0, step=0.5)
            with col2:
                cost_input   = st.number_input("Cost Price (TND)", min_value=0.0, value=0.0, step=0.5)
                qty_input    = st.number_input("Initial Quantity", min_value=0, value=0, step=1)
                reorder_input = st.number_input("Reorder Level", min_value=0, value=5, step=1)

            submitted = st.form_submit_button("➕ Add Product", use_container_width=True)

        if submitted:
            try:
                sku  = validate_sku(sku_input)
                name = validate_non_empty_string(name_input, "Name")
                product = manager.add_product(
                    sku, name, price_input, cost_input, int(qty_input), int(reorder_input)
                )
                st.success(f"✅ Product '{product.name}' (SKU: {product.sku}) added successfully!")
                st.rerun()
            except (RetailTrackError, ValueError) as e:
                st.error(str(e))

    # ── Tab 2: Update / Restock ──
    with tab2:
        st.subheader("Update or Restock a Product")
        products = manager.get_all_products()
        if not products:
            st.info("No products available. Add a product first.")
        else:
            sku_options = {f"{p.sku} — {p.name}": p.sku for p in products}
            selected_label = st.selectbox("Select a product", list(sku_options.keys()))
            selected_sku   = sku_options[selected_label]
            product        = manager.get_product(selected_sku)

            st.write(
                f"**Current Info:** Price: {product.price:.2f} TND | "
                f"Cost: {product.cost:.2f} TND | Stock: {product.quantity} | "
                f"Reorder Level: {product.reorder_level}"
            )

            action = st.radio(
                "What would you like to update?",
                ["Selling Price", "Cost Price", "Reorder Level", "Restock (add quantity)"],
            )

            new_value = st.text_input("New Value")

            if st.button("✅ Apply Update", use_container_width=True):
                try:
                    if action == "Selling Price":
                        manager.update_price(selected_sku, validate_price(new_value, "Selling Price"))
                        st.success(f"Selling price updated to {new_value} TND.")
                    elif action == "Cost Price":
                        manager.update_cost(selected_sku, validate_price(new_value, "Cost Price"))
                        st.success(f"Cost price updated to {new_value} TND.")
                    elif action == "Reorder Level":
                        manager.update_reorder_level(selected_sku, validate_quantity(new_value, "Reorder Level"))
                        st.success(f"Reorder level updated to {new_value}.")
                    elif action == "Restock (add quantity)":
                        amount = validate_positive_quantity(new_value, "Restock Amount")
                        product = manager.restock_product(selected_sku, amount)
                        st.success(f"Added {amount} units. New stock: {product.quantity}.")
                    st.rerun()
                except (RetailTrackError, ValueError) as e:
                    st.error(str(e))

    # ── Tab 3: Remove Product ──
    with tab3:
        st.subheader("Remove a Product")
        products = manager.get_all_products()
        if not products:
            st.info("No products available.")
        else:
            sku_options    = {f"{p.sku} — {p.name}": p.sku for p in products}
            selected_label = st.selectbox("Select a product to remove", list(sku_options.keys()))
            selected_sku   = sku_options[selected_label]

            st.warning(f"⚠️ You are about to permanently remove: **{selected_label}**")

            if st.button("🗑️ Confirm Remove", use_container_width=True):
                try:
                    manager.remove_product(selected_sku)
                    st.success(f"Product '{selected_sku}' removed.")
                    st.rerun()
                except RetailTrackError as e:
                    st.error(str(e))


# ════════════════════════════════════════════════════════════════
# PAGE 3: PROCESS SALE
# ════════════════════════════════════════════════════════════════

elif page == "💰 Process Sale":
    st.title("💰 Process a Sale")

    products = manager.get_all_products()

    if not products:
        st.warning("No products in the inventory. Add products first.")
    else:
        sku_options    = {f"{p.sku} — {p.name} (Stock: {p.quantity})": p.sku for p in products}
        selected_label = st.selectbox("Select a product", list(sku_options.keys()))
        selected_sku   = sku_options[selected_label]
        product        = manager.get_product(selected_sku)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Price", f"{product.price:.2f} TND")
        with col2:
            st.metric("In Stock", f"{product.quantity} units")
        with col3:
            st.metric("Reorder Level", product.reorder_level)

        if product.is_low_stock():
            st.warning(f"⚠️ This product is already at or below its reorder level!")

        qty_to_sell = st.number_input("Quantity to Sell", min_value=1, max_value=max(product.quantity, 1), step=1)

        if st.button("💰 Process Sale", use_container_width=True):
            try:
                txn = manager.process_sale(selected_sku, int(qty_to_sell))
                st.success(
                    f"✅ Sale complete! Transaction ID: **{txn.transaction_id}** | "
                    f"Total: **{txn.calculate_total():.2f} TND**"
                )
                # Show receipt in a code block
                st.code(generate_sale_receipt(txn, product.name))

                # Refresh to show updated stock
                updated_product = manager.get_product(selected_sku)
                if updated_product.is_low_stock():
                    st.warning(
                        f"⚠️ '{updated_product.name}' is now low on stock! "
                        f"(Qty: {updated_product.quantity})"
                    )
                st.rerun()
            except RetailTrackError as e:
                st.error(str(e))


# ════════════════════════════════════════════════════════════════
# PAGE 4: TRANSACTION HISTORY
# ════════════════════════════════════════════════════════════════

elif page == "📋 Transaction History":
    st.title("📋 Transaction History")

    transactions = manager.get_all_transactions()

    if not transactions:
        st.info("No transactions recorded yet. Process a sale to see history.")
    else:
        # Filter options
        filter_option = st.radio("Filter by:", ["All", "By SKU"], horizontal=True)

        if filter_option == "By SKU":
            sku_filter = st.text_input("Enter SKU to filter (e.g. ELEC001)")
            if sku_filter:
                try:
                    sku_filter = validate_sku(sku_filter)
                    transactions = filter_transactions_by_sku(manager.inventory, sku_filter)
                    st.caption(f"Showing transactions for SKU: {sku_filter}")
                except (RetailTrackError, ValueError) as e:
                    st.error(str(e))
                    transactions = []

        if transactions:
            rows = []
            for t in transactions:
                rows.append({
                    "Transaction ID": t.transaction_id,
                    "SKU":            t.product_sku,
                    "Qty Sold":       t.quantity_sold,
                    "Unit Price":     t.unit_price,
                    "Total (TND)":    round(t.calculate_total(), 2),
                    "Date":           t.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                })

            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True)

            total = sum(t.calculate_total() for t in transactions)
            st.metric("Total Revenue (shown)", f"{total:,.2f} TND")
        else:
            st.info("No transactions match the filter.")


# ════════════════════════════════════════════════════════════════
# PAGE 5: REPORTS
# ════════════════════════════════════════════════════════════════

elif page == "📈 Reports":
    st.title("📈 Reports & Analytics")

    products     = manager.get_all_products()
    transactions = manager.get_all_transactions()

    col1, col2 = st.columns(2)

    with col1:
        total_revenue = sum(t.calculate_total() for t in transactions)
        st.metric("💰 Total Revenue", f"{total_revenue:,.2f} TND")
        st.metric("🧾 Total Transactions", len(transactions))
        st.metric("📦 Total Products", len(products))
        st.metric("⚠️ Low Stock Items", len(manager.get_low_stock_products()))

    with col2:
        st.subheader("Revenue by Product")
        from data_processing import get_revenue_by_product
        revenue_map = get_revenue_by_product(manager.inventory)
        if revenue_map:
            rev_data = []
            for sku, rev in revenue_map.items():
                name = manager.inventory.products[sku].name if sku in manager.inventory.products else sku
                rev_data.append({"Product": name, "Revenue (TND)": round(rev, 2)})
            rev_df = pd.DataFrame(rev_data).set_index("Product")
            st.bar_chart(rev_df)
        else:
            st.info("No sales data yet.")

    st.divider()

    # ── Export Button ──
    st.subheader("📄 Export Daily Report")
    if st.button("📥 Generate & Save Report (data/daily_report.txt)", use_container_width=True):
        manager.export_report()
        st.success("✅ Report saved to `data/daily_report.txt`!")

    # ── Full performance report text ──
    st.divider()
    st.subheader("Full Performance Report")
    if st.button("📊 Generate Performance Report"):
        report_text = generate_performance_report(manager.inventory)
        st.code(report_text)
