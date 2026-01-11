import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
import re

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
# SESSION STATE
# ---------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = "admin"
if "refresh" not in st.session_state:
    st.session_state.refresh = False

if st.session_state.refresh:
    st.session_state.refresh = False
    st.experimental_rerun()

# ---------------------------
# DARK THEME & CSS
# ---------------------------
st.markdown("""
<style>
.stApp { background-color: #0E1117; color: #F1F1F1; }
.css-18e3th9 { background-color: #161B26; }
h1,h2,h3,h4,h5,h6 { color: #F1F1F1; }
.stButton>button { background-color: #1f2a38; color: #F1F1F1; border-radius: 8px; border: 1px solid #2A3342; }
.stButton>button:hover { background-color: #2A3342; }
.stTextInput>div>div>input, .stNumberInput>div>div>input { background-color: #1f2a38; color: #F1F1F1; border: 1px solid #2A3342; border-radius: 5px; }
.stDataFrame { background-color: #161B26; color: #F1F1F1; }
.card { background-color: #161B26; border: 1px solid #2A3342; border-radius: 10px; padding: 20px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# LOGIN (Simplified to Passcode Only)
# ---------------------------
if not st.session_state.authenticated:
    st.title("🔒 Lumina Waters – Login")
    code_input = st.text_input("Enter 6-digit passcode", type="password")

    login_clicked = st.button("Login")  # Capture click in a variable

    if login_clicked:
        if code_input == st.secrets["APP_PASSCODE"]:
            st.session_state.authenticated = True
            st.session_state.user_role = "admin"
            st.experimental_rerun()  # Safe to call inside button callback
        else:
            st.error("❌ Incorrect passcode")

    st.stop()  # Stop execution until login is successful
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
    st.stop()

# ---------------------------
# UTILITIES
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

def validate_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)



# ---------------------------
# HEADER
# ---------------------------
st.title("💧 Lumina Waters Finance")

# ---------------------------
# NAVIGATION TABS
# ---------------------------
tabs = st.tabs([
    "📊 Dashboard", "👥 Customers", "📝 Orders", "💳 Transactions",
    "🧾 Expenses", "💰 Other Income", "📦 Inventory", "📄 Invoices"
])

# ---------------------------
# DASHBOARD
# ---------------------------
with tabs[0]:
    st.header("📊 Financial Overview")
    orders = load_data(sheets["orders"])
    expenses = load_data(sheets["expenses"])
    income = load_data(sheets["income"])
    
    if not expenses.empty:
        import plotly.express as px
        fig = px.pie(expenses, names="Category", values="Amount", title="Expense Breakdown")
        st.plotly_chart(fig)

# ---------------------------
# CUSTOMERS
# ---------------------------
with tabs[1]:
    st.header("👥 Customers")
    customers = load_data(sheets["customers"])
    name = st.text_input("Name", key="customer_name")
    ctype = st.selectbox("Type", ["Restaurant","Mall","Other"], key="customer_type")
    contact = st.text_input("Contact", key="customer_contact")
    email = st.text_input("Email", key="customer_email")
    address = st.text_input("Address", key="customer_address")
    vip = st.checkbox("VIP", key="customer_vip")
    notes = st.text_area("Notes", key="customer_notes")
    if st.button("Save Customer", key="save_customer"):
        if name and validate_email(email):
            cid = len(customers)+1
            append_row_safe(sheets["customers"], [cid, name, ctype, contact, email, address, vip, notes])
            st.success("Customer added!")
            st.session_state.refresh = True
            st.stop()
        else:
            st.error("Invalid email or missing name.")
    st.dataframe(customers, width="stretch")

# ---------------------------
# ORDERS
# ---------------------------
with tabs[2]:
    st.header("📝 Orders")
    orders = load_data(sheets["orders"])
    customers = load_data(sheets["customers"])
    customer = st.selectbox("Customer", customers["Name"] if not customers.empty else [], key="order_customer")
    order_date = st.date_input("Order Date", datetime.today(), key="order_date")
    delivery_date = st.date_input("Delivery Date", datetime.today(), key="order_delivery")
    items = st.text_input("Items Ordered", key="order_items")
    qty = st.number_input("Quantity", min_value=1, key="order_qty")
    price = st.number_input("Price per Item", min_value=0.0, key="order_price")
    pay_status = st.selectbox("Payment Status", ["Paid","Partial","Unpaid"], key="order_pay_status")
    order_status = st.selectbox("Order Status", ["Pending","Delivered","Cancelled"], key="order_status")
    notes = st.text_area("Notes", key="order_notes")
    if st.button("Save Order", key="save_order") and not customers.empty:
        cid = customers[customers["Name"]==customer]["Customer ID"].values[0]
        total = qty*price
        oid = len(orders)+1
        append_row_safe(sheets["orders"], [oid, cid, str(order_date), str(delivery_date), items, qty, price, total, pay_status, order_status, notes])
        st.success("Order added!")
        st.session_state.refresh = True
        st.stop()
    st.dataframe(orders, width="stretch")

# ---------------------------
# TRANSACTIONS
# ---------------------------
with tabs[3]:
    st.header("💳 Transactions")
    transactions = load_data(sheets["transactions"])
    orders = load_data(sheets["orders"])
    oid = st.selectbox("Order ID", orders["Order ID"] if not orders.empty else [], key="trans_oid")
    date = st.date_input("Date", datetime.today(), key="trans_date")
    amount = st.number_input("Amount Paid", min_value=0.0, key="trans_amount")
    method = st.selectbox("Payment Method", ["Cash","Bank","Online"], key="trans_method")
    notes = st.text_area("Notes", key="trans_notes")
    if st.button("Save Transaction", key="save_transaction") and not orders.empty:
        total = orders[orders["Order ID"]==oid]["Total Amount"].values[0]
        paid_sum = transactions[transactions["Order ID"]==oid]["Amount Paid"].sum() if not transactions.empty else 0
        remaining = total - (paid_sum + amount)
        tid = len(transactions)+1
        append_row_safe(sheets["transactions"], [tid, oid, str(date), amount, method, remaining, notes])
        st.success("Transaction added!")
        st.session_state.refresh = True
        st.stop()
    st.dataframe(transactions, width="stretch")

# ---------------------------
# EXPENSES
# ---------------------------
with tabs[4]:
    st.header("🧾 Expenses")
    expenses = load_data(sheets["expenses"])
    date = st.date_input("Date", datetime.today(), key="exp_date")
    category = st.text_input("Category", key="exp_category")
    desc = st.text_input("Description", key="exp_desc")
    amount = st.number_input("Amount", min_value=0.0, key="exp_amount")
    method = st.selectbox("Payment Method", ["Cash","Bank","Online"], key="exp_method")
    notes = st.text_area("Notes", key="exp_notes")
    if st.button("Save Expense", key="save_expense"):
        eid = len(expenses)+1
        append_row_safe(sheets["expenses"], [eid, str(date), category, desc, amount, method, notes])
        st.success("Expense added!")
        st.session_state.refresh = True
        st.stop()
    st.dataframe(expenses, width="stretch")

# ---------------------------
# OTHER INCOME
# ---------------------------
with tabs[5]:
    st.header("💰 Other Income")
    income = load_data(sheets["income"])
    date = st.date_input("Date", datetime.today(), key="inc_date")
    source = st.text_input("Source", key="inc_source")
    amount = st.number_input("Amount", min_value=0.0, key="inc_amount")
    method = st.selectbox("Payment Method", ["Cash","Bank","Online"], key="inc_method")
    notes = st.text_area("Notes", key="inc_notes")
    if st.button("Save Income", key="save_income"):
        iid = len(income)+1
        append_row_safe(sheets["income"], [iid, str(date), source, amount, method, notes])
        st.success("Income added!")
        st.session_state.refresh = True
        st.stop()
    st.dataframe(income, width="stretch")

# ---------------------------
# INVENTORY
# ---------------------------
with tabs[6]:
    st.header("📦 Inventory")
    inventory = load_data(sheets["inventory"])
    item_name = st.text_input("Item Name", key="inv_name")
    qty = st.number_input("Quantity", min_value=0, key="inv_qty")
    unit_price = st.number_input("Unit Price", min_value=0.0, key="inv_price")
    if st.button("Save Item", key="save_inv"):
        iid = len(inventory)+1
        append_row_safe(sheets["inventory"], [iid, item_name, qty, unit_price])
        st.success("Item added!")
        st.session_state.refresh = True
        st.stop()
    st.dataframe(inventory, width="stretch")
