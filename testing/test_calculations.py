import sys
import os

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_path not in sys.path:
    sys.path.append(project_path)


from app import pv_system_calculations as pv_calc

class Location:
    longitude: float
    latitude: float

class Rooftop:
    tilt_angle: float
    azimut_angle: float

class house:
    location: Location
    rooftop: Rooftop
    annual_el_demand: float

class pv_system:
    size = float
    cost_per_kWp = float
    annual_production = float

Location.latitude = 48.1374
Location.longitude = 11.5755
Rooftop.tilt_angle = 70
Rooftop.azimut_angle = 135
house.location = Location
house.rooftop = Rooftop
house.annual_el_demand = 5000

pv_system.size = 0.6

annual_el_production, el_production_timeseries = pv_calc.calculate_hourly_el_production(house,pv_system)
el_demand_timeseries =pv_calc.estimate_hourly_el_consumption(house)
cost_savings_GGV, profit_grid_feed_in = pv_calc.calculate_cost_savings(el_production_timeseries, el_demand_timeseries)

print(cost_savings_GGV,profit_grid_feed_in)