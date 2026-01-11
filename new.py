import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import re

# ───────────────────────────────────────────────
# PAGE CONFIGURATION
# ───────────────────────────────────────────────
st.set_page_config(
    page_title="💧 Lumina Waters Finance",
    layout="wide",
    page_icon="💧",
    initial_sidebar_state="expanded"
)

# ───────────────────────────────────────────────
# DARK THEME (simple version)
# ───────────────────────────────────────────────
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #F1F1F1; }
    .block-container { padding-top: 1rem !important; }
    h1,h2,h3,h4,h5,h6 { color:#E0E0FF; }
    .stButton>button { 
        background-color:#1f2a38; 
        color:#F1F1F1; 
        border-radius:6px; 
        border:1px solid #3a4552;
    }
    .stButton>button:hover { background-color:#2e3b4c; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input { 
        background-color:#1a2230; 
        color:#e0e0ff; 
        border:1px solid #3a4552;
    }
    </style>
""", unsafe_allow_html=True)

# ───────────────────────────────────────────────
# SESSION STATE
# ───────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = "viewer"

# ───────────────────────────────────────────────
# SIMPLE LOGIN
# ───────────────────────────────────────────────
if not st.session_state.authenticated:
    st.title("🔒 Lumina Waters Finance")
    st.markdown("### Enter 6-digit passcode")
    
    code_input = st.text_input("", type="password", max_chars=6, key="passcode_input")
    
    if st.button("Login", use_container_width=True):
        if code_input == st.secrets["APP_PASSCODE"]:
            st.session_state.authenticated = True
            st.session_state.user_role = "admin"
            st.success("Login successful → refreshing...")
            st.rerun()
        else:
            st.error("Incorrect passcode")
    st.stop()

# ───────────────────────────────────────────────
# GOOGLE SHEETS CONNECTION
# ───────────────────────────────────────────────
@st.cache_resource
def get_google_sheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope)
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
    sheets = get_google_sheets()
except Exception as e:
    st.error("Cannot connect to Google Sheets")
    st.exception(e)
    st.stop()

# ───────────────────────────────────────────────
# HELPER FUNCTIONS
# ───────────────────────────────────────────────
def load_data(ws):
    try:
        data = ws.get_all_values()
        if len(data) <= 1:
            return pd.DataFrame()
        df = pd.DataFrame(data[1:], columns=[c.strip() for c in data[0]])
        return df
    except Exception as e:
        st.error(f"Failed to load sheet: {str(e)}")
        return pd.DataFrame()

def get_next_id(worksheet):
    try:
        ids = worksheet.col_values(1)[1:]  # skip header
        numeric = [int(x) for x in ids if x.strip().isdigit()]
        return max(numeric) + 1 if numeric else 1
    except:
        return 1

def append_row_safe(ws, values):
    clean_values = []
    for v in values:
        if pd.isna(v):
            clean_values.append("")
        elif isinstance(v, (pd.Timestamp, datetime)):
            clean_values.append(v.strftime("%Y-%m-%d"))
        else:
            clean_values.append(str(v))
    ws.append_row(clean_values)

def is_valid_email(email):
    if not email:
        return True
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, str(email)))

# ───────────────────────────────────────────────
# HEADER & NAVIGATION
# ───────────────────────────────────────────────
st.title("💧 Lumina Waters Finance")

tabs = st.tabs([
    "Dashboard", "Customers", "Orders", "Transactions",
    "Expenses", "Other Income", "Inventory"
])

# ───────────────────────────────────────────────
# DASHBOARD
# ───────────────────────────────────────────────
with tabs[0]:
    st.subheader("Financial Overview")
    
    orders = load_data(sheets["orders"])
    trans = load_data(sheets["transactions"])
    expenses = load_data(sheets["expenses"])
    other_income = load_data(sheets["income"])
    
    total_sales = pd.to_numeric(orders.get("Total Amount", pd.Series()), errors='coerce').sum()
    received = pd.to_numeric(trans.get("Amount Paid", pd.Series()), errors='coerce').sum()
    extra = pd.to_numeric(other_income.get("Amount", pd.Series()), errors='coerce').sum()
    total_exp = pd.to_numeric(expenses.get("Amount", pd.Series()), errors='coerce').sum()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sales", f"₹ {total_sales:,.0f}")
    col2.metric("Received", f"₹ {received + extra:,.0f}")
    col3.metric("Expenses", f"₹ {total_exp:,.0f}", delta_color="inverse")
    col4.metric("Net Balance", f"₹ {(received + extra - total_exp):,.0f}")
    
    if not expenses.empty:
        fig = px.pie(expenses, names="Category", values="Amount",
                     title="Expense Distribution",
                     hole=0.38,
                     color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig, use_container_width=True)

# ───────────────────────────────────────────────
# CUSTOMERS
# ───────────────────────────────────────────────
with tabs[1]:
    st.subheader("Customers")
    customers = load_data(sheets["customers"])
    
    search = st.text_input("Search name / contact / email", "").strip()
    if search:
        mask = (
            customers["Name"].str.contains(search, case=False, na=False) |
            customers.get("Contact","").str.contains(search, na=False) |
            customers.get("Email","").str.contains(search, case=False, na=False)
        )
        customers = customers[mask]
    
    st.dataframe(customers, use_container_width=True, hide_index=True)
    
    if st.session_state.user_role == "admin":
        with st.expander("➕ Add New Customer"):
            with st.form("new_customer_form"):
                col1, col2 = st.columns([5,3])
                with col1: name = st.text_input("Full Name *")
                with col2: ctype = st.selectbox("Type", ["Restaurant","Hotel","Mall","Office","Other"])
                
                col3, col4 = st.columns(2)
                with col3: contact = st.text_input("Phone / WhatsApp")
                with col4: email = st.text_input("Email")
                
                address = st.text_input("Address")
                vip = st.checkbox("VIP Customer")
                notes = st.text_area("Notes", height=80)
                
                submitted = st.form_submit_button("Save Customer")
                
                if submitted:
                    if not name.strip():
                        st.error("Name is required")
                    elif email and not is_valid_email(email):
                        st.error("Invalid email format")
                    else:
                        new_id = get_next_id(sheets["customers"])
                        row = [new_id, name.strip(), ctype, contact, email, address, "Yes" if vip else "", notes]
                        append_row_safe(sheets["customers"], row)
                        st.success(f"Customer added → ID: {new_id}")
                        st.rerun()

# ───────────────────────────────────────────────
# ORDERS (simplified version - you can expand later)
# ───────────────────────────────────────────────
with tabs[2]:
    st.subheader("Orders")
    orders = load_data(sheets["orders"])
    st.dataframe(orders, use_container_width=True, hide_index=True)

    customers = load_data(sheets["customers"])
    
    if st.session_state.user_role == "admin" and not customers.empty:
        with st.expander("➕ New Order"):
            with st.form("new_order_form"):
                customer_choice = st.selectbox(
                    "Customer",
                    options=customers["Name"].tolist(),
                    format_func=lambda x: x
                )
                
                col1, col2 = st.columns(2)
                with col1: order_date = st.date_input("Order Date", datetime.today())
                with col2: delivery_date = st.date_input("Delivery Date", datetime.today())
                
                items = st.text_input("Items / Description")
                col3, col4 = st.columns(2)
                with col3: quantity = st.number_input("Quantity", min_value=1, step=1)
                with col4: unit_price = st.number_input("Price per unit (₹)", min_value=0.0, step=1.0)
                
                payment_status = st.selectbox("Payment Status", ["Unpaid","Partial","Paid"])
                order_status = st.selectbox("Order Status", ["Pending","Delivered","Cancelled"])
                notes = st.text_area("Notes", height=70)
                
                if st.form_submit_button("Create Order"):
                    if not items.strip():
                        st.error("Please enter items description")
                    else:
                        try:
                            cid = customers[customers["Name"] == customer_choice]["Customer ID"].iloc[0]
                        except:
                            cid = "?"
                        
                        total = quantity * unit_price
                        new_oid = get_next_id(sheets["orders"])
                        
                        row = [
                            new_oid, cid, str(order_date), str(delivery_date),
                            items, quantity, unit_price, total,
                            payment_status, order_status, notes
                        ]
                        append_row_safe(sheets["orders"], row)
                        st.success(f"Order #{new_oid} created")
                        st.rerun()

# You can continue implementing Transactions, Expenses, Income, Inventory
# in similar pattern using forms + get_next_id() + append_row_safe()

st.caption("Lumina Waters Finance • v0.8 • January 2025")