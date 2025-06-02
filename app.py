import streamlit as st
import pandas as pd
import datetime
import os

# Load or create Excel file
EXCEL_FILE = "inventory_system.xlsx"

required_sheets = {
    "Stock": ["ItemCode", "Item", "Stock", "Price1", "Price2", "Price3"],
    "Sales": ["Date", "ItemCode", "Qty", "Price", "Total", "InvoiceType"],
    "StockUpdate": ["Date", "ItemCode", "Qty", "Type", "BoughtPrice"],
    "Cheques": ["Date", "FutureDate", "ItemCode", "Qty", "Amount", "Claimed"],
    "Expenses": ["Month", "Type", "Amount"],
    "BillToBill": ["Date", "ItemCode", "Qty", "Amount", "DueDate", "Paid"]
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

# Helper functions
def load_sheet(sheet):
    return pd.read_excel(EXCEL_FILE, sheet_name=sheet)

def save_sheet(df, sheet):
    with pd.ExcelWriter(EXCEL_FILE, mode="a", engine="openpyxl", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name=sheet, index=False)

# UI Tabs
st.set_page_config(layout="wide")
st.title("Inventory Management System")
tabs = st.tabs(["Current Stock", "Sales & Stock Update", "Cheques", "Monthly Payments", "Dashboard", "Bill-to-Bill Invoices"])

# 1. Current Stock
with tabs[0]:
    stock_df = load_sheet("Stock")
    def highlight_low(val):
        color = "red" if val < 10 else "black"
        return f"color: {color}"
    st.dataframe(stock_df.style.applymap(highlight_low, subset=["Stock"]))

# 2. Sales and Stock Update
with tabs[1]:
    stock_df = load_sheet("Stock")
    st.subheader("Add New Item")
    new_item_code = st.text_input("New Item Code")
    new_item_name = st.text_input("Item Name")
    new_item_stock = st.number_input("Initial Stock", min_value=0)
    new_price1 = st.number_input("Selling Price 1", min_value=0)
    new_price2 = st.number_input("Selling Price 2", min_value=0)
    new_price3 = st.number_input("Selling Price 3", min_value=0)

    if st.button("Add Item"):
        if new_item_code and new_item_name:
            if new_item_code in stock_df["ItemCode"].values:
                st.warning("Item code already exists.")
            else:
                stock_df.loc[len(stock_df)] = [new_item_code, new_item_name, new_item_stock, new_price1, new_price2, new_price3]
                save_sheet(stock_df, "Stock")
                st.success("New item added successfully.")
        else:
            st.warning("Please enter both Item Code and Item Name.")

    subtab = st.radio("Choose Option", ["Sales", "Stock Update"])

    if subtab == "Sales":
        sales_df = load_sheet("Sales")
        stock_df = load_sheet("Stock")
        st.write("Record Sale")
        item_code = st.selectbox("Item Code", stock_df["ItemCode"])
        item_match = stock_df[stock_df.ItemCode == item_code]
        if not item_match.empty:
            item_row = item_match.iloc[0]
            qty = st.number_input("Qty", 1)
            price = st.selectbox("Price", ["Price1", "Price2", "Price3"])
            invoice_type = st.selectbox("Invoice Type", ["Normal", "Bill-to-Bill"])
            use_cheque = st.checkbox("Paid by Cheque")
            future_date = None
            if use_cheque:
                future_date = st.date_input("Future Cheque Date")
            if st.button("Record Sale"):
                total = qty * item_row[price]
                sales_df.loc[len(sales_df)] = [datetime.date.today(), item_code, qty, item_row[price], total, invoice_type]
                save_sheet(sales_df, "Sales")
                stock_df.loc[stock_df.ItemCode == item_code, "Stock"] -= qty
                save_sheet(stock_df, "Stock")
                if use_cheque:
                    chq_df = load_sheet("Cheques")
                    chq_df.loc[len(chq_df)] = [datetime.date.today(), future_date, item_code, qty, total, False]
                    save_sheet(chq_df, "Cheques")
                if invoice_type == "Bill-to-Bill":
                    bill_df = load_sheet("BillToBill")
                    due_date = datetime.date.today() + datetime.timedelta(weeks=2)
                    bill_df.loc[len(bill_df)] = [datetime.date.today(), item_code, qty, total, due_date, False]
                    save_sheet(bill_df, "BillToBill")
                st.success("Sale recorded")
        else:
            st.warning("Selected Item Code not found in stock data.")

    elif subtab == "Stock Update":
        update_df = load_sheet("StockUpdate")
        stock_df = load_sheet("Stock")
        item_code = st.selectbox("Item Code", stock_df["ItemCode"], key="update_item")
        qty = st.number_input("Qty", 1, key="update_qty")
        bought_price = st.number_input("Bought Price per Unit", 0, key="update_price")
        if st.button("Add Stock"):
            stock_df.loc[stock_df.ItemCode == item_code, "Stock"] += qty
            save_sheet(stock_df, "Stock")
            update_df.loc[len(update_df)] = [datetime.date.today(), item_code, qty, "Add", bought_price]
            save_sheet(update_df, "StockUpdate")
            st.success("Stock updated")

# 3. Cheques
with tabs[2]:
    chq_df = load_sheet("Cheques")
    stock_df = load_sheet("Stock")
    st.write("Outstanding Cheques")
    for i, row in chq_df[chq_df.Claimed == False].iterrows():
        item_name = stock_df[stock_df.ItemCode == row['ItemCode']]['Item'].values[0]
        due_text = f" (Due: {row['FutureDate'].date()})" if pd.notnull(row['FutureDate']) else ""
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"{row['Date']} - {item_name} - Qty: {row['Qty']} - Rs. {row['Amount']}{due_text}")
        with col2:
            if st.button("Claim", key=f"claim_{i}"):
                chq_df.at[i, "Claimed"] = True
                save_sheet(chq_df, "Cheques")
                st.success("Cheque Claimed")
    st.write("All Cheques")
    st.dataframe(chq_df)

