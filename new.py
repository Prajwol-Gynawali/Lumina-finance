import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
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
# DARK THEME & CSS
# ---------------------------
st.markdown("""
<style>
.stApp {background-color: #0E1117; color: #F1F1F1;}
.css-18e3th9 {background-color: #161B26;}
h1,h2,h3,h4,h5,h6 {color: #F1F1F1;}
.stButton>button {background-color: #1f2a38; color: #F1F1F1; border-radius: 8px; border: 1px solid #2A3342;}
.stButton>button:hover {background-color: #2A3342;}
.stTextInput>div>div>input, .stNumberInput>div>div>input {background-color: #1f2a38; color: #F1F1F1; border:1px solid #2A3342; border-radius:5px;}
.stDataFrame {background-color: #161B26; color: #F1F1F1;}
.card {background-color: #161B26; border:1px solid #2A3342; border-radius:10px; padding:20px; margin:10px 0;}
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
    code_input = st.text_input("Enter 6-digit passcode", type="password")
    if st.button("Login"):
        if code_input == st.secrets["APP_PASSCODE"]:
            st.session_state.authenticated = True
            st.session_state.user_role = "admin"
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

def paginate_dataframe(df, page_size=10, section_name="default"):
    if df.empty:
        return df, 0
    total_pages = (len(df) // page_size) + 1
    key = f"{section_name}_page_{id(df)}"  # unique per section
    page = st.selectbox("Page", range(1, total_pages+1), key=key)
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
    filename = f"invoice_{order_id}.pdf"
    pdf.output(filename)
    return filename

# ---------------------------
# NAVIGATION TABS
# ---------------------------
tabs = st.tabs([
    "📊 Dashboard", "👥 Customers", "📝 Orders", "💳 Transactions",
    "🧾 Expenses", "💰 Other Income", "📦 Inventory", "📄 Invoices", "⚙️ Settings"
])

# ---------------------------
# DASHBOARD (Pie chart only)
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
    
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Sales", f"₹ {total_sales:,.0f}")
    c2.metric("Money Received", f"₹ {paid+extra_income:,.0f}")
    c3.metric("Total Expenses", f"₹ {total_expenses:,.0f}")
    c4.metric("Net Balance", f"₹ {net_balance:,.0f}")
    
    if not expenses.empty:
        fig = px.pie(expenses, names="Category", values="Amount", title="Expense Breakdown")
        st.plotly_chart(fig, use_container_width=True)

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
            name = st.text_input("Name")
            ctype = st.selectbox("Type", ["Restaurant", "Mall", "Other"])
            contact = st.text_input("Contact")
            email = st.text_input("Email")
            address = st.text_input("Address")
            vip = st.checkbox("VIP")
            notes = st.text_area("Notes", key="customer_notes")
            if st.button("Save Customer"):
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
            customer = st.selectbox("Customer", customers["Name"])
            order_date = st.date_input("Order Date", datetime.today())
            delivery_date = st.date_input("Delivery Date")
            items = st.text_input("Items Ordered")
            qty = st.number_input("Quantity", min_value=1)
            price = st.number_input("Price per Item", min_value=0.0)
            pay_status = st.selectbox("Payment Status", ["Paid", "Partial", "Unpaid"])
            order_status = st.selectbox("Order Status", ["Pending","Delivered","Cancelled"])
            notes = st.text_area("Notes", key=f"order_notes_{oid}")
            if st.button("Save Order"):
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
            oid = st.selectbox("Order ID", orders["Order ID"])
            date = st.date_input("Date", datetime.today())
            amount = st.number_input("Amount Paid", min_value=0.0)
            method = st.selectbox("Payment Method", ["Cash","Bank","Online"])
            notes = st.text_area("Notes")
            if st.button("Save Transaction"):
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
            date = st.date_input("Date", datetime.today())
            category = st.text_input("Category")
            desc = st.text_input("Description")
            amount = st.number_input("Amount", min_value=0.0)
            method = st.selectbox("Payment Method", ["Cash","Bank","Online"])
            notes = st.text_area("Notes")
            if st.button("Save Expense"):
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
            date = st.date_input("Date", datetime.today())
            source = st.text_input("Source")
            amount = st.number_input("Amount", min_value=0.0)
            method = st.selectbox("Payment Method", ["Cash","Bank","Online"])
            notes = st.text_area("Notes")
            if st.button("Save Income"):
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
    inv_pag,_ = paginate_dataframe(inventory)
    st.dataframe(inv_pag, width="stretch")

    if st.session_state.user_role=="admin":
        with st.expander("➕ Add Item"):
            item_name = st.text_input("Item Name")
            qty = st.number_input("Quantity", min_value=0)
            unit_price = st.number_input("Unit Price", min_value=0.0)
            if st.button("Save Item"):
                iid = len(inventory)+1
                append_row_safe(sheets["inventory"], [iid, item_name, qty, unit_price])
                st.success("Item added!")
                st.experimental_rerun()

# ---------------------------
# INVOICES
# ---------------------------
with tabs[7]:
    st.header("📄 Invoices")
    orders = load_data(sheets["orders"])
    customers = load_data(sheets["customers"])
    oid_select = st.selectbox("Select Order ID for Invoice", orders["Order ID"] if not orders.empty else [])
    if oid_select and st.button("Generate Invoice"):
        order = orders[orders["Order ID"]==oid_select].iloc[0]
        customer_name = customers[customers["Customer ID"]==order["Customer ID"]]["Name"].values[0]
        pdf_file = generate_invoice(oid_select, customer_name, order["Items Ordered"], order["Total Amount"])
        with open(pdf_file, "rb") as f:
            st.download_button("Download Invoice", data=f, file_name=pdf_file, mime="application/pdf")

# ---------------------------
# SETTINGS
# ---------------------------
with tabs[8]:
    st.header("⚙️ Settings")
    st.subheader("Account")
    if st.session_state.user_role=="admin":
        st.write("Admin can export data:")
        if st.button("Export Customers CSV"):
            customers = load_data(sheets["customers"])
            csv = customers.to_csv(index=False)
            st.download_button("Download Customers CSV", data=csv, file_name="customers.csv", mime="text/csv")