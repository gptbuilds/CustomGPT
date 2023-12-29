tools_list = [
   {"type": "code_interpreter"}, {"type": "retrieval"},
   {
    "type": "function",
    "function": {
        "name": "query_real_estate",
        "description": "Query a real estate database for property listings",
        "parameters": {
            "type": "object",
            "properties": {
                "bedrooms": {
                    "type": "string",
                    "description": "Number of bedrooms, formatted as a string (e.g., '4 bds'). Use 'any' for no specific preference."
                },
                "location": {
                    "type": "string",
                    "description": "Part of the address to filter properties (e.g., 'Seattle, WA'). Use 'any' for no specific preference."
                },
                "budget": {
                    "type": "string",
                    "description": "Maximum price in a string format (e.g., '$2,399,000')"
                }
            },
            "required": ["bedrooms", "location", "budget"]
        }
    }
},
   {
    "type": "function",
    "function": {
        "name": "store_contact_info_on_make_webhook",
        "description": "Store user contact information via a Make Webhook, which then updates Google Sheets",
        "parameters": {
            "type": "object",
            "properties": {
                "user_name": {"type": "string", "description": "The user's name"},
                "email": {"type": "string", "description": "The user's email address"},
                "phone": {"type": "string", "description": "The user's phone number"},
                "additional_info": {"type": "string", "description": "Any additional information about the user"}
            },
            "required": ["user_name", "email", "phone"]
        }
    }
},
   {
    "type": "function",
    "function": {
        "name": "contact_second_line_agent",
        "description": "Send an SMS to a realtor if the message is flagged as urgent or important.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The customer message to be potentially forwarded."
                },
                "agent_id": {
                    "type": "string",
                    "description": "The identifier for the second-line agent, typically the realtor's phone number."
                },
                "send_sms_flag": {
                    "type": "boolean",
                    "description": "Flag to determine whether to send an SMS or not."
                }
            },
            "required": ["message", "agent_id", "send_sms_flag"]
        }
    }
}

]
