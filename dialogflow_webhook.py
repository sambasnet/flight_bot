from flask import Flask, request, jsonify
import requests
import datetime
from dateutil.parser import parse

app = Flask(__name__)

# Amadeus API Credentials (replace with yours)
AMADEUS_API_KEY = 'vKUpfPJalE4qdORBvtMAndwOQIAyGZ6u'
AMADEUS_API_SECRET = 'jJyg4CimyfFfxnSF'

# Get Amadeus token
def get_amadeus_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': AMADEUS_API_KEY,
        'client_secret': AMADEUS_API_SECRET
    }
    response = requests.post(url, data=data)
    return response.json().get('access_token')

# Convert city name to IATA code using Amadeus API
def get_iata_code(city_name, token):
    url = f"https://test.api.amadeus.com/v1/reference-data/locations"
    params = {
        'keyword': city_name,
        'subType': 'CITY'
    }
    headers = {
        'Authorization': f'Bearer {token}'
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    try:
        return data['data'][0]['iataCode']
    except:
        return None

# Handle the webhook call
@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json()

    try:
        origin = req['queryResult']['parameters']['origin'][0]
        destination = req['queryResult']['parameters']['destination'][0]
        raw_date = req['queryResult']['parameters']['date'][0]
    except Exception:
        return jsonify({
            "fulfillmentText": "Sorry, I couldn't extract flight details. Can you rephrase?"
        })

    # Parse the date
    try:
        travel_date = parse(raw_date).strftime('%Y-%m-%d')
    except:
        return jsonify({
            "fulfillmentText": "Please provide the travel date in a valid format like June 30 or 2025-06-30."
        })

    token = get_amadeus_token()
    if not token:
        return jsonify({
            "fulfillmentText": "Unable to authenticate with the flight service. Please try again later."
        })

    # Get IATA codes
    origin_code = get_iata_code(origin, token)
    destination_code = get_iata_code(destination, token)

    if not origin_code or not destination_code:
        return jsonify({
            "fulfillmentText": "Invalid city name. Please try again."
        })

    if origin_code == destination_code:
        return jsonify({
            "fulfillmentText": "Origin and destination can't be the same. Please enter different cities."
        })

    # Search for flights
    flight_url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {'Authorization': f'Bearer {token}'}
    params = {
        'originLocationCode': origin_code,
        'destinationLocationCode': destination_code,
        'departureDate': travel_date,
        'adults': 1,
        'nonStop': False,
        'max': 3
    }

    res = requests.get(flight_url, headers=headers, params=params)
    data = res.json()

    try:
        offers = data['data']
        flights = []
        for offer in offers:
            price = offer['price']['total']
            itinerary = offer['itineraries'][0]['segments'][0]
            dep = itinerary['departure']
            arr = itinerary['arrival']
            airline = itinerary['carrierCode']
            flights.append(f"✈️ {airline} | {dep['iataCode']} → {arr['iataCode']} at {dep['at']} | ₹{price}")
        reply = "\n\n".join(flights)
    except Exception:
        reply = "No flights found for the given cities and date. Try a different search."

    return jsonify({"fulfillmentText": reply})
