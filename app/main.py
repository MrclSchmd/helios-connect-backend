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

# Define the data models for location, rooftop, and house
class Location(BaseModel):
    longitude: float
    latitude: float

class Rooftop(BaseModel):
    tilt_angle: float
    azimut_angle: float

class House(BaseModel):
    location: Location
    rooftop: Rooftop
    annual_el_demand: float

# Define the API endpoint for the calculation
@app.post("/api/calculate")
def calculate_pv_system(house: House):
    """
    Calculates the performance and basic economic data of a photovoltaic (PV) system for a given house.

    Parameters:
        house (House): Object containing information about the annual electricity demand, location, and rooftop of the house.

    Returns:
        dict: A dictionary containing the following information:
            - annual_el_production (float): The annual electricity production of the PV system.
            - monthly_el_production (list): A list of monthly electricity production values.
            - cost_savings_GGV (float): The cost savings from using the PV system within the GGV.
            - profit_grid_feed_in (float): The profit from feeding excess electricity into the grid.
            - payback_period (float): The payback period of the PV system in years.
            - annual_CO2_reduction (float): The annual CO2 reduction achieved by using the PV system.
            - monthly_CO2_reduction (list): A list of monthly CO2 reduction values.
    """
    pv_system = pv_calc.create_pv_system(house.annual_el_demand)
    annual_el_production, el_production_timeseries, monthly_el_production = pv_calc.calculate_hourly_el_production(house,pv_system)
    el_demand_timeseries = pv_calc.estimate_hourly_el_consumption(house)
    cost_savings_GGV, profit_grid_feed_in = pv_calc.calculate_cost_savings(el_production_timeseries, el_demand_timeseries)
    payback_period = pv_calc.calculate_payback_period(cost_savings_GGV, profit_grid_feed_in, pv_system.total_cost)
    annual_CO2_reduction, monthly_CO2_reduction = pv_calc.calculate_CO2_reduction(monthly_el_production)

    return {
        "annual_el_production": annual_el_production,
        "monthly_el_production": monthly_el_production,
        "cost_savings_GGV": cost_savings_GGV,
        "profit_grid_feed_in": profit_grid_feed_in,
        "payback_period": payback_period,
        "annual_CO2_reduction": annual_CO2_reduction,
        "monthly_CO2_reduction": monthly_CO2_reduction
    }