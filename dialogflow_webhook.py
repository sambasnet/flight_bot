from flask import Flask, request, jsonify
import requests
import os
import datetime

app = Flask(__name__)

# Replace with your actual Amadeus API credentials
AMADEUS_CLIENT_ID = "vKUpfPJalE4qdORBvtMAndwOQIAyGZ6u"
AMADEUS_CLIENT_SECRET = "jJyg4CimyfFfxnSF"
ACCESS_TOKEN = None

# Get Amadeus access token
def get_amadeus_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_CLIENT_ID,
        "client_secret": AMADEUS_CLIENT_SECRET,
    }
    response = requests.post(url, data=payload)
    return response.json().get("access_token")

# Convert city name to IATA code
def get_iata_code(city_name, access_token):
    url = f"https://test.api.amadeus.com/v1/reference-data/locations?subType=CITY&keyword={city_name}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    try:
        return response.json()['data'][0]['iataCode']
    except:
        return None

# Search flights
def search_flights(origin, destination, date, access_token):
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": date,
        "adults": 1,
        "nonStop": False,
        "max": 3  # Limit to 3 flights
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

@app.route('/webhook', methods=['POST'])
def dialogflow_webhook():
    global ACCESS_TOKEN

    req = request.get_json()
    parameters = req["queryResult"]["parameters"]
    origin = parameters.get("origin", [None])[0]
    destination = parameters.get("destination", [None])[0]
    date = parameters.get("date", [None])[0]

    if not origin or not destination or not date:
        return jsonify({
            "fulfillmentText": "Please provide origin, destination, and travel date."
        })

    # Get token if not set
    if not ACCESS_TOKEN:
        ACCESS_TOKEN = get_amadeus_token()

    # Convert city names to IATA codes
    origin_code = get_iata_code(origin, ACCESS_TOKEN)
    destination_code = get_iata_code(destination, ACCESS_TOKEN)

    if not origin_code or not destination_code:
        return jsonify({
            "fulfillmentText": "Invalid city name. Please try again."
        })

    # Format the date
    try:
        formatted_date = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        return jsonify({
            "fulfillmentText": "Please provide the date in YYYY-MM-DD format."
        })

    # Search for flights
    flight_data = search_flights(origin_code, destination_code, formatted_date, ACCESS_TOKEN)

    # Parse flight offers
    try:
        offers = flight_data["data"]
        response_lines = []
        for offer in offers:
            itinerary = offer["itineraries"][0]
            segments = itinerary["segments"]
            departure = segments[0]["departure"]["at"]
            arrival = segments[-1]["arrival"]["at"]
            duration = itinerary["duration"]
            price = offer["price"]["total"]
            response_lines.append(
                f"✈️ Flight: {origin_code} to {destination_code}\n"
                f"🕓 Departure: {departure}\n"
                f"🛬 Arrival: {arrival}\n"
                f"⏱️ Duration: {duration}\n"
                f"💰 Price: ${price}\n"
                "-------------------"
            )
        return jsonify({
            "fulfillmentText": "\n\n".join(response_lines)
        })
    except:
        return jsonify({
            "fulfillmentText": "Sorry, no flights found or something went wrong."
        })

if __name__ == '__main__':
    app.run(debug=True)
