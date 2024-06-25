from fastapi import FastAPI
from pydantic import BaseModel
from . import pv_system_calculations as pv_calc
from fastapi.middleware.cors import CORSMiddleware


# Allow CORS for frontend
origins = [
    "http://localhost:3000",  # Allow frontend origin
    "http://helios-connect-frontend.185.170.114.79.sslip.io"
    # Add any other origins as needed
]

app = FastAPI()

# Add CORSMiddleware to the application
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

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
    el_demand_timeseries =pv_calc.estimate_hourly_el_consumption(house)
    cost_savings_GGV, profit_grid_feed_in = pv_calc.calculate_cost_savings(el_production_timeseries, el_demand_timeseries)
    return {
        "annual_el_production": annual_el_production,
        "cost_savings_GGV": cost_savings_GGV,
        "profit_grid_feed_in": profit_grid_feed_in,
        # "CO2_reduction": co2_reduction 
    }