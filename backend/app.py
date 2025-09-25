import os
import json
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

FBI_API_KEY = os.getenv("FBI_API_KEY", "")
DEFAULT_TIMEOUT = 12


def safe_get(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Optional[requests.Response]:
	try:
		resp = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
		resp.raise_for_status()
		return resp
	except Exception:
		return None


@app.get("/")
def root() -> Any:
	return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/styles.css")
def styles() -> Any:
	return send_from_directory(FRONTEND_DIR, "styles.css")


@app.get("/app.js")
def app_js() -> Any:
	return send_from_directory(FRONTEND_DIR, "app.js")


@app.get("/api/health")
def health() -> Any:
	return jsonify({"ok": True})


@app.get("/api/weather")
def get_weather() -> Any:
	lat = request.args.get("lat")
	lon = request.args.get("lon")
	if not lat or not lon:
		return jsonify({"error": "lat and lon are required"}), 400

	params = {
		"latitude": lat,
		"longitude": lon,
		"current": ",".join([
			"temperature_2m",
			"precipitation",
			"wind_speed_10m",
			"relative_humidity_2m",
			"weather_code",
		]),
	}
	resp = safe_get("https://api.open-meteo.com/v1/forecast", params=params)
	if not resp:
		return jsonify({"current": None, "source": "open-meteo", "note": "unavailable"}), 502

	data = resp.json()
	return jsonify({"current": data.get("current", {}), "source": "open-meteo"})


@app.get("/api/alerts")
def get_alerts() -> Any:
	lat = request.args.get("lat")
	lon = request.args.get("lon")
	if not lat or not lon:
		return jsonify({"error": "lat and lon are required"}), 400

	nws = safe_get(f"https://api.weather.gov/alerts/active", params={"point": f"{lat},{lon}"}, headers={"Accept": "application/geo+json"})
	alerts = []
	if nws:
		try:
			features = nws.json().get("features", [])
			for f in features:
				props = f.get("properties", {})
				alerts.append({
					"id": f.get("id"),
					"event": props.get("event"),
					"headline": props.get("headline"),
					"areaDesc": props.get("areaDesc"),
					"severity": props.get("severity"),
					"urgency": props.get("urgency"),
					"effective": props.get("effective"),
					"expires": props.get("expires"),
					"instruction": props.get("instruction"),
				})
		except Exception:
			alerts = []

	return jsonify({"alerts": alerts, "source": "NWS"})


@app.get("/api/amber")
def get_amber() -> Any:
	# NCMEC AMBER Alert RSS (nationwide)
	rss_url = "https://www.missingkids.org/feeds/amber.xml"
	resp = safe_get(rss_url)
	if not resp:
		return jsonify({"items": [], "source": "NCMEC", "note": "unavailable"}), 502

	text = resp.text
	# Lightweight, naive extraction of items to avoid adding XML parser dep
	items: list[Dict[str, str]] = []
	for chunk in text.split("<item>")[1:]:
		title_start = chunk.find("<title>")
		title_end = chunk.find("</title>")
		link_start = chunk.find("<link>")
		link_end = chunk.find("</link>")
		desc_start = chunk.find("<description>")
		desc_end = chunk.find("</description>")
		if title_start != -1 and title_end != -1:
			title = chunk[title_start + 7:title_end].strip()
		else:
			title = "AMBER Alert"
		link = chunk[link_start + 6:link_end].strip() if link_start != -1 and link_end != -1 else ""
		description = chunk[desc_start + 13:desc_end].strip() if desc_start != -1 and desc_end != -1 else ""
		items.append({"title": title, "link": link, "description": description})

	return jsonify({"items": items, "source": "NCMEC"})


@app.get("/api/protocols")
def get_protocols() -> Any:
	# Minimal, general-purpose emergency guidance
	protocols = [
		{
			"type": "tornado",
			"title": "Tornado Safety",
			"steps": [
				"Go to a small, windowless interior room on the lowest level.",
				"Cover your head and neck; protect from flying debris.",
				"Avoid windows and large open rooms like gyms.",
			]
		},
		{
			"type": "earthquake",
			"title": "Earthquake Safety",
			"steps": [
				"Drop, Cover, and Hold On.",
				"Stay indoors until shaking stops and it is safe to exit.",
				"If outdoors, move away from buildings, streetlights, and utility wires.",
			]
		},
		{
			"type": "wildfire",
			"title": "Wildfire Safety",
			"steps": [
				"Prepare to evacuate; keep car fueled and backed in.",
				"Keep N95 mask for smoke; close windows and doors.",
				"Follow local evacuation orders immediately.",
			]
		},
		{
			"type": "flood",
			"title": "Flood Safety",
			"steps": [
				"Turn Around, Don't Drown: avoid driving through floodwaters.",
				"Move to higher ground; avoid basements and low-lying areas.",
				"Disconnect electricity if instructed by authorities.",
			]
		}
	]
	return jsonify({"protocols": protocols})


@app.get("/api/crime")
def get_crime() -> Any:
	lat = request.args.get("lat")
	lon = request.args.get("lon")
	if not lat or not lon:
		return jsonify({"error": "lat and lon are required"}), 400

	# Simple coordinate-to-state mapping (approximate)
	lat_f = float(lat)
	lon_f = float(lon)
	state_abbr = None
	
	# Basic US state boundaries (simplified)
	if 24.5 <= lat_f <= 31.0 and -87.6 <= lon_f <= -80.0:
		state_abbr = "FL"
	elif 30.0 <= lat_f <= 35.0 and -88.0 <= lon_f <= -80.0:
		state_abbr = "GA"
	elif 32.0 <= lat_f <= 35.0 and -88.0 <= lon_f <= -80.0:
		state_abbr = "SC"
	elif 33.0 <= lat_f <= 36.0 and -84.0 <= lon_f <= -75.0:
		state_abbr = "NC"
	elif 36.0 <= lat_f <= 39.0 and -84.0 <= lon_f <= -75.0:
		state_abbr = "VA"
	elif 38.0 <= lat_f <= 40.0 and -79.0 <= lon_f <= -75.0:
		state_abbr = "MD"
	elif 39.0 <= lat_f <= 42.0 and -80.0 <= lon_f <= -74.0:
		state_abbr = "PA"
	elif 40.0 <= lat_f <= 45.0 and -79.0 <= lon_f <= -71.0:
		state_abbr = "NY"
	elif 41.0 <= lat_f <= 42.0 and -73.0 <= lon_f <= -71.0:
		state_abbr = "CT"
	elif 41.0 <= lat_f <= 43.0 and -72.0 <= lon_f <= -70.0:
		state_abbr = "MA"
	elif 43.0 <= lat_f <= 45.0 and -72.0 <= lon_f <= -70.0:
		state_abbr = "VT"
	elif 43.0 <= lat_f <= 47.0 and -71.0 <= lon_f <= -66.0:
		state_abbr = "ME"
	elif 40.0 <= lat_f <= 42.0 and -75.0 <= lon_f <= -73.0:
		state_abbr = "NJ"
	elif 38.0 <= lat_f <= 40.0 and -75.0 <= lon_f <= -73.0:
		state_abbr = "DE"
	elif 31.0 <= lat_f <= 37.0 and -114.0 <= lon_f <= -109.0:
		state_abbr = "AZ"
	elif 31.0 <= lat_f <= 37.0 and -115.0 <= lon_f <= -108.0:  # Extended range for Arizona
		state_abbr = "AZ"
	elif 31.0 <= lat_f <= 37.0 and -109.0 <= lon_f <= -103.0:
		state_abbr = "NM"
	elif 25.0 <= lat_f <= 36.0 and -106.0 <= lon_f <= -93.0:
		state_abbr = "TX"
	elif 33.0 <= lat_f <= 37.0 and -94.0 <= lon_f <= -89.0:
		state_abbr = "AR"
	elif 30.0 <= lat_f <= 35.0 and -94.0 <= lon_f <= -88.0:
		state_abbr = "LA"
	elif 30.0 <= lat_f <= 35.0 and -91.0 <= lon_f <= -88.0:
		state_abbr = "MS"
	elif 30.0 <= lat_f <= 35.0 and -88.0 <= lon_f <= -84.0:
		state_abbr = "AL"
	elif 24.0 <= lat_f <= 31.0 and -87.0 <= lon_f <= -80.0:
		state_abbr = "FL"
	elif 40.0 <= lat_f <= 42.0 and -84.0 <= lon_f <= -80.0:
		state_abbr = "OH"
	elif 37.0 <= lat_f <= 40.0 and -85.0 <= lon_f <= -81.0:
		state_abbr = "WV"
	elif 36.0 <= lat_f <= 39.0 and -85.0 <= lon_f <= -81.0:
		state_abbr = "KY"
	elif 35.0 <= lat_f <= 37.0 and -90.0 <= lon_f <= -81.0:
		state_abbr = "TN"
	elif 38.0 <= lat_f <= 40.0 and -88.0 <= lon_f <= -84.0:
		state_abbr = "IN"
	elif 37.0 <= lat_f <= 42.0 and -91.0 <= lon_f <= -87.0:
		state_abbr = "IL"
	elif 40.0 <= lat_f <= 43.0 and -96.0 <= lon_f <= -90.0:
		state_abbr = "IA"
	elif 42.0 <= lat_f <= 47.0 and -97.0 <= lon_f <= -89.0:
		state_abbr = "WI"
	elif 43.0 <= lat_f <= 49.0 and -97.0 <= lon_f <= -89.0:
		state_abbr = "MN"
	elif 40.0 <= lat_f <= 43.0 and -104.0 <= lon_f <= -95.0:
		state_abbr = "NE"
	elif 38.0 <= lat_f <= 40.0 and -102.0 <= lon_f <= -94.0:
		state_abbr = "KS"
	elif 35.0 <= lat_f <= 37.0 and -103.0 <= lon_f <= -94.0:
		state_abbr = "OK"
	elif 36.0 <= lat_f <= 42.0 and -120.0 <= lon_f <= -114.0:
		state_abbr = "NV"
	elif 32.0 <= lat_f <= 42.0 and -124.0 <= lon_f <= -114.0:
		state_abbr = "CA"
	elif 45.0 <= lat_f <= 49.0 and -125.0 <= lon_f <= -116.0:
		state_abbr = "WA"
	elif 42.0 <= lat_f <= 46.0 and -125.0 <= lon_f <= -116.0:
		state_abbr = "OR"
	elif 40.0 <= lat_f <= 45.0 and -111.0 <= lon_f <= -104.0:
		state_abbr = "CO"
	elif 41.0 <= lat_f <= 45.0 and -112.0 <= lon_f <= -104.0:
		state_abbr = "UT"
	elif 42.0 <= lat_f <= 49.0 and -117.0 <= lon_f <= -104.0:
		state_abbr = "MT"
	elif 44.0 <= lat_f <= 49.0 and -117.0 <= lon_f <= -104.0:
		state_abbr = "ND"
	elif 43.0 <= lat_f <= 46.0 and -104.0 <= lon_f <= -96.0:
		state_abbr = "SD"
	elif 40.0 <= lat_f <= 43.0 and -104.0 <= lon_f <= -95.0:
		state_abbr = "WY"
	elif 45.0 <= lat_f <= 49.0 and -125.0 <= lon_f <= -66.0:
		state_abbr = "AK"
	elif 18.0 <= lat_f <= 22.0 and -162.0 <= lon_f <= -154.0:
		state_abbr = "HI"
	
	# Catch-all for specific coordinates that don't match boundaries
	if state_abbr is None:
		if 33.0 <= lat_f <= 34.0 and -112.5 <= lon_f <= -111.0:  # Phoenix area (wider range)
			state_abbr = "AZ"
	
	print(f"DEBUG: Coordinates {lat},{lon} mapped to state: {state_abbr}")

	# Generate location-based mock crime data
	if state_abbr and len(state_abbr) == 2:
		# Create realistic crime data that varies by state
		state_crime_rates = {
			"NY": {"homicide": 5, "robbery": 120, "aggravated_assault": 180, "burglary": 280, "larceny": 1200, "motor_vehicle_theft": 150, "violent_crime": 305, "property_crime": 1630},
			"CA": {"homicide": 4, "robbery": 95, "aggravated_assault": 220, "burglary": 320, "larceny": 1400, "motor_vehicle_theft": 280, "violent_crime": 319, "property_crime": 2000},
			"TX": {"homicide": 6, "robbery": 110, "aggravated_assault": 250, "burglary": 350, "larceny": 1100, "motor_vehicle_theft": 200, "violent_crime": 366, "property_crime": 1650},
			"FL": {"homicide": 7, "robbery": 130, "aggravated_assault": 200, "burglary": 300, "larceny": 1000, "motor_vehicle_theft": 180, "violent_crime": 337, "property_crime": 1480},
			"AZ": {"homicide": 8, "robbery": 140, "aggravated_assault": 280, "burglary": 400, "larceny": 900, "motor_vehicle_theft": 250, "violent_crime": 428, "property_crime": 1550},
			"IL": {"homicide": 9, "robbery": 150, "aggravated_assault": 300, "burglary": 450, "larceny": 800, "motor_vehicle_theft": 220, "violent_crime": 459, "property_crime": 1470},
			"PA": {"homicide": 5, "robbery": 100, "aggravated_assault": 180, "burglary": 250, "larceny": 700, "motor_vehicle_theft": 150, "violent_crime": 285, "property_crime": 1100},
			"OH": {"homicide": 6, "robbery": 110, "aggravated_assault": 200, "burglary": 280, "larceny": 750, "motor_vehicle_theft": 160, "violent_crime": 316, "property_crime": 1190},
			"GA": {"homicide": 7, "robbery": 120, "aggravated_assault": 220, "burglary": 320, "larceny": 850, "motor_vehicle_theft": 180, "violent_crime": 347, "property_crime": 1350},
			"NC": {"homicide": 6, "robbery": 105, "aggravated_assault": 190, "burglary": 270, "larceny": 720, "motor_vehicle_theft": 140, "violent_crime": 301, "property_crime": 1130},
			"MI": {"homicide": 8, "robbery": 125, "aggravated_assault": 240, "burglary": 350, "larceny": 780, "motor_vehicle_theft": 200, "violent_crime": 373, "property_crime": 1330},
			"NJ": {"homicide": 4, "robbery": 90, "aggravated_assault": 160, "burglary": 220, "larceny": 650, "motor_vehicle_theft": 120, "violent_crime": 254, "property_crime": 990},
			"VA": {"homicide": 5, "robbery": 95, "aggravated_assault": 170, "burglary": 240, "larceny": 680, "motor_vehicle_theft": 130, "violent_crime": 270, "property_crime": 1050},
			"WA": {"homicide": 4, "robbery": 85, "aggravated_assault": 150, "burglary": 200, "larceny": 600, "motor_vehicle_theft": 110, "violent_crime": 239, "property_crime": 910},
			"MA": {"homicide": 3, "robbery": 80, "aggravated_assault": 140, "burglary": 180, "larceny": 550, "motor_vehicle_theft": 100, "violent_crime": 223, "property_crime": 830},
			"TN": {"homicide": 7, "robbery": 115, "aggravated_assault": 210, "burglary": 290, "larceny": 760, "motor_vehicle_theft": 170, "violent_crime": 332, "property_crime": 1220},
			"IN": {"homicide": 6, "robbery": 100, "aggravated_assault": 180, "burglary": 260, "larceny": 700, "motor_vehicle_theft": 150, "violent_crime": 286, "property_crime": 1110},
			"MO": {"homicide": 8, "robbery": 130, "aggravated_assault": 250, "burglary": 340, "larceny": 820, "motor_vehicle_theft": 190, "violent_crime": 388, "property_crime": 1350},
			"MD": {"homicide": 9, "robbery": 140, "aggravated_assault": 270, "burglary": 380, "larceny": 900, "motor_vehicle_theft": 210, "violent_crime": 419, "property_crime": 1490},
			"WI": {"homicide": 5, "robbery": 90, "aggravated_assault": 160, "burglary": 220, "larceny": 620, "motor_vehicle_theft": 120, "violent_crime": 255, "property_crime": 960},
			"CO": {"homicide": 4, "robbery": 85, "aggravated_assault": 150, "burglary": 200, "larceny": 580, "motor_vehicle_theft": 110, "violent_crime": 239, "property_crime": 890},
			"MN": {"homicide": 3, "robbery": 75, "aggravated_assault": 130, "burglary": 180, "larceny": 520, "motor_vehicle_theft": 100, "violent_crime": 208, "property_crime": 800},
			"SC": {"homicide": 8, "robbery": 125, "aggravated_assault": 230, "burglary": 320, "larceny": 800, "motor_vehicle_theft": 180, "violent_crime": 363, "property_crime": 1300},
			"AL": {"homicide": 9, "robbery": 135, "aggravated_assault": 260, "burglary": 360, "larceny": 850, "motor_vehicle_theft": 200, "violent_crime": 404, "property_crime": 1420},
			"LA": {"homicide": 12, "robbery": 160, "aggravated_assault": 320, "burglary": 420, "larceny": 950, "motor_vehicle_theft": 250, "violent_crime": 492, "property_crime": 1620},
			"KY": {"homicide": 6, "robbery": 105, "aggravated_assault": 190, "burglary": 270, "larceny": 720, "motor_vehicle_theft": 150, "violent_crime": 301, "property_crime": 1140},
			"OR": {"homicide": 4, "robbery": 80, "aggravated_assault": 140, "burglary": 190, "larceny": 560, "motor_vehicle_theft": 110, "violent_crime": 224, "property_crime": 860},
			"OK": {"homicide": 7, "robbery": 115, "aggravated_assault": 220, "burglary": 300, "larceny": 750, "motor_vehicle_theft": 170, "violent_crime": 342, "property_crime": 1220},
			"CT": {"homicide": 3, "robbery": 70, "aggravated_assault": 120, "burglary": 160, "larceny": 480, "motor_vehicle_theft": 90, "violent_crime": 193, "property_crime": 730},
			"UT": {"homicide": 2, "robbery": 60, "aggravated_assault": 100, "burglary": 140, "larceny": 400, "motor_vehicle_theft": 80, "violent_crime": 162, "property_crime": 620},
			"IA": {"homicide": 2, "robbery": 55, "aggravated_assault": 90, "burglary": 120, "larceny": 350, "motor_vehicle_theft": 70, "violent_crime": 147, "property_crime": 540},
			"NV": {"homicide": 6, "robbery": 110, "aggravated_assault": 200, "burglary": 280, "larceny": 700, "motor_vehicle_theft": 160, "violent_crime": 316, "property_crime": 1140},
			"AR": {"homicide": 8, "robbery": 125, "aggravated_assault": 240, "burglary": 330, "larceny": 780, "motor_vehicle_theft": 180, "violent_crime": 373, "property_crime": 1290},
			"MS": {"homicide": 10, "robbery": 145, "aggravated_assault": 280, "burglary": 380, "larceny": 900, "motor_vehicle_theft": 220, "violent_crime": 435, "property_crime": 1500},
			"KS": {"homicide": 5, "robbery": 90, "aggravated_assault": 160, "burglary": 220, "larceny": 620, "motor_vehicle_theft": 130, "violent_crime": 255, "property_crime": 970},
			"NM": {"homicide": 8, "robbery": 130, "aggravated_assault": 250, "burglary": 340, "larceny": 800, "motor_vehicle_theft": 190, "violent_crime": 388, "property_crime": 1330},
			"NE": {"homicide": 3, "robbery": 65, "aggravated_assault": 110, "burglary": 150, "larceny": 420, "motor_vehicle_theft": 90, "violent_crime": 178, "property_crime": 660},
			"WV": {"homicide": 6, "robbery": 100, "aggravated_assault": 180, "burglary": 250, "larceny": 680, "motor_vehicle_theft": 140, "violent_crime": 286, "property_crime": 1070},
			"ID": {"homicide": 2, "robbery": 50, "aggravated_assault": 80, "burglary": 110, "larceny": 320, "motor_vehicle_theft": 60, "violent_crime": 132, "property_crime": 490},
			"HI": {"homicide": 2, "robbery": 45, "aggravated_assault": 70, "burglary": 100, "larceny": 280, "motor_vehicle_theft": 50, "violent_crime": 117, "property_crime": 430},
			"NH": {"homicide": 1, "robbery": 40, "aggravated_assault": 60, "burglary": 80, "larceny": 240, "motor_vehicle_theft": 40, "violent_crime": 101, "property_crime": 360},
			"ME": {"homicide": 1, "robbery": 35, "aggravated_assault": 50, "burglary": 70, "larceny": 200, "motor_vehicle_theft": 35, "violent_crime": 86, "property_crime": 305},
			"MT": {"homicide": 2, "robbery": 45, "aggravated_assault": 70, "burglary": 90, "larceny": 260, "motor_vehicle_theft": 50, "violent_crime": 117, "property_crime": 400},
			"RI": {"homicide": 2, "robbery": 50, "aggravated_assault": 80, "burglary": 100, "larceny": 300, "motor_vehicle_theft": 60, "violent_crime": 132, "property_crime": 460},
			"DE": {"homicide": 4, "robbery": 70, "aggravated_assault": 120, "burglary": 160, "larceny": 480, "motor_vehicle_theft": 100, "violent_crime": 194, "property_crime": 740},
			"SD": {"homicide": 2, "robbery": 40, "aggravated_assault": 60, "burglary": 80, "larceny": 220, "motor_vehicle_theft": 40, "violent_crime": 102, "property_crime": 340},
			"ND": {"homicide": 1, "robbery": 30, "aggravated_assault": 40, "burglary": 60, "larceny": 160, "motor_vehicle_theft": 30, "violent_crime": 71, "property_crime": 250},
			"AK": {"homicide": 4, "robbery": 60, "aggravated_assault": 100, "burglary": 120, "larceny": 360, "motor_vehicle_theft": 80, "violent_crime": 164, "property_crime": 560},
			"VT": {"homicide": 1, "robbery": 25, "aggravated_assault": 35, "burglary": 50, "larceny": 140, "motor_vehicle_theft": 25, "violent_crime": 61, "property_crime": 215},
			"WY": {"homicide": 1, "robbery": 20, "aggravated_assault": 30, "burglary": 40, "larceny": 120, "motor_vehicle_theft": 20, "violent_crime": 51, "property_crime": 180}
		}
		
		crime_data = state_crime_rates.get(state_abbr, {
			"homicide": 5, "robbery": 100, "aggravated_assault": 180, "burglary": 250, 
			"larceny": 700, "motor_vehicle_theft": 150, "violent_crime": 285, "property_crime": 1100
		})
		
		return jsonify({
			"scope": "state",
			"source": "mock",
			"state": state_abbr,
			"stats": crime_data
		})

	# Fallback to demo data
	return jsonify({
		"scope": "demo",
		"source": "demo",
		"state": state_abbr,
		"stats": {
			"homicide": 3,
			"robbery": 55,
			"aggravated_assault": 210,
			"burglary": 230,
			"larceny": 900,
			"motor_vehicle_theft": 220,
			"violent_crime": 420,
			"property_crime": 1350,
			"year": 2023
		}
	})


if __name__ == "__main__":
	port = int(os.getenv("PORT", "5002"))
	app.run(host="0.0.0.0", port=port)
