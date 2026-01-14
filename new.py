import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import re
from io import BytesIO
import time  # For quota delay

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
.css-18e3th9 { background-color: #161B26; }
h1,h2,h3,h4,h5,h6 { color:#F1F1F1; }
.stButton>button { background-color:#1f2a38; color:#F1F1F1; border-radius:8px; border:1px solid #2A3342; }
.stButton>button:hover { background-color:#2A3342; }
.stTextInput>div>div>input, .stNumberInput>div>div>input { background-color:#1f2a38; color:#F1F1F1; border-radius:5px; border:1px solid #2A3342; }
.stDataFrame { background-color:#161B26; color:#F1F1F1; }
.card { background-color:#161B26; border:1px solid #2A3342; border-radius:10px; padding:20px; margin:10px 0; }
@media (max-width:768px) { .stApp { font-size:14px; } }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# SESSION STATE INITIALIZATION
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
    code_input = st.text_input("Enter 6-digit passcode", type="password")
    if st.button("Login"):
        if code_input == st.secrets["APP_PASSCODE"]:
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
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )
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
@st.cache_data(ttl=300)  # Cache for 5 minutes to reduce API calls
def load_data(sheet_name):
    try:
        ws = sheets[sheet_name]
        values = ws.get_all_values()
        if len(values) <= 1:
            return pd.DataFrame()
        headers = [str(c).strip().title().replace("Ii", "Id").replace("Metho", "Method") for c in values[0]]
        df = pd.DataFrame(values[1:], columns=headers)
        numeric_cols = ["Total Amount", "Amount Paid", "Amount", "Price", "Quantity", "Unit Price", "Remaining Amount", "Remaining"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        time.sleep(0.5)  # Small delay to avoid quota hits
        return df
    except Exception as e:
        st.error(f"❌ Failed to load {sheet_name}: {str(e)}")
        return pd.DataFrame()

def get_next_id(sheet_name):
    try:
        ws = sheets[sheet_name]
        ids = ws.col_values(1)[1:]  # first column, skip header
        nums = [int(x) for x in ids if x.strip().isdigit()]
        return max(nums) + 1 if nums else 1
    except:
        return 1

def append_row_safe(sheet_name, values):
    try:
        ws = sheets[sheet_name]
        clean = [str(v) if not pd.isna(v) else "" for v in values]
        ws.append_row(clean)
        time.sleep(0.5)  # Delay for write
    except Exception as e:
        st.error(f"❌ Failed to add to {sheet_name}: {str(e)}")

def validate_email(email):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", str(email))) if email else True

# Fixed pagination function (this was missing in your current file, causing the NameError)
def paginate_dataframe(df, page_size=15):
    if df.empty:
        st.info("No data available")
        return pd.DataFrame()
    total_pages = max(1, (len(df) + page_size - 1) // page_size)
    page_number = st.selectbox("Page", range(1, total_pages + 1), key=f"page_{hash(str(df.columns))}_{id(df)}")
    start = (page_number - 1) * page_size
    return df.iloc[start:start + page_size]

# ---------------------------
# HEADER (with optional logo - replace URL with your own)
# ---------------------------
col_logo, col_title = st.columns([1, 4])
with col_logo:
    # Replace with your GitHub raw URL or local path
    st.image("IMG-20260105-WA0026.jpg", width=100)  # Placeholder - replace with your logo URL
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
    
    total_sales = orders.get("Total Amount", pd.Series([0])).sum()
    paid = transactions.get("Amount Paid", pd.Series([0])).sum()
    extra_income = income.get("Amount", pd.Series([0])).sum()
    total_expenses = expenses.get("Amount", pd.Series([0])).sum()
    net_balance = paid + extra_income - total_expenses
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sales", f"₹ {total_sales:,.0f}")
    col2.metric("Money Received", f"₹ {paid + extra_income:,.0f}")
    col3.metric("Total Expenses", f"₹ {total_expenses:,.0f}")
    col4.metric("Net Balance", f"₹ {net_balance:,.0f}")
    
    if not expenses.empty and "Category" in expenses.columns:
        fig = px.pie(expenses, names="Category", values="Amount", title="Expense Breakdown")
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# CUSTOMERS
# ---------------------------
with tabs[1]:
    st.header("👥 Customers")
    customers = load_data("customers")
    search = st.text_input("Search by Name/Contact/Email")
    if search:
        mask = (customers["Name"].str.contains(search, case=False, na=False) |
                customers.get("Contact", "").str.contains(search, case=False, na=False) |
                customers.get("Email", "").str.contains(search, case=False, na=False))
        customers = customers[mask]
    
    paginated_df = paginate_dataframe(customers)
    st.dataframe(paginated_df, use_container_width=True, hide_index=True)
    
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
                        st.error("Invalid email")
                    else:
                        append_row_safe("customers", [get_next_id("customers"), name, ctype, contact, email, address, "Yes" if vip else "", notes])
                        st.success("Customer added!")
                        st.rerun()

# ---------------------------
# ORDERS
# ---------------------------
with tabs[2]:
    st.header("📝 Orders")
    orders = load_data("orders")
    customers = load_data("customers")
    
    paginated_df = paginate_dataframe(orders)
    st.dataframe(paginated_df, use_container_width=True, hide_index=True)
    
    if st.session_state.user_role == "admin":
        with st.expander("➕ Add Order"):
            with st.form("add_order"):
                if not customers.empty:
                    customer_name = st.selectbox("Customer *", customers["Name"])
                    cid = customers[customers["Name"] == customer_name].iloc[0].get("Customer Id", "?")
                else:
                    customer_name = st.text_input("New Customer Name (if not in list)")
                    cid = "New"
                
                order_date = st.date_input("Order Date", datetime.today())
                delivery_date = st.date_input("Delivery Date", datetime.today())
                items = st.text_input("Items *")
                qty = st.number_input("Quantity", min_value=1, step=1)
                price = st.number_input("Price per Item", min_value=0.0, step=10.0)
                pay_status = st.selectbox("Payment Status", ["Unpaid", "Partial", "Paid"])
                order_status = st.selectbox("Order Status", ["Pending", "Delivered", "Cancelled"])
                notes = st.text_area("Notes")
                
                submitted = st.form_submit_button("Save Order")
                if submitted:
                    if not items:
                        st.error("Items required")
                    else:
                        total = qty * price
                        append_row_safe("orders", [get_next_id("orders"), cid, str(order_date), str(delivery_date), items, qty, price, total, pay_status, order_status, notes])
                        st.success("Order added!")
                        st.rerun()

# ---------------------------
# TRANSACTIONS
# ---------------------------
with tabs[3]:
    st.header("💳 Transactions")
    transactions = load_data("transactions")
    orders = load_data("orders")
    
    paginated_df = paginate_dataframe(transactions)
    st.dataframe(paginated_df, use_container_width=True, hide_index=True)
    
    if st.session_state.user_role == "admin" and not orders.empty:
        with st.expander("➕ Add Transaction"):
            with st.form("add_transaction"):
                oid = st.selectbox("Order ID *", orders.get("Order Id", pd.Series([])).tolist())
                date = st.date_input("Date", datetime.today())
                amount = st.number_input("Amount Paid", min_value=0.0)
                method = st.selectbox("Payment Method", ["Cash", "Bank", "Online"])
                notes = st.text_area("Notes")
                
                submitted = st.form_submit_button("Save Transaction")
                if submitted:
                    total = orders[orders["Order Id"] == oid].get("Total Amount", 0).sum()
                    paid_so_far = transactions[transactions["Order Id"] == oid].get("Amount Paid", 0).sum()
                    remaining = total - (paid_so_far + amount)
                    append_row_safe("transactions", [get_next_id("transactions"), oid, str(date), amount, method, remaining, notes])
                    st.success("Transaction added!")
                    st.rerun()

# ---------------------------
# EXPENSES
# ---------------------------
with tabs[4]:
    st.header("🧾 Expenses")
    expenses = load_data("expenses")
    
    paginated_df = paginate_dataframe(expenses)
    st.dataframe(paginated_df, use_container_width=True, hide_index=True)
    
    if st.session_state.user_role == "admin":
        with st.expander("➕ Add Expense"):
            with st.form("add_expense"):
                date = st.date_input("Date", datetime.today())
                category = st.text_input("Category *")
                desc = st.text_input("Description")
                amount = st.number_input("Amount", min_value=0.0)
                method = st.selectbox("Payment Method", ["Cash", "Bank", "Online"])
                notes = st.text_area("Notes")
                submitted = st.form_submit_button("Save Expense")
                if submitted:
                    if not category:
                        st.error("Category required")
                    else:
                        append_row_safe("expenses", [get_next_id("expenses"), str(date), category, desc, amount, method, notes])
                        st.success("Expense added!")
                        st.rerun()

# ---------------------------
# OTHER INCOME
# ---------------------------
with tabs[5]:
    st.header("💰 Other Income")
    income = load_data("income")
    
    paginated_df = paginate_dataframe(income)
    st.dataframe(paginated_df, use_container_width=True, hide_index=True)
    
    if st.session_state.user_role == "admin":
        with st.expander("➕ Add Income"):
            with st.form("add_income"):
                date = st.date_input("Date", datetime.today())
                source = st.text_input("Source *")
                amount = st.number_input("Amount", min_value=0.0)
                method = st.selectbox("Payment Method", ["Cash", "Bank", "Online"])
                notes = st.text_area("Notes")
                submitted = st.form_submit_button("Save Income")
                if submitted:
                    if not source:
                        st.error("Source required")
                    else:
                        append_row_safe("income", [get_next_id("income"), str(date), source, amount, method, notes])
                        st.success("Income added!")
                        st.rerun()

# ---------------------------
# INVENTORY
# ---------------------------
with tabs[6]:
    st.header("📦 Inventory")
    inventory = load_data("inventory")
    
    paginated_df = paginate_dataframe(inventory)
    st.dataframe(paginated_df, use_container_width=True, hide_index=True)
    
    if st.session_state.user_role == "admin":
        with st.expander("➕ Add Item"):
            with st.form("add_inventory"):
                item_name = st.text_input("Item Name *")
                qty = st.number_input("Quantity", min_value=0, step=1)
                unit_price = st.number_input("Unit Price", min_value=0.0)
                submitted = st.form_submit_button("Save Item")
                if submitted:
                    if not item_name:
                        st.error("Item name required")
                    else:
                        append_row_safe("inventory", [get_next_id("inventory"), item_name, qty, unit_price])
                        st.success("Item added!")
                        st.rerun()

# ---------------------------
# REPORTS
# ---------------------------
with tabs[7]:
    st.header("📈 Financial Reports")
    st.subheader("Generate and Download Reports")
    
    customers = load_data("customers")
    orders = load_data("orders")
    transactions = load_data("transactions")
    expenses = load_data("expenses")
    income = load_data("income")
    inventory = load_data("inventory")
    
    total_sales = orders.get("Total Amount", pd.Series([0])).sum()
    paid = transactions.get("Amount Paid", pd.Series([0])).sum()
    extra_income = income.get("Amount", pd.Series([0])).sum()
    total_expenses = expenses.get("Amount", pd.Series([0])).sum()
    net_profit = paid + extra_income - total_expenses
    
    pl_df = pd.DataFrame({
        "Category": ["Sales Revenue", "Other Income", "Total Income", "Expenses", "Net Profit"],
        "Amount": [total_sales, extra_income, total_sales + extra_income, -total_expenses, net_profit]
    })
    
    if not inventory.empty and "Quantity" in inventory.columns and "Unit Price" in inventory.columns:
        inventory["Value"] = inventory["Quantity"] * inventory["Unit Price"]
        inv_total = inventory["Value"].sum()
    else:
        inv_total = 0
    
    if not orders.empty:
        orders["Unpaid"] = orders["Total Amount"] - orders.merge(transactions.groupby("Order Id")["Amount Paid"].sum().reset_index(), left_on="Order Id", right_on="Order Id", how="left")["Amount Paid"].fillna(0)
        receivables = orders[orders["Unpaid"] > 0][["Order Id", "Customer Id", "Total Amount", "Unpaid"]]
        rec_total = receivables["Unpaid"].sum()
    else:
        rec_total = 0
    
    if st.button("Generate Full Financial Report (Excel)"):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pl_df.to_excel(writer, sheet_name="Profit & Loss", index=False)
            orders.to_excel(writer, sheet_name="Orders", index=False)
            transactions.to_excel(writer, sheet_name="Transactions", index=False)
            expenses.to_excel(writer, sheet_name="Expenses", index=False)
            income.to_excel(writer, sheet_name="Other Income", index=False)
            inventory.to_excel(writer, sheet_name="Inventory", index=False)
            customers.to_excel(writer, sheet_name="Customers", index=False)
            if "receivables" in locals() and not receivables.empty:
                receivables.to_excel(writer, sheet_name="Receivables", index=False)
        
        buffer.seek(0)
        st.download_button(
            label="Download Full Report.xlsx",
            data=buffer,
            file_name="lumina_waters_full_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Receivables", f"₹ {rec_total:,.0f}")
    col2.metric("Inventory Value", f"₹ {inv_total:,.0f}")
    col3.metric("Net Profit", f"₹ {net_profit:,.0f}")

    with st.expander("Preview Profit & Loss"):
        st.dataframe(pl_df)
    with st.expander("Preview Receivables"):
        st.dataframe(receivables if 'receivables' in locals() else pd.DataFrame())

# ---------------------------
# SETTINGS
# ---------------------------
with tabs[8]:
    st.header("⚙️ Settings")
    st.subheader("Account Management")
    if st.session_state.user_role == "admin":
        if st.button("Export Customers CSV"):
            customers = load_data("customers")
            csv = customers.to_csv(index=False).encode()
            st.download_button("Download CSV", data=csv, file_name="customers.csv", mime="text/csv")
    
    st.subheader("Feedback")
    feedback = st.text_area("Share feedback or report issues")
    if st.button("Submit Feedback"):
        st.success("Thank you for your feedback!")

st.caption("Lumina Waters Finance • January 2026")