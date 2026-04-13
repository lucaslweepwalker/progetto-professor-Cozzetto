from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import os
from models import APIResponse
import client

app = FastAPI(
    title="F1 Stats API",
    description="Formula 1 statistics powered by Jolpica/Ergast",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_PATH = os.path.join(BASE_DIR, "../f1-frontend")
CIRCUITS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../f1-frontend/img/circuits")


# ---------------------------------------------------------------------------
# Seasons
# ---------------------------------------------------------------------------

@app.get("/seasons", response_model=APIResponse, tags=["Seasons"])
async def list_seasons():
    try:
        seasons = await client.get_seasons()
        return APIResponse(success=True, data=seasons)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------

@app.get("/drivers/{year}", response_model=APIResponse, tags=["Drivers"])
async def driver_standings(year: int):
    try:
        standings = await client.get_driver_standings(year)
        if not standings:
            raise HTTPException(status_code=404, detail=f"No driver standings found for {year}")
        return APIResponse(success=True, data=[s.model_dump() for s in standings])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/drivers/{year}/{driver_id}", response_model=APIResponse, tags=["Drivers"])
async def driver_info(year: int, driver_id: str):
    try:
        driver = await client.get_driver_info(year, driver_id)
        if not driver:
            raise HTTPException(status_code=404, detail=f"Driver '{driver_id}' not found in {year}")
        return APIResponse(success=True, data=driver.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------

@app.get("/constructors/{year}", response_model=APIResponse, tags=["Constructors"])
async def constructor_standings(year: int):
    try:
        standings = await client.get_constructor_standings(year)
        if not standings:
            raise HTTPException(status_code=404, detail=f"No constructor standings found for {year}")
        return APIResponse(success=True, data=[s.model_dump() for s in standings])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/constructors/{year}/{constructor_id}/drivers", response_model=APIResponse, tags=["Constructors"])
async def team_drivers(year: int, constructor_id: str):
    try:
        drivers = await client.get_team_drivers(year, constructor_id)
        return APIResponse(success=True, data=[d.model_dump() for d in drivers])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Circuit images
# ---------------------------------------------------------------------------

@app.get("/circuits/debug", tags=["Circuits"])
async def circuit_debug():
    """Shows resolved path and all found SVG files — use this to diagnose image issues."""
    import os as _os
    resolved = _os.path.abspath(client.CIRCUITS_IMG_PATH)
    files = client.list_circuit_images()
    return {"resolved_path": resolved, "exists": _os.path.isdir(resolved), "files": files}


@app.get("/circuits/image", response_model=APIResponse, tags=["Circuits"])
async def circuit_image(circuit_id: str = Query(...), year: int = Query(...), round: int = Query(None)):
    """
    Resolve the best matching SVG filename for a circuit, year and optional round.
    Example: /circuits/image?circuit_id=bahrain&year=2020&round=16
    """
    filename = client.resolve_circuit_image(circuit_id, year, round)
    if filename:
        return APIResponse(success=True, data={"url": f"/img/circuits/{filename}"})
    return APIResponse(success=True, data={"url": None})


# ---------------------------------------------------------------------------
# Races
# ---------------------------------------------------------------------------

@app.get("/races/{year}", response_model=APIResponse, tags=["Races"])
async def race_list(year: int):
    try:
        races = await client.get_races(year)
        if not races:
            raise HTTPException(status_code=404, detail=f"No races found for {year}")
        return APIResponse(success=True, data=[r.model_dump() for r in races])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/races/{year}/{round_number}/results", response_model=APIResponse, tags=["Races"])
async def race_results(year: int, round_number: int):
    try:
        race = await client.get_race_results(year, round_number)
        if not race:
            raise HTTPException(status_code=404, detail=f"No results found for {year} round {round_number}")
        return APIResponse(success=True, data=race.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/races/{year}/{round_number}/qualifying", response_model=APIResponse, tags=["Races"])
async def qualifying_results(year: int, round_number: int):
    try:
        race = await client.get_qualifying_results(year, round_number)
        if not race:
            raise HTTPException(status_code=404, detail=f"No qualifying found for {year} round {round_number}")
        return APIResponse(success=True, data=race.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/races/{year}/{round_number}/sprint", response_model=APIResponse, tags=["Races"])
async def sprint_results(year: int, round_number: int):
    try:
        race = await client.get_sprint_results(year, round_number)
        if not race:
            raise HTTPException(status_code=404, detail=f"No sprint found for {year} round {round_number}")
        return APIResponse(success=True, data=race.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/races/{year}/{round_number}/pitstops", response_model=APIResponse, tags=["Races"])
async def pit_stops(year: int, round_number: int):
    try:
        stops = await client.get_pit_stops(year, round_number)
        return APIResponse(success=True, data=stops)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# SVG file server — returns SVG files with correct Content-Type header
# ---------------------------------------------------------------------------

from fastapi.responses import FileResponse

@app.get("/img/circuits/{filename}", tags=["Circuits"])
async def serve_circuit_svg(filename: str):
    filepath = os.path.join(CIRCUITS_PATH, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail=f"File not found")
    return FileResponse(filepath, media_type="image/svg+xml")


# ---------------------------------------------------------------------------
# Frontend static files
# ---------------------------------------------------------------------------

app.mount("/", StaticFiles(directory=FRONTEND_PATH, html=True), name="frontend")