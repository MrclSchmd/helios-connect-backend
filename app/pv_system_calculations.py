from pvlib import pvsystem, modelchain, location
import pandas as pd
from pvlib.iotools import get_pvgis_tmy

def create_pv_system(annual_el_demand):  
    class pv_system:
        def __init__(self, size, cost_per_kWp, annual_production):
            self.size = size
            self.cost_per_kWp = cost_per_kWp
            self.annual_production = annual_production

    # PV System size in kWp
    pv_system.size = annual_el_demand / 1000

    return pv_system


def calculate_hourly_el_production(house, pv_system):

    # ghi = Global Horizontal Irradiance (W/m^2)
    # dhi = Diffuse Horizontal Irradiance (W/m^2)
    # dni = Direct Normal Irradiance (W/m^2)

    latitude = house.location.latitude
    longitude = house.location.longitude

    df, _, _, metadata = get_pvgis_tmy(latitude, longitude, map_variables=True, startyear=2006)

    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    df.drop(columns=['temp_air', 'relative_humidity', 'IR(h)', 'wind_speed', 'wind_direction', 'pressure'], inplace=True)

    # sort df by month and day (ignore year)
    df['month'] = df.index.month
    df['day'] = df.index.day
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    df['second'] = df.index.second
    df['year'] = 2023
    df['date'] = pd.to_datetime(df[['year', 'month', 'day', 'hour', 'minute', 'second']])
    df.set_index('date', inplace=True)
    df.drop(columns=['month', 'day', 'hour', 'minute', 'second', 'year'], inplace=True)
    df = df.sort_values(by='date')

    # important variables
    name_of_array = 'South-East-Facing Array'

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
    location_munich = location.Location(latitude, longitude)
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

    # important variables
    power_consumption_per_year = house.annual_el_demand

    # read data/GGV_SLP_1000_MWh_2021_01-2020-09-24.csv from line 11
    df = pd.read_csv('data/GGV_SLP_1000_MWh_2021_01-2020-09-24.csv', skiprows=10, encoding='latin1', delimiter=';')

    # drop the following columns:  G00 [kW]	G00 [kWh]	G10 [kW]	G10 [kWh]	G20 [kW]	G20 [kWh]	G30 [kW]	G30 [kWh]	G40 [kW]	G40 [kWh]	G50 [kW]	G50 [kWh]	G60 [kW]	G60 [kWh]	L00 [kW]	L00 [kWh]	L10 [kW]	L10 [kWh]	L20 [kW]	L20 [kWh]	Bnd [kW]	Bnd [kWh]	M00 [kW]	M00 [kWh]	KW1 [kW]	KW1 [kWh]
    df.drop(columns=['G00 [kW]', 'G00 [kWh]', 'G10 [kW]', 'G10 [kWh]', 'G20 [kW]', 'G20 [kWh]', 'G30 [kW]', 'G30 [kWh]', 'G40 [kW]', 'G40 [kWh]', 'G50 [kW]', 'G50 [kWh]', 'G60 [kW]', 'G60 [kWh]', 'L00 [kW]', 'L00 [kWh]', 'L10 [kW]', 'L10 [kWh]', 'L20 [kW]', 'L20 [kWh]', 'Bnd [kW]', 'Bnd [kWh]', 'M00 [kW]', 'M00 [kWh]', 'KW1 [kW]', 'KW1 [kWh]'], inplace=True)

    # drop the following columns: Messwert-Nr. , So-/Wi-Zeit , Monat, Tag, Wochentag, Datum, Ferien, Tagesart, Jahr, MP von,	MP bis
    df.drop(columns=['Messwert-Nr.', 'So-/Wi-Zeit', 'Monat', 'Tag', 'Wochentag', 'Datum', 'Ferien', 'Tagesart', 'Jahr', 'MP von', 'MP bis'], inplace=True)

    # make "Zeitstempel von" to datetime, now it is in the format  01.01.2021 00:00, so we need to convert it to 2021-01-01 00:00
    df['Zeitstempel von'] = pd.to_datetime(df['Zeitstempel von'], format='%d.%m.%Y %H:%M')

    df.sort_values(by='Zeitstempel von', inplace=True)

    df.set_index('Zeitstempel von', inplace=True)

    # drop NaN values
    df.dropna(inplace=True)

    # make H00 [kW] to float
    df['H00 [kW]'] = df['H00 [kW]'].str.replace(',', '.').astype(float)
    # same with H00 [kWh]
    df['H00 [kWh]'] = df['H00 [kWh]'].str.replace(',', '.').astype(float)

    # sum up the values of H00 [kWh] to get the total output
    total_output = df['H00 [kWh]'].sum()
    # print(f"Total Output: {total_output} kWh")

    # calculate the factor, to get 3000 kWh
    factor = power_consumption_per_year / total_output
    # print(f"Factor: {factor}")

    # multiply the values of H00 [kW] with the factor
    df['H00 recalculated [kW]'] = df['H00 [kW]'] * factor
    # multiply the values of H00 [kWh] with the factor
    df['H00 recalculated [kWh]'] = df['H00 [kWh]'] * factor

    # calculate the total output again (should be equal to the 3000 to calculate the factor)
    total_output = df['H00 recalculated [kWh]'].sum()
    # print(f"Total Output recalculated: {total_output} kWh")

    # plot with plotly express
        # import plotly.express as px
        # import plotly.graph_objects as go

        # fig = go.Figure()
        # fig.add_trace(go.Scatter(x=df.index, y=df['H00 recalculated [kW]'], mode='lines', name='Total Output'))
        # fig.update_layout(title=f"Power consumption over the year, total power consumption of {power_consumption_per_year} kWh")
        # fig.show()

    # prepare consumption data
    consumption_data = df.drop(columns=['Zeitstempel bis', 'H00 [kW]', 'H00 [kWh]'])
    consumption_data['date'] = consumption_data.index
    consumption_data['date'] = pd.to_datetime(consumption_data['date'], utc=True)
    # set year to 2023
    consumption_data['date'] = consumption_data['date'] + pd.offsets.DateOffset(years=2)
    el_demand_timeseries = consumption_data

    return el_demand_timeseries


