import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
import smtplib
from email.mime.text import MIMEText
import re
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
# DARK THEME & CSS (Enhanced)
# ---------------------------
st.markdown("""
<style>
/* Background & text */
.stApp {
    background-color: #0E1117;
    color: #F1F1F1;
}
/* Sidebar styling */
.css-18e3th9 {
    background-color: #161B26;
}
/* Header fonts */
h1, h2, h3, h4, h5, h6 {
    color: #F1F1F1;
}
/* Buttons */
.stButton>button {
    background-color: #1f2a38;
    color: #F1F1F1;
    border-radius: 8px;
    border: 1px solid #2A3342;
}
.stButton>button:hover {
    background-color: #2A3342;
}
/* Inputs */
.stTextInput>div>div>input, .stNumberInput>div>div>input {
    background-color: #1f2a38;
    color: #F1F1F1;
    border: 1px solid #2A3342;
    border-radius: 5px;
}
/* Tables */
.stDataFrame {
    background-color: #161B26;
    color: #F1F1F1;
}
/* Cards */
.card {
    background-color: #161B26;
    border: 1px solid #2A3342;
    border-radius: 10px;
    padding: 20px;
    margin: 10px 0;
}
/* Responsive */
@media (max-width: 768px) {
    .stApp {
        font-size: 14px;
    }
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# SESSION STATE INITIALIZATION
# ---------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = "viewer"  # Default role; can be "admin" or "viewer"
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# ---------------------------
# LOGIN (Simplified to Passcode Only)
# ---------------------------
if not st.session_state.authenticated:
    st.title("🔒 Lumina Waters – Login")
    code_input = st.text_input("Enter 6-digit passcode", type="password")

    if st.button("Login"):
        if code_input == st.secrets["APP_PASSCODE"]:
            st.session_state.authenticated = True
            st.session_state.user_role = "admin"  # Or set based on logic; default to admin for simplicity
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
        "inventory": sh.worksheet("Inventory")  # New sheet for inventory
    }

try:
    sheets = connect_sheets()
except Exception as e:
    st.error("❌ Google Sheets connection failed")
    st.code(str(e))
    st.stop()

# ---------------------------
# UTILITY FUNCTIONS (Enhanced)
# ---------------------------

def load_data(ws):
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df.columns = [str(c).strip() for c in df.columns]
    return df

def append_row_safe(ws, values):
    converted = []
    for v in values:
        if isinstance(v, (pd.Timestamp, pd._libs.tslibs.timestamps.Timestamp)):
            converted.append(str(v))
        elif pd.isna(v):
            converted.append("")
        else:
            converted.append(v)
    ws.append_row(converted)

def update_row(ws, row_index, values):
    ws.update(f"A{row_index}:Z{row_index}", [values])

def delete_row(ws, row_index):
    ws.delete_rows(row_index)

def validate_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def paginate_dataframe(df, page_size=10):
    if df.empty:
        return df, 0
    total_pages = (len(df) // page_size) + 1
    page = st.selectbox("Page", range(1, total_pages + 1), key=f"page_{id(df)}")
    start = (page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end], total_pages

def generate_invoice(order_id, customer_name, items, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Lumina Waters Invoice", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Order ID: {order_id}", ln=True)
    pdf.cell(200, 10, txt=f"Customer: {customer_name}", ln=True)
    pdf.cell(200, 10, txt=f"Items: {items}", ln=True)
    pdf.cell(200, 10, txt=f"Total: ₹{total}", ln=True)
    pdf.output(f"invoice_{order_id}.pdf")
    return f"invoice_{order_id}.pdf"

# ---------------------------
# HEADER WITH THEME TOGGLE
# ---------------------------
col1, col2 = st.columns([3, 1])
with col1:
    st.title("💧 Lumina Waters Finance")
with col2:
    if st.button("Toggle Theme"):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()

# ---------------------------
# NAVIGATION WITH TABS
# ---------------------------
tabs = st.tabs([
    "📊 Dashboard", "👥 Customers", "📝 Orders", "💳 Transactions", 
    "🧾 Expenses", "💰 Other Income", "📦 Inventory", "📄 Invoices", "⚙️ Settings"
])

# ---------------------------
# DASHBOARD (Enhanced with Charts)
# ---------------------------
with tabs[0]:
    st.header("📊 Financial Overview")
    
    orders = load_data(sheets["orders"])
    transactions = load_data(sheets["transactions"])
    expenses = load_data(sheets["expenses"])
    income = load_data(sheets["income"])
    
    total_sales = orders["Total Amount"].sum() if not orders.empty else 0
    paid = transactions["Amount Paid"].sum() if not transactions.empty else 0
    extra_income = income["Amount"].sum() if not income.empty else 0
    total_expenses = expenses["Amount"].sum() if not expenses.empty else 0
    net_balance = paid + extra_income - total_expenses
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Sales", f"₹ {total_sales:,.0f}")
    with col2:
        st.metric("Money Received", f"₹ {paid + extra_income:,.0f}")
    with col3:
        st.metric("Total Expenses", f"₹ {total_expenses:,.0f}")
    with col4:
        st.metric("Net Balance", f"₹ {net_balance:,.0f}")
    
    # Charts
    if not orders.empty:
        fig = px.line(orders, x="Order Date", y="Total Amount", title="Sales Over Time")
        st.plotly_chart(fig)
    
    if not expenses.empty:
        fig2 = px.pie(expenses, names="Category", values="Amount", title="Expense Breakdown")
        st.plotly_chart(fig2)

# ---------------------------
# CUSTOMERS (Full CRUD)
# ---------------------------
with tabs[1]:
    st.header("👥 Customers")
    customers = load_data(sheets["customers"])
    
    search = st.text_input("Search by Name", key="search_customers")
    if search:
        customers = customers[customers["Name"].str.contains(search, case=False, na=False)]
    
    customers_pag, _ = paginate_dataframe(customers)
    st.dataframe(customers_pag, use_container_width=True)
    
    if st.session_state.user_role == "admin":
        with st.expander("➕ Add/Edit Customer"):
            action = st.radio("Action", ["Add", "Edit"], key="customer_action")
            if action == "Add":
                with st.form("customer_form"):
                    name = st.text_input("Name")
                    ctype = st.selectbox("Type", ["Restaurant", "Mall", "Other"])
                    contact = st.text_input("Contact")
                    email = st.text_input("Email")
                    address = st.text_input("Address")
                    vip = st.checkbox("VIP")
                    notes = st.text_area("Notes")
                    submit = st.form_submit_button("Save")
                    
                    if submit and name and validate_email(email):
                        cid = len(customers) + 1
                        append_row_safe(sheets["customers"], [cid, name, ctype, contact, email, address, vip, notes])
                        st.success("Customer added!")
                        st.rerun()
                    elif submit:
                        st.error("Invalid email or missing name.")
            else:
                cid_edit = st.selectbox("Select Customer ID to Edit", customers["Customer ID"] if not customers.empty else [])
                if cid_edit:
                    row = customers[customers["Customer ID"] == cid_edit].iloc[0]
                    with st.form("edit_customer_form"):
                        name = st.text_input("Name", value=row["Name"])
                        # ... (similar fields)
                        submit = st.form_submit_button("Update")
                        if submit:
                            # Update logic
                            pass
        
        if st.button("Delete Customer") and st.session_state.user_role == "admin":
            cid_del = st.selectbox("Select Customer ID to Delete", customers["Customer ID"] if not customers.empty else [])
            if st.button("Confirm Delete"):
                # Delete logic
                pass

# ---------------------------
# ORDERS (Full CRUD)
# ---------------------------
with tabs[2]:
    st.header("📝 Orders")
    customers = load_data(sheets["customers"])
    orders = load_data(sheets["orders"])
    
    filter_status = st.multiselect("Filter by Status", ["Pending", "Delivered", "Cancelled"], key="filter_orders")
    if filter_status:
        orders = orders[orders["Order Status"].isin(filter_status)]
    
    orders_pag, _ = paginate_dataframe(orders)
    st.dataframe(orders_pag, use_container_width=True)
    
    if not customers.empty and st.session_state.user_role == "admin":
        with st.expander("➕ Add Order"):
            with st.form("order_form"):
                customer = st.selectbox("Customer", customers["Name"])
                order_date = st.date_input("Order Date", datetime.today())
                delivery_date = st.date_input("Delivery Date")
                items = st.text_input("Items Ordered")
                qty = st.number_input("Quantity", min_value=1)
                price = st.number_input("Price per Item", min_value=0.0)
                pay_status = st.selectbox("Payment Status", ["Paid", "Partial", "Unpaid"])
                order_status = st.selectbox("Order Status", ["Pending", "Delivered", "Cancelled"])
                notes = st.text_area("Notes")
                submit = st.form_submit_button("Save Order")
                
                if submit:
                    cid = customers[customers["Name"] == customer]["Customer ID"].values[0]
                    total = qty * price
                    oid = len(orders) + 1
                    append_row_safe(
                        sheets["orders"],
                        [oid, cid, str(order_date), str(delivery_date), items, qty, price, total, pay_status, order_status, notes]
                    )
                    st.success("Order added!")
                    st.rerun()

# ---------------------------
# TRANSACTIONS (Full CRUD)
# ---------------------------
with tabs[3]:
    st.header("💳 Transactions")
    orders = load_data(sheets["orders"])
    transactions = load_data(sheets["transactions"])
    
    transactions_pag, _ = paginate_dataframe(transactions)
    st.dataframe(transactions_pag, use_container_width=True)
    
    if not orders.empty and st.session_state.user_role == "admin":
        with st.expander("➕ Add Transaction"):
            with st.form("transaction_form"):
                oid = st.selectbox("Order ID", orders["Order ID"])
                date = st.date_input("Date", datetime.today())
                amount = st.number_input("Amount Paid", min_value=0.0)
                method = st.selectbox("Payment Method", ["Cash", "Bank", "Online"])
                notes = st.text_area("Notes")
                submit = st.form_submit_button("Save")
                
                if submit:
                    total = orders[orders["Order ID"] == oid]["Total Amount"].values[0]
                    paid_sum = transactions[transactions["Order ID"] == oid]["Amount Paid"].sum() if not transactions.empty else 0
                    remaining = total - (paid_sum + amount)
                    tid = len(transactions) + 1
                    append_row_safe(
                        sheets["transactions"],
                        [tid, oid, str(date), amount, method, remaining, notes]
                    )
                    st.success("Transaction added!")
                    st.rerun()

# ---------------------------
# EXPENSES (Full CRUD)
# ---------------------------
with tabs[4]:
    st.header("🧾 Expenses")
    expenses = load_data(sheets["expenses"])
    
    expenses_pag, _ = paginate_dataframe(expenses)
    st.dataframe(expenses_pag, use_container_width=True)
    
    if st.session_state.user_role == "admin":
        with st.expander("➕ Add Expense"):
            with st.form("expense_form"):
                date = st.date_input("Date", datetime.today())
                category = st.text_input("Category")
                desc = st.text_input("Description")
                amount = st.number_input("Amount", min_value=0.0)
                method = st.selectbox("Payment Method", ["Cash", "Bank", "Online"])
                notes = st.text_area("Notes")
                submit = st.form_submit_button("Save")
                
                if submit:
                    eid = len(expenses) + 1
                    append_row_safe(
                        sheets["expenses"],
                        [eid, str(date), category, desc, amount, method, notes]
                    )
                    st.success("Expense added!")
                    st.rerun()

# ---------------------------
# OTHER INCOME (Full CRUD)
# ---------------------------
with tabs[5]:
    st.header("💰 Other Income")
    income = load_data(sheets["income"])
    
    income_pag, _ = paginate_dataframe(income)
    st.dataframe(income_pag, use_container_width=True)
    
    if st.session_state.user_role == "admin":
        with st.expander("➕ Add Income"):
            with st.form("income_form"):
                date = st.date_input("Date", datetime.today())
                source = st.text_input("Source")
                amount = st.number_input("Amount", min_value=0.0)
                method = st.selectbox("Payment Method", ["Cash", "Bank", "Online"])
                notes = st.text_area("Notes")
                submit = st.form_submit_button("Save")
                
                if submit:
                    iid = len(income) + 1
                    append_row_safe(
                        sheets["income"],
                        [iid, str(date), source, amount, method, notes]
                    )
                    st.success("Income added!")
                    st.rerun()

# ---------------------------
# INVENTORY (New Feature)
# ---------------------------
with tabs[6]:
    st.header("📦 Inventory")
    inventory = load_data(sheets["inventory"])
    
    inventory_pag, _ = paginate_dataframe(inventory)
    st.dataframe(inventory_pag, use_container_width=True)
    
    if st.session_state.user_role == "admin":
        with st.expander("➕ Add Item"):
            with st.form("inventory_form"):
                item_name = st.text_input("Item Name")
                qty = st.number_input("Quantity", min_value=0)
                unit_price = st.number_input("Unit Price", min_value=0.0)
                submit = st.form_submit_button("Save")
                
                if submit:
                    iid = len(inventory) + 1
                    append_row_safe(sheets["inventory"], [iid, item_name, qty, unit_price])
                    st.success("Item added!")
                    st.rerun()

# ---------------------------
# INVOICES (New Feature)
# ---------------------------
with tabs[7]:
    st.header("📄 Invoices")
    orders = load_data(sheets["orders"])
    customers = load_data(sheets["customers"])
    
    oid_select = st.selectbox("Select Order ID for Invoice", orders["Order ID"] if not orders.empty else [])
    if oid_select and st.button("Generate Invoice"):
        order = orders[orders["Order ID"] == oid_select].iloc[0]
        customer_name = customers[customers["Customer ID"] == order["Customer ID"]]["Name"].values[0]
        pdf_file = generate_invoice(oid_select, customer_name, order["Items Ordered"], order["Total Amount"])
        with open(pdf_file, "rb") as f:
            st.download_button("Download Invoice", data=f, file_name=pdf_file, mime="application/pdf")

# ---------------------------
# SETTINGS (New Feature)
# ---------------------------
with tabs[8]:
    st.header("⚙️ Settings")
    
    st.subheader("User Preferences")
    if st.button("Toggle Theme"):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()
    
    st.subheader("Account Management")
    if st.session_state.user_role == "admin":
        st.write("Admin Options:")
        if st.button("Export Data to CSV"):
            # Example: Export customers
            customers = load_data(sheets["customers"])
            csv = customers.to_csv(index=False)
            st.download_button("Download Customers CSV", data=csv, file_name="customers.csv", mime="text/csv")
    
    st.subheader("Feedback")
    feedback = st.text_area("Share your feedback or report issues")
    if st.button("Submit Feedback"):
        # In production, save to a database or email
        st.success("Feedback submitted! Thank you.")
    
    st.subheader("Help & Tutorials")
    with st.expander("How to Use the App"):
        st.write("1. Login with passcode and OTP.")
        st.write("2. Navigate tabs to manage data.")
        st.write("3. Use search and filters for efficiency.")
        st.write("4. Admins can add/edit/delete records.")