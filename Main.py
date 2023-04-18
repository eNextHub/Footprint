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
Coun_info = pd.read_excel('Aggregations\Support.xlsx', sheet_name='Countries', index_col=[0], header=[0])

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
                Res.loc[(m,y,c,'Heating'),e] = Coun_info.loc[c,'GHG emiss Heating share']*Worlds[m,y].EY.loc[e,(Countries,sN,Consumption_cats)].sum()
                Res.loc[(m,y,c,'Driving'),e] = Coun_info.loc[c,'GHG emiss Driving share']*Worlds[m,y].EY.loc[e,(Countries,sN,Consumption_cats)].sum()


#%% Adding GHG with a 100-years GWP
Res['GHG'] = Res['CH4']*25 + Res['CO2']*1 + Res['N2O']*298
# %% Adding the need and the sector
Map1 = pd.read_excel('Aggregations\Support.xlsx', sheet_name='Sectors to needs', index_col=[0], header=[0]).to_dict()['Need']
Map2 = pd.read_excel('Aggregations\Support.xlsx', sheet_name='Sectors to needs', index_col=[0], header=[0]).to_dict()['Settori']
Res['Need'] = Res.index.get_level_values('Sector').map(Map1)
Res['Settori'] = Res.index.get_level_values('Sector').map(Map2)
RES = Res.reset_index().set_index(['Mode','Year','Region','Sector','Settori','Need'])
# %% Importing the color palette
Colors = pd.read_excel('Aggregations\Support.xlsx', sheet_name='Needs colors', index_col=[0], header=[0]).to_dict()['Color']

# %% Plotting the results
import plotly.express as px

plot = RES.groupby(['Need','Settori']).sum().reset_index()
plot['% GHG'] = round(plot['GHG'] / plot['GHG'].sum()*100,1).astype(str) + '%'
plot['GHG pc'] = round(plot['GHG']/Coun_info.loc[Countries[0],'Population']).astype(str) + ' kgCO2eq per capita'


# make a dataframe with GHG emissions per capita by need
GHG_need = round(plot.groupby('Need').sum()/Coun_info.loc[Countries[0],'Population']/1000,1).reset_index()
plot['GHG_need'] = plot['Need'].map(GHG_need.set_index('Need')['GHG'])

# add a column to plot in which the name of the need and the GHG_need are displayed together
plot['Need and GHG'] = plot['Need'] + ' ~' + plot['GHG_need'].astype(str) + ' ton'

fig = px.treemap(plot, path=['Need and GHG','Settori'], values='GHG', color='Need', color_discrete_map=Colors, hover_data=['% GHG','GHG pc'])
fig.update_layout(template='plotly_white', font_family='HelveticaNeue')
fig.update_layout(
    plot_bgcolor='black', # Set dark background
    paper_bgcolor='black')
fig.update_traces(marker=dict(cornerradius=15))

# Add percentage in each section of the treemap
fig.data[0].textinfo = 'label+percent root'

# Add percentage also at the bottom of the treemap
fig.data[0].insidetextfont.size = 30
fig.data[0].insidetextfont.color = 'black'

# Add title showing the total emissions
fig.update_layout(title_text=f"Emissioni totali di gas serra: ~{round(plot['GHG'].sum()/Coun_info.loc[Countries[0],'Population']*1e-3,1)} tonCO2eq per italiano all'anno")
fig.update_layout(title_x=0.5)

# Decrease distance between title and treemap
fig.update_layout(title_y=0.95)
# Make title white
fig.update_layout(title_font_color='white')

# Save the figure
fig.write_html(f'Figures/Footprint Treemap {Years[0]}.html')
fig.show()

# %%
