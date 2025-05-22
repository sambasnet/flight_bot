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
def get_iata_code(city_name, access_token):
    url = f"https://test.api.amadeus.com/v1/reference-data/locations?subType=CITY&keyword={city_name}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    try:
        return response.json()['data'][0]['iataCode']
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
    offers = data.get('data', [])

    if not offers:
        reply = "❌ No flight offers found for the given cities and date."
    else:
        flights = []

        for offer in offers:
            try:
                price = offer['price']['total']
                currency = offer['price']['currency']
                itinerary = offer['itineraries'][0]
                segments = itinerary.get('segments', [])

                if not segments:
                    continue

                # Handle multi-segment flights
                first_seg = segments[0]
                last_seg = segments[-1]

                dep_code = first_seg['departure'].get('iataCode', 'N/A')
                arr_code = last_seg['arrival'].get('iataCode', 'N/A')
                dep_time = first_seg['departure'].get('at', 'N/A')
                duration = itinerary.get('duration', 'N/A')
                airline = first_seg.get('carrierCode', 'N/A')

                flights.append(
                    f"✈️ {airline} | {dep_code} → {arr_code}\n🕒 {dep_time} ⏱ {duration}\n💰 ₹{price} {currency}"
                )
            except Exception as e:
                print(f"[Offer Parse Error] {e}")
                continue

        reply = "\n\n".join(flights) if flights else "❌ No valid flight details could be parsed."

except Exception as e:
    print(f"[General Error] {e}")
    reply = "⚠️ An error occurred while searching for flights. Please try again later."


    return jsonify({"fulfillmentText": reply})
