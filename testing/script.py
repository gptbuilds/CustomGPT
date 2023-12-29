import json
import sqlite3


json_file = r'C:\Users\61481\OneDrive\Desktop\Custom GPT\property_list.json'
with open(json_file, 'r') as file:
    data = json.load(file)

conn = sqlite3.connect('real_estate.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS properties (
        Position TEXT,
        Price TEXT,
        Bedrooms TEXT,
        Bathroom TEXT,
        Area_sqft TEXT,
        Description TEXT,
        Address TEXT,
        Other_info TEXT,
        Image TEXT,
        Detail_link TEXT
    )
''')


for record in data:  
    cursor.execute('''
        INSERT INTO properties 
        (Position, Price, Bedrooms, Bathroom, Area_sqft, Description, Address, Other_info, Image, Detail_link) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (record["Position"], record["Price"], record["Bedroom(s)"], record["Bathroom"], record["Area (sqft)"], 
          record["Description"], record["Address"], record["Other info"], record["Image"], record["Detail link"]))


conn.commit()
conn.close()
