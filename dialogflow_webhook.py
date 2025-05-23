from flask import Flask, request, jsonify
import requests
from dateutil.parser import parse
import traceback

app = Flask(__name__)

# Amadeus API credentials (replace with your actual keys)
AMADEUS_API_KEY = 'vKUpfPJalE4qdORBvtMAndwOQIAyGZ6u'
AMADEUS_API_SECRET = 'jJyg4CimyfFfxnSF'


# Get Amadeus OAuth token
def get_amadeus_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': AMADEUS_API_KEY,
        'client_secret': AMADEUS_API_SECRET
    }
    try:
        response = requests.post(url, data=data, timeout=5)
        return response.json().get('access_token')
    except Exception as e:
        print("Token error:", e)
        return None


# Get IATA code from city name
def get_iata_code(city, token):
    url = f"https://test.api.amadeus.com/v1/reference-data/locations"
    params = {'subType': 'CITY', 'keyword': city}
    headers = {'Authorization': f'Bearer {token}'}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        return res.json()['data'][0]['iataCode']
    except Exception as e:
        print(f"IATA lookup failed for {city}:", e)
        return None


# Webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        req = request.get_json()
        origin = req['queryResult']['parameters']['origin'][0]
        destination = req['queryResult']['parameters']['destination'][0]
        raw_date = req['queryResult']['parameters']['date'][0]

        # Convert date to YYYY-MM-DD
        travel_date = parse(raw_date).strftime('%Y-%m-%d')

        # Authenticate
        token = get_amadeus_token()
        if not token:
            return jsonify({"fulfillmentText": "Failed to connect to flight service. Try again later."})

        # Get IATA codes
        origin_code = get_iata_code(origin, token)
        destination_code = get_iata_code(destination, token)

        if not origin_code or not destination_code:
            return jsonify({"fulfillmentText": "Invalid city name. Please check your origin and destination."})

        if origin_code == destination_code:
            return jsonify({"fulfillmentText": "Origin and destination can't be the same."})

        # Search flights
        flight_url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        headers = {'Authorization': f'Bearer {token}'}
        params = {
            'originLocationCode': origin_code,
            'destinationLocationCode': destination_code,
            'departureDate': travel_date,
            'adults': 1,
            'max': 3
        }

        res = requests.get(flight_url, headers=headers, params=params, timeout=5)
        offers = res.json().get('data', [])

        if not offers:
            return jsonify({"fulfillmentText": "No flights found for the given cities and date."})

        # Format response
        flights = []
        for offer in offers:
            price = offer['price']['total']
            currency = offer['price']['currency']
            segment = offer['itineraries'][0]['segments'][0]
            airline = segment['carrierCode']
            from_code = segment['departure']['iataCode']
            to_code = segment['arrival']['iataCode']
            dep_time = segment['departure']['at']
            flights.append(f"✈️ {airline}: {from_code} → {to_code} at {dep_time} | ₹{price} {currency}")

        reply = "\n\n".join(flights)
        print("Reply:", reply)
        return jsonify({"fulfillmentText": reply})

    except Exception as e:
        print("Webhook error:", e)
        traceback.print_exc()
        return jsonify({"fulfillmentText": "Sorry, something went wrong while processing your request."})


# For local testing (optional)
if __name__ == "__main__":
    app.run(port=5000)
