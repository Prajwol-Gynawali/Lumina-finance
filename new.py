"""
Lumina Waters Finance Management System - Enhanced Version
==========================================================
A comprehensive Streamlit application for managing water delivery business finances.
Features: Dashboard, Customers, Orders, Transactions, Expenses, Income, Analytics, and more.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="💧 Lumina Waters | Finance Management",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': '💧 Lumina Waters Finance Management System v2.0',
        'Get Help': None,
        'Report a bug': None
    }
)

# ============================================================================
# CUSTOM CSS STYLING
# ============================================================================
st.markdown("""
<style>
    /* Main App Background */
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 50%, #0d0d2b 100%);
    }

    /* Custom Cards */
    .metric-card {
        background: linear-gradient(145deg, #1e1e3f, #2a2a5e);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }

    /* Metric Values */
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        color: #00d4ff;
    }
    .metric-label {
        font-size: 14px;
        color: #aaa;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Section Headers */
    .section-header {
        background: linear-gradient(90deg, #00d4ff, #0099cc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 32px;
        font-weight: bold;
        margin-bottom: 20px;
    }

    /* Custom Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #00d4ff, #0099cc);
        border: none;
        border-radius: 10px;
        color: white;
        font-weight: bold;
        padding: 10px 25px;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 20px rgba(0, 212, 255, 0.4);
    }

    /* Danger Button */
    .danger-btn > button {
        background: linear-gradient(135deg, #ff4757, #ff3838) !important;
    }
    .danger-btn > button:hover {
        box-shadow: 0 5px 20px rgba(255, 71, 87, 0.4) !important;
    }

    /* Success Button */
    .success-btn > button {
        background: linear-gradient(135deg, #2ed573, #26de81) !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a3e 0%, #0f0f23 100%);
        border-right: 1px solid rgba(255,255,255,0.1);
    }

    /* DataFrames */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
    }

    /* Custom Container */
    .custom-container {
        background: rgba(255,255,255,0.05);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
    }

    /* Status Colors */
    .status-paid { color: #2ed573; font-weight: bold; }
    .status-partial { color: #ffa502; font-weight: bold; }
    .status-unpaid { color: #ff4757; font-weight: bold; }
    .status-pending { color: #ffa502; font-weight: bold; }
    .status-delivered { color: #2ed573; font-weight: bold; }
    .status-cancelled { color: #ff4757; font-weight: bold; }

    /* Search Box */
    .search-box {
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }

    /* Alert Boxes */
    .alert-success {
        background: linear-gradient(135deg, rgba(46, 213, 115, 0.2), rgba(46, 213, 115, 0.1));
        border: 1px solid #2ed573;
        border-radius: 10px;
        padding: 15px;
        color: #2ed573;
    }
    .alert-warning {
        background: linear-gradient(135deg, rgba(255, 165, 2, 0.2), rgba(255, 165, 2, 0.1));
        border: 1px solid #ffa502;
        border-radius: 10px;
        padding: 15px;
        color: #ffa502;
    }
    .alert-error {
        background: linear-gradient(135deg, rgba(255, 71, 87, 0.2), rgba(255, 71, 87, 0.1));
        border: 1px solid #ff4757;
        border-radius: 10px;
        padding: 15px;
        color: #ff4757;
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #00d4ff, #0099cc) !important;
    }

    /* Info Box */
    .info-box {
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.1), rgba(0, 153, 204, 0.05));
        border-left: 4px solid #00d4ff;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Responsive Design */
    @media (max-width: 768px) {
        .metric-value { font-size: 20px; }
        .section-header { font-size: 24px; }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'refresh_trigger' not in st.session_state:
    st.session_state.refresh_trigger = False
if 'action_message' not in st.session_state:
    st.session_state.action_message = None

# ============================================================================
# GOOGLE SHEETS CONNECTION
# ============================================================================
@st.cache_data(ttl=60)
def load_data_cached(ws_name):
    """Load data with caching for better performance"""
    try:
        records = ws.get_all_records()
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error loading {ws_name}: {e}")
        return pd.DataFrame()

def connect_sheets():
    """Establish connection to Google Sheets"""
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

# Initialize connection
try:
    sheets = connect_sheets()
    st.session_state.data_loaded = True
except Exception as e:
    st.error(f"❌ Connection Failed: {e}")
    st.info("Please check your Google Sheets credentials and make sure 'LuminaWatersDB' spreadsheet exists.")
    st.stop()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def append_row_safe(ws, values):
    """Safely append row to worksheet"""
    converted = []
    for v in values:
        if isinstance(v, (pd.Timestamp, pd._libs.tslibs.timestamps.Timestamp)):
            converted.append(str(v))
        elif pd.isna(v):
            converted.append("")
        elif isinstance(v, (bool,)):
            converted.append("Yes" if v else "No")
        else:
            converted.append(v)
    ws.append_row(converted)
    return True

def delete_row_safe(ws, row_num):
    """Delete a specific row (shift up)"""
    ws.delete_row(row_num)
    return True

def get_row_number(df, column, value):
    """Get actual row number in sheet (accounting for header)"""
    try:
        idx = df.index[df[column].astype(str) == str(value)].tolist()
        if idx:
            return idx[0] + 2  # +2 for header row and 0-index
        return None
    except:
        return None

def trigger_refresh():
    """Trigger data refresh across the app"""
    st.session_state.refresh_trigger = True
    st.cache_data.clear()

def show_success(message):
    """Show success notification"""
    st.session_state.action_message = ("success", message)

def show_error(message):
    """Show error notification"""
    st.session_state.action_message = ("error", message)

def export_to_csv(df):
    """Export dataframe to CSV"""
    return df.to_csv(index=False).encode('utf-8')

def export_to_excel(df, sheet_name):
    """Export dataframe to Excel"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

# ============================================================================
# SIDEBAR NAVIGATION
# ============================================================================
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="font-size: 40px; margin: 0;">💧</h1>
        <h2 style="color: #00d4ff; margin: 10px 0;">Lumina Waters</h2>
        <p style="color: #888; font-size: 12px;">Finance Management</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    menu = st.radio(
        "📋 Navigation",
        [
            "🏠 Dashboard",
            "👥 Customers",
            "📝 Orders",
            "💳 Transactions",
            "🧾 Expenses",
            "💰 Other Income",
            "📊 Analytics",
            "⚙️ Settings"
        ]
    )

    st.markdown("---")

    # Quick Stats in Sidebar
    st.markdown("### 📈 Quick Stats")
    try:
        orders = load_data_cached("orders")
        customers = load_data_cached("customers")
        if not orders.empty and "Total Amount" in orders.columns:
            total_sales = orders["Total Amount"].sum()
            st.markdown(f"""
            <div class="custom-container">
                <p style="margin:0; color:#888;">Total Sales</p>
                <p style="margin:0; font-size:24px; color:#00d4ff; font-weight:bold;">₹ {total_sales:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)
        if not customers.empty:
            st.markdown(f"""
            <div class="custom-container">
                <p style="margin:0; color:#888;">Total Customers</p>
                <p style="margin:0; font-size:24px; color:#00d4ff; font-weight:bold;">{len(customers)}</p>
            </div>
            """, unsafe_allow_html=True)
    except:
        pass

    # Connection Status
    st.markdown("---")
    st.markdown("🟢 Connected to Google Sheets")

# ============================================================================
# NOTIFICATION DISPLAY
# ============================================================================
if st.session_state.action_message:
    msg_type, msg_text = st.session_state.action_message
    if msg_type == "success":
        st.markdown(f"""
        <div class="alert-success">
            ✅ {msg_text}
        </div>
        """, unsafe_allow_html=True)
    elif msg_type == "error":
        st.markdown(f"""
        <div class="alert-error">
            ❌ {msg_text}
        </div>
        """, unsafe_allow_html=True)
    st.session_state.action_message = None

# ============================================================================
# MAIN CONTENT AREA
# ============================================================================

# ---------------- DASHBOARD ----------------
if menu == "🏠 Dashboard":
    st.markdown('<h1 class="section-header">📊 Dashboard Overview</h1>', unsafe_allow_html=True)

    # Load all data
    with st.spinner('Loading dashboard data...'):
        customers = load_data_cached("customers")
        orders = load_data_cached("orders")
        transactions = load_data_cached("transactions")
        expenses = load_data_cached("expenses")
        income = load_data_cached("income")

    # Date Range Filter
    col_date1, col_date2, col_date3 = st.columns([2, 2, 1])
    with col_date1:
        start_date = st.date_input("From Date", value=datetime.now().replace(day=1), key="dash_start")
    with col_date2:
        end_date = st.date_input("To Date", value=datetime.now(), key="dash_end")
    with col_date3:
        if st.button("🔄 Refresh"):
            trigger_refresh()
            st.rerun()

    # Filter data by date
    if not orders.empty and "Order Date" in orders.columns:
        orders["Order Date"] = pd.to_datetime(orders["Order Date"], errors='coerce')
        orders = orders[(orders["Order Date"] >= pd.to_datetime(start_date)) &
                       (orders["Order Date"] <= pd.to_datetime(end_date))]

    # Calculate metrics
    total_sales = orders["Total Amount"].sum() if not orders.empty and "Total Amount" in orders.columns else 0
    paid_amount = transactions["Amount Paid"].sum() if not transactions.empty and "Amount Paid" in transactions.columns else 0
    extra_income = income["Amount"].sum() if not income.empty and "Amount" in income.columns else 0
    total_expenses = expenses["Amount"].sum() if not expenses.empty and "Amount" in expenses.columns else 0
    net_balance = paid_amount + extra_income - total_expenses
    pending_amount = total_sales - paid_amount

    # Pending orders count
    pending_orders = len(orders[orders["Payment Status"].isin(["Unpaid", "Partial"])]) if not orders.empty else 0

    st.markdown("---")

    # Metrics Cards
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-label">💰 Total Sales</p>
            <p class="metric-value">₹ {total_sales:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-label">✅ Received</p>
            <p class="metric-value">₹ {paid_amount + extra_income:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-label">⏳ Pending</p>
            <p class="metric-value">₹ {pending_amount:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-label">💸 Expenses</p>
            <p class="metric-value">₹ {total_expenses:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        net_color = "#2ed573" if net_balance >= 0 else "#ff4757"
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-label">📈 Net Balance</p>
            <p class="metric-value" style="color: {net_color};">₹ {net_balance:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Charts Row
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("### 📈 Sales Trend")
        if not orders.empty and "Order Date" in orders.columns and "Total Amount" in orders.columns:
            # Group by date
            sales_by_date = orders.groupby("Order Date")["Total Amount"].sum().reset_index()
            sales_by_date = sales_by_date.sort_values("Order Date")

            if not sales_by_date.empty:
                fig = px.line(
                    sales_by_date,
                    x="Order Date",
                    y="Total Amount",
                    markers=True,
                    line_color="#00d4ff",
                    fill=True,
                    fillcolor="rgba(0, 212, 255, 0.1)"
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#fff",
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No sales data available for selected period")
        else:
            st.info("No orders data available")

    with col_chart2:
        st.markdown("### 🥧 Expense Breakdown")
        if not expenses.empty and "Category" in expenses.columns and "Amount" in expenses.columns:
            expense_by_cat = expenses.groupby("Category")["Amount"].sum().reset_index()
            if not expense_by_cat.empty:
                fig = px.pie(
                    expense_by_cat,
                    values="Amount",
                    names="Category",
                    color_discrete_sequence=px.colors.qualitative.Cyan
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#fff",
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No expense data available")
        else:
            st.info("No expenses data available")

    st.markdown("---")

    # Recent Activity & Alerts
    col_alert, col_recent = st.columns([1, 2])

    with col_alert:
        st.markdown("### 🚨 Alerts")
        if pending_orders > 0:
            st.markdown(f"""
            <div class="alert-warning">
                📋 <b>{pending_orders} orders</b> pending payment
            </div>
            """, unsafe_allow_html=True)

        if not orders.empty:
            today_orders = orders[orders["Order Date"] == pd.to_datetime(datetime.now().date())]
            if not today_orders.empty:
                st.markdown(f"""
                <div class="info-box">
                    📦 <b>{len(today_orders)} new orders</b> placed today
                </div>
                """, unsafe_allow_html=True)

        if not customers.empty:
            vip_customers = customers[customers["VIP"].astype(str).str.lower() == "yes"]
            if not vip_customers.empty:
                st.markdown(f"""
                <div class="info-box">
                    ⭐ <b>{len(vip_customers)} VIP customers</b> to prioritize
                </div>
                """, unsafe_allow_html=True)

    with col_recent:
        st.markdown("### 📋 Recent Orders")
        if not orders.empty and "Order Date" in orders.columns:
            recent_orders = orders.sort_values("Order Date", ascending=False).head(5)
            if not recent_orders.empty:
                st.dataframe(
                    recent_orders[["Order ID", "Customer ID", "Total Amount", "Payment Status", "Order Status", "Order Date"]],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No recent orders")
        else:
            st.info("No orders available")

# ---------------- CUSTOMERS ----------------
elif menu == "👥 Customers":
    st.markdown('<h1 class="section-header">👥 Customer Management</h1>', unsafe_allow_html=True)

    # Load data
    customers = load_data_cached("customers")

    # Search and Filter
    col_search, col_refresh = st.columns([4, 1])
    with col_search:
        search_term = st.text_input("🔍 Search customers by name, contact, or email", placeholder="Type to search...")
    with col_refresh:
        if st.button("🔄 Refresh"):
            trigger_refresh()
            st.rerun()

    # Filter data
    if search_term and not customers.empty:
        customers = customers[
            customers.apply(lambda row: search_term.lower() in str(row).lower(), axis=1)
        ]

    # Display count
    st.markdown(f"**Showing {len(customers)} customers**")

    # Tabs for View/Add/Edit
    tab1, tab2 = st.tabs(["👁️ View Customers", "➕ Add Customer"])

    with tab1:
        if not customers.empty:
            # Column selector
            all_cols = list(customers.columns)
            selected_cols = st.multiselect("Select columns to display", all_cols, default=all_cols[:5])

            # Data display with pagination
            page_size = st.selectbox("Rows per page", [5, 10, 25, 50], index=1)
            page_num = st.number_input("Page", min_value=1, max_value=max(1, (len(customers) + page_size - 1) // page_size), value=1)

            start_idx = (page_num - 1) * page_size
            end_idx = start_idx + page_size

            st.dataframe(customers[selected_cols].iloc[start_idx:end_idx], use_container_width=True, hide_index=True)

            # Edit/Delete Section
            st.markdown("---")
            st.markdown("### ✏️ Edit Customer")
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                edit_id = st.selectbox("Select Customer ID to Edit", customers["Customer ID"].astype(str).tolist() if "Customer ID" in customers.columns else [])
            with col_edit2:
                action = st.selectbox("Action", ["Edit", "Delete"])

            if edit_id:
                customer_data = customers[customers["Customer ID"].astype(str) == str(edit_id)].iloc[0]

                if action == "Edit":
                    with st.form("edit_customer_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            new_name = st.text_input("Name", value=str(customer_data.get("Name", "")))
                            new_type = st.selectbox("Type", ["Restaurant", "Mall", "Other"],
                                                   index=["Restaurant", "Mall", "Other"].index(customer_data.get("Type", "Other")) if customer_data.get("Type") in ["Restaurant", "Mall", "Other"] else 2)
                            new_contact = st.text_input("Contact", value=str(customer_data.get("Contact", "")))
                            new_email = st.text_input("Email", value=str(customer_data.get("Email", "")))
                        with col2:
                            new_address = st.text_input("Address", value=str(customer_data.get("Address", "")))
                            new_vip = st.checkbox("VIP", value=str(customer_data.get("VIP", "")).lower() == "yes")
                            new_notes = st.text_area("Notes", value=str(customer_data.get("Notes", "")))

                        submit_edit = st.form_submit_button("💾 Save Changes")

                        if submit_edit:
                            row_num = get_row_number(customers, "Customer ID", edit_id)
                            if row_num:
                                append_row_safe(sheets["customers"], [int(edit_id), new_name, new_type, new_contact, new_email, new_address, new_vip, new_notes])
                                show_success(f"Customer {edit_id} updated successfully!")
                                trigger_refresh()
                                st.rerun()

                elif action == "Delete":
                    st.markdown('<div class="alert-warning">⚠️ Are you sure you want to delete this customer?</div>', unsafe_allow_html=True)
                    if st.button("🗑️ Delete Customer"):
                        row_num = get_row_number(customers, "Customer ID", edit_id)
                        if row_num:
                            delete_row_safe(sheets["customers"], row_num)
                            show_success(f"Customer {edit_id} deleted successfully!")
                            trigger_refresh()
                            st.rerun()
        else:
            st.info("No customers found")

    with tab2:
        with st.form("add_customer_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Name *", placeholder="Customer name")
                ctype = st.selectbox("Type", ["Restaurant", "Mall", "Other"])
                contact = st.text_input("Contact *", placeholder="Phone number")
                email = st.text_input("Email", placeholder="Email address")
            with col2:
                address = st.text_input("Address", placeholder="Full address")
                vip = st.checkbox("VIP Customer")
                notes = st.text_area("Notes", placeholder="Additional notes...")

            st.markdown("* Required fields")

            submit = st.form_submit_button("💾 Add Customer", use_container_width=True)

            if submit and name and contact:
                cid = len(customers) + 1
                append_row_safe(sheets["customers"], [int(cid), name, ctype, contact, email, address, vip, notes])
                show_success(f"Customer '{name}' added successfully!")
                trigger_refresh()
                st.rerun()



