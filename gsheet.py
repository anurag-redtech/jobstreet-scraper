import gspread
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import os.path
import pickle
import pandas as pd
import pytz
import json

TOKEN_PICKLE = 'token.pickle'
SERVICE_ACCOUNT_FILE = 'credentials.json'  # Your service account JSON

# The Google Sheets API scopes required
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")

if creds_json:
    # Running on GitHub Actions
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
else:
    # Running locally
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

client = gspread.authorize(creds)


# Example scraped data
all_jobs_data = {"name": ["Anurag", "Sunil", "Suhas"], "job_profile": ["DA", "DE", "DS"]}
df_new = pd.DataFrame(all_jobs_data)


def job_street_listing_details(df=df_new, code_for="None"):
    
    if code_for == "job_listing_details":
        worksheet = sheet.worksheet("JobStreet")
    else: 
        worksheet = sheet.worksheet("JobStreet:Candidates")

    # Add IST timestamp column
    ist = pytz.timezone('Asia/Kolkata')
    timestamp = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')
    df['Scrape_Timestamp_IST'] = timestamp

    # Get existing data
    existing_df = get_as_dataframe(worksheet, evaluate_formulas=True, header=0)
    existing_df = existing_df.dropna(how='all')

    # Append new rows
    updated_df = pd.concat([existing_df, df], ignore_index=True)

    # Write back the updated DataFrame to the worksheet
    set_with_dataframe(worksheet, updated_df)  # <-- pass worksheet, not sheet
