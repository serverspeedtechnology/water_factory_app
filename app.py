import pandas as pd
import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Agua Mundial Water Factory Tracker", layout="wide")

# 1. Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)


def load_data():
  try:
    df = conn.read(worksheet="Ledger", ttl="0s")
    return df.dropna(how="all")
  except Exception:
    return pd.DataFrame(
        columns=[
            "Date",
            "Opening_Stock",
            "Bags_Produced",
            "Bags_Sold",
            "Closing_Stock",
            "Diesel_Litres",
            "Delivery_Fuel_Cost",
            "Other_Expenses",
            "Total_Revenue",
            "Total_Variable_Costs",
            "Daily_Net_Profit",
            "Upkeep_Drawn",
            "Working_Capital",
            "Capital_Change_Pct",
            "Growth_Rate_Pct",
        ]
    )


st.title("💧 Water Factory Tracker")
ledger_df = load_data()

# --- INPUT FORM (Manual Expenses & Production Input) ---
with st.form("daily_entry"):
  entry_date = st.date_input("Date")

  col1, col2 = st.columns(2)
  with col1:
    opening_stock = st.number_input("Opening Stock (Bags)", value=0, step=1)
    bags_produced = st.number_input("Bags Produced Today", value=200, step=1)
    bags_sold = st.number_input("Bags Sold Today", value=180, step=1)
    selling_price = st.number_input("Selling Price per Bag (₦)", value=350.0)

  with col2:
    # Manual cost inputs
    diesel_litres = st.number_input("Diesel Consumed (Litres)", value=5.0)
    diesel_price_per_litre = st.number_input(
        "Price per Litre of Diesel (₦)", value=2000.0
    )
    delivery_fuel_cost = st.number_input(
        "Delivery Fuel / Transport Cost (₦)", value=1000.0
    )
    other_expenses = st.number_input(
        "Other Expenses (Labor, Sachet Film, etc.) (₦)", value=15000.0
    )
    upkeep_drawn = st.number_input(
        "Family Upkeep Drawn Today (₦)", value=5000.0
    )

  submit = st.form_submit_button("Calculate & Post to Sheet")

if submit:
  # Prevent duplicate submission
  submission_key = f"{entry_date}_{bags_sold}_{other_expenses}"
  if st.session_state.get("last_submission") == submission_key:
    st.warning("This entry has already been submitted!")
    st.stop()
  st.session_state["last_submission"] = submission_key

  # --- AUTOMATED CALCULATION ENGINE ---
  closing_stock = (opening_stock + bags_produced) - bags_sold

  # Total diesel financial cost
  total_diesel_cost = diesel_litres * diesel_price_per_litre

  # Total Variable Cost (TVC) sums up all your manual inputs
  total_variable_costs = (
      total_diesel_cost + delivery_fuel_cost + other_expenses
  )

  # Revenue & Profit
  total_revenue = bags_sold * selling_price
  daily_net_profit = total_revenue - total_variable_costs

  # Get previous working capital (Default to your initial ₦250,000 investment if empty)
  prev_capital = (
      ledger_df.iloc[-1]["Working_Capital"]
      if not ledger_df.empty and "Working_Capital" in ledger_df.columns
      else 250000.0
  )

  # Net Working Capital change (Profit minus upkeep drawn out of the business)
  working_capital = prev_capital + daily_net_profit - upkeep_drawn

  # Percentage changes
  capital_change_pct = (
      ((working_capital - prev_capital) / prev_capital) * 100
      if prev_capital > 0
      else 0.0
  )

  prev_revenue = (
      ledger_df.iloc[-1]["Total_Revenue"]
      if not ledger_df.empty and "Total_Revenue" in ledger_df.columns
      else total_revenue
  )
  growth_rate_pct = (
      ((total_revenue - prev_revenue) / prev_revenue) * 100
      if prev_revenue > 0
      else 0.0
  )

  # --- POST TO GOOGLE APPS SCRIPT WEB APP ---
  # (Replace with your actual deployed Apps Script Web App URL)
  WEB_APP_URL = "https://script.google.com/macros/s/AKfycbweVgthY2HblY8uOaxmMxI8tpNoA_t2lXvS4YjsU-z4lu9qiD5gyYX6uPvHZHZ1BNDXpQ/exec"

  payload = {
      "Date": str(entry_date),
      "Opening_Stock": opening_stock,
      "Bags_Produced": bags_produced,
      "Bags_Sold": bags_sold,
      "Closing_Stock": closing_stock,
      "Diesel_Litres": diesel_litres,
      "Delivery_Fuel_Cost": delivery_fuel_cost,
      "Other_Expenses": other_expenses,
      "Total_Revenue": total_revenue,
      "Total_Variable_Costs": total_variable_costs,
      "Daily_Net_Profit": daily_net_profit,
      "Upkeep_Drawn": upkeep_drawn,
      "Working_Capital": working_capital,
      "Capital_Change_Pct": round(capital_change_pct, 2),
      "Growth_Rate_Pct": round(growth_rate_pct, 2),
  }

  response = requests.post(WEB_APP_URL, json=payload)
  if response.status_code == 200:
    st.success("Successfully calculated and saved to Google Sheets!")
    st.rerun()
  else:
    st.error("Failed to save entry.")

# --- DISPLAY LEDGER ---
st.subheader("📜 Factory Ledger History")
st.dataframe(ledger_df)
