from pydantic import BaseModel
from typing import Optional, List


class Driver(BaseModel):
    driver_id: str
    code: Optional[str]
    number: Optional[str]
    first_name: str
    last_name: str
    nationality: str
    date_of_birth: Optional[str]
    url: Optional[str]


class DriverStanding(BaseModel):
    position: int
    points: float
    wins: int
    driver: Driver
    constructor_name: str


class Constructor(BaseModel):
    constructor_id: str
    name: str
    nationality: str
    url: Optional[str]


class ConstructorStanding(BaseModel):
    position: int
    points: float
    wins: int
    constructor: Constructor


class RaceResult(BaseModel):
    position: Optional[str]
    driver: Driver
    constructor_name: str
    grid: Optional[str]
    laps: Optional[str]
    status: Optional[str]
    fastest_lap_time: Optional[str]
    fastest_lap_rank: Optional[str]
    points: Optional[float]


class Race(BaseModel):
    season: int
    round: int
    race_name: str
    circuit_name: str
    circuit_id: Optional[str]          # e.g. "monza" — used to resolve local SVG
    circuit_wiki_url: Optional[str]
    country: str
    date: str
    results: Optional[List[RaceResult]] = None


class APIResponse(BaseModel):
    success: bool
    data: object
    message: Optional[str] = None