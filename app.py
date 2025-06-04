import streamlit as st
import pandas as pd
import datetime
import os

EXCEL_FILE = "inventory_system.xlsx"

required_sheets = {
    "Stock": ["ItemCode", "Item", "Stock", "Price1", "Price2", "Price3"],
    "Sales": ["Date", "ItemCode", "Qty", "Price", "Total", "InvoiceType", "InvoiceID"],
    "StockUpdate": ["Date", "ItemCode", "Qty", "Type", "BoughtPrice"],
    "Cheques": ["Date", "FutureDate", "ItemCode", "Qty", "Amount", "Claimed"],
    "Expenses": ["Month", "Type", "Amount"],
    "BillToBill": ["Date", "InvoiceID", "Amount", "DueDate", "Paid"],
    "OwingPurchases": ["Date", "InvoiceID", "Amount", "DueDate", "Paid"]
}

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

def ensure_columns(df, required_cols):
    """Make sure DataFrame has all required columns, adding any missing as empty."""
    for col in required_cols:
        if col not in df.columns:
            if col in ["Paid", "Claimed"]:
                df[col] = False
            else:
                df[col] = pd.NA
    return df

def load_sheet(sheet):
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name=sheet)
        df = ensure_columns(df, required_sheets[sheet])
        return df
    except Exception as e:
        st.error(f"Error loading sheet '{sheet}': {e}")
        return pd.DataFrame(columns=required_sheets[sheet])

def save_sheet(df, sheet):
    with pd.ExcelWriter(EXCEL_FILE, mode="a", engine="openpyxl", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name=sheet, index=False)

st.set_page_config(layout="wide")
st.title("Inventory Management System")

cheques_df = load_sheet("Cheques")
owing_df = load_sheet("OwingPurchases")
stock_df = load_sheet("Stock")
sales_df = load_sheet("Sales")
update_df = load_sheet("StockUpdate")
expenses_df = load_sheet("Expenses")
bill_df = load_sheet("BillToBill")

# Calculate reminders
today = datetime.date.today()

def due_soon_alert(df, date_col, bool_col):
    # Check if any rows have unpaid/unclaimed and due date within 3 days
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce').dt.date
    for idx, row in df.iterrows():
        if not row[bool_col] and row[date_col] is not pd.NaT:
            days_left = (row[date_col] - today).days
            if days_left <= 3 and days_left >= 0:
                return True
    return False

cheques_due_soon = due_soon_alert(cheques_df, "FutureDate", "Claimed")
owing_due_soon = due_soon_alert(owing_df, "DueDate", "Paid")

cheques_label = "Cheques" + (" 🔴" if cheques_due_soon else "")
owing_label = "Owing Purchases" + (" 🔴" if owing_due_soon else "")

tabs = st.tabs([
    "Current Stock",
    "Sales & Stock Update",
    cheques_label,
    "Monthly Payments",
    "Bill-to-Bill Invoices",
    owing_label,
    "Dashboard"
])

# Current Stock tab
with tabs[0]:
    st.subheader("Stock Overview")
    def highlight_low_stock(val):
        return ["background-color: red" if v < 10 else "" for v in val] if val.name == "Stock" else ["" for _ in val]

    st.dataframe(stock_df.style.apply(highlight_low_stock, axis=0), use_container_width=True)

# Sales & Stock Update tab
with tabs[1]:
    st.subheader("Add Sale")
    with st.form("sale_form"):
        date = st.date_input("Date", value=today)
        item_code = st.selectbox("Item Code", stock_df["ItemCode"].unique())
        qty = st.number_input("Quantity", min_value=1)
        price_col = st.selectbox("Selling Price Column", ["Price1", "Price2", "Price3"])
        invoice_type = st.selectbox("Invoice Type", ["Cash", "Credit"])
        invoice_id = st.text_input("Invoice ID")
        submitted = st.form_submit_button("Record Sale")

        if submitted:
            item_row = stock_df[stock_df["ItemCode"] == item_code].iloc[0]
            selling_price = item_row[price_col]
            total = qty * selling_price
            sales_df.loc[len(sales_df)] = [date, item_code, qty, selling_price, total, invoice_type, invoice_id]
            update_df.loc[len(update_df)] = [date, item_code, -qty, "Sale", pd.NA]
            stock_df.loc[stock_df["ItemCode"] == item_code, "Stock"] -= qty
            save_sheet(sales_df, "Sales")
            save_sheet(update_df, "StockUpdate")
            save_sheet(stock_df, "Stock")
            st.success("Sale recorded.")

    st.subheader("Update Stock")
    with st.form("stock_update_form"):
        date = st.date_input("Date", value=today, key="stock")
        item_code = st.selectbox("Item Code", stock_df["ItemCode"].unique(), key="stock_item")
        qty = st.number_input("Quantity", min_value=1, key="stock_qty")
        bought_price = st.number_input("Bought Price", min_value=0.0, step=0.01)
        submitted = st.form_submit_button("Update Stock")

        if submitted:
            update_df.loc[len(update_df)] = [date, item_code, qty, "Restock", bought_price]
            stock_df.loc[stock_df["ItemCode"] == item_code, "Stock"] += qty
            save_sheet(update_df, "StockUpdate")
            save_sheet(stock_df, "Stock")
            st.success("Stock updated.")