# 4. Monthly Payments
with tabs[3]:
    exp_df = load_sheet("Expenses")
    st.write("Add Monthly Expense")
    month = st.date_input("Month", value=datetime.date.today()).strftime('%Y-%m')
    exp_type = st.selectbox("Type", ["Salary", "Electricity", "Oil", "Repairs"])
    amt = st.number_input("Amount", 0)
    if st.button("Add Expense"):
        exp_df.loc[len(exp_df)] = [month, exp_type, amt]
        save_sheet(exp_df, "Expenses")
        st.success("Expense added")
    st.dataframe(exp_df)

# 5. Dashboard
with tabs[4]:
    sales_df = load_sheet("Sales")
    exp_df = load_sheet("Expenses")
    stock_df = load_sheet("Stock")
    if not sales_df.empty:
        profit = sales_df.Total.sum() - exp_df.Amount.sum()
        st.metric("Profit / Loss", f"Rs. {profit}")
        st.write("Most Moving Items (Monthly)")
        sales_df["Month"] = pd.to_datetime(sales_df["Date"]).dt.to_period("M")
        monthly_top = sales_df.groupby(["Month", "ItemCode"]).Qty.sum().reset_index()
        monthly_top = monthly_top.merge(stock_df[["ItemCode", "Item"]], on="ItemCode", how="left")
        st.dataframe(monthly_top.sort_values(by="Qty", ascending=False))

        st.write("Most Moving Items (Yearly)")
        sales_df["Year"] = pd.to_datetime(sales_df["Date"]).dt.year
        yearly_top = sales_df.groupby(["Year", "ItemCode"]).Qty.sum().reset_index()
        yearly_top = yearly_top.merge(stock_df[["ItemCode", "Item"]], on="ItemCode", how="left")
        st.dataframe(yearly_top.sort_values(by="Qty", ascending=False))

# 6. Bill-to-Bill Tab
with tabs[5]:
    bill_df = load_sheet("BillToBill")
    stock_df = load_sheet("Stock")
    st.subheader("Bill-to-Bill Invoices")
    for i, row in bill_df.iterrows():
        item_name = stock_df[stock_df.ItemCode == row['ItemCode']]['Item'].values[0]
        is_late = pd.Timestamp.now().date() > pd.to_datetime(row['DueDate']).date()
        row_color = "🔴 Late" if is_late and not row['Paid'] else "✅ Paid" if row['Paid'] else "🟡 Pending"
        col1, col2 = st.columns([5, 1])
        with col1:
            st.write(f"{row['Date']} - {item_name} - Qty: {row['Qty']} - Rs. {row['Amount']} - Due: {row['DueDate'].date()} - {row_color}")
        with col2:
            if not row['Paid'] and st.button("Mark Paid", key=f"paid_{i}"):
                bill_df.at[i, "Paid"] = True
                save_sheet(bill_df, "BillToBill")
                st.success("Invoice marked as paid")
    st.dataframe(bill_df)