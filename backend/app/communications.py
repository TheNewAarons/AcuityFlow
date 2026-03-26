import os
from twilio.rest import Client
import logging

logger = logging.getLogger(__name__)

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID") # AC...
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")   # Main Auth Token or API Secret
TWILIO_API_KEY_SID = os.getenv("TWILIO_API_KEY_SID") # Optional SK...
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER") # Ej: +14155238886 o whatsapp:+14155238886

def get_twilio_client():
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.warning("Twilio credentials are not set. Messages will only be simulated.")
        return None
    try:
        # If API Key SID is provided, use it as username and Auth Token as secret, while providing Account SID
        if TWILIO_API_KEY_SID:
            return Client(TWILIO_API_KEY_SID, TWILIO_AUTH_TOKEN, TWILIO_ACCOUNT_SID)
        # Default: Account SID as username, Auth Token as password
        return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    except Exception as e:
        logger.error(f"Failed to initialize Twilio client: {e}")
        return None

def send_message(to_number: str, text: str) -> bool:
    """
    Sends a message via Twilio (SMS or WhatsApp depending on the number format).
    Returns True if sent successfully or simulated successfully.
    """
    if not to_number:
        logger.error("Cannot send message. Destination phone number is empty.")
        return False
        
    client = get_twilio_client()
    
    if not client:
        # Modo simulación si no hay credenciales
        print(f"\n[SIMULADOR TWILIO] MOCK SEND -> To: {to_number}")
        print(f"[SIMULADOR TWILIO] Body:\n{text}\n")
        return True
        
    try:
        # Detectar si es WhatsApp o SMS
        from_number = TWILIO_FROM_NUMBER
        is_whatsapp = from_number and from_number.startswith("whatsapp:")
        to_formatted = f"whatsapp:{to_number}" if is_whatsapp and not to_number.startswith("whatsapp:") else to_number
        
        message = client.messages.create(
            body=text,
            from_=from_number,
            to=to_formatted
        )
        print(f"[TWILIO SUCCESS] Message sent. SID: {message.sid}")
        return True
    except Exception as e:
        print(f"[TWILIO ERROR] Failed to send message: {e}")
        return False
