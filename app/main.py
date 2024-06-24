from fastapi import FastAPI
from pydantic import BaseModel
import pv_system_calculations as pv_calc
from typing import List, Optional

app = FastAPI()

class Location(BaseModel):
    longitude: float
    latitude: float

class Rooftop(BaseModel):
    tilt_angle: float
    azimut_angle: float

class House(BaseModel):
    location: Location
    rooftop: Rooftop
    # number_of_people: int
    annual_el_demand: float
    # current_el_price: float # in €/kWh

# @app.get("/")
# async def root():
#     return {"message": "Hello World"}

@app.post("/api/calculate")
def calculate_pv_system(house: House):
    pv_system = pv_calc.create_pv_system(house.annual_el_demand)
    annual_el_production, el_production_timeseries = pv_calc.calculate_hourly_el_production(house,pv_system)
    el_production_timeseries =pv_calc.estimate_hourly_el_consumption(house)
    # cost_savings = pv_calc.calculate_cost_savings(el_production_timeseries, el_production_timeseries)
    return {
        "annual_el_production": annual_el_production,
        # "cost_savings": cost_savings,
        # "CO2_reduction": co2_reduction 
    }