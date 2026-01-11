import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

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
    code_input = st.text_input("Enter 6-digit passcode", type="password", key="login_passcode")
    if st.button("Login", key="login_button"):
        if code_input == st.secrets["APP_PASSCODE"]:
            st.session_state.authenticated = True
            st.session_state.user_role = "admin"
            st.success("✅ Login successful!")
            st.experimental_rerun()
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
def load_data(ws):
    try:
        values = ws.get_all_values()
        if not values:
            return pd.DataFrame()
        df = pd.DataFrame(values[1:], columns=values[0])
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error("❌ Failed to load sheet: " + str(e))
        return pd.DataFrame()

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
    import re
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def paginate_dataframe(df, page_size=10, key_prefix="page"):
    if df.empty:
        return df, 0
    total_pages = (len(df) // page_size) + 1
    page = st.selectbox("Page", range(1, total_pages + 1), key=f"{key_prefix}_{id(df)}")
    start = (page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end], total_pages

# ---------------------------
# HEADER
# ---------------------------
col1, col2 = st.columns([3, 1])
with col1:
    st.title("💧 Lumina Waters Finance")
with col2:
    if st.button("Toggle Theme", key="header_toggle_theme"):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.experimental_rerun()

# ---------------------------
# NAVIGATION
# ---------------------------
tabs = st.tabs([
    "📊 Dashboard", "👥 Customers", "📝 Orders", "💳 Transactions",
    "🧾 Expenses", "💰 Other Income", "📦 Inventory", "⚙️ Settings"
])

# ---------------------------
# DASHBOARD
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
    with col1: st.metric("Total Sales", f"₹ {total_sales:,.0f}")
    with col2: st.metric("Money Received", f"₹ {paid + extra_income:,.0f}")
    with col3: st.metric("Total Expenses", f"₹ {total_expenses:,.0f}")
    with col4: st.metric("Net Balance", f"₹ {net_balance:,.0f}")
    
    if not expenses.empty:
        fig2 = px.pie(expenses, names="Category", values="Amount", title="Expense Breakdown")
        st.plotly_chart(fig2, use_container_width=True)

# ---------------------------
# CUSTOMERS
# ---------------------------
with tabs[1]:
    st.header("👥 Customers")
    customers = load_data(sheets["customers"])
    search = st.text_input("Search by Name", key="search_customers")
    if search:
        customers = customers[customers["Name"].str.contains(search, case=False, na=False)]
    customers_pag,_ = paginate_dataframe(customers)
    st.dataframe(customers_pag, width="stretch")
    
    if st.session_state.user_role=="admin":
        with st.expander("➕ Add Customer"):
            name = st.text_input("Name", key="customer_name_new")
            ctype = st.selectbox("Type", ["Restaurant", "Mall", "Other"], key="customer_type_new")
            contact = st.text_input("Contact", key="customer_contact_new")
            email = st.text_input("Email", key="customer_email_new")
            address = st.text_input("Address", key="customer_address_new")
            vip = st.checkbox("VIP", key="customer_vip_new")
            notes = st.text_area("Notes", key="customer_notes_new")
            if st.button("Save Customer", key="customer_save_btn"):
                if name and validate_email(email):
                    cid = len(customers)+1
                    append_row_safe(sheets["customers"], [cid, name, ctype, contact, email, address, vip, notes])
                    st.success("Customer added!")
                    st.experimental_rerun()
                else:
                    st.error("Invalid email or missing name.")

# ---------------------------
# ORDERS
# ---------------------------
with tabs[2]:
    st.header("📝 Orders")
    customers = load_data(sheets["customers"])
    orders = load_data(sheets["orders"])
    
    orders_pag,_ = paginate_dataframe(orders)
    st.dataframe(orders_pag, width="stretch")
    
    if st.session_state.user_role=="admin" and not customers.empty:
        with st.expander("➕ Add Order"):
            customer = st.selectbox("Customer", customers["Name"], key="order_customer_new")
            order_date = st.date_input("Order Date", datetime.today(), key="order_date_new")
            delivery_date = st.date_input("Delivery Date", datetime.today(), key="order_delivery_new")
            items = st.text_input("Items Ordered", key="order_items_new")
            qty = st.number_input("Quantity", min_value=1, key="order_qty_new")
            price = st.number_input("Price per Item", min_value=0.0, key="order_price_new")
            pay_status = st.selectbox("Payment Status", ["Paid", "Partial", "Unpaid"], key="order_paystatus_new")
            order_status = st.selectbox("Order Status", ["Pending","Delivered","Cancelled"], key="order_status_new")
            notes = st.text_area("Notes", key="order_notes_new")
            if st.button("Save Order", key="order_save_btn"):
                cid = customers[customers["Name"]==customer]["Customer ID"].values[0]
                total = qty*price
                oid = len(orders)+1
                append_row_safe(sheets["orders"], [oid, cid, str(order_date), str(delivery_date), items, qty, price, total, pay_status, order_status, notes])
                st.success("Order added!")
                st.experimental_rerun()

# ---------------------------
# TRANSACTIONS
# ---------------------------
with tabs[3]:
    st.header("💳 Transactions")
    orders = load_data(sheets["orders"])
    transactions = load_data(sheets["transactions"])
    trans_pag,_ = paginate_dataframe(transactions)
    st.dataframe(trans_pag, width="stretch")

    if st.session_state.user_role=="admin" and not orders.empty:
        with st.expander("➕ Add Transaction"):
            oid = st.selectbox("Order ID", orders["Order ID"], key="trans_oid_new")
            date = st.date_input("Date", datetime.today(), key="trans_date_new")
            amount = st.number_input("Amount Paid", min_value=0.0, key="trans_amount_new")
            method = st.selectbox("Payment Method", ["Cash","Bank","Online"], key="trans_method_new")
            notes = st.text_area("Notes", key="trans_notes_new")
            if st.button("Save Transaction", key="trans_save_btn"):
                total = orders[orders["Order ID"]==oid]["Total Amount"].values[0]
                paid_sum = transactions[transactions["Order ID"]==oid]["Amount Paid"].sum() if not transactions.empty else 0
                remaining = total - (paid_sum + amount)
                tid = len(transactions)+1
                append_row_safe(sheets["transactions"], [tid, oid, str(date), amount, method, remaining, notes])
                st.success("Transaction added!")
                st.experimental_rerun()

# ---------------------------
# EXPENSES
# ---------------------------
with tabs[4]:
    st.header("🧾 Expenses")
    expenses = load_data(sheets["expenses"])
    expenses_pag,_ = paginate_dataframe(expenses)
    st.dataframe(expenses_pag, width="stretch")

    if st.session_state.user_role=="admin":
        with st.expander("➕ Add Expense"):
            date = st.date_input("Date", datetime.today(), key="expense_date_new")
            category = st.text_input("Category", key="expense_category_new")
            desc = st.text_input("Description", key="expense_desc_new")
            amount = st.number_input("Amount", min_value=0.0, key="expense_amount_new")
            method = st.selectbox("Payment Method", ["Cash","Bank","Online"], key="expense_method_new")
            notes = st.text_area("Notes", key="expense_notes_new")
            if st.button("Save Expense", key="expense_save_btn"):
                eid = len(expenses)+1
                append_row_safe(sheets["expenses"], [eid, str(date), category, desc, amount, method, notes])
                st.success("Expense added!")
                st.experimental_rerun()

# ---------------------------
# OTHER INCOME
# ---------------------------
with tabs[5]:
    st.header("💰 Other Income")
    income = load_data(sheets["income"])
    income_pag,_ = paginate_dataframe(income)
    st.dataframe(income_pag, width="stretch")

    if st.session_state.user_role=="admin":
        with st.expander("➕ Add Income"):
            date = st.date_input("Date", datetime.today(), key="income_date_new")
            source = st.text_input("Source", key="income_source_new")
            amount = st.number_input("Amount", min_value=0.0, key="income_amount_new")
            method = st.selectbox("Payment Method", ["Cash","Bank","Online"], key="income_method_new")
            notes = st.text_area("Notes", key="income_notes_new")
            if st.button("Save Income", key="income_save_btn"):
                iid = len(income)+1
                append_row_safe(sheets["income"], [iid, str(date), source, amount, method, notes])
                st.success("Income added!")
                st.experimental_rerun()

# ---------------------------
# INVENTORY
# ---------------------------
with tabs[6]:
    st.header("📦 Inventory")
    inventory = load_data(sheets["inventory"])
    inventory_pag,_ = paginate_dataframe(inventory)
    st.dataframe(inventory_pag, width="stretch")

    if st.session_state.user_role=="admin":
        with st.expander("➕ Add Item"):
            item_name = st.text_input("Item Name", key="inventory_name_new")
            qty = st.number_input("Quantity", min_value=0, key="inventory_qty_new")
            unit_price = st.number_input("Unit Price", min_value=0.0, key="inventory_price_new")
            if st.button("Save Item", key="inventory_save_btn"):
                iid = len(inventory)+1
                append_row_safe(sheets["inventory"], [iid, item_name, qty, unit_price])
                st.success("Item added!")
                st.experimental_rerun()

# ---------------------------
# SETTINGS
# ---------------------------
with tabs[7]:
    st.header("⚙️ Settings")
    st.subheader("User Preferences")
    if st.button("Toggle Theme", key="settings_toggle_theme"):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.experimental_rerun()

    st.subheader("Account Management")
    if st.session_state.user_role=="admin":
        st.write("Admin Options:")
        if st.button("Export Customers CSV", key="export_customers"):
            customers = load_data(sheets["customers"])
            csv = customers.to_csv(index=False)
            st.download_button("Download Customers CSV", data=csv, file_name="customers.csv", mime="text/csv")
    
    st.subheader("Feedback")
    feedback = st.text_area("Share your feedback or report issues", key="settings_feedback")
    if st.button("Submit Feedback", key="feedback_submit_btn"):
        st.success("Feedback submitted! Thank you.")