from pvlib import pvsystem, modelchain, location, temperature
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
    monthly_production: pd.DataFrame
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

    # important variables
    name_of_array = 'main-module'

    # Simulate a PV system with the weather data
    # Define the PV system

    # get the temperature model parameters
    temperature_model_parameters = temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['close_mount_glass_glass']

    # define the array kwargs
    # with gamma_pdc=-0.004, typical temperature coefficient of the DC power of the module
    array_kwargs = dict(
        module_parameters=dict(pdc0=pv_system.size, gamma_pdc=-0.004),
        temperature_model_parameters=temperature_model_parameters
    )

    # define the array
    arrays = [
        pvsystem.Array(pvsystem.FixedMount(house.rooftop.tilt_angle, house.rooftop.azimut_angle), name=name_of_array,
                    **array_kwargs)
    ]
    # define the location
    location_obj = location.Location(house.location.latitude, house.location.longitude)
    system = pvsystem.PVSystem(arrays=arrays, inverter_parameters=dict(pdc0=pv_system.size))
    mc = modelchain.ModelChain(system, location_obj, aoi_model='physical',
                            spectral_model='no_loss')

    # run pv system simulation
    mc.run_model(df)

    # get the results
    pv_simulation_results = mc.results.ac

    # calculate the sum of the DC output
    annual_el_production = round(pv_simulation_results.sum(), 2)  

    # create a DataFrame with the hourly electricity production data
    el_production_timeseries = pd.DataFrame({'el_production':pv_simulation_results.values})
    el_production_timeseries.index = pv_simulation_results.index
    el_production_timeseries.index.name ='datetime'

    # resample the data to monthly values
    monthly_el_production = el_production_timeseries.resample('M').sum().round(2)
    monthly_el_production.index = monthly_el_production.index.strftime('%B')
    monthly_el_production.index.name = 'Month'
        
    return annual_el_production, el_production_timeseries, monthly_el_production


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
    # read required from data/GGV_SLP_1000_MWh_2021_01-2020-09-24.csv 
    df = pd.read_csv('data/GGV_SLP_1000_MWh_2021_01-2020-09-24.csv', skiprows=10, encoding='latin1', delimiter=';',usecols=['Zeitstempel von', 'H00 [kWh]'])

    # convert "Zeitstempel von" to datetime
    df['Zeitstempel von'] = pd.to_datetime(df['Zeitstempel von'], format='%d.%m.%Y %H:%M')

    # drop NaN values
    df.dropna(inplace=True)

    # generate a continous datetime index for 2023
    start_date = '2023-01-01 00:00:00'
    end_date = '2023-12-31 23:45:00'
    df.index = pd.date_range(start=start_date, end=end_date, freq='15T', tz='UTC')
    df.index.name='datetime'

    # convert H00 [kWh] to float
    df['H00 [kWh]'] = df['H00 [kWh]'].str.replace(',', '.').astype(float)

    # calculate the standard total annual electricity consumption
    st_total_annual_consumption = df['H00 [kWh]'].sum()

    # calculate the factor for linear scaling of the demand timeseries
    scaling_factor = house.annual_el_demand / st_total_annual_consumption

    # multiply the values of H00 [kWh] with the factor
    df['H00 recalculated [kWh]'] = df['H00 [kWh]'] * scaling_factor

    # prepare consumption data
    el_demand_timeseries = df.drop(columns=['Zeitstempel von', 'H00 [kWh]'])

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
    production_and_consumption = pd.merge(el_demand_timeseries, el_production_timeseries, how='left', left_index=True, right_index=True)

    # Fill NaN values with the last value
    production_and_consumption.fillna(method='ffill', inplace=True)

    # Calculate the produced energy (kWh) in this quarter hour (power / 4)
    production_and_consumption['el_production [kWh]'] = production_and_consumption['el_production'] * 0.25
    production_and_consumption.drop(columns=['el_production'], inplace=True)

    # Calculate the cost savings
    # If more electricity is needed than produced -> the produced electricity does not need to be purchased -> savings of 0.3 ct/kWh
    # If less electricity is needed than produced -> surplus electricity is fed into the grid -> feed-in tariff of 8.03 ct/kWh (2024)

    # Calculate a dataframe with min(production, consumption) for each row -> This is the electricity produced and used for own needs
    production_and_consumption['min_prod_cons'] = production_and_consumption[['H00 recalculated [kWh]', 'el_production [kWh]']].min(axis=1)

    # Price per kWh
    electricity_price = 0.27

    # Calculate the saved costs by multiplying the min with the electricity price
    production_and_consumption['saved_costs'] = production_and_consumption['min_prod_cons'] * electricity_price

    # Calculate the total saved costs (GGV)
    cost_savings_GGV = round(production_and_consumption['saved_costs'].sum(),2)

    # Calculate the production surplus
    production_surplus = (production_and_consumption['el_production [kWh]'] - production_and_consumption['H00 recalculated [kWh]']).clip(lower=0)

    # Feed-in tariff in 2024
    feed_in_tariff = 0.0803

    # Calculate the profit from grid feed-in
    profit_grid_feed_in = round(production_surplus.sum() * feed_in_tariff, 2)

    return cost_savings_GGV, profit_grid_feed_in

def calculate_CO2_reduction(monthly_el_production):
    """
    Calculate the CO2 reduction based on the annual electricity production of the PV system.

    Parameters
    ----------
    annual_el_production: float
        The annual electricity production of the PV system in kWh.

    Returns
    -------
    CO2_reduction: float
        The CO2 reduction in kg per year.
    """
    # CO2 emissions per kWh in Germany in 2023
    # https://www.umweltbundesamt.de/themen/co2-emissionen-pro-kilowattstunde-strom-2023
    CO2_emission_factor = 0.380 # kg/kWh

    # Calculate the monthly and annual CO2 reduction
    monthly_CO2_reduction = round(monthly_el_production * CO2_emission_factor, 2)
    monthly_CO2_reduction.rename(columns={'el_production':'CO2_reduction'}, inplace=True)
    annual_CO2_reduction = float(monthly_CO2_reduction.sum())

    return annual_CO2_reduction, monthly_CO2_reduction