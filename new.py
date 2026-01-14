import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import re
from io import BytesIO
import time

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="💧 Lumina Waters Finance",
    layout="wide",
    page_icon="💧",
    initial_sidebar_state="expanded"
)

# ---------------------------
# DARK THEME CSS
# ---------------------------
st.markdown("""
<style>
.stApp { background-color: #0E1117; color: #F1F1F1; }
h1,h2,h3,h4,h5,h6 { color:#F1F1F1; }
.stButton>button { background-color:#1f2a38; color:#F1F1F1; border-radius:8px; border:1px solid #2A3342; }
.stButton>button:hover { background-color:#2A3342; }
.stTextInput>div>div>input, .stNumberInput>div>div>input { background-color:#1f2a38; color:#F1F1F1; border-radius:5px; border:1px solid #2A3342; }
.stDataFrame { background-color:#161B26; color:#F1F1F1; }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# SESSION STATE
# ---------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = "viewer"

# ---------------------------
# LOGIN
# ---------------------------
if not st.session_state.authenticated:
    st.title("🔒 Lumina Waters – Login")
    code = st.text_input("Enter 6-digit passcode", type="password")
    if st.button("Login"):
        if code == st.secrets["APP_PASSCODE"]:
            st.session_state.authenticated = True
            st.session_state.user_role = "admin"
            st.success("✅ Login successful!")
            st.rerun()
        else:
            st.error("❌ Incorrect passcode")
    st.stop()

# ---------------------------
# GOOGLE SHEETS CONNECTION
# ---------------------------
@st.cache_resource
def connect_sheets():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    sh = client.open("LuminaWatersDB")
    return {
        "customers": sh.worksheet("Customers"),
        "orders": sh.worksheet("Orders"),
        "transactions": sh.worksheet("Transactions"),
        "expenses": sh.worksheet("Expenses"),
        "income": sh.worksheet("OtherIncome"),
        "inventory": sh.worksheet("Inventory")
    }

try:
    sheets = connect_sheets()
except Exception as e:
    st.error("❌ Google Sheets connection failed")
    st.code(str(e))
    st.stop()

# ---------------------------
# UTILITY FUNCTIONS
# ---------------------------
@st.cache_data(ttl=60)  # Reduced cache time to 1 minute for fresher data
def load_data(sheet_name):
    try:
        ws = sheets[sheet_name]
        values = ws.get_all_values()
        if len(values) <= 1:
            return pd.DataFrame()
        headers = [str(c).strip() for c in values[0]]
        df = pd.DataFrame(values[1:], columns=headers)
        
        # More robust numeric conversion
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ["amount", "price", "quantity", "qty", "remaining", "paid"]):
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.replace('₹', '').str.strip(), errors='coerce').fillna(0)
        
        time.sleep(0.3)
        return df
    except Exception as e:
        st.error(f"❌ Failed to load {sheet_name}: {str(e)}")
        return pd.DataFrame()

def get_next_id(sheet_name):
    try:
        ids = sheets[sheet_name].col_values(1)[1:]
        nums = [int(x) for x in ids if str(x).strip().isdigit()]
        return max(nums) + 1 if nums else 1
    except:
        return 1

def append_row_safe(sheet_name, values):
    try:
        clean = ["" if pd.isna(v) else str(v) for v in values]
        sheets[sheet_name].append_row(clean)
        time.sleep(0.5)
        load_data.clear()  # Clear cache after adding data
    except Exception as e:
        st.error(f"❌ Failed to add to {sheet_name}: {str(e)}")
        raise

def validate_email(email):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", str(email))) if email else True

def paginate_dataframe(df, page_size=15):
    if df.empty:
        st.info("No data available")
        return pd.DataFrame()
    total_pages = max(1, (len(df) + page_size - 1) // page_size)
    page = st.selectbox("Page", range(1, total_pages + 1), key=f"page_{id(df)}")
    start = (page - 1) * page_size
    return df.iloc[start:start + page_size]

def find_column(df, keywords):
    """Helper function to find column by keywords"""
    if df.empty:
        return None
    for col in df.columns:
        col_lower = col.lower()
        if all(keyword.lower() in col_lower for keyword in keywords.split()):
            return col
    return None

# ---------------------------
# HEADER WITH LOGO
# ---------------------------
col_logo, col_title = st.columns([1, 5])
with col_logo:
    # Option 1: Use a text logo if no image available
    st.markdown("### 💧")
    # Option 2: Uncomment and replace with your actual logo URL
    # st.image("YOUR_LOGO_URL_HERE", width=120)
with col_title:
    st.title("💧 Lumina Waters Finance")

# ---------------------------
# NAVIGATION
# ---------------------------
tabs = st.tabs([
    "📊 Dashboard", "👥 Customers", "📝 Orders", "💳 Transactions",
    "🧾 Expenses", "💰 Other Income", "📦 Inventory", "📈 Reports", "⚙️ Settings"
])

# ---------------------------
# DASHBOARD
# ---------------------------
with tabs[0]:
    st.header("📊 Financial Overview")
    orders = load_data("orders")
    transactions = load_data("transactions")
    expenses = load_data("expenses")
    income = load_data("income")

    # Use dynamic column finding
    total_amount_col = find_column(orders, "total amount") or "Total Amount"
    amount_paid_col = find_column(transactions, "amount paid") or "Amount Paid"
    income_amount_col = find_column(income, "amount") or "Amount"
    expense_amount_col = find_column(expenses, "amount") or "Amount"

    total_sales = orders[total_amount_col].sum() if total_amount_col in orders.columns else 0
    paid = transactions[amount_paid_col].sum() if amount_paid_col in transactions.columns else 0
    extra_income = income[income_amount_col].sum() if income_amount_col in income.columns else 0
    total_expenses = expenses[expense_amount_col].sum() if expense_amount_col in expenses.columns else 0
    net_balance = paid + extra_income - total_expenses

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sales", f"₹ {total_sales:,.0f}")
    col2.metric("Money Received", f"₹ {paid + extra_income:,.0f}")
    col3.metric("Total Expenses", f"₹ {total_expenses:,.0f}")
    col4.metric("Net Balance", f"₹ {net_balance:,.0f}")

    category_col = find_column(expenses, "category")
    if not expenses.empty and category_col and category_col in expenses.columns:
        expense_summary = expenses.groupby(category_col)[expense_amount_col].sum().reset_index()
        if not expense_summary.empty:
            fig = px.pie(expense_summary, names=category_col, values=expense_amount_col, title="Expense Breakdown")
            st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# CUSTOMERS
# ---------------------------
with tabs[1]:
    st.header("👥 Customers")
    customers = load_data("customers")
    
    if not customers.empty:
        search = st.text_input("Search by Name/Contact/Email")
        if search:
            name_col = find_column(customers, "name") or "Name"
            contact_col = find_column(customers, "contact") or "Contact"
            email_col = find_column(customers, "email") or "Email"
            
            mask = pd.Series([False] * len(customers))
            if name_col in customers.columns:
                mask |= customers[name_col].astype(str).str.contains(search, case=False, na=False)
            if contact_col in customers.columns:
                mask |= customers[contact_col].astype(str).str.contains(search, case=False, na=False)
            if email_col in customers.columns:
                mask |= customers[email_col].astype(str).str.contains(search, case=False, na=False)
            customers = customers[mask]

        paginated = paginate_dataframe(customers)
        if not paginated.empty:
            st.dataframe(paginated, use_container_width=True, hide_index=True)
    else:
        st.info("No customers yet. Add your first customer below!")

    if st.session_state.user_role == "admin":
        with st.expander("➕ Add Customer"):
            with st.form("add_customer"):
                name = st.text_input("Name *")
                ctype = st.selectbox("Type", ["Restaurant", "Mall", "Office", "Other"])
                contact = st.text_input("Contact")
                email = st.text_input("Email")
                address = st.text_input("Address")
                vip = st.checkbox("VIP")
                notes = st.text_area("Notes")
                submitted = st.form_submit_button("Save Customer")
                if submitted:
                    if not name:
                        st.error("Name is required")
                    elif email and not validate_email(email):
                        st.error("Invalid email format")
                    else:
                        try:
                            append_row_safe("customers", [get_next_id("customers"), name, ctype, contact, email, address, "Yes" if vip else "", notes])
                            st.success("✅ Customer added successfully!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to add customer: {str(e)}")

# ---------------------------
# ORDERS
# ---------------------------
with tabs[2]:
    st.header("📝 Orders")
    orders = load_data("orders")
    customers = load_data("customers")

    if not orders.empty:
        paginated = paginate_dataframe(orders)
        if not paginated.empty:
            st.dataframe(paginated, use_container_width=True, hide_index=True)
    else:
        st.info("No orders yet. Create your first order below!")

    if st.session_state.user_role == "admin":
        with st.expander("➕ Add Order"):
            with st.form("add_order"):
                if not customers.empty:
                    customer_id_col = find_column(customers, "customer id") or customers.columns[0]
                    name_col = find_column(customers, "name") or customers.columns[1] if len(customers.columns) > 1 else customer_id_col
                    
                    customer_options = [f"{row[customer_id_col]} – {row[name_col]}" for _, row in customers.iterrows()]
                    selected = st.selectbox("Customer *", customer_options)
                    cid = selected.split(" – ")[0] if " – " in selected else selected
                else:
                    cid = st.text_input("Customer ID *")

                order_date = st.date_input("Order Date", datetime.today())
                delivery_date = st.date_input("Delivery Date", datetime.today())
                items = st.text_input("Items *")
                qty = st.number_input("Quantity", min_value=1, step=1, value=1)
                price = st.number_input("Price per Item", min_value=0.0, step=10.0, value=0.0)
                pay_status = st.selectbox("Payment Status", ["Unpaid", "Partial", "Paid"])
                order_status = st.selectbox("Order Status", ["Pending", "Delivered", "Cancelled"])
                notes = st.text_area("Notes")

                submitted = st.form_submit_button("Save Order")
                if submitted:
                    if not items or not cid:
                        st.error("Customer and Items are required")
                    else:
                        try:
                            total = qty * price
                            append_row_safe("orders", [get_next_id("orders"), cid, str(order_date), str(delivery_date), items, qty, price, total, pay_status, order_status, notes])
                            st.success("✅ Order added successfully!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to add order: {str(e)}")

# ---------------------------
# TRANSACTIONS
# ---------------------------
with tabs[3]:
    st.header("💳 Transactions")
    transactions = load_data("transactions")
    orders = load_data("orders")

    if not transactions.empty:
        paginated = paginate_dataframe(transactions)
        if not paginated.empty:
            st.dataframe(paginated, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions yet. Record your first payment below!")

    if st.session_state.user_role == "admin" and not orders.empty:
        with st.expander("➕ Add Transaction"):
            with st.form("add_transaction"):
                order_id_col = find_column(orders, "order id")
                if not order_id_col:
                    st.error("Could not find 'Order ID' column in Orders sheet. Please check your sheet headers.")
                    st.stop()
                
                order_options = orders[order_id_col].dropna().astype(str).unique().tolist()
                oid = st.selectbox("Order ID *", order_options)

                date = st.date_input("Date", datetime.today())
                amount = st.number_input("Amount Paid", min_value=0.0, value=0.0)
                method = st.selectbox("Payment Method", ["Cash", "Bank", "Online"])
                notes = st.text_area("Notes")

                submitted = st.form_submit_button("Save Transaction")
                if submitted:
                    total_amount_col = find_column(orders, "total amount")
                    amount_paid_col = find_column(transactions, "amount paid")

                    if not total_amount_col or total_amount_col not in orders.columns:
                        st.error("Could not find 'Total Amount' column in Orders sheet.")
                    elif not amount or amount <= 0:
                        st.error("Please enter a valid payment amount")
                    else:
                        try:
                            total = orders[orders[order_id_col].astype(str) == str(oid)][total_amount_col].sum()
                            
                            if not transactions.empty and amount_paid_col and amount_paid_col in transactions.columns:
                                transaction_order_id_col = find_column(transactions, "order id")
                                if transaction_order_id_col:
                                    paid_so_far = transactions[transactions[transaction_order_id_col].astype(str) == str(oid)][amount_paid_col].sum()
                                else:
                                    paid_so_far = 0
                            else:
                                paid_so_far = 0
                            
                            remaining = total - (paid_so_far + amount)
                            append_row_safe("transactions", [get_next_id("transactions"), oid, str(date), amount, method, remaining, notes])
                            st.success("✅ Transaction recorded successfully!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to add transaction: {str(e)}")

# ---------------------------
# EXPENSES
# ---------------------------
with tabs[4]:
    st.header("🧾 Expenses")
    expenses = load_data("expenses")

    if not expenses.empty:
        paginated = paginate_dataframe(expenses)
        if not paginated.empty:
            st.dataframe(paginated, use_container_width=True, hide_index=True)
    else:
        st.info("No expenses yet. Record your first expense below!")

    if st.session_state.user_role == "admin":
        with st.expander("➕ Add Expense"):
            with st.form("add_expense"):
                date = st.date_input("Date", datetime.today())
                category = st.text_input("Category *", placeholder="e.g., Transport, Supplies, Salary")
                desc = st.text_input("Description", placeholder="Brief description")
                amount = st.number_input("Amount", min_value=0.0, value=0.0)
                method = st.selectbox("Payment Method", ["Cash", "Bank", "Online"])
                notes = st.text_area("Notes")
                submitted = st.form_submit_button("Save Expense")
                if submitted:
                    if not category:
                        st.error("Category is required")
                    elif amount <= 0:
                        st.error("Please enter a valid amount")
                    else:
                        try:
                            append_row_safe("expenses", [get_next_id("expenses"), str(date), category, desc, amount, method, notes])
                            st.success("✅ Expense recorded successfully!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to add expense: {str(e)}")

# ---------------------------
# OTHER INCOME
# ---------------------------
with tabs[5]:
    st.header("💰 Other Income")
    income = load_data("income")

    if not income.empty:
        paginated = paginate_dataframe(income)
        if not paginated.empty:
            st.dataframe(paginated, use_container_width=True, hide_index=True)
    else:
        st.info("No other income yet. Record your first income entry below!")

    if st.session_state.user_role == "admin":
        with st.expander("➕ Add Income"):
            with st.form("add_income"):
                date = st.date_input("Date", datetime.today())
                source = st.text_input("Source *", placeholder="e.g., Interest, Refund, Bonus")
                amount = st.number_input("Amount", min_value=0.0, value=0.0)
                method = st.selectbox("Payment Method", ["Cash", "Bank", "Online"])
                notes = st.text_area("Notes")
                submitted = st.form_submit_button("Save Income")
                if submitted:
                    if not source:
                        st.error("Source is required")
                    elif amount <= 0:
                        st.error("Please enter a valid amount")
                    else:
                        try:
                            append_row_safe("income", [get_next_id("income"), str(date), source, amount, method, notes])
                            st.success("✅ Income recorded successfully!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to add income: {str(e)}")


# ---------------------------
# INVENTORY
# ---------------------------
with tabs[6]:
    st.header("ðŸ“¦ Inventory")
    inventory = load_data("inventory")

    if not inventory.empty:
        paginated = paginate_dataframe(inventory)
        if not paginated.empty:
            st.dataframe(paginated, use_container_width=True, hide_index=True)
    else:
        st.info("No inventory items yet. Add your first item below!")

    if st.session_state.user_role == "admin":
        with st.expander("âž• Add Item"):
            with st.form("add_inventory"):
                item_name = st.text_input("Item Name *", placeholder="e.g., 20L Bottle, 5L Bottle")
                qty = st.number_input("Quantity", min_value=0, step=1, value=0)
                unit_price = st.number_input("Unit Price", min_value=0.0, value=0.0)
                submitted = st.form_submit_button("Save Item")
                if submitted:
                    if not item_name:
                        st.error("Item name is required")
                    else:
                        try:
                            append_row_safe("inventory", [get_next_id("inventory"), item_name, qty, unit_price])
                            st.success("âœ… Item added successfully!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to add item: {str(e)}")

# ---------------------------
# REPORTS
# ---------------------------
with tabs[7]:
    st.header("ðŸ“ˆ Financial Reports")
    st.subheader("Generate and Download Reports")

    customers = load_data("customers")
    orders = load_data("orders")
    transactions = load_data("transactions")
    expenses = load_data("expenses")
    income = load_data("income")
    inventory = load_data("inventory")

    # Dynamic column finding for all calculations
    total_amount_col = find_column(orders, "total amount") or "Total Amount"
    amount_paid_col = find_column(transactions, "amount paid") or "Amount Paid"
    income_amount_col = find_column(income, "amount") or "Amount"
    expense_amount_col = find_column(expenses, "amount") or "Amount"

    total_sales = orders[total_amount_col].sum() if total_amount_col in orders.columns else 0
    paid = transactions[amount_paid_col].sum() if amount_paid_col in transactions.columns else 0
    extra_income = income[income_amount_col].sum() if income_amount_col in income.columns else 0
    total_expenses = expenses[expense_amount_col].sum() if expense_amount_col in expenses.columns else 0
    net_profit = paid + extra_income - total_expenses

    pl_df = pd.DataFrame({
        "Category": ["Sales Revenue", "Other Income", "Total Income", "Expenses", "Net Profit"],
        "Amount": [total_sales, extra_income, total_sales + extra_income, -total_expenses, net_profit]
    })

    # Inventory valuation
    inv_total = 0
    qty_col = find_column(inventory, "quantity")
    unit_price_col = find_column(inventory, "unit price")
    if not inventory.empty and qty_col and unit_price_col:
        if qty_col in inventory.columns and unit_price_col in inventory.columns:
            inventory["Value"] = inventory[qty_col] * inventory[unit_price_col]
            inv_total = inventory["Value"].sum()

    # Receivables calculation
    rec_total = 0
    receivables = pd.DataFrame()
    if not orders.empty and not transactions.empty:
        order_id_col = find_column(orders, "order id")
        trans_order_id_col = find_column(transactions, "order id")
        
        if order_id_col and trans_order_id_col and amount_paid_col and total_amount_col:
            if order_id_col in orders.columns and trans_order_id_col in transactions.columns:
                paid_by_order = transactions.groupby(trans_order_id_col)[amount_paid_col].sum().reset_index()
                paid_by_order.columns = [order_id_col, "TotalPaid"]
                
                orders_merged = orders.merge(paid_by_order, on=order_id_col, how="left")
                orders_merged["TotalPaid"] = orders_merged["TotalPaid"].fillna(0)
                orders_merged["Unpaid"] = orders_merged[total_amount_col] - orders_merged["TotalPaid"]
                
                customer_id_col = find_column(orders, "customer id")
                select_cols = [order_id_col]
                if customer_id_col and customer_id_col in orders_merged.columns:
                    select_cols.append(customer_id_col)
                select_cols += [total_amount_col, "Unpaid"]
                
                receivables = orders_merged[orders_merged["Unpaid"] > 0][select_cols]
                rec_total = orders_merged["Unpaid"].sum()

    # Display metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Receivables", f"â‚¹ {rec_total:,.0f}")
    col2.metric("Inventory Value", f"â‚¹ {inv_total:,.0f}")
    col3.metric("Net Profit", f"â‚¹ {net_profit:,.0f}")

    # Full report generation
    if st.button("ðŸ“Š Generate Full Financial Report (Excel)"):
        try:
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                pl_df.to_excel(writer, sheet_name="Profit & Loss", index=False)
                if not orders.empty:
                    orders.to_excel(writer, sheet_name="Orders", index=False)
                if not transactions.empty:
                    transactions.to_excel(writer, sheet_name="Transactions", index=False)
                if not expenses.empty:
                    expenses.to_excel(writer, sheet_name="Expenses", index=False)
                if not income.empty:
                    income.to_excel(writer, sheet_name="Other Income", index=False)
                if not inventory.empty:
                    inventory.to_excel(writer, sheet_name="Inventory", index=False)
                if not customers.empty:
                    customers.to_excel(writer, sheet_name="Customers", index=False)
                if not receivables.empty:
                    receivables.to_excel(writer, sheet_name="Receivables", index=False)

            buffer.seek(0)
            st.download_button(
                label="â¬‡ï¸ Download Full Report.xlsx",
                data=buffer,
                file_name=f"lumina_waters_report_{datetime.today().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.success("âœ… Report generated successfully!")
        except Exception as e:
            st.error(f"Failed to generate report: {str(e)}")

    with st.expander("ðŸ“„ Preview Profit & Loss"):
        st.dataframe(pl_df.style.format({"Amount": "â‚¹ {:,.0f}"}), use_container_width=True)

    with st.expander("ðŸ’µ Preview Receivables"):
        if not receivables.empty:
            format_dict = {"Unpaid": "â‚¹ {:,.0f}"}
            if total_amount_col in receivables.columns:
                format_dict[total_amount_col] = "â‚¹ {:,.0f}"
            st.dataframe(receivables.style.format(format_dict), use_container_width=True)
        else:
            st.info("No outstanding receivables")

# ---------------------------
# SETTINGS
# ---------------------------
with tabs[8]:
    st.header("âš™ï¸ Settings")
    st.subheader("Account Management")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Role", st.session_state.user_role.title())
    with col2:
        if st.button("ðŸšª Logout"):
            st.session_state.authenticated = False
            st.session_state.user_role = "viewer"
            st.rerun()
    
    st.divider()
    
    if st.session_state.user_role == "admin":
        st.subheader("Data Export")
        if st.button("ðŸ“¥ Export All Data (Excel)"):
            try:
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    load_data("customers").to_excel(writer, sheet_name="Customers", index=False)
                    load_data("orders").to_excel(writer, sheet_name="Orders", index=False)
                    load_data("transactions").to_excel(writer, sheet_name="Transactions", index=False)
                    load_data("expenses").to_excel(writer, sheet_name="Expenses", index=False)
                    load_data("income").to_excel(writer, sheet_name="Other Income", index=False)
                    load_data("inventory").to_excel(writer, sheet_name="Inventory", index=False)
                buffer.seek(0)
                st.download_button(
                    "â¬‡ï¸ Download All Data.xlsx", 
                    data=buffer, 
                    file_name=f"lumina_waters_all_data_{datetime.today().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.success("âœ… Data exported successfully!")
            except Exception as e:
                st.error(f"Failed to export data: {str(e)}")

    st.divider()
    st.subheader("ðŸ’¬ Feedback")
    with st.form("feedback_form"):
        feedback = st.text_area("Share feedback or report issues"