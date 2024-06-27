from pvlib import pvsystem, modelchain, location
import pandas as pd
from pvlib.iotools import get_pvgis_tmy

def create_pv_system(annual_el_demand):
    """
    Create a PV system object with the given annual electricity demand.

    Parameters
    ----------
    annual_el_demand: float
        The annual electricity demand in kWh.

    Returns
    -------
    pv_system: object
        A PV system object with attributes for size, cost_per_kWp, and annual_production.
    """ 
    # Define a class for the PV system
    class pv_system:
        def __init__(self, size, cost_per_kWp, annual_production):
            self.size = size
            self.cost_per_kWp = cost_per_kWp
            self.annual_production = annual_production

    # Estimate the PV system size in kWp
    pv_system.size = annual_el_demand / 1000
    
    return pv_system


def calculate_hourly_el_production(house, pv_system):
    """
    Calculate the hourly electricity production of the PV system by 
    using the PVGIS API which generates typical meteorological year (TMY) 
    data for a given location.

    Parameters
    ----------
    house: class 
        A class containing the location and rooftop information of the house.
    pv_system: class
        A class containing the size and cost_per_kWp of the PV system.

    Returns
    -------
    sum_dc_output: float
    production_timeseries: pd.DataFrame
    """
    # Generate typical meteorological year (TMY) data for given location
    df, _, _, _ = get_pvgis_tmy(house.location.latitude, house.location.longitude, map_variables=True, startyear=2006)
    
    # ghi = Global Horizontal Irradiance (W/m^2)
    # dhi = Diffuse Horizontal Irradiance (W/m^2)
    # dni = Direct Normal Irradiance (W/m^2)

    # convert the index to datetime
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    # drop unnecessary columns
    df.drop(columns=['temp_air', 'relative_humidity', 'IR(h)', 'wind_speed', 'wind_direction', 'pressure'], inplace=True)
    
    # generate a continous datetime index for 2023
    current_index = df.index

    # sort df by month and day (ignore year)
    new_index = pd.to_datetime({
        'year': 2023,
        'month': current_index.month,
        'day': current_index.day,
        'hour': current_index.hour,
        'minute': current_index.minute,
        'second': current_index.second
    }, utc=True)

    # set new index
    df.index = new_index
    # Sort the dataframe by date
    df.sort_index(inplace=True)
    # # Sort the dataframe by date
    # df.sort_values(by='date', inplace=True)

    # important variables
    name_of_array = 'main-module'

    # Simulate a PV system with the weather data
    # Define the PV system
    array_kwargs = dict(
        module_parameters=dict(pdc0=pv_system.size, gamma_pdc=-0.004),
        temperature_model_parameters=dict(a=-3.56, b=-0.075, deltaT=3)
    )

    arrays = [
        pvsystem.Array(pvsystem.FixedMount(house.rooftop.tilt_angle, house.rooftop.azimut_angle), name=name_of_array,
                    **array_kwargs)
    ]
    location_munich = location.Location(house.location.latitude, house.location.longitude)
    system = pvsystem.PVSystem(arrays=arrays, inverter_parameters=dict(pdc0=pv_system.size))
    mc = modelchain.ModelChain(system, location_munich, aoi_model='physical',
                            spectral_model='no_loss')

    # pv system simulation
    mc.run_model(df)

    resulting_values = mc.results.ac

    # calculate the sum of the DC output
    sum_dc_output = resulting_values.sum()  

    el_production_timeseries = pd.DataFrame({'date': resulting_values.index, 'production_value':resulting_values.values})
    el_production_timeseries['date'] = pd.to_datetime(el_production_timeseries['date'], utc=True)
        
    return sum_dc_output, el_production_timeseries


