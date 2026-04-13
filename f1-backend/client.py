import httpx
import os
import re
from typing import List, Optional
from models import (
    Driver, DriverStanding,
    Constructor, ConstructorStanding,
    Race, RaceResult
)

BASE_URL = "https://api.jolpi.ca/ergast/f1"

# Path to the circuits image folder
# Works whether uvicorn is run from f1-backend/ or the project root
_here = os.path.dirname(os.path.abspath(__file__))
CIRCUITS_IMG_PATH = os.path.join(_here, "../f1-frontend/img/circuits")

# Simple in-memory cache
_cache: dict = {}


async def _get(url: str) -> dict:
    if url in _cache:
        return _cache[url]
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        _cache[url] = data
        return data


# ---------------------------------------------------------------------------
# Circuit image resolution
# ---------------------------------------------------------------------------

def list_circuit_images() -> List[str]:
    """Return all SVG filenames in the circuits image folder."""
    try:
        files = os.listdir(CIRCUITS_IMG_PATH)
        return [f for f in files if f.endswith(".svg")]
    except FileNotFoundError:
        return []


def resolve_circuit_image(circuit_id: str, year: int, round_number: Optional[int] = None) -> Optional[str]:
    """
    Given a circuit_id, year and optional round number, find the best matching SVG filename.
    Priority:
      1. circuitId_year_rROUND.svg        exact year + round (e.g. bahrain_2020_r16.svg)
      2. circuitId_startYear_endYear.svg  year falls within range (e.g. adelaide_1985_1995.svg)
      3. circuitId.svg                    default fallback
      4. None                             no match
    """
    files = list_circuit_images()
    escaped = re.escape(circuit_id)

    # 1. Exact year + round match: circuitId_year_rROUND.svg
    if round_number is not None:
        exact = f"{circuit_id}_{year}_r{round_number}.svg"
        if exact in files:
            return exact

    # 2. Year range match: circuitId_startYear_endYear.svg
    # Uses re.escape so circuit IDs with underscores (e.g. albert_park) work correctly.
    range_pattern = re.compile(rf"^{escaped}_(\d{{4}})_(\d{{4}})\.svg$")
    matches = []
    for filename in files:
        m = range_pattern.match(filename)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            if start <= year <= end:
                matches.append((end - start, filename))

    if matches:
        matches.sort(key=lambda x: x[0])  # smallest range wins (most specific)
        return matches[0][1]

    # 3. Default fallback: circuitId.svg
    default = f"{circuit_id}.svg"
    if default in files:
        return default

    return None


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _parse_driver(raw: dict) -> Driver:
    return Driver(
        driver_id=raw.get("driverId", ""),
        code=raw.get("code"),
        number=raw.get("permanentNumber"),
        first_name=raw.get("givenName", ""),
        last_name=raw.get("familyName", ""),
        nationality=raw.get("nationality", ""),
        date_of_birth=raw.get("dateOfBirth"),
        url=raw.get("url"),
    )


def _parse_constructor(raw: dict) -> Constructor:
    return Constructor(
        constructor_id=raw.get("constructorId", ""),
        name=raw.get("name", ""),
        nationality=raw.get("nationality", ""),
        url=raw.get("url"),
    )


def _parse_race_result(raw: dict) -> RaceResult:
    fastest_lap = raw.get("FastestLap", {})
    fastest_lap_time = fastest_lap.get("Time", {}).get("time") if fastest_lap else None
    fastest_lap_rank = fastest_lap.get("rank") if fastest_lap else None
    return RaceResult(
        position=raw.get("position"),
        driver=_parse_driver(raw.get("Driver", {})),
        constructor_name=raw.get("Constructor", {}).get("name", ""),
        grid=raw.get("grid"),
        laps=raw.get("laps"),
        status=raw.get("status"),
        fastest_lap_time=fastest_lap_time,
        fastest_lap_rank=fastest_lap_rank,
        points=float(raw.get("points", 0)),
    )


# ---------------------------------------------------------------------------
# Public API functions
# ---------------------------------------------------------------------------

async def get_driver_standings(year: int) -> List[DriverStanding]:
    url = f"{BASE_URL}/{year}/driverStandings.json"
    data = await _get(url)
    standings_list = (
        data["MRData"]["StandingsTable"]
        ["StandingsLists"][0]["DriverStandings"]
    )
    result = []
    for item in standings_list:
        result.append(DriverStanding(
            position=int(item.get("position", 0)),
            points=float(item.get("points", 0)),
            wins=int(item.get("wins", 0)),
            driver=_parse_driver(item.get("Driver", {})),
            constructor_name=item["Constructors"][0]["name"] if item.get("Constructors") else "",
        ))
    return result


async def get_driver_info(year: int, driver_id: str) -> Optional[DriverStanding]:
    standings = await get_driver_standings(year)
    for standing in standings:
        if standing.driver.driver_id == driver_id:
            return standing
    return None


async def get_constructor_standings(year: int) -> List[ConstructorStanding]:
    url = f"{BASE_URL}/{year}/constructorStandings.json"
    data = await _get(url)
    standings_list = (
        data["MRData"]["StandingsTable"]
        ["StandingsLists"][0]["ConstructorStandings"]
    )
    result = []
    for item in standings_list:
        result.append(ConstructorStanding(
            position=int(item.get("position", 0)),
            points=float(item.get("points", 0)),
            wins=int(item.get("wins", 0)),
            constructor=_parse_constructor(item.get("Constructor", {})),
        ))
    return result


