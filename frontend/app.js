const $ = (sel) => document.querySelector(sel);

async function fetchJSON(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    return await res.json();
}

function setCoords(lat, lon) {
    $("#coords").textContent = `Latitude: ${lat.toFixed(4)}, Longitude: ${lon.toFixed(4)}`;
}

function formatWeather(weather) {
    if (!weather || !weather.current) return "No weather data available";
    const w = weather.current;
    return `Temperature: ${w.temperature_2m}°C (${Math.round(w.temperature_2m * 9 / 5 + 32)}°F)
Precipitation: ${w.precipitation}mm
Wind Speed: ${w.wind_speed_10m} km/h
Humidity: ${w.relative_humidity_2m}%
Weather Code: ${w.weather_code}`;
}

async function loadAll(lat, lon) {
    setCoords(lat, lon);
    try {
        const weather = await fetchJSON(`/api/weather?lat=${lat}&lon=${lon}`);
        $("#weatherData").textContent = formatWeather(weather);
    } catch (e) {
        $("#weatherData").textContent = "Weather unavailable.";
    }

    try {
        const alerts = await fetchJSON(`/api/alerts?lat=${lat}&lon=${lon}`);
        const list = $("#alertsList");
        list.innerHTML = "";
        (alerts.alerts || []).slice(0, 10).forEach((a) => {
            const li = document.createElement("li");
            li.textContent = `${a.event || "Alert"}: ${a.headline || a.areaDesc || ""}`;
            list.appendChild(li);
        });
    } catch (e) {
        $("#alertsList").innerHTML = "<li>Alerts unavailable.</li>";
    }

    try {
        const amber = await fetchJSON(`/api/amber`);
        const list = $("#amberList");
        list.innerHTML = "";
        (amber.items || []).slice(0, 10).forEach((i) => {
            const li = document.createElement("li");
            const a = document.createElement("a");
            a.href = i.link || "#";
            a.target = "_blank";
            a.textContent = i.title || "AMBER Alert";
            li.appendChild(a);
            list.appendChild(li);
        });
    } catch (e) {
        $("#amberList").innerHTML = "<li>AMBER feed unavailable.</li>";
    }

    try {
        const protocols = await fetchJSON(`/api/protocols`);
        const wrap = $("#protocolsList");
        wrap.innerHTML = "";
        (protocols.protocols || []).forEach((p) => {
            const div = document.createElement("div");
            div.className = "protocol";
            const h3 = document.createElement("h3");
            h3.textContent = p.title;
            div.appendChild(h3);
            const ol = document.createElement("ol");
            p.steps.forEach((s) => {
                const li = document.createElement("li");
                li.textContent = s;
                ol.appendChild(li);
            });
            div.appendChild(ol);
            wrap.appendChild(div);
        });
    } catch (e) {
        $("#protocolsList").textContent = "Protocols unavailable.";
    }

    function formatCrime(crime) {
        if (!crime || !crime.stats) return "No crime data available";
        const s = crime.stats;
        const year = s.year || "N/A";
        return `Crime Statistics (${year})
State: ${crime.state || "Unknown"}

Violent Crime: ${s.violent_crime || "N/A"}
• Homicide: ${s.homicide || "N/A"}
• Robbery: ${s.robbery || "N/A"}
• Aggravated Assault: ${s.aggravated_assault || "N/A"}

Property Crime: ${s.property_crime || "N/A"}
• Burglary: ${s.burglary || "N/A"}
• Larceny: ${s.larceny || "N/A"}
• Motor Vehicle Theft: ${s.motor_vehicle_theft || "N/A"}

Source: ${crime.source || "Unknown"}`;
    }

    try {
        const crime = await fetchJSON(`/api/crime?lat=${lat}&lon=${lon}`);
        $("#crimeData").textContent = formatCrime(crime);
    } catch (e) {
        $("#crimeData").textContent = "Crime data unavailable.";
    }
}

async function geocodeZipcode(zipcode) {
    try {
        const response = await fetch(`https://api.zippopotam.us/us/${zipcode}`);
        if (!response.ok) throw new Error("Invalid ZIP code");
        const data = await response.json();
        const place = data.places[0];
        return {
            latitude: parseFloat(place.latitude),
            longitude: parseFloat(place.longitude),
            city: place["place name"],
            state: place.state
        };
    } catch (error) {
        throw new Error("Could not find coordinates for ZIP code");
    }
}

$("#locateBtn").addEventListener("click", () => {
    if (!navigator.geolocation) {
        alert("Geolocation not supported.");
        return;
    }
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const { latitude, longitude } = pos.coords;
            loadAll(latitude, longitude);
        },
        (err) => {
            alert("Failed to get location: " + err.message);
        }
    );
});

$("#zipcodeBtn").addEventListener("click", async () => {
    const zipcode = $("#zipcodeInput").value.trim();
    if (!zipcode || zipcode.length !== 5 || !/^\d+$/.test(zipcode)) {
        alert("Please enter a valid 5-digit ZIP code");
        return;
    }

    try {
        const location = await geocodeZipcode(zipcode);
        loadAll(location.latitude, location.longitude);
        $("#coords").textContent = `${location.city}, ${location.state} (ZIP: ${zipcode})`;
    } catch (error) {
        alert(error.message);
    }
});

$("#zipcodeInput").addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
        $("#zipcodeBtn").click();
    }
});
