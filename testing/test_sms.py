import requests

# Endpoint URL of the '/SMS' route in your Flask app
url = 'http://localhost:5000/SMS'  # Replace with your Flask app's URL

# Sample data mimicking what Twilio sends
data = {
    'From': '+61481737005',  # Replace with a sample sender number
    'Body': 'Urgent - Need to contact Manager for House Inspection'  # Replace with a test SMS message
}

response = requests.post(url, data=data)

print(f'Status Code: {response.status_code}')
print(f'Response: {response.text}')
