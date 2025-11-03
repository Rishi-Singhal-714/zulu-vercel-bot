import os
import json
import requests

# Read Gallabox credentials from environment
GALLABOX_API_KEY = os.getenv("GALLABOX_API_KEY", "")
GALLABOX_API_SECRET = os.getenv("GALLABOX_API_SECRET", "")
GALLABOX_CHANNEL_ID = os.getenv("GALLABOX_CHANNEL_ID", "")
GALLABOX_API_URL = "https://backend.gallabox.com/api/v1/messages/whatsapp"

def send_whatsapp_message(phone, text):
    """Send WhatsApp text message via Gallabox API"""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": GALLABOX_API_KEY,
        "x-api-secret": GALLABOX_API_SECRET,
    }
    payload = {
        "channelId": GALLABOX_CHANNEL_ID,
        "to": phone,
        "type": "text",
        "message": {"text": text}
    }

    try:
        r = requests.post(GALLABOX_API_URL, headers=headers, json=payload)
        print("📤 Gallabox send response:", r.status_code, r.text)
    except Exception as e:
        print("❌ Gallabox send error:", e)


def handler(request, response):
    """Vercel entrypoint — Gallabox webhook receiver"""
    try:
        if request.method == "GET":
            response.status_code = 200
            response.body = json.dumps({"status": "ok", "message": "Gallabox Webhook Active!"})
            return response

        if request.method == "POST":
            try:
                data = request.json()
            except Exception:
                response.status_code = 400
                response.body = json.dumps({"error": "Invalid JSON"})
                return response

            print("📩 Received Gallabox message:", json.dumps(data, indent=2))

            # Parse WhatsApp message
            user_phone = data.get("data", {}).get("from", "")
            user_message = data.get("data", {}).get("message", {}).get("text", "").strip().lower()

            if not user_phone or not user_message:
                response.status_code = 200
                response.body = json.dumps({"status": "ignored"})
                return response

            # If user says hi
            if user_message == "hi":
                send_whatsapp_message(user_phone, "hi 👋")
            else:
                send_whatsapp_message(user_phone, "Hello! Please say 'hi' to start 🙂")

            response.status_code = 200
            response.body = json.dumps({"status": "ok"})
            return response

        response.status_code = 405
        response.body = json.dumps({"error": "Method not allowed"})
        return response

    except Exception as e:
        print("❌ Error in webhook:", e)
        response.status_code = 500
        response.body = json.dumps({"error": str(e)})
        return response
