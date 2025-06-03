import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder

# Load or create Excel file
EXCEL_FILE = "inventory_system.xlsx"

required_sheets = {
    "Stock": ["ItemCode", "Item", "Stock", "Price1", "Price2", "Price3"],
    "Sales": ["Date", "ItemCode", "Qty", "Price", "Total", "InvoiceType"],
    "StockUpdate": ["Date", "ItemCode", "Qty", "Type", "BoughtPrice"],
    "Cheques": ["Date", "FutureDate", "ItemCode", "Qty", "Amount", "Claimed"],
    "Expenses": ["Month", "Type", "Amount"],
    "BillToBill": ["Date", "ItemCode", "Qty", "Amount", "DueDate", "Paid"],
    "OwingPurchases": ["Date", "ItemCode", "Qty", "Amount", "DueDate", "Paid"]
}

# Initialize Excel file if not exists
if not os.path.exists(EXCEL_FILE):
    with pd.ExcelWriter(EXCEL_FILE) as writer:
        for sheet, cols in required_sheets.items():
            pd.DataFrame(columns=cols).to_excel(writer, sheet_name=sheet, index=False)
else:
    existing_sheets = pd.ExcelFile(EXCEL_FILE).sheet_names
    with pd.ExcelWriter(EXCEL_FILE, mode="a", engine="openpyxl", if_sheet_exists="overlay") as writer:
        for sheet, cols in required_sheets.items():
            if sheet not in existing_sheets:
                pd.DataFrame(columns=cols).to_excel(writer, sheet_name=sheet, index=False)

# Helper functions
@st.cache_data(ttl=60)
def load_sheet(sheet):
    try:
        return pd.read_excel(EXCEL_FILE, sheet_name=sheet)
    except Exception as e:
        st.error(f"Error loading sheet '{sheet}': {e}")
        return pd.DataFrame(columns=required_sheets[sheet])

def save_sheet(df, sheet):
    with pd.ExcelWriter(EXCEL_FILE, mode="a", engine="openpyxl", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name=sheet, index=False)

# UI Configuration
st.set_page_config(layout="wide", page_title="Inventory Management System", page_icon="📊")
st.title("📦 Inventory Management System")

# Custom CSS for better styling
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stAlert {
        border-radius: 10px;
    }
    .st-bb {
        background-color: white;
    }
    .st-at {
        background-color: #f0f2f6;
    }
    .st-ax {
        border-radius: 10px;
        border: 1px solid #e1e4e8;
    }
    .stButton>button {
        border-radius: 8px;
        padding: 0.5rem 1rem;
    }
    .stDateInput, .stNumberInput, .stSelectbox, .stTextInput {
        border-radius: 8px;
    }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    .metric-title {
        font-size: 1rem;
        color: #6c757d;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.5rem;
        color: #343a40;
        font-weight: 700;
    }
    .tab-container {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Load sheets
cheques_df = load_sheet("Cheques")
owing_df = load_sheet("OwingPurchases")
stock_df = load_sheet("Stock")
sales_df = load_sheet("Sales")
update_df = load_sheet("StockUpdate")
expenses_df = load_sheet("Expenses")
bill_df = load_sheet("BillToBill")

# Ensure required columns exist
for col in ["FutureDate", "Claimed"]:
    if col not in cheques_df.columns:
        cheques_df[col] = None if col == "FutureDate" else False
for col in ["DueDate", "Paid"]:
    if col not in owing_df.columns:
        owing_df[col] = None if col == "DueDate" else False

# Calculate reminders
today = datetime.date.today()
cheques_due_soon = any(
    (not claimed) and (pd.to_datetime(future).date() - today).days <= 3
    for future, claimed in zip(cheques_df["FutureDate"].fillna(today), cheques_df["Claimed"].fillna(False))
owing_due_soon = any(
    (not paid) and (pd.to_datetime(due).date() - today).days <= 3
    for due, paid in zip(owing_df["DueDate"].fillna(today), owing_df["Paid"].fillna(False))

# Tab labels with alerts
cheques_label = "💳 Cheques" + (" 🔴" if cheques_due_soon else "")
owing_label = "📝 Owing Purchases" + (" 🔴" if owing_due_soon else "")

tabs = st.tabs([
    "📊 Dashboard",
    "📦 Current Stock",
    "💰 Sales & Stock",
    cheques_label,
    "💸 Monthly Payments",
    "🧾 Bill-to-Bill",
    owing_label
])

# Tab: Dashboard
with tabs[0]:
    st.subheader("📊 Business Overview")
    
    # Create date filters
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=today - datetime.timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", value=today)
    
    # Filter data based on date range
    filtered_sales = sales_df[(pd.to_datetime(sales_df['Date']).dt.date >= start_date) & 
                             (pd.to_datetime(sales_df['Date']).dt.date <= end_date)]
    filtered_expenses = expenses_df[(pd.to_datetime(expenses_df['Month']).dt.date >= start_date) & 
                                  (pd.to_datetime(expenses_df['Month']).dt.date <= end_date)]
    
    # Calculate metrics
    total_sales = filtered_sales["Total"].sum()
    total_expense = filtered_expenses["Amount"].sum()
    profit = total_sales - total_expense
    avg_daily_sales = total_sales / ((end_date - start_date).days + 1)
    
    # Display metrics in cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Sales</div>
            <div class="metric-value">Rs. {total_sales:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Expenses</div>
            <div class="metric-value">Rs. {total_expense:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Profit</div>
            <div class="metric-value">Rs. {profit:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Avg Daily Sales</div>
            <div class="metric-value">Rs. {avg_daily_sales:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Sales Trend Chart
    st.subheader("📈 Sales Trend")
    if not filtered_sales.empty:
        sales_trend = filtered_sales.groupby(pd.to_datetime(filtered_sales['Date']).dt.date)['Total'].sum().reset_index()
        fig = px.line(sales_trend, x="Date", y="Total", 
                     title="Daily Sales Trend",
                     labels={"Total": "Sales Amount (Rs.)", "Date": "Date"})
        fig.update_layout(plot_bgcolor='white', paper_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No sales data available for the selected period.")
    
    # Top Selling Items
    st.subheader("🏆 Top Selling Items")
    if not filtered_sales.empty:
        # Merge with stock data to get item names
        top_items = filtered_sales.merge(stock_df[['ItemCode', 'Item']], on='ItemCode', how='left')
        top_items = top_items.groupby(['ItemCode', 'Item'])['Qty'].sum().nlargest(10).reset_index()
        
        fig = px.bar(top_items, x='Item', y='Qty', 
                     title="Top 10 Items by Quantity Sold",
                     labels={"Qty": "Quantity Sold", "Item": "Product Name"})
        fig.update_layout(plot_bgcolor='white', paper_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No sales data available for the selected period.")
    
    # Monthly Sales Breakdown
    st.subheader("🗓 Monthly Sales Breakdown")
    if not sales_df.empty:
        monthly_sales = sales_df.copy()
        monthly_sales['Month'] = pd.to_datetime(monthly_sales['Date']).dt.to_period('M')
        monthly_sales = monthly_sales.groupby('Month')['Total'].sum().reset_index()
        monthly_sales['Month'] = monthly_sales['Month'].astype(str)
        
        fig = px.bar(monthly_sales, x='Month', y='Total',
                     title="Monthly Sales Comparison",
                     labels={"Total": "Sales Amount (Rs.)", "Month": "Month"})
        fig.update_layout(plot_bgcolor='white', paper_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No sales data available.")