def calculate_cost_savings(el_production_timeseries,el_demand_timeseries):

    production_data = el_production_timeseries
    consumption_data = el_demand_timeseries

    # Merge the production  and the consumption fields
    production_and_consumption = pd.merge(consumption_data, production_data, on='date', how='left')

    # fill NaN values with the last value
    production_and_consumption.fillna(method='bfill', inplace=True)

    # calculate the produced energy (kwh) in this quarter hour (power / 4)
    production_and_consumption['production_value_kwh'] = production_and_consumption['production_value'] * 0.25
    sum_dc_output = production_and_consumption['production_value_kwh'].sum()
    print(f"Sum of DC output: {sum_dc_output} KW h")

    # Berechne die gesparten Kosten
    # Der Strom, der selbst produziert wurde, muss nicht mehr eingekauft werden. Wenn werniger Strom gebraucht wird, als produziert, wird der 
    # Überschusstrom ins Netz eingespeist aber nicht vergütet. Es zählt also nur der Strom, der selbst verbraucht wird!

    # Price per KWh
    electricity_price = 0.3

    # calculate a dataframe with min(production, consumption) for each row -> This is the electricity produced and used for own needs
    production_and_consumption['min_prod_cons'] = production_and_consumption[['H00 recalculated [kWh]', 'production_value_kwh']].min(axis=1)

    # calculate the saved costs by multiplying the min with the electricity price
    production_and_consumption['saved_costs'] = production_and_consumption['min_prod_cons'] * electricity_price

    # calculate the total saved costs
    total_saved_costs = production_and_consumption['saved_costs'].sum()
    

    cost_savings = total_saved_costs

    return  cost_savings