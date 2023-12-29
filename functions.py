import sqlite3
import requests
from twilio.rest import Client
import os
from dotenv import load_dotenv

import re
load_dotenv()


# Twilio setup
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


# Function to Strip the Budget to only numbers
def normalize_budget(budget):
    numeric_budget = re.sub(r'[^0-9.]', '', budget)
    try:
        return float(numeric_budget)
    except ValueError:
        return None

# Function to query the database
def query_real_estate(bedrooms, location, budget):
    result_str = ""

    # Normalize and validate budget
    budget_number = normalize_budget(budget)
    if budget_number is None:
        return "Invalid budget format. Please enter a numeric value for the budget."

    try:
        conn = sqlite3.connect('real_estate.db')
        cursor = conn.cursor()

        # Use SQL LIKE for matching
        query = 'SELECT * FROM properties WHERE CAST(REPLACE(REPLACE(Price, "$", ""), ",", "") AS REAL) <= ?'
        params = [budget_number]

        if bedrooms.lower() != 'any':
            query += ' AND LOWER(Bedrooms) LIKE ?'
            params.append('%' + bedrooms.lower() + '%')

        if location.lower() != 'any':
            query += ' AND LOWER(Address) LIKE ?'
            params.append('%' + location.lower() + '%')

        cursor.execute(query, params)
        rows = cursor.fetchall()

        if not rows:
            result_str = "No properties found matching the criteria."
        else:
            for row in rows:
                result_str += f"Position: {row[0]}, Price: {row[1]}, Bedrooms: {row[2]}, Bathroom: {row[3]}, Area (sqft): {row[4]}, Description: {row[5]}, Address: {row[6]}, Other info: {row[7]}, Image: {row[8]}, Detail link: {row[9]}\n\n"

    except sqlite3.Error as e:
        result_str = f"An error occurred while accessing the database: {e}"
    finally:
        conn.close()

    return result_str

# Function to send contact info to Make and Google Sheets
def store_contact_info_on_make_webhook(email, phone, additional_info):
    
    webhook_url = "https://hook.make.com/your_unique_webhook"

    # Payload
    data = {
        "email": email,
        "phone": phone,
        "additional_info": additional_info
    }

    # Send a POST request to the Make Webhook
    try:
        response = requests.post(webhook_url, json=data)
        response.raise_for_status() 
        return "Data successfully sent to Make and Google Sheets."
    except requests.RequestException as e:
        return f"An error occurred: {e}"



# Mock SMS function
def mock_send_sms(to_number, message):
    # Simulate sending an SMS
    print(f"Mock SMS to {to_number}: {message}")
    return "mock_sms_sid"

# Function to send SMS - REAL
def send_sms(to_number, message):
    to_number = +61481737005
    message = twilio_client.messages.create(
        body=message,
        from_=TWILIO_PHONE_NUMBER,
        to=to_number
    )
    return message.sid  # Returns the message SID

# Function to contact second line agent
def contact_second_line_agent(message, agent_id, send_sms_flag, test_mode=False):
    if send_sms_flag:
        if test_mode:
            sms_response = mock_send_sms(agent_id, message)
            return f"Test mode - SMS Response: {sms_response}"
        else:
            sms_sid = send_sms(agent_id, message)
            return f"SMS sent to realtor with SID: {sms_sid}"
    else:
        return "Handled internally: " + message



