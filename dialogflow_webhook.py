from flask import Flask, request, jsonify
import requests
import datetime
from dateutil.parser import parse
import time

app = Flask(__name__)

AMADEUS_API_KEY = 'vKUpfPJalE4qdORBvtMAndwOQIAyGZ6u'
AMADEUS_API_SECRET = 'jJyg4CimyfFfxnSF'

def get_amadeus_token():
    try:
        url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        data = {
            'grant_type': 'client_credentials',
            'client_id': AMADEUS_API_KEY,
            'client_secret': AMADEUS_API_SECRET
        }
        response = requests.post(url, data=data, timeout=3)
        return response.json().get('access_token')
    except Exception:
        return None

def get_iata_code(city_name, access_token):
    try:
        url = f"https://test.api.amadeus.com/v1/reference-data/locations?subType=CITY&keyword={city_name}"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(url, headers=headers, timeout=3)
        return response.json()['data'][0]['iataCode']
    except Exception:
        return None

@app.route("/webhook", methods=["POST"])
def webhook():
    start = time.time()
    req = request.get_json()

    try:
        origin = req['queryResult']['parameters']['origin'][0]
        destination = req['queryResult']['parameters']['destination'][0]
        raw_date = req['queryResult']['parameters']['date'][0]
    except Exception:
        return jsonify({"fulfillmentText": "Sorry, I couldn't extract flight details. Can you rephrase?"})

    try:
        travel_date = parse(raw_date).strftime('%Y-%m-%d')
    except:
        return jsonify({"fulfillmentText": "Please provide a valid travel date."})

    token = get_amadeus_token()
    if not token:
        return jsonify({"fulfillmentText": "Authentication failed. Try again later."})

    origin_code = get_iata_code(origin, token)
    destination_code = get_iata_code(destination, token)

    if not origin_code or not destination_code:
        return jsonify({"fulfillmentText": "City not recognized. Try again with a valid city name."})

    if origin_code == destination_code:
        return jsonify({"fulfillmentText": "Origin and destination cannot be the same."})

    flight_url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {'Authorization': f'Bearer {token}'}
    params = {
        'originLocationCode': origin_code,
        'destinationLocationCode': destination_code,
        'departureDate': travel_date,
        'adults': 1,
        'nonStop': "false",
        'max': 1
    }

    try:
        res = requests.get(flight_url, headers=headers, params=params, timeout=3)
        offers = res.json().get('data', [])

        if not offers:
            return jsonify({"fulfillmentText": "No flights found. Try a different date or city."})

        offer = offers[0]
        price = offer['price']['total']
        currency = offer['price']['currency']
        segment = offer['itineraries'][0]['segments'][0]
        airline = segment['carrierCode']
        from_code = segment['departure']['iataCode']
        to_code = segment['arrival']['iataCode']
        dep_time = segment['departure']['at']

        reply = f"\u2708\ufe0f {airline}: {from_code} \u2192 {to_code} at {dep_time} | ₹{price} {currency}"
    except Exception:
        reply = "There was a problem retrieving flights. Please try again later."

    print("Total processing time:", time.time() - start)
    return jsonify({"fulfillmentText": reply})
