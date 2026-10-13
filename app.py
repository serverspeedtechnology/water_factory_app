import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Water Factory Tracker", layout="wide")

# 1. Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)


# 2. Helper function to load latest sheet data
def load_data():
  try:
    df = conn.read(worksheet="Ledger", ttl="0s")
    return df.dropna(how="all")
  except Exception:
    return pd.DataFrame(
        columns=[
            "Date",
            "Bags_Sold",
            "Revenue",
            "Var_Costs",
            "Gross_Margin",
            "Upkeep_Drawn",
            "Loan_Payment",
            "Interest_Accrued",
            "Loan_Balance",
            "Working_Capital",
        ]
    )


st.title("💧 Water Factory Tracker")

# Load existing ledger from Google Sheets
ledger_df = load_data()

# --- INPUT FORM ---
with st.form("daily_entry"):
  entry_date = st.date_input("Date")
  bags_sold = st.number_input("Bags Sold", value=200)
  selling_price = st.number_input("Selling Price (₦)", value=350.0)
  var_costs = st.number_input("Total Variable Costs (₦)", value=25000.0)
  upkeep_drawn = st.number_input("Upkeep Drawn (₦)", value=10000.0)
  loan_payment = st.number_input("Loan Payment (₦)", value=12000.0)

  submit = st.form_submit_button("Submit Entry")

if submit:
  total_revenue = bags_sold * selling_price
  gross_margin = total_revenue - var_costs

  # Calculate running totals from previous row
  prev_loan = ledger_df.iloc[-1]["Loan_Balance"] if not ledger_df.empty else 500000.0
  prev_cap = ledger_df.iloc[-1]["Working_Capital"] if not ledger_df.empty else 250000.0

  interest_today = prev_loan * 0.0018
  new_loan = max(0.0, prev_loan + interest_today - loan_payment)
  new_cap = prev_cap + (gross_margin - upkeep_drawn - 333.33 - loan_payment)

  # Create new row
  new_row = pd.DataFrame([{
      "Date": str(entry_date),
      "Bags_Sold": bags_sold,
      "Revenue": total_revenue,
      "Var_Costs": var_costs,
      "Gross_Margin": gross_margin,
      "Upkeep_Drawn": upkeep_drawn,
      "Loan_Payment": loan_payment,
      "Interest_Accrued": interest_today,
      "Loan_Balance": new_loan,
      "Working_Capital": new_cap,
  }])
import requests

  # Paste your deployed Google Apps Script Web App URL here
  WEB_APP_URL = "https://script.google.com/macros/s/AKfycbweVgthY2HblY8uOaxmMxI8tpNoA_t2lXvS4YjsU-z4lu9qiD5gyYX6uPvHZHZ1BNDXpQ/exec"

  payload = {
      "Date": str(entry_date),
      "Bags_Sold": bags_sold,
      "Revenue": total_revenue,
      "Var_Costs": var_costs,
      "Gross_Margin": gross_margin,
      "Upkeep_Drawn": upkeep_drawn,
      "Loan_Payment": loan_payment,
      "Interest_Accrued": interest_today,
      "Loan_Balance": new_loan,
      "Working_Capital": new_cap,
  }

  response = requests.post(WEB_APP_URL, json=payload)
  st.success("Successfully saved to Google Sheets!")
  st.rerun()

# --- DISPLAY DATA ---
st.subheader("📜 Recent Records")
st.dataframe(load_data())