async def get_races(year: int) -> List[Race]:
    url = f"{BASE_URL}/{year}/races.json?limit=100"
    data = await _get(url)
    races_raw = data["MRData"]["RaceTable"]["Races"]
    result = []
    for r in races_raw:
        circuit = r.get("Circuit", {})
        circuit_id = circuit.get("circuitId", "")
        result.append(Race(
            season=int(r.get("season", year)),
            round=int(r.get("round", 0)),
            race_name=r.get("raceName", ""),
            circuit_name=circuit.get("circuitName", ""),
            circuit_id=circuit_id,
            circuit_wiki_url=circuit.get("url"),
            country=circuit.get("Location", {}).get("country", ""),
            date=r.get("date", ""),
            results=None,
        ))
    return result


async def get_race_results(year: int, round_number: int) -> Optional[Race]:
    url = f"{BASE_URL}/{year}/{round_number}/results.json"
    data = await _get(url)
    races_raw = data["MRData"]["RaceTable"]["Races"]
    if not races_raw:
        return None
    r = races_raw[0]
    circuit = r.get("Circuit", {})
    circuit_id = circuit.get("circuitId", "")
    results = [_parse_race_result(res) for res in r.get("Results", [])]
    return Race(
        season=int(r.get("season", year)),
        round=int(r.get("round", round_number)),
        race_name=r.get("raceName", ""),
        circuit_name=circuit.get("circuitName", ""),
        circuit_id=circuit_id,
        circuit_wiki_url=circuit.get("url"),
        country=circuit.get("Location", {}).get("country", ""),
        date=r.get("date", ""),
        results=results,
    )


async def get_qualifying_results(year: int, round_number: int) -> Optional[Race]:
    url = f"{BASE_URL}/{year}/{round_number}/qualifying.json"
    data = await _get(url)
    races_raw = data["MRData"]["RaceTable"]["Races"]
    if not races_raw:
        return None
    r = races_raw[0]
    circuit = r.get("Circuit", {})
    quali_results = []
    for item in r.get("QualifyingResults", []):
        quali_results.append(RaceResult(
            position=item.get("position"),
            driver=_parse_driver(item.get("Driver", {})),
            constructor_name=item.get("Constructor", {}).get("name", ""),
            grid=None,
            laps=None,
            status=item.get("Q3") or item.get("Q2") or item.get("Q1"),
            fastest_lap_time=item.get("Q1"),
            fastest_lap_rank=None,
            points=None,
        ))
    return Race(
        season=int(r.get("season", year)),
        round=int(r.get("round", round_number)),
        race_name=r.get("raceName", ""),
        circuit_name=circuit.get("circuitName", ""),
        circuit_id=circuit.get("circuitId", ""),
        circuit_wiki_url=circuit.get("url"),
        country=circuit.get("Location", {}).get("country", ""),
        date=r.get("date", ""),
        results=quali_results,
    )


async def get_sprint_results(year: int, round_number: int) -> Optional[Race]:
    url = f"{BASE_URL}/{year}/{round_number}/sprint.json"
    try:
        data = await _get(url)
        races_raw = data["MRData"]["RaceTable"]["Races"]
        if not races_raw:
            return None
        r = races_raw[0]
        circuit = r.get("Circuit", {})
        results = [_parse_race_result(res) for res in r.get("SprintResults", [])]
        return Race(
            season=int(r.get("season", year)),
            round=int(r.get("round", round_number)),
            race_name=r.get("raceName", ""),
            circuit_name=circuit.get("circuitName", ""),
            circuit_id=circuit.get("circuitId", ""),
            circuit_wiki_url=circuit.get("url"),
            country=circuit.get("Location", {}).get("country", ""),
            date=r.get("date", ""),
            results=results,
        )
    except Exception:
        return None


async def get_pit_stops(year: int, round_number: int) -> list:
    url = f"{BASE_URL}/{year}/{round_number}/pitstops.json?limit=100"
    try:
        data = await _get(url)
        races_raw = data["MRData"]["RaceTable"]["Races"]
        if not races_raw:
            return []
        return races_raw[0].get("PitStops", [])
    except Exception:
        return []


async def get_team_drivers(year: int, constructor_id: str) -> List[DriverStanding]:
    url = f"{BASE_URL}/{year}/constructors/{constructor_id}/driverStandings.json"
    try:
        data = await _get(url)
        standings_lists = data["MRData"]["StandingsTable"]["StandingsLists"]
        if not standings_lists:
            return []
        driver_standings = standings_lists[0].get("DriverStandings", [])
        result = []
        for item in driver_standings:
            result.append(DriverStanding(
                position=int(item.get("position", 0)),
                points=float(item.get("points", 0)),
                wins=int(item.get("wins", 0)),
                driver=_parse_driver(item.get("Driver", {})),
                constructor_name=item["Constructors"][0]["name"] if item.get("Constructors") else "",
            ))
        return result
    except Exception:
        return []


async def get_seasons() -> List[int]:
    url = f"{BASE_URL}/seasons.json?limit=100"
    data = await _get(url)
    seasons = data["MRData"]["SeasonTable"]["Seasons"]
    return sorted([int(s["season"]) for s in seasons], reverse=True)