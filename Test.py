import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np
import re
from datetime import datetime, timedelta
import calendar


# ---------------------------
# Load and preprocess data
# ---------------------------
@st.cache_data
def load_data():
    df = pd.read_excel("OnlineRetail.xlsx")
    df = df[~df["InvoiceNo"].astype(str).str.startswith("C")]
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["TotalPrice"] = df["Quantity"] * df["UnitPrice"]
    df = df.dropna(subset=["CustomerID"])
    return df


df = load_data()


# ---------------------------
# Helper: Parse Month Names to Numbers (for multi-select)
# ---------------------------
def month_name_to_number(month_name):
    # month_name_to_number converts a valid month name to its number (1-12)
    month_name = month_name.strip().lower()
    for i in range(1, 13):
        if month_name == calendar.month_name[i].lower() or month_name == calendar.month_abbr[i].lower():
            return i
    return None


# ---------------------------
# Helper: Advanced filter for product description (supports AND, OR, NOT)
# ---------------------------
def filter_descriptions(df, query):
    """Filter the dataframe's 'Description' column using the query string with simple boolean operators."""
    # Convert query to uppercase for consistency
    query = query.upper()

    # Split the query into tokens based on operators. This simple approach assumes users
    # separate words and operators with spaces.
    tokens = re.split(r'\s+(AND|OR|NOT)\s+', query)
    tokens = [token.strip() for token in tokens if token.strip()]

    # If there are no operators, use simple search
    if len(tokens) == 1:
        return df[df['Description'].str.upper().str.contains(tokens[0], na=False)]

    # If the query contains 'AND', require all terms to appear.
    if "AND" in tokens:
        keywords = [token for token in tokens if token not in ["AND", "OR", "NOT"]]
        mask = np.ones(len(df), dtype=bool)
        for kw in keywords:
            mask = mask & df['Description'].str.upper().str.contains(kw, na=False)
        return df[mask]

    # If the query contains 'OR', return rows that contain at least one keyword.
    if "OR" in tokens:
        keywords = [token for token in tokens if token not in ["AND", "OR", "NOT"]]
        mask = np.zeros(len(df), dtype=bool)
        for kw in keywords:
            mask = mask | df['Description'].str.upper().str.contains(kw, na=False)
        return df[mask]

    # If the query contains 'NOT', assume the format: <include keywords> NOT <exclude keywords>
    if "NOT" in tokens:
        # For simplicity, split into two parts based on 'NOT'
        parts = query.split("NOT")
        include_part = parts[0].strip()
        exclude_part = parts[1].strip() if len(parts) > 1 else ""
        mask_include = df['Description'].str.upper().str.contains(include_part, na=False)
        mask_exclude = ~df['Description'].str.upper().str.contains(exclude_part, na=False)
        return df[mask_include & mask_exclude]

    # Fallback: return the dataframe unfiltered if no operator is handled
    return df


# ---------------------------
# Streamlit UI
# ---------------------------
st.title("Dashboard: Online Retail Sales")

agg_options = [
    "Sales per Day",
    "Sales per Month",
    "Sales per Year",
    "Sales per Customer",
    "Sales per Country",
    "Sales per Product/Description Keyword"
]
aggregation = st.selectbox("Select Aggregation Type", agg_options)

# ---------------------------
# For Sales per Month: use a multiselect widget for months
# ---------------------------
if aggregation == "Sales per Month":
    available_months = list(calendar.month_name[1:])  # Skip indexing 0, which is empty.
    selected_months = st.multiselect("Select one or more months", options=available_months)
    # Convert selected month names to numbers
    selected_month_numbers = [month_name_to_number(m) for m in selected_months if month_name_to_number(m) is not None]

else:
    selected_month_numbers = None
    selected_years = None

# ---------------------------
# For Sales per Product: allow complex keyword query
# ---------------------------
if aggregation == "Sales per Product/Description Keyword":
    prod_query = st.text_input("Enter product description query (use AND, OR, NOT for combinations)", "")
else:
    prod_query = ""

# ---------------------------
# Filtering and Aggregation Logic
# ---------------------------
df_filtered = df.copy()

if aggregation == "Sales per Day":
    df_filtered["Day"] = df_filtered["InvoiceDate"].dt.date
    sales_data = df_filtered.groupby("Day", as_index=False)["TotalPrice"].sum()
    fig = px.line(sales_data, x="Day", y="TotalPrice", title="Daily Sales",
                  labels={"TotalPrice": "Sales (£)", "Day": "Date"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sales_data)

elif aggregation == "Sales per Month":
    # Create Month & Year columns
    df_filtered["Month"] = df_filtered["InvoiceDate"].dt.month
    df_filtered["Year"] = df_filtered["InvoiceDate"].dt.year
    # If user selected specific months, filter by those
    if selected_month_numbers:
        df_filtered = df_filtered[df_filtered["Month"].isin(selected_month_numbers)]
        st.info(f"Filtering for months: {', '.join(selected_months)}")
    # Group by Year and Month (to account for multiple years)
    sales_data = df_filtered.groupby(["Year", "Month"], as_index=False)["TotalPrice"].sum()
    # Create a period label in the format "Month - Year" (e.g., "December - 2010")
    sales_data["Period"] = sales_data.apply(
        lambda row: f"{calendar.month_name[int(row['Month'])]} - {int(row['Year'])}", axis=1)
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
    sales_data = df_filtered.groupby("CustomerID", as_index=False)["TotalPrice"].sum().sort_values(by="TotalPrice",
                                                                                                   ascending=False)
    fig = px.treemap(sales_data.head(20), path=["CustomerID"], values="TotalPrice",
                     title="Top 20 Customers by Sales",
                     color="TotalPrice",
                     color_continuous_scale="Blues")
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
    # If a product query is provided, apply our advanced filtering
    if prod_query:
        df_filtered = filter_descriptions(df_filtered, prod_query)
        st.info(f"Filtering descriptions with query: {prod_query}")
    sales_data = df_filtered.groupby("Description", as_index=False)["TotalPrice"].sum().sort_values(by="TotalPrice",
                                                                                                    ascending=False)
    fig = px.bar(sales_data.head(20),
                 x="TotalPrice",
                 y="Description",
                 orientation="h",
                 title=f"Top 20 Products by Sales{' matching: ' + prod_query if prod_query else ''}",
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