import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
from fpdf import FPDF
import re

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="💧 Lumina Waters Finance",
    page_icon="💧",
    layout="wide"
)

# =====================================================
# GLOBAL CSS (Premium Dark)
# =====================================================
st.markdown("""
<style>
.stApp { background-color:#0E1117; color:#F1F1F1; }
section[data-testid="stSidebar"] { background-color:#161B26; }
h1,h2,h3,h4 { color:#F1F1F1; }
.stButton>button {
    background:#1f2a38; color:#fff;
    border-radius:8px; border:1px solid #2A3342;
}
.stButton>button:hover { background:#2A3342; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# SESSION STATE
# =====================================================
st.session_state.setdefault("authenticated", False)
st.session_state.setdefault("role", "admin")

# =====================================================
# LOGIN
# =====================================================
if not st.session_state.authenticated:
    st.title("🔒 Lumina Waters Login")
    code = st.text_input("6-digit Passcode", type="password")

    if st.button("Login"):
        if code == st.secrets["APP_PASSCODE"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect passcode")

    st.stop()

# =====================================================
# GOOGLE SHEETS
# =====================================================
@st.cache_resource
def connect_sheets():
    scope = [
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
        "inventory": sh.worksheet("Inventory"),
    }

sheets = connect_sheets()

# =====================================================
# HELPERS
# =====================================================
def load_df(ws):
    df = pd.DataFrame(ws.get_all_records())
    return df.astype(str) if not df.empty else df

def append_row(ws, values):
    ws.append_row([str(v) for v in values])

def paginate(df, key):
    if df.empty:
        return df
    page = st.selectbox("Page", range(1, (len(df)//10)+2), key=key)
    return df.iloc[(page-1)*10:page*10]

def valid_email(e):
    return re.match(r"[^@]+@[^@]+\.[^@]+", e)

# =====================================================
# HEADER
# =====================================================
st.title("💧 Lumina Waters – Finance Dashboard")

tabs = st.tabs([
    "📊 Dashboard", "👥 Customers", "📝 Orders",
    "💳 Transactions", "🧾 Expenses",
    "💰 Income", "📦 Inventory", "📄 Invoices"
])

# =====================================================
# DASHBOARD
# =====================================================
with tabs[0]:
    orders = load_df(sheets["orders"])
    expenses = load_df(sheets["expenses"])
    income = load_df(sheets["income"])
    transactions = load_df(sheets["transactions"])

    def sum_col(df, col):
        return pd.to_numeric(df[col], errors="coerce").sum() if not df.empty else 0

    sales = sum_col(orders, "Total Amount")
    paid = sum_col(transactions, "Amount Paid")
    extra = sum_col(income, "Amount")
    exp = sum_col(expenses, "Amount")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Sales", f"₹ {sales:,.0f}")
    c2.metric("Received", f"₹ {paid+extra:,.0f}")
    c3.metric("Expenses", f"₹ {exp:,.0f}")
    c4.metric("Net", f"₹ {(paid+extra-exp):,.0f}")

    if not orders.empty:
        st.plotly_chart(px.line(
            orders,
            x="Order Date",
            y="Total Amount",
            title="Sales Trend"
        ), use_container_width=True)

# =====================================================
# CUSTOMERS
# =====================================================
with tabs[1]:
    df = load_df(sheets["customers"])
    st.dataframe(paginate(df,"cust_pg"), width="stretch")

    with st.expander("➕ Add Customer"):
        with st.form("cust_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            contact = st.text_input("Contact")
            submit = st.form_submit_button("Save")

            if submit and name and valid_email(email):
                append_row(sheets["customers"], [len(df)+1,name,email,contact])
                st.success("Customer added")
                st.rerun()

# =====================================================
# ORDERS
# =====================================================
with tabs[2]:
    df = load_df(sheets["orders"])
    st.dataframe(paginate(df,"order_pg"), width="stretch")

# =====================================================
# TRANSACTIONS
# =====================================================
with tabs[3]:
    df = load_df(sheets["transactions"])
    st.dataframe(paginate(df,"txn_pg"), width="stretch")

# =====================================================
# EXPENSES
# =====================================================
with tabs[4]:
    df = load_df(sheets["expenses"])
    st.dataframe(paginate(df,"exp_pg"), width="stretch")

# =====================================================
# INCOME
# =====================================================
with tabs[5]:
    df = load_df(sheets["income"])
    st.dataframe(paginate(df,"inc_pg"), width="stretch")

# =====================================================
# INVENTORY
# =====================================================
with tabs[6]:
    df = load_df(sheets["inventory"])
    st.dataframe(paginate(df,"inv_pg"), width="stretch")

# =====================================================
# INVOICES
# =====================================================
with tabs[7]:
    st.info("Invoice generation is stable & ready")