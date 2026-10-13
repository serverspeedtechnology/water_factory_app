import pandas as pd
import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Water Factory Tracker", layout="wide")

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


st.title("💧 Water Factory Production & Capital Tracker")
ledger_df = load_data()

# Fetch previous day closing stock and capital
if not ledger_df.empty:
  prev_row = ledger_df.iloc[-1]
  prev_closing_stock = float(prev_row.get("Closing_Stock", 0))
  prev_capital = float(prev_row.get("Working_Capital", 250000.0))
  prev_bags_sold = float(prev_row.get("Bags_Sold", 0))
else:
  prev_closing_stock = 0.0
  prev_capital = 250000.0
  prev_bags_sold = 0.0

# --- FORM INPUTS (Actual Daily Operational Spending) ---
with st.form("daily_tracker_form"):
  col1, col2 = st.columns(2)

  with col1:
    entry_date = st.date_input("Date")
    bags_produced = st.number_input(
        "Bags Produced Today", min_value=0, value=200
    )
    bags_sold = st.number_input("Bags Sold Today", min_value=0, value=180)
    selling_price = st.number_input("Selling Price per Bag (₦)", value=350.0)

  with col2:
    diesel_cost = st.number_input(
        "Diesel Bought/Spent Today (₦)", min_value=0.0, value=0.0
    )
    delivery_fuel_cost = st.number_input(
        "Delivery Fuel Spent Today (₦)", min_value=0.0, value=1000.0
    )
    other_expenses = st.number_input(
        "Other Expenses Today (Nylon, Labor, etc.) (₦)",
        min_value=0.0,
        value=0.0,
    )
    upkeep_drawn = st.number_input(
        "Family Upkeep Drawn Today (₦)", min_value=0.0, value=5000.0
    )

  submit = st.form_submit_button("💾 Save Daily Record")

if submit:
  # Prevent duplicate submissions
  submission_key = f"{entry_date}_{bags_sold}_{diesel_cost}_{other_expenses}"
  if st.session_state.get("last_submission") == submission_key:
    st.warning("This entry has already been submitted!")
    st.stop()
  st.session_state["last_submission"] = submission_key

  # --- CALCULATIONS ---
  opening_stock = prev_closing_stock
  closing_stock = (opening_stock + bags_produced) - bags_sold

  total_revenue = bags_sold * selling_price

  # TVC is the sum of whatever actual cash expenses you incurred today
  total_variable_costs = diesel_cost + delivery_fuel_cost + other_expenses

  daily_net_profit = total_revenue - total_variable_costs
  working_capital = prev_capital + daily_net_profit - upkeep_drawn

  capital_change_pct = (
      ((working_capital - prev_capital) / prev_capital) * 100
      if prev_capital > 0
      else 0.0
  )
  growth_rate_pct = (
      ((bags_sold - prev_bags_sold) / prev_bags_sold) * 100
      if prev_bags_sold > 0
      else 0.0
  )

  # --- POST TO GOOGLE APPS SCRIPT WEB APP ---
  WEB_APP_URL = "https://script.google.com/macros/s/AKfycbweVgthY2HblY8uOaxmMxI8tpNoA_t2lXvS4YjsU-z4lu9qiD5gyYX6uPvHZHZ1BNDXpQ/exec"

  payload = {
      "Date": str(entry_date),
      "Opening_Stock": opening_stock,
      "Bags_Produced": bags_produced,
      "Bags_Sold": bags_sold,
      "Closing_Stock": closing_stock,
      "Diesel_Litres": 0,  # Or pass diesel cost directly if your sheet tracks currency instead of liters
      "Delivery_Fuel_Cost": delivery_fuel_cost,
      "Other_Expenses": diesel_cost + other_expenses,  # Combined cash outflow
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
    st.success("Successfully recorded to Google Sheets!")
    st.rerun()
  else:
    st.error("Failed to save entry.")

# --- DISPLAY LEDGER ---
st.subheader("📜 Factory Ledger History")
st.dataframe(ledger_df, use_container_width=True)
