## Alert Hub

A minimal full-stack app that serves local weather, government alerts (NWS), AMBER alerts (NCMEC RSS), emergency protocols, and crime statistics (FBI API if configured). Frontend uses browser geolocation.

### Prerequisites
- Python 3.10+
- macOS/Linux/Windows

### Setup
1. Create and activate venv, install deps:
```bash
cd /Users/cgy/Downloads/Alert
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. (Optional) Configure FBI API key for real crime statistics:
- Get a key from `https://api.usa.gov/crime/fbi/sapi/api/signed`.
- Export env variable or put into your shell profile:
```bash
export FBI_API_KEY=your_key_here
export PORT=5002
```

If you cannot set dotfiles in this workspace, you can export the variables in the same terminal before running.

### Run
```bash
source .venv/bin/activate
python backend/app.py
```
Open `http://localhost:5002` in your browser, click "Use My Location".

### API Endpoints
- `GET /api/health` – health check
- `GET /api/weather?lat=..&lon=..` – current weather via Open-Meteo
- `GET /api/alerts?lat=..&lon=..` – active NWS alerts for the point
- `GET /api/amber` – NCMEC AMBER alert RSS items (nationwide)
- `GET /api/protocols` – curated emergency protocols
- `GET /api/crime?lat=..&lon=..` – state-level FBI stats if `FBI_API_KEY` set; demo otherwise

### Notes
- NWS requires a valid User-Agent per policy; the current usage is light. For production, consider adding a contact email header.
- AMBER feed parsing is simplified; switch to an XML parser (e.g., `feedparser`) for robustness.
- Crime stats resolve state from reverse geocoding; for city/agency-level data, integrate place-to-ORI mapping.
# Alert_Hub
