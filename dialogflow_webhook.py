from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

CLIENT_ID = "vKUpfPJalE4qdORBvtMAndwOQIAyGZ6u"
CLIENT_SECRET = "jJyg4CimyfFfxnSF"

def get_amadeus_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    res = requests.post(url, data=payload)
    return res.json()["access_token"]

def get_iata_code(city_name,token):
    url = f"https://test.api.amadeus.com/v1/reference-data/locations?subType=CITY&keyword={city_name}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    data = response.json()
    try:
        return data["data"][0]["iataCode"]
    except:
        return None

def search_flights(origin, destination, date):
    token = get_amadeus_token()
    origin_iata = get_iata_code(origin, token)
    destination_iata = get_iata_code(destination, token)

    if not origin_iata or not destination_iata:
        return "Invalid city name. Please try again."

    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "originLocationCode": origin_iata,
        "destinationLocationCode": destination_iata,
        "departureDate": date,
        "adults": 1,
        "currencyCode": "USD",
        "max": 3
    }
    res = requests.get(url, headers=headers, params=params).json()
    flights = res.get("data", [])
    if not flights:
        return "No flights found."

    results = []
    for offer in flights:
        price = offer["price"]["total"]
        duration = offer["itineraries"][0]["duration"].replace("PT", "")
        airline = offer["validatingAirlineCodes"][0]
        results.append(f"${price} - {airline} - {duration}")

    return "\n".join(results)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    origin = data['queryResult']['parameters']['origin']
    destination = data['queryResult']['parameters']['destination']
    date = data['queryResult']['parameters']['date']

    response_text = search_flights(origin, destination, date)

    return jsonify({"fulfillmentText": response_text})

if __name__ == '__main__':
    app.run(debug=True)
