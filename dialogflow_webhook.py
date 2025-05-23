from flask import Flask, request, jsonify
import requests
from dateutil.parser import parse

app = Flask(__name__)

AMADEUS_API_KEY = 'vKUpfPJalE4qdORBvtMAndwOQIAyGZ6u'
AMADEUS_API_SECRET = 'jJyg4CimyfFfxnSF'

# Get Amadeus access token
def get_amadeus_token():
    try:
        response = requests.post(
            "https://test.api.amadeus.com/v1/security/oauth2/token",
            data={
                'grant_type': 'client_credentials',
                'client_id': AMADEUS_API_KEY,
                'client_secret': AMADEUS_API_SECRET
            },
            timeout=2
        )
        return response.json().get('access_token')
    except:
        return None

# Convert city name to IATA code
def get_iata_code(city_name, token):
    try:
        url = f"https://test.api.amadeus.com/v1/reference-data/locations"
        params = {'subType': 'CITY', 'keyword': city_name}
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(url, headers=headers, params=params, timeout=2)
        return response.json()['data'][0]['iataCode']
    except:
        return None

@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json()

    try:
        origin = req['queryResult']['parameters']['origin'][0]
        destination = req['queryResult']['parameters']['destination'][0]
        raw_date = req['queryResult']['parameters']['date'][0]
    except Exception:
        return jsonify({"fulfillmentText": "Sorry, I couldn't extract flight details. Please rephrase."})

    try:
        travel_date = parse(raw_date).strftime('%Y-%m-%d')
    except:
        return jsonify({"fulfillmentText": "Please provide a valid travel date like June 30."})

    token = get_amadeus_token()
    if not token:
        return jsonify({"fulfillmentText": "Flight service authentication failed. Try again later."})

    origin_code = get_iata_code(origin, token)
    destination_code = get_iata_code(destination, token)

    if not origin_code or not destination_code:
        return jsonify({"fulfillmentText": "Invalid city name. Please try different cities."})
    if origin_code == destination_code:
        return jsonify({"fulfillmentText": "Origin and destination cannot be the same."})

    flight_url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {'Authorization': f'Bearer {token}'}
    body = {
        'currencyCode': 'INR',
        'originLocationCode': origin_code,
        'destinationLocationCode': destination_code,
        'departureDate': travel_date,
        'adults': 1,
        'max': 1  # Limit to 1 offer
    }

    try:
        res = requests.post(flight_url, headers=headers, json=body, timeout=2)
        data = res.json()
        offer = data['data'][0]
        segment = offer['itineraries'][0]['segments'][0]
        airline = segment['carrierCode']
        dep = segment['departure']
        arr = segment['arrival']
        price = offer['price']['total']
        currency = offer['price']['currency']
        reply = f"✈️ {airline}: {dep['iataCode']} → {arr['iataCode']} at {dep['at']} | ₹{price} {currency}"
    except:
        reply = "No flights found for the given cities and date. Try a different search."

    return jsonify({"fulfillmentText": reply})
