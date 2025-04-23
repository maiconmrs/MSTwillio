import os
import time
from dotenv import load_dotenv
from twilio.rest import Client

# === ENV + TWILIO SETUP ===

def load_env_variables():
    """
    Loads environment variables from a .env file using dotenv.
    Returns a dictionary with the credentials and phone numbers.
    """
    load_dotenv()
    return {
        "account_sid": os.getenv("MS_TWILIO_ACCOUNT_SID"),
        "api_key_sid": os.getenv("MS_TWILIO_API_KEY_SID"),
        "api_key_secret": os.getenv("MS_TWILIO_SECRET"),
        "phone_number": os.getenv("PHONE_NUMBER"),
        "ms_number": os.getenv("MS_NUMBER"),
        "service_sid": os.getenv("MS_TWILIO_DEFAULT_SERVICE_SID"),
    }

def format_number(number):
    """
    Ensures the phone number is in the correct format for Twilio WhatsApp.
    It removes any existing 'whatsapp:' prefix and adds it back cleanly.
    """
    number = number.replace("whatsapp:", "").strip()
    return f"whatsapp:{number}"

def setup_twilio_client(env):
    """
    Initializes the Twilio client using the API keys and account SID.
    """
    return Client(env["api_key_sid"], env["api_key_secret"], env["account_sid"])


# === WHATSAPP OPERATIONS ===

def send_initial_message(client, from_number, to_number):
    """
    Sends a one-time WhatsApp message using the Twilio Messaging API.
    This is separate from the conversation flow.
    """
    message = client.messages.create(
        body='This is a message that I want to send over WhatsApp with Twilio!',
        from_=from_number,
        to=to_number
    )
    print("from server (Messaging API):", message.body)
    print("✅ Message SID:", message.sid)
    return message


# === CONVERSATION MANAGEMENT ===

def get_or_create_conversation(service):
    """
    Checks for an existing conversation with a friendly name.
    If not found, creates a new conversation.
    """
    conversations = service.conversations.list()
    convo = next((c for c in conversations if c.friendly_name == 'Friendly Conversation'), None)
    
    if convo:
        print("ℹ️ Reusing existing conversation.")
    else:
        convo = service.conversations.create(friendly_name='Friendly Conversation')
        print("✅ Created new conversation.")
    
    return convo

def ensure_participant(conversation, phone_number, proxy_number):
    """
    Checks if the participant (user's WhatsApp number) is already in the conversation.
    If not, adds the participant using their number and the proxy (Twilio) number.
    """
    participants = conversation.participants.list()
    already_exists = any(p.messaging_binding['address'] == phone_number for p in participants)

    if not already_exists:
        print(f"Adding participant with address: {phone_number}")
        print(f"Using proxy address: {proxy_number}")
        conversation.participants.create(
            messaging_binding_address=phone_number,
            messaging_binding_proxy_address=proxy_number
        )
        print("✅ Participant added to conversation.")
    else:
        print("ℹ️ Participant already exists in the conversation.")


# === MESSAGE POLLING ===

def poll_messages(conversation, user_number):
    """
    Continuously polls the conversation for new incoming messages from the user.
    Replies with an automated message if it receives a new message from the user.
    """
    print("📲 Waiting for replies from your WhatsApp...")
    last_sid = None

    while True:
        messages = conversation.messages.list()

        if messages:
            last_msg = messages[-1]
            if last_msg.sid != last_sid and last_msg.author == user_number:
                print("from phone:", last_msg.body)

                reply = "✅ Message received. I am the server."
                print("from server:", reply)

                conversation.messages.create(author="system", body=reply)
                last_sid = last_msg.sid

        time.sleep(1)


# === MAIN ENTRY POINT ===

def main():
    # Load environment variables and normalize phone numbers
    env = load_env_variables()
    env["phone_number"] = format_number(env["phone_number"])
    env["ms_number"] = format_number(env["ms_number"])

    # Set up Twilio client and conversation service
    client = setup_twilio_client(env)
    service = client.conversations.v1.services(env["service_sid"])

    # Send a simple WhatsApp message using Messaging API (not conversation-based)
    send_initial_message(client, env["ms_number"], env["phone_number"])

    # Ensure we have a conversation and the user is added to it
    conversation = get_or_create_conversation(service)
    ensure_participant(conversation, env["phone_number"], env["ms_number"])

    # Start polling for replies from the user's phone
    poll_messages(conversation, env["phone_number"])


# Run the script if called directly
if __name__ == "__main__":
    main()