# Cheques tab
with tabs[2]:
    st.subheader("Cheques")
    with st.expander("Add New Cheque"):
        with st.form("add_cheque"):
            date = st.date_input("Date", value=today, key="chq_date")
            future_date = st.date_input("Future Date", key="future_date")
            item_code = st.selectbox("Item Code", stock_df["ItemCode"].unique(), key="chq_item")
            qty = st.number_input("Quantity", min_value=1, key="chq_qty")
            amount = st.number_input("Amount", min_value=0.0, step=0.01)
            submitted = st.form_submit_button("Add Cheque")
            if submitted:
                cheques_df.loc[len(cheques_df)] = [date, future_date, item_code, qty, amount, False]
                save_sheet(cheques_df, "Cheques")
                st.success("Cheque added.")

    st.subheader("Update Claimed Status")
    for i, row in cheques_df.iterrows():
        checked = st.checkbox(f"Claimed: {row['ItemCode']} on {row['FutureDate']}", value=row["Claimed"], key=f"chq_{i}")
        cheques_df.at[i, "Claimed"] = checked

    if st.button("Save Cheque Updates"):
        save_sheet(cheques_df, "Cheques")
        st.success("Cheque updates saved.")

    st.dataframe(cheques_df)

# Monthly Payments tab
with tabs[3]:
    st.subheader("Monthly Expenses")
    with st.expander("Add New Expense"):
        with st.form("add_expense"):
            month = st.date_input("Month", value=today, key="exp_month")
            expense_type = st.text_input("Type")
            amount = st.number_input("Amount", min_value=0.0, step=0.01)
            submitted = st.form_submit_button("Add Expense")
            if submitted:
                expenses_df.loc[len(expenses_df)] = [month.strftime("%Y-%m"), expense_type, amount]
                save_sheet(expenses_df, "Expenses")
                st.success("Expense added.")
    st.dataframe(expenses_df)

# Bill-to-Bill tab
with tabs[4]:
    st.subheader("Bill-to-Bill Invoices")
    st.dataframe(bill_df[["Date", "InvoiceID", "Amount", "DueDate", "Paid"]])

# Owing Purchases tab
with tabs[5]:
    st.subheader("Owing Purchases")
    st.subheader("Update Paid Status")
    for i, row in owing_df.iterrows():
        checked = st.checkbox(f"Paid: {row['InvoiceID']} due {row['DueDate']}", value=row["Paid"], key=f"own_{i}")
        owing_df.at[i, "Paid"] = checked

    if st.button("Save Owing Updates"):
        save_sheet(owing_df, "OwingPurchases")
        st.success("Owing purchase updates saved.")

    st.dataframe(owing_df[["Date", "InvoiceID", "Amount", "DueDate", "Paid"]])

# Dashboard tab
with tabs[6]:
    st.subheader("Summary Dashboard")
    total_sales = sales_df["Total"].sum()
    total_expense = expenses_df["Amount"].sum()

    selected_price_col = st.selectbox("Select Price Column for Stock Value", ["Price1", "Price2", "Price3"], index=0)
    total_stock_value = (stock_df["Stock"] * stock_df[selected_price_col]).sum()

    profit = 0
    try:
        for idx, sale in sales_df.iterrows():
            item_code = sale["ItemCode"]
            qty_sold = sale["Qty"]
            bought_prices = update_df[(update_df["ItemCode"] == item_code) & (update_df["BoughtPrice"].notnull())]["BoughtPrice"]
            cost_price = bought_prices.mean() if not bought_prices.empty else 0
            profit += qty_sold * (sale["Price"] - cost_price)
    except Exception:
        profit = total_sales - total_expense

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sales", f"Rs {total_sales:,.2f}")
    col2.metric("Total Expenses", f"Rs {total_expense:,.2f}")
    col3.metric("Total Stock Value", f"Rs {total_stock_value:,.2f}")
    col4.metric("Estimated Profit", f"Rs {profit:,.2f}")
