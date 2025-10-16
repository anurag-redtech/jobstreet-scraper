import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import os.path
import pickle
import pandas as pd
import pytz

TOKEN_PICKLE = 'token.pickle'
CREDENTIALS_FILE = 'credentials.json'  # Make sure to set your credentials file path

# The Google Sheets API scopes required
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_gspread_client():
    creds = None
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PICKLE, 'wb') as token:
            pickle.dump(creds, token)

    client = gspread.authorize(creds)
    return client

# Connect to Google Sheets
client = get_gspread_client()
sheet = client.open_by_key("1Ga57xJYX5AstCeBNCrfxNwdT4sriXAp6LB95fZzed64")


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

    # print(f"\n{'=' * 50}")
    # print("SCRAPING COMPLETED!")
    # print(f"Total jobs scraped in this run: {len(all_jobs_data['name'])}")
    # print(f"Total rows in Google Sheet now: {len(updated_df)}")
    # print("Data appended to Google Sheet: JobStreet Listings")
