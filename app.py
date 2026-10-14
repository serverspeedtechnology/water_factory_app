import pandas as pd
import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Water Factory Production & Capital Tracker", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)


def load_data():
  try:
    df = conn.read(worksheet="Ledger", ttl="0s")
    df = df.dropna(subset=["Date"])
    return df
  except Exception:
    return pd.DataFrame(
        columns=[
            "Date",
            "Opening_Stock",
            "Bags_Produced",
            "Bags_Sold",
            "Closing_Stock",
            "Total_Revenue",
            "Total_Variable_Costs",
            "Daily_Net_Profit",
            "Upkeep_Drawn",
            "Capital_Injection",
            "Working_Capital",
            "Capital_Change_Pct",
            "Growth_Rate_Pct",
        ]
    )


st.title("💧 Agua Mundial Water Factory Management App")
ledger_df = load_data()

# --- INTELLIGENT BASELINE RECOVERY (Sheet + Session State) ---
if "latest_closing_stock" not in st.session_state:
  if not ledger_df.empty:
    st.session_state["latest_closing_stock"] = float(
        ledger_df.iloc[-1].get("Closing_Stock", 0)
    )
    st.session_state["latest_capital"] = float(
        ledger_df.iloc[-1].get("Working_Capital", 250000.0)
    )
    st.session_state["latest_bags_sold"] = float(
        ledger_df.iloc[-1].get("Bags_Sold", 0)
    )
  else:
    st.session_state["latest_closing_stock"] = 0.0
    st.session_state["latest_capital"] = 250000.0
    st.session_state["latest_bags_sold"] = 0.0

prev_closing_stock = st.session_state["latest_closing_stock"]
prev_capital = st.session_state["latest_capital"]
prev_bags_sold = st.session_state["latest_bags_sold"]

# --- DAILY ENTRY FORM ---
with st.form("factory_daily_form"):
  entry_date = st.date_input("Date")

  col1, col2 = st.columns(2)

  with col1:
    st.subheader("📦 Inventory & Sales")
    # Display current opening stock for user visibility
    st.info(f"Carried-Over Opening Stock: **{int(prev_closing_stock)} bags**")

    bags_produced = st.number_input(
        "Bags Produced Today (0 if no production)", min_value=0, value=0, step=1
    )
    bags_sold = st.number_input(
        "Bags Sold Today (Retail & Bulk)", min_value=0, value=150, step=1
    )
    total_revenue = st.number_input(
        "Total Cash Collected from Sales (₦)", min_value=0.0, value=52500.0
    )

  with col2:
    st.subheader("💸 Cash Outflows & Injections")
    diesel_cost = st.number_input(
        "Diesel Spent Today (₦)", min_value=0.0, value=0.0
    )
    delivery_fuel_cost = st.number_input(
        "Delivery / Transport Fuel (₦)", min_value=0.0, value=1000.0
    )
    other_expenses = st.number_input(
        "Other Expenses (Nylon, Minor Repairs, etc.) (₦)",
        min_value=0.0,
        value=0.0,
    )
    upkeep_drawn = st.number_input(
        "Family Upkeep Drawn (₦)", min_value=0.0, value=5000.0
    )
    capital_injection = st.number_input(
        "External Capital Injection (₦)", min_value=0.0, value=0.0
    )

  submit = st.form_submit_button("💾 Calculate & Save Daily Record")

if submit:
  # Prevent duplicate submissions
  submission_key = f"{entry_date}_{bags_sold}_{total_revenue}"
  if st.session_state.get("last_submission") == submission_key:
    st.warning("This entry has already been submitted!")
    st.stop()
  st.session_state["last_submission"] = submission_key

  # --- CALCULATION ENGINE ---
  opening_stock = prev_closing_stock
  closing_stock = (opening_stock + bags_produced) - bags_sold

  total_variable_costs = diesel_cost + delivery_fuel_cost + other_expenses
  daily_net_profit = total_revenue - total_variable_costs

  net_capital_change = daily_net_profit - upkeep_drawn + capital_injection
  working_capital = prev_capital + net_capital_change

  capital_change_pct = (
      (net_capital_change / prev_capital) * 100 if prev_capital > 0 else 0.0
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
      "Total_Revenue": total_revenue,
      "Total_Variable_Costs": total_variable_costs,
      "Daily_Net_Profit": daily_net_profit,
      "Upkeep_Drawn": upkeep_drawn,
      "Capital_Injection": capital_injection,
      "Working_Capital": working_capital,
      "Capital_Change_Pct": round(capital_change_pct, 2),
      "Growth_Rate_Pct": round(growth_rate_pct, 2),
  }

  response = requests.post(WEB_APP_URL, json=payload)
  if response.status_code == 200:
    # Update session memory instantly so next entry picks it up right away
    st.session_state["latest_closing_stock"] = closing_stock
    st.session_state["latest_capital"] = working_capital
    st.session_state["latest_bags_sold"] = bags_sold

    st.success("Successfully calculated and saved to Google Sheets!")
    st.rerun()
  else:
    st.error("Failed to save entry. Check your Web App URL.")

# --- DISPLAY DASHBOARD METRICS & LEDGER ---
st.divider()
if not ledger_df.empty:
  latest = ledger_df.iloc[-1]
  c1, c2, c3, c4 = st.columns(4)
  c1.metric(
      "Unsold Stock (Closing)",
      f"{int(st.session_state.get('latest_closing_stock', latest['Closing_Stock']))} bags",
  )
  c2.metric(
      "Working Capital Base",
      f"₦{st.session_state.get('latest_capital', latest['Working_Capital']):,.2f}",
  )
  c3.metric("Sales Volume", f"{int(latest['Bags_Sold'])} bags")
  c4.metric("Daily Net Profit", f"₦{latest['Daily_Net_Profit']:,.2f}")

st.subheader("📜 Factory Ledger History")
st.dataframe(ledger_df, use_container_width=True)
