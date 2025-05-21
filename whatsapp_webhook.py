from flask import Flask, request
import requests
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

DIALOGFLOW_WEBHOOK_URL = "https://flight-bot-c4t6.onrender.com/webhook"

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")

    # Format Dialogflow JSON
    dialogflow_data = {
        "queryInput": {
            "text": {
                "text": incoming_msg,
                "languageCode": "en"
            }
        },
        "queryParams": {
            "source": "whatsapp",
            "payload": {"from": sender}
        }
    }

    # Call Dialogflow webhook
    response = requests.post(DIALOGFLOW_WEBHOOK_URL, json={
        "queryResult": {
            "queryText": incoming_msg,
            "parameters": {
                "origin": "",  # optional: parse with NLP
                "destination": "",
                "date": ""
            }
        }
    })

    result = response.json()
    reply_text = result.get("fulfillmentText", "Sorry, something went wrong.")

    # Respond back to WhatsApp via Twilio
    twilio_response = MessagingResponse()
    twilio_response.message(reply_text)

    return str(twilio_response)

if __name__ == "__main__":
    app.run(debug=True)
