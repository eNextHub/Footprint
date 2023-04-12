#%% Start with importing pandas, mario and numpy
import pandas as pd
import mario
import numpy as np

#%% Now is time to import our databases
user = r'C:\Users\nicog\Politecnico di Milano\DENG-SESAM - Documenti\DATASETS\Exiobase 3.8.2\IOT' # Your path to the folder containing Exiobase
Modes = ['pxp'] # Which versions of Exiobase you want to use?
Years = [2019] # Which years?
Worlds = {} # Initializing the dictionaries of all the worlds
sN = slice(None) # Useful to include levels when slicing dataframes

# Select the interested levels of information
Consumption_cats = ['Final consumption expenditure by households'] # Before aggregation
Countries = ['IT'] # Before aggregation

#%% Importing a version of a chosen dataframe so
World = mario.parse_exiobase_3(user+f'\IOT_{Years[0]}_{Modes[0]}.zip', name=f'First') # Import the right Exiobase version and year
World.aggregate('Aggregations\Aggregation.xlsx')

#%% Building the Indeces of the results dataframe
Regions = World.get_index('Region')
Sectors = World.get_index('Sector')
Sat_accounts = World.get_index('Satellite account')
Res_col = pd.Index(Sat_accounts, name='Satellite accounts')
Res_row = pd.MultiIndex.from_product([Modes,Years,Regions,Sectors], names=['Mode','Year','Region','Sector'])
Res = pd.DataFrame(0, index=Res_row, columns=Res_col)

#%% Loop through each combination of mode and year and parse the corresponding Exiobase data
for m in Modes:
    for y in Years:
        path = user+f'\IOT_{y}_{m}.zip' # Complete the path
        Worlds[m,y] = mario.parse_exiobase_3(path, name=f'{m} - {y}') # Import the right Exiobase version and year
        Worlds[m,y].aggregate('Aggregations\Aggregation.xlsx')

        for e in Sat_accounts:
            f = Worlds[m,y].f.loc[e]
            f_diag = np.diag(f)
            Y = Worlds[m,y].Y.loc[:,(Countries,sN,Consumption_cats)].sum(1)
            Calc = pd.DataFrame(f_diag@Y.values, index= Worlds[m,y].Y.index, columns=[e])

            for r in Regions:
                for p in Sectors:
                    Res.loc[(m,y,r,p),e] = Calc.loc[(r,sN,p),e][0]
            for c in Countries:
                Res.loc[(m,y,c,'Heating'),e] = 0.4*Worlds[m,y].EY.loc[e,(Countries,sN,Consumption_cats)].sum()
                Res.loc[(m,y,c,'Driving'),e] = 0.6*Worlds[m,y].EY.loc[e,(Countries,sN,Consumption_cats)].sum()


#%% Adding GHG
Res['GHG'] = Res['CH4']*25 + Res['CO2']*1 + Res['N2O']*268
# %%
Map = pd.read_excel('Aggregations\Sectors to needs.xlsx', index_col=[0], header=[0]).to_dict()['Need']
Res['Need'] = Res.index.get_level_values('Sector').map(Map)
RES = Res.reset_index().set_index(['Mode','Year','Region','Sector','Need'])
# %%
