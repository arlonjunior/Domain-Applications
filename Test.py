import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np
import re
from datetime import datetime, timedelta

# For handling month names
import calendar


# ============================================
# 1. DATA LOADING & PREPROCESSING
# ============================================

@st.cache_data
def load_data():
    # Load the dataset. Make sure 'OnlineRetail.xlsx' is in the same folder.
    df = pd.read_excel('C:/Users/arlon/Downloads/OnlineRetail.xlsx')

    # Remove cancelled orders (InvoiceNo that starts with "C")
    df = df[~df["InvoiceNo"].astype(str).str.startswith("C")]

    # Convert InvoiceDate to datetime
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])

    # Calculate TotalPrice for each transaction
    df["TotalPrice"] = df["Quantity"] * df["UnitPrice"]

    # Drop rows missing CustomerID (for customer-based aggregations)
    df = df.dropna(subset=["CustomerID"])

    return df


df = load_data()


# ============================================
# 2. HELPER FUNCTIONS
# ============================================

def parse_month_input(month_input):
    """
    Convert an input (number string or month name) into a month number (1-12).
    Returns None if input is empty or invalid.
    """
    if not month_input:
        return None
    month_input = month_input.strip().lower()
    if month_input.isdigit():
        month_num = int(month_input)
        if 1 <= month_num <= 12:
            return month_num
    else:
        # Check if input matches any month name or abbreviation
        for i in range(1, 13):
            month_name = calendar.month_name[i].lower()
            month_abbr = calendar.month_abbr[i].lower()
            if month_input in [month_name, month_abbr]:
                return i
    return None


# ============================================
# 3. USER INTERFACE: SELECT AGGREGATION FUNCTIONALITY
# ============================================

st.title("Online Retail Sales Aggregator")

st.markdown("This web app retrieves sales aggregation based on your choice:")

agg_options = [
    "Sales per Day",
    "Sales per Month",
    "Sales per Year",
    "Sales per Customer",
    "Sales per Country",
    "Sales per Product/Description Keyword"
]
aggregation = st.selectbox("Select Aggregation Type", agg_options)

# If "Sales per Month", allow an optional filter for a specific month.
if aggregation == "Sales per Month":
    month_input = st.text_input(
        "Optional: Enter a month (number e.g., 3 or name e.g., March) to filter. If left blank, all months will be shown.")
    filter_month = parse_month_input(month_input)
else:
    filter_month = None

# For product aggregation, input a keyword
if aggregation == "Sales per Product/Description Keyword":
    prod_keyword = st.text_input("Enter product description keyword (case insensitive) to filter products.", "")
else:
    prod_keyword = ""

# ============================================
# 4. AGGREGATION & VISUALIZATION
# ============================================

# Make a copy of the dataframe for filtering if needed.
df_filtered = df.copy()

# Depending on the aggregation type, process and display the results.
if aggregation == "Sales per Day":
    # Group by the date (day resolution)
    df_filtered["Day"] = df_filtered["InvoiceDate"].dt.date
    sales_data = df_filtered.groupby("Day", as_index=False)["TotalPrice"].sum()
    fig = px.line(sales_data, x="Day", y="TotalPrice", title="Daily Sales",
                  labels={"TotalPrice": "Sales (£)", "Day": "Date"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sales_data)

elif aggregation == "Sales per Month":
    # Create "Month" and "Year" columns based on InvoiceDate
    df_filtered["Month"] = df_filtered["InvoiceDate"].dt.month
    df_filtered["Year"] = df_filtered["InvoiceDate"].dt.year

    # If the user provided a specific month filter, apply it.
    if filter_month:
        df_filtered = df_filtered[df_filtered["Month"] == filter_month]
        st.info(f"Filtering for Month: {calendar.month_name[filter_month]}")

    # Group by Year and Month to aggregate sales
    sales_data = df_filtered.groupby(["Year", "Month"], as_index=False)["TotalPrice"].sum()

    # Create a human-friendly period label, e.g., "March 2011"
    # sales_data["Period"] = sales_data.apply(lambda row:
    # f"{calendar.month_name[int(row['Month'])]} {row['Year']}", axis=1)
    sales_data["Period"] = sales_data.apply(lambda row: f"{calendar.month_name[int(row['Month'])]} - {int(row['Year'])}", axis=1)

    # Display the results using a bar chart and dataframe
    fig = px.bar(sales_data, x="Period", y="TotalPrice", title="Monthly Sales", labels={"TotalPrice": "Sales (£)"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sales_data)

elif aggregation == "Sales per Year":
    df_filtered["Year"] = df_filtered["InvoiceDate"].dt.year
    sales_data = df_filtered.groupby("Year", as_index=False)["TotalPrice"].sum()
    fig = px.bar(sales_data, x="Year", y="TotalPrice", title="Yearly Sales", labels={"TotalPrice": "Sales (£)"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sales_data)

elif aggregation == "Sales per Customer":
    # Group by CustomerID
    sales_data = df_filtered.groupby("CustomerID", as_index=False)["TotalPrice"].sum().sort_values(by="TotalPrice",
                                                                                                   ascending=False)
    fig = px.bar(sales_data.head(20), x="CustomerID", y="TotalPrice", title="Top 20 Customers by Sales",
                 labels={"TotalPrice": "Sales (£)"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sales_data)

elif aggregation == "Sales per Country":
    # Group by Country
    sales_data = df_filtered.groupby("Country", as_index=False)["TotalPrice"].sum().sort_values(by="TotalPrice",
                                                                                                ascending=False)
    fig = px.bar(sales_data, x="Country", y="TotalPrice", title="Sales by Country", labels={"TotalPrice": "Sales (£)"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sales_data)

elif aggregation == "Sales per Product/Description Keyword":
    # Filter products based on keyword in 'Description' (case-insensitive)
    if prod_keyword:
        df_filtered = df_filtered[df_filtered["Description"].str.contains(prod_keyword, case=False, na=False)]
    sales_data = df_filtered.groupby("Description", as_index=False)["TotalPrice"].sum().sort_values(by="TotalPrice",
                                                                                                    ascending=False)
    fig = px.bar(sales_data.head(20), x="TotalPrice", y="Description", orientation="h",
                 title=f"Top 20 Products by Sales{' matching "' + prod_keyword + '"' if prod_keyword else ''}",
                 labels={"TotalPrice": "Sales (£)", "Description": "Product Description"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sales_data)

else:
    st.write("Please select an aggregation type from the dropdown.")

st.markdown("---")
st.markdown(
    "This app provides various functionalities to aggregate online retail sales by date (day/month/year), customer, "
    "country, and product keywords. Adjust inputs and filters in the sidebar and main panel to explore the data "
    "further.")

