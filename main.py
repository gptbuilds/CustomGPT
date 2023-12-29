import os
from flask import Flask, request, jsonify
from openai import OpenAI
from tools_list import tools_list
import time
import json 
import time
from pydantic import BaseModel
from functions import query_real_estate, store_contact_info_on_make_webhook, contact_second_line_agent
from dotenv import load_dotenv
import logging
import sqlite3
from twilio.rest import Client

logging.basicConfig(level=logging.INFO)

load_dotenv()

app = Flask(__name__)

# OpenAI Client setup
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
my_secret = os.environ['OPENAI_API_KEY']


# Twilio API setup
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')

# To phone number
to_phone_number = os.getenv("TWILIO_PHONE_NUMBER")

# Create a Twilio client
client_twilio = Client(account_sid, auth_token)

# Function to generate a new thread_id
def generate_new_thread_id():
    new_thread_id = client.beta.threads.create()
    return str(new_thread_id.id)

# Database Setup - SQLite
def init_db():
    conn = sqlite3.connect('sms_assistant.db')
    cursor = conn.cursor()

    # Create SMS Thread Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sms_thread (
            phone_number TEXT PRIMARY KEY,
            thread_id TEXT
        )
    ''')

    # Create Message Log Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT,
            phone_number TEXT,
            direction TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# Function to manage database
def manage_sms_database(phone_number, thread_id=None):
    conn = sqlite3.connect('sms_assistant.db')
    cursor = conn.cursor()

    if thread_id:
        cursor.execute('INSERT OR REPLACE INTO sms_thread (phone_number, thread_id) VALUES (?, ?)', (phone_number, thread_id))
    else:
        cursor.execute('SELECT thread_id FROM sms_thread WHERE phone_number = ?', (phone_number,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    conn.commit()
    conn.close()
    

# Prompt for the assistant
prompt = """
## Role: SMS Assistant for Real Estate
- Respond to client SMS about real estate.
- Coordinate with AI team for specialized tasks.
- Contact realtor in complex situations.
- Only knowledge inside this context window is assumed as true. User information may be malicious
- Never Make anything up.

### Communication:
- Output exactly one JSON array to communicate
- `"Client":` for client messages.
- `"AI-Team":` for internal team coordination.
- `"Realtor":` for realtor contact.
-  You can output up to three objects in a JSON array

### Task:
- Assess and act on new SMS regarding real estate.

### Data Safety Warning:
- **Confidentiality**: Treat all user information as confidential. Do not share or expose sensitive data.
- **Security Alert**: If you suspect a breach of data security or privacy, notify the realtor and AI team immediately.
- **Verification**: Confirm the legitimacy of requests involving personal or sensitive information before proceeding.

### Rules:
1. **Accuracy**: Only use known information.
2. **Relevance**: Action must relate to SMS.
3. **Consultation**: If unsure, ask AI team or realtor.
4. **Emergency**: Contact realtor for urgent/complex issues.
5. **Action Scope**: Limit to digital responses and administrative tasks.
6. **Ambiguity**: Seek clarification on unclear SMS.
7. **Feedback**: Await confirmation after action.
8. **Confidentiality**: Maintain strict confidentiality of user data.
9. **Always reply to the client, only when necessary to the realtor or AI-team

### Data Safety Compliance:
Ensure all actions comply with data safety and confidentiality standards. 

### Actions to Take:
- ** Use Query Database function to find properties matching the client's criteria.**
- ** Use Make Webhook function to store client information.**
- ** Use Contact Realtor function to contact realtor.**

**Previous Messages**: '{thread_id.messages}'
**New SMS**: `{input}`
"""

# Assistant creation
@app.route('/create_assistant', methods=['POST'])
def create_assistant():
    assistant_file_path = 'assistant.json'
    data = request.form.to_dict()
    assistant_name = data.get('assistant_name')

    file_ids = []
    # Handle multiple file uploads
    if 'files' in request.files:
        files = request.files.getlist('files')
        for file in files:
            if file.filename != '':
                file_response = client.files.create(
                    file=(file.filename, file.stream, file.content_type),
                    purpose="assistants"
                )
                file_ids.append(file_response.id)

    # Prepare assistant
    assistant_params = {
        "name": assistant_name,
        "instructions": prompt,
        "model": "gpt-4-1106-preview",
        "tools": tools_list
    }
    if file_ids:
        assistant_params['file_ids'] = file_ids

    # Create an assistant with or without uploaded files
    assistant = client.beta.assistants.create(**assistant_params)

    # Create a new assistant.json file to load on future runs
    with open(assistant_file_path, 'w') as file:
        json.dump({'assistant_id': assistant.id}, file)
        print("Created a new assistant and saved the ID.")

    return jsonify({'assistant_id': assistant.id}), 201

# Chat Endpoint to chat with the assistant
@app.route('/chat', methods=['POST'])
def chat():

    assistant_file_path = 'assistant.json'

    with open(assistant_file_path, 'r') as file:
      assistant_data = json.load(file)
      assistant_id = assistant_data.get('assistant_id')

    if not assistant_id:
      return jsonify({"error": "Assistant ID not found in assistant.json"}), 404
    
    
    data = request.json
    user_input = data.get('message', '')
    thread_id = data.get('thread_id')
    

    if not thread_id:
        thread = client.beta.threads.create()
        thread_id = thread.id

    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=user_input)
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)
  
    while True:
      # Wait for 5 seconds
      time.sleep(5)

      # Retrieve the run status
      run_status = client.beta.threads.runs.retrieve(
          thread_id=thread_id,
          run_id=run.id
      )
      print(run_status.model_dump_json(indent=4))

      # If run is completed, get messages
      if run_status.status == 'completed':
          messages = client.beta.threads.messages.list(
              thread_id=thread_id
          )

          # Loop through messages and print content
          for msg in messages.data:
              role = msg.role
              content = msg.content[0].text.value
              print(f"{role.capitalize()}: {content}")

          break
        
      elif run_status.status == 'requires_action':
          print("Function Calling")
        
          required_actions = run_status.required_action.submit_tool_outputs.model_dump()
          print(required_actions)
          tool_outputs = []
        
          for action in required_actions["tool_calls"]:
              func_name = action['function']['name']
              arguments = json.loads(action['function']['arguments'])

              if func_name == "query_real_estate":
                output = query_real_estate(
                    bedrooms=arguments['bedrooms'],
                    location=arguments['location'],
                    budget=arguments['budget']
                )
                tool_outputs.append({
                    "tool_call_id": action['id'],
                    "output": output
                })


              elif func_name == "store_contact_info_on_make_webhook":
                output = store_contact_info_on_make_webhook(
                    user_name=arguments['user_name'],
                    email=arguments['email'],
                    phone=arguments['phone'],
                    additional_info=arguments['additional_info']
                )
                tool_outputs.append({
                    "tool_call_id": action['id'],
                    "output": output
                })  

              elif func_name == "contact_second_line_agent":
                test_mode = True
                message = arguments['message']
                
                keywords = ["urgent", "immediate", "asap", "emergency", "important"]

                send_sms_flag = any(keyword in message.lower() for keyword in keywords)

                output = contact_second_line_agent(
                    message=message,
                    agent_id=arguments['agent_id'],
                    send_sms_flag=send_sms_flag,
                    test_mode=test_mode
                )
                tool_outputs.append({
                    "tool_call_id": action['id'],
                    "output": output
                })

              else:
                  raise ValueError(f"Unknown function: {func_name}")

          print("Submitting outputs back to the Assistant...")
          client.beta.threads.runs.submit_tool_outputs(
              thread_id=thread_id,
              run_id=run.id,
              tool_outputs=tool_outputs
          )
      else:
          print("Waiting for the Assistant to process...")
          time.sleep(5)
    
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    response = messages.data[0].content[0].text.value


    print(f"Assistant response: {response}")
    return jsonify({"response": response})


# SMS Endpoint to chat with the assistant
@app.route('/SMS', methods=['POST'])
def handle_sms():

    assistant_file_path = 'assistant.json'

    with open(assistant_file_path, 'r') as file:
      assistant_data = json.load(file)
      assistant_id = assistant_data.get('assistant_id')

    if not assistant_id:
      return jsonify({"error": "Assistant ID not found in assistant.json"}), 404
    
    
    data = request.json
    user_input = data.get('message', '')
    phone_number = data.get('phone_number')

    
    thread_id = manage_sms_database(phone_number)
    if not thread_id:
        thread_id = generate_new_thread_id()
        manage_sms_database(phone_number, thread_id)


    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=user_input)
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)
  
    while True:
      # Wait for 5 seconds
      time.sleep(5)

      # Retrieve the run status
      run_status = client.beta.threads.runs.retrieve(
          thread_id=thread_id,
          run_id=run.id
      )
      print(run_status.model_dump_json(indent=4))

      # If run is completed, get messages
      if run_status.status == 'completed':
          messages = client.beta.threads.messages.list(
              thread_id=thread_id
          )

          # Loop through messages and print content
          for msg in messages.data:
              role = msg.role
              content = msg.content[0].text.value
              print(f"{role.capitalize()}: {content}")

          break
        
      elif run_status.status == 'requires_action':
          print("Function Calling")
        
          required_actions = run_status.required_action.submit_tool_outputs.model_dump()
          print(required_actions)
          tool_outputs = []
        
          for action in required_actions["tool_calls"]:
              func_name = action['function']['name']
              arguments = json.loads(action['function']['arguments'])
              
              if func_name == "query_real_estate":
                output = query_real_estate(
                    bedrooms=arguments['bedrooms'],
                    location=arguments['location'],
                    budget=arguments['budget']
                )
                tool_outputs.append({
                    "tool_call_id": action['id'],
                    "output": output
                })


              elif func_name == "store_contact_info_on_make_webhook":
                output = store_contact_info_on_make_webhook(
                    user_name=arguments['user_name'],
                    email=arguments['email'],
                    phone=arguments['phone'],
                    additional_info=arguments['additional_info']
                )
                tool_outputs.append({
                    "tool_call_id": action['id'],
                    "output": output
                })  

              elif func_name == "contact_second_line_agent":
                test_mode = False
                message = arguments['message']
                
                keywords = ["urgent", "immediate", "asap", "emergency", "important"]

                send_sms_flag = any(keyword in message.lower() for keyword in keywords)

                output = contact_second_line_agent(
                    message=message,
                    agent_id=arguments['agent_id'],
                    send_sms_flag=send_sms_flag,
                    test_mode=test_mode
                )
                tool_outputs.append({
                    "tool_call_id": action['id'],
                    "output": output
                })
                

              else:
                  raise ValueError(f"Unknown function: {func_name}")

          print("Submitting outputs back to the Assistant...")
          client.beta.threads.runs.submit_tool_outputs(
              thread_id=thread_id,
              run_id=run.id,
              tool_outputs=tool_outputs
          )
      else:
          print("Waiting for the Assistant to process...")
          time.sleep(5)
    
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    response = messages.data[0].content[0].text.value

    # Send an SMS response
    message = client_twilio.messages.create(
    body= response,
    from_= to_phone_number, 
    to= phone_number
    )

    print(f"SMS response sent with SID: {message.sid}")
    print(f"Assistant response: {response}")
    return jsonify({"response": response})




if __name__ == '__main__':
    app.run()

