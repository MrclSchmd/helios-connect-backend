import sys
import os

# Get the absolute path of the project directory
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_path not in sys.path:
    sys.path.append(project_path)

from app import pv_system_calculations as pv_calc

# Define the Location class
class Location:
    longitude: float
    latitude: float

# Define the Rooftop class
class Rooftop:
    tilt_angle: float
    azimut_angle: float

# Define the house class
class house:
    location: Location
    rooftop: Rooftop
    annual_el_demand: float

# Define the pv_system class
class pv_system:
    size = float
    cost_per_kWp = float
    annual_production = float

# Set the values for Location, Rooftop, house, and pv_system
Location.latitude = 48.1374
Location.longitude = 11.5755
Rooftop.tilt_angle = 70
Rooftop.azimut_angle = 135
house.location = Location
house.rooftop = Rooftop
house.annual_el_demand = 5000

# Create a PV system
pv_system = pv_calc.create_pv_system(house.annual_el_demand)

# Calculate the annual electricity production
annual_el_production, el_production_timeseries, monthly_el_production = pv_calc.calculate_hourly_el_production(house, pv_system)

# Estimate the hourly electricity consumption
el_demand_timeseries = pv_calc.estimate_hourly_el_consumption(house)

# Calculate the cost savings and profit from grid feed-in
cost_savings_GGV, profit_grid_feed_in = pv_calc.calculate_cost_savings(el_production_timeseries, el_demand_timeseries)

# Calculate the CO2 reduction
annual_CO2_reduction, monthly_CO2_reduction = pv_calc.calculate_CO2_reduction(monthly_el_production)

# Print the results
print({
        "annual_el_production": annual_el_production,
        "monthly_el_production": monthly_el_production,
        "cost_savings_GGV": cost_savings_GGV,
        "profit_grid_feed_in": profit_grid_feed_in,
        "annual_CO2_reduction": annual_CO2_reduction,
        "monthly_CO2_reduction": monthly_CO2_reduction
    })