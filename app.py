import streamlit as st
import pandas as pd
import os
import openpyxl

# Load Excel
FILE_PATH = "C:\\Users\\Malavi\\Desktop\\inventery\\Inventry.xlsx"

@st.cache_data
def load_inventory():
    if os.path.exists(FILE_PATH):
        return pd.read_excel(FILE_PATH)
    else:
        return pd.DataFrame(columns=["Product", "Stock", "Price"])

def save_inventory(df):
    df.to_excel(FILE_PATH, index=False)

st.title("📦 Inventory Management System")

inventory_df = load_inventory()

# Show Inventory
st.subheader("📋 Current Inventory")
st.dataframe(inventory_df)

# --- Record Sale ---
st.subheader("🛒 Record Daily Sale")

product_list = inventory_df["Product"].tolist()
selected_product = st.selectbox("Select Product", product_list)

quantity = st.number_input("Quantity Sold", min_value=1, step=1)

if st.button("Record Sale"):
    idx = inventory_df[inventory_df["Product"] == selected_product].index[0]
    
    if inventory_df.at[idx, "Stock"] >= quantity:
        inventory_df.at[idx, "Stock"] -= quantity
        save_inventory(inventory_df)
        st.success(f"Recorded sale: {quantity} x {selected_product}")
    else:
        st.error("Not enough stock!")

# --- Add/Update Stock ---
st.subheader("➕ Add / Update Stock")

new_product = st.text_input("Product Name")
new_stock = st.number_input("Stock Quantity", min_value=0, step=1)
new_price = st.number_input("Price", min_value=0.0, step=0.1)

if st.button("Add/Update Product"):
    if new_product:
        if new_product in inventory_df["Product"].values:
            # Update
            idx = inventory_df[inventory_df["Product"] == new_product].index[0]
            inventory_df.at[idx, "Stock"] += new_stock
            inventory_df.at[idx, "Price"] = new_price
        else:
            # Add
            inventory_df = inventory_df.append({"Product": new_product, "Stock": new_stock, "Price": new_price}, ignore_index=True)
        
        save_inventory(inventory_df)
        st.success(f"{new_product} added/updated successfully.")
    else:
        st.error("Product name cannot be empty.")
