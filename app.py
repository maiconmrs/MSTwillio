import os
import time
from dotenv import load_dotenv
from flask import Flask
from twilio.rest import Client

# Load environment variables
load_dotenv()
ACCOUNT_SID = os.getenv("MS_TWILIO_ACCOUNT_SID")
API_KEY_SID = os.getenv("MS_TWILIO_API_KEY_SID")
API_KEY_SECRET = os.getenv("MS_TWILIO_SECRET")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")              # Your personal WhatsApp number (sender)
MS_NUMBER = os.getenv("MS_NUMBER")                      # Twilio sandbox number (registered sender)
SERVICE_SID = os.getenv("MS_TWILIO_DEFAULT_SERVICE_SID")

# Ensure proper WhatsApp prefix (clean and normalize)
PHONE_NUMBER = PHONE_NUMBER.replace("whatsapp:", "").strip()
MS_NUMBER = MS_NUMBER.replace("whatsapp:", "").strip()
PHONE_NUMBER = f"whatsapp:{PHONE_NUMBER}"
MS_NUMBER = f"whatsapp:{MS_NUMBER}"

# Setup Twilio client
client = Client(API_KEY_SID, API_KEY_SECRET, ACCOUNT_SID)
service = client.conversations.v1.services(SERVICE_SID)

# ✅ STEP 1 — Send WhatsApp message using Messaging API
message = client.messages.create(
    body='This is a message that I want to send over WhatsApp with Twilio!',
    from_=MS_NUMBER,
    to=PHONE_NUMBER
)
print("from server (Messaging API):", message.body)
print("✅ Message SID:", message.sid)

# ✅ STEP 2 — Reuse existing conversation or create a new one
existing_conversations = service.conversations.list()
conversation = next((c for c in existing_conversations if c.friendly_name == 'Friendly Conversation'), None)

if conversation:
    print("ℹ️ Reusing existing conversation.")
else:
    conversation = service.conversations.create(friendly_name='Friendly Conversation')
    print("✅ Created new conversation.")

# Check if participant already exists
participants = conversation.participants.list()
already_added = any(p.messaging_binding['address'] == PHONE_NUMBER for p in participants)

if not already_added:
    print(f"Adding participant with address: {PHONE_NUMBER}")
    print(f"Using proxy address: {MS_NUMBER}")
    conversation.participants.create(
        messaging_binding_address=PHONE_NUMBER,
        messaging_binding_proxy_address=MS_NUMBER
    )
    print("✅ Participant added to conversation.")
else:
    print("ℹ️ Participant already exists in the conversation.")

# Optional: keep Flask alive (no webhook used)
app = Flask(__name__)

@app.route("/")
def home():
    return "Polling bot is running!"

if __name__ == "__main__":
    from threading import Thread
    Thread(target=lambda: app.run(port=8080)).start()

    print("📲 Waiting for replies from your WhatsApp...")

    last_sid = None

    while True:
        messages = conversation.messages.list()

        if messages:
            last_msg = messages[-1]
            if last_msg.sid != last_sid and last_msg.author == PHONE_NUMBER:
                print("from phone:", last_msg.body)

                reply = "✅ Message received. I am the server."
                print("from server:", reply)

                conversation.messages.create(author="system", body=reply)
                last_sid = last_msg.sid

        time.sleep(1)