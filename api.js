const BASE_URL = "http://localhost:8000";

async function _get(endpoint) {
    const response = await fetch(`${BASE_URL}${endpoint}`);
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Unknown error");
    }
    const json = await response.json();
    if (!json.success) throw new Error(json.message || "API returned success: false");
    return json.data;
}

// ---------------------------------------------------------------------------
// Seasons
// ---------------------------------------------------------------------------

async function getSeasons() {
    return await _get("/seasons");
}

// ---------------------------------------------------------------------------
// Drivers
// ---------------------------------------------------------------------------

async function getDriverStandings(year) {
    return await _get(`/drivers/${year}`);
}

async function getDriverInfo(year, driverId) {
    return await _get(`/drivers/${year}/${driverId}`);
}

// ---------------------------------------------------------------------------
// Constructors
// ---------------------------------------------------------------------------

async function getConstructorStandings(year) {
    return await _get(`/constructors/${year}`);
}

async function getTeamDrivers(year, constructorId) {
    return await _get(`/constructors/${year}/${constructorId}/drivers`);
}

// ---------------------------------------------------------------------------
// Circuit images
// ---------------------------------------------------------------------------

/**
 * Resolve the best matching local SVG for a circuit and year.
 * Returns a full URL to the image (e.g. "http://localhost:8000/img/circuits/monza.svg")
 * or null if no file exists for that circuit.
 */
async function getCircuitImageUrl(circuitId, year, round = null) {
    if (!circuitId) return null;
    try {
        let endpoint = `/circuits/image?circuit_id=${encodeURIComponent(circuitId)}&year=${year}`;
        if (round !== null) endpoint += `&round=${round}`;
        const data = await _get(endpoint);
        if (!data.url) return null;
        return `${BASE_URL}${data.url}`;
    } catch {
        return null;
    }
}

// ---------------------------------------------------------------------------
// Races
// ---------------------------------------------------------------------------

async function getRaces(year) {
    return await _get(`/races/${year}`);
}

async function getRaceResults(year, round) {
    return await _get(`/races/${year}/${round}/results`);
}

async function getQualifyingResults(year, round) {
    return await _get(`/races/${year}/${round}/qualifying`);
}

async function getSprintResults(year, round) {
    return await _get(`/races/${year}/${round}/sprint`);
}

async function getPitStops(year, round) {
    return await _get(`/races/${year}/${round}/pitstops`);
}