def estimate_hourly_el_consumption(house):
    """
    Estimate the hourly electricity consumption of the house from total annual electricity consumption .

    Parameters
    ----------
    house: class 
        A class containing information about total annual electricity consumption of the house.

    Returns
    -------
    el_demand_timeseries: pd.DataFrame
        A DataFrame containing the hourly electricity consumption data.
    """
    # import standard load profile data
    # read data/GGV_SLP_1000_MWh_2021_01-2020-09-24.csv from line 11
    df = pd.read_csv('data/GGV_SLP_1000_MWh_2021_01-2020-09-24.csv', skiprows=10, encoding='latin1', delimiter=';')

    # drop unnecessary columns
    df.drop(columns=['G00 [kW]', 'G00 [kWh]', 'G10 [kW]', 'G10 [kWh]', 'G20 [kW]', 'G20 [kWh]', 'G30 [kW]', 'G30 [kWh]', 'G40 [kW]', 'G40 [kWh]', 'G50 [kW]', 'G50 [kWh]', 'G60 [kW]', 'G60 [kWh]', 'L00 [kW]', 'L00 [kWh]', 'L10 [kW]', 'L10 [kWh]', 'L20 [kW]', 'L20 [kWh]', 'Bnd [kW]', 'Bnd [kWh]', 'M00 [kW]', 'M00 [kWh]', 'KW1 [kW]', 'KW1 [kWh]'], inplace=True)

    # drop unnecessary columns
    df.drop(columns=['Messwert-Nr.', 'So-/Wi-Zeit', 'Monat', 'Tag', 'Wochentag', 'Datum', 'Ferien', 'Tagesart', 'Jahr', 'MP von', 'MP bis'], inplace=True)

    # convert "Zeitstempel von" to datetime
    df['Zeitstempel von'] = pd.to_datetime(df['Zeitstempel von'], format='%d.%m.%Y %H:%M')

    # sort dataframe by "Zeitstempel von"
    df.sort_values(by='Zeitstempel von', inplace=True)

    # set "Zeitstempel von" as index
    df.set_index('Zeitstempel von', inplace=True)

    # drop NaN values
    df.dropna(inplace=True)

    # convert H00 [kW] to float
    df['H00 [kW]'] = df['H00 [kW]'].str.replace(',', '.').astype(float)
    # convert H00 [kWh] to float
    df['H00 [kWh]'] = df['H00 [kWh]'].str.replace(',', '.').astype(float)

    # calculate the total output
    total_output = df['H00 [kWh]'].sum()

    # calculate the factor for linear scaling of the demand timeseries
    factor = house.annual_el_demand / total_output

    # multiply the values of H00 [kW] with the factor
    df['H00 recalculated [kW]'] = df['H00 [kW]'] * factor
    # multiply the values of H00 [kWh] with the factor
    df['H00 recalculated [kWh]'] = df['H00 [kWh]'] * factor

    # calculate the total output again
    total_output = df['H00 recalculated [kWh]'].sum()

    # prepare consumption data
    consumption_data = df.drop(columns=['Zeitstempel bis', 'H00 [kW]', 'H00 [kWh]'])
    consumption_data['date'] = consumption_data.index
    consumption_data['date'] = pd.to_datetime(consumption_data['date'], utc=True)
    # set year to 2023
    consumption_data['date'] = consumption_data['date'] + pd.offsets.DateOffset(years=2)
    el_demand_timeseries = consumption_data

    return el_demand_timeseries


def calculate_cost_savings(el_production_timeseries, el_demand_timeseries):
    """
    Calculate the cost savings by sharing electricity in the house (GGV) and 
    the profit from grid feed-in based on the hourly electricity production and consumption.

    Parameters
    ----------
    el_production_timeseries: pd.DataFrame
        A DataFrame containing the hourly electricity production data.
    el_demand_timeseries: pd.DataFrame
        A DataFrame containing the hourly electricity consumption data.

    Returns
    -------
    cost_savings_GGV: float
        The total cost savings from self-consumption of electricity within the GGV.
    profit_grid_feed_in: float
        The profit from grid feed-in of surplus electricity.
    """
    # Merge the production and the consumption fields
    production_and_consumption = pd.merge(el_demand_timeseries, el_production_timeseries, on='date', how='left')

    # Fill NaN values with the last value
    production_and_consumption.fillna(method='bfill', inplace=True)

    # Calculate the produced energy (kWh) in this quarter hour (power / 4)
    production_and_consumption['production_value_kwh'] = production_and_consumption['production_value'] * 0.25

    # Calculate the cost savings
    # If more electricity is needed than produced -> the produced electricity does not need to be purchased -> savings of 0.3 ct/kWh
    # If less electricity is needed than produced -> surplus electricity is fed into the grid -> feed-in tariff of 8.03 ct/kWh (2024)

    # Calculate a dataframe with min(production, consumption) for each row -> This is the electricity produced and used for own needs
    production_and_consumption['min_prod_cons'] = production_and_consumption[['H00 recalculated [kWh]', 'production_value_kwh']].min(axis=1)

    # Price per kWh
    electricity_price = 0.3

    # Calculate the saved costs by multiplying the min with the electricity price
    production_and_consumption['saved_costs'] = production_and_consumption['min_prod_cons'] * electricity_price

    # Calculate the total saved costs (GGV)
    cost_savings_GGV = round(production_and_consumption['saved_costs'].sum(),2)

    # Calculate the production surplus
    production_surplus = production_and_consumption['production_value_kwh'] - production_and_consumption['H00 recalculated [kWh]']
    production_surplus[production_surplus < 0] = 0

    # Calculate the profit from grid feed-in
    profit_grid_feed_in = round(production_surplus.sum() * 0.0803, 2)

    return cost_savings_GGV, profit_grid_feed_in