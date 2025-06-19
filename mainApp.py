import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np
import re
import calendar
from datetime import datetime, timedelta


# Load and preprocess the dataset
@st.cache_data
def load_data():
    df = pd.read_excel('C:/Users/arlon/Downloads/OnlineRetail.xlsx')
    df = df[~df['InvoiceNo'].astype(str).str.startswith('C')]
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['TotalPrice'] = df['Quantity'] * df['UnitPrice']
    return df



df = load_data()

# Set up the dashboard UI
st.title("Online Retail Business Dashboard")
st.markdown("This dashboard demonstrates a basic natural language query interface for online retail data analysis.")

# Get natural language query
query = st.text_input("Enter your query (e.g., 'Show me last month's sales in UK'):")

if query:
    st.markdown("### Processing Your Query")
    date_filter = None
    country_filter = None

    # Country filter extraction
    country_pattern = re.search(r"in (\w+)", query, re.IGNORECASE)
    if country_pattern:
        country_filter = country_pattern.group(1)
        st.write(f"Detected Country Filter: **{country_filter}**")

    # Date filter extraction for "last month"
    if "last month" in query.lower():
        max_date = df['InvoiceDate'].max()
        first_day_current_month = datetime(max_date.year, max_date.month, 1)
        last_month_end = first_day_current_month - timedelta(days=1)
        last_month_start = datetime(last_month_end.year, last_month_end.month, 1)
        date_filter = (last_month_start, last_month_end)
        st.write(f"Detected Date Filter: **{last_month_start.date()}** to **{last_month_end.date()}** (Last Month)")

    # Apply filters
    df_filtered = df.copy()
    if country_filter:
        df_filtered = df_filtered[df_filtered['Country'].str.lower() == country_filter.lower()]
    if date_filter:
        start_date, end_date = date_filter
        df_filtered = df_filtered[(df_filtered['InvoiceDate'] >= start_date) & (df_filtered['InvoiceDate'] <= end_date)]

    # Compute key metrics
    total_sales = df_filtered['TotalPrice'].sum()
    total_transactions = df_filtered['InvoiceNo'].nunique()
    avg_transaction = total_sales / total_transactions if total_transactions > 0 else 0

    st.markdown("### Summary Metrics")
    st.write(f"**Total Sales:** £{total_sales:,.2f}")
    st.write(f"**Total Transactions:** {total_transactions:,}")
    st.write(f"**Average Transaction Value:** £{avg_transaction:,.2f}")

    # Daily sales trend visualization
    st.markdown("### Daily Sales Trend")
    df_filtered['Day'] = df_filtered['InvoiceDate'].dt.date
    daily_sales = df_filtered.groupby('Day')['TotalPrice'].sum().reset_index()
    fig = px.line(daily_sales, x='Day', y='TotalPrice', title="Daily Sales Trend",
                  labels={"TotalPrice": "Sales (£)", "Day": "Date"})
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Sample of Filtered Data")
    st.dataframe(df_filtered.head())
else:
    st.markdown("### No Query Entered")
    st.write("Please enter a query at the top (e.g., 'Show me last month's sales in UK') to see the dashboard.")
