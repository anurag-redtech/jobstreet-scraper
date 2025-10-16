import pandas as pd
import re 
import csv

def normalize_indonesian_phone(phone):
    """
    Normalize an Indonesian phone number to the format 628XXXXXXXXX.
    Returns empty string for missing or invalid numbers.
    """
    if pd.isna(phone):
        return ""
    
    phone = str(phone)  # Ensure it's a string
    # Remove all non-digit characters
    phone = re.sub(r"[^\d]", "", phone)
    
    # Skip empty strings
    if not phone:
        return ""
    
    # Convert leading 0 to 62
    if phone.startswith("0"):
        phone = "62" + phone[1:]
    
    return phone


# ✅ Read CSV correctly
df_candidates = pd.read_csv("jobstreet_candidates.csv")

# Apply phone normalization
df_candidates["Phone"] = df_candidates["Phone"].apply(normalize_indonesian_phone)

print(df_candidates["Phone"])
