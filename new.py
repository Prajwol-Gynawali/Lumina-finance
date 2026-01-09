import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Lumina Waters Finance", layout="wide", page_icon="💧", initial_sidebar_state="expanded")
st.title("💧 Lumina Waters – Finance Management")
st.caption("Premium Drinking Water • Finance Control System")

# Dark theme customizations
st.markdown(
    """
    <style>
        .stApp {
            background-color: #0E1117;
            color: #F1F1F1;
        }
        .css-1d391kg {color:#F1F1F1;}
        .st-bc {background-color:#161B26;}
        .st-cb {background-color:#161B26;}
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
menu = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Customers",
        "Orders",
        "Transactions",
        "Expenses",
        "Other Income"
    ]
)

# -------------------------------------------------
# GOOGLE SHEETS CONNECTION
# -------------------------------------------------
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
        "income": sh.worksheet("OtherIncome")
    }

try:
    sheets = connect_sheets()
except Exception as e:
    st.error("❌ Google Sheets connection failed")
    st.code(str(e))
    st.stop()

# -------------------------------------------------
# UTILITIES
# -------------------------------------------------
def load_data(ws):
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df.columns = [str(c).strip() for c in df.columns]
    return df

def safe(v):
    if pd.isna(v):
        return ""
    if hasattr(v, "item"):
        return v.item()
    return v

def append_row_safe(ws, values):
    # Convert all to Python native types to avoid JSON serialization errors
    converted = []
    for v in values:
        if isinstance(v, (pd._libs.tslibs.timestamps.Timestamp, pd.Timestamp)):
            converted.append(str(v))
        elif pd.isna(v):
            converted.append("")
        else:
            converted.append(v)
    ws.append_row(converted)

# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------
if menu == "Dashboard":
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

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Sales", f"₹ {total_sales:,.0f}")
    c2.metric("Money Received", f"₹ {paid + extra_income:,.0f}")
    c3.metric("Total Expenses", f"₹ {total_expenses:,.0f}")
    c4.metric("Net Balance", f"₹ {net_balance:,.0f}")

# -------------------------------------------------
# CUSTOMERS
# -------------------------------------------------
elif menu == "Customers":
    st.header("👥 Customers")
    customers = load_data(sheets["customers"])

    with st.expander("➕ Add Customer"):
        with st.form("customer_form"):
            name = st.text_input("Name")
            ctype = st.selectbox("Type", ["Restaurant", "Mall", "Other"])
            contact = st.text_input("Contact")
            email = st.text_input("Email")
            address = st.text_input("Address")
            vip = st.checkbox("VIP")
            notes = st.text_area("Notes")
            submit = st.form_submit_button("Save")

            if submit and name:
                cid = len(customers) + 1
                append_row_safe(sheets["customers"], [int(cid), name, ctype, contact, email, address, vip, notes])
                st.success("Customer added! Please refresh to see the updated list.")


    st.dataframe(customers, use_container_width=True)

# -------------------------------------------------
# ORDERS
# -------------------------------------------------
elif menu == "Orders":
    st.header("📝 Orders")
    customers = load_data(sheets["customers"])
    orders = load_data(sheets["orders"])

    if not customers.empty:
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
                    append_row_safe(sheets["orders"], [int(oid), int(cid), str(order_date), str(delivery_date), items, int(qty), float(price), float(total), pay_status, order_status, notes])
                    st.success("Order added! Please refresh to see the updated list.")

    st.dataframe(orders, use_container_width=True)

# -------------------------------------------------
# TRANSACTIONS
# -------------------------------------------------
elif menu == "Transactions":
    st.header("💳 Transactions")
    orders = load_data(sheets["orders"])
    transactions = load_data(sheets["transactions"])

    if not orders.empty:
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
                    append_row_safe(sheets["transactions"], [int(tid), int(oid), str(date), float(amount), method, float(remaining), notes])
                    st.success("Transaction added! Please refresh to see the updated list.")

    st.dataframe(transactions, use_container_width=True)

# -------------------------------------------------
# EXPENSES
# -------------------------------------------------
elif menu == "Expenses":
    st.header("🧾 Expenses")
    expenses = load_data(sheets["expenses"])

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
                append_row_safe(sheets["expenses"], [int(eid), str(date), category, desc, float(amount), method, notes])
                st.success("Expense added! Please refresh to see the updated list.")

    st.dataframe(expenses, use_container_width=True)

# -------------------------------------------------
# OTHER INCOME
# -------------------------------------------------
elif menu == "Other Income":
    st.header("💰 Other Income")
    income = load_data(sheets["income"])

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
                append_row_safe(sheets["income"], [int(iid), str(date), source, float(amount), method, notes])
                st.success("Income added! Please refresh to see the updated list.")

    st.dataframe(income, use_container_width=True)
