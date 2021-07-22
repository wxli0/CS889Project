import dash
import numpy as np
import pandas as pd
import json
import geojson
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
   
map_data_path = "map_data/"
covid_data_path = "covid_data/"
taxi_data_path = "taxi_data/"

# taxi zones
with open(map_data_path + "taxi_zones.geojson") as f:
    taxigj = geojson.load(f)
nzones = len(taxigj["features"])

# taxi data
taxidf = pd.read_csv(taxi_data_path + "taxi_data.csv")[:nzones]

# covid zones (zip codes)
with open(map_data_path + "zip_codes.geojson") as f:
    covidgj = geojson.load(f)
nzips = len(covidgj["features"])
zip_lookup = {int(feature["properties"]["postalCode"]) : feature
                for feature in covidgj["features"]}

# covid data
coviddf = pd.read_csv(covid_data_path + "covid_data-2020-3.csv")[:nzips]

# dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[
        'https://codepen.io/chriddyp/pen/bWLwgP.css'
    ]
)

# figures
choroplethHeight = 600
taxifig = px.choropleth(taxidf, geojson=taxigj, 
                        locations="PULocationID", color="yellow_log_total_amount",
                        color_continuous_scale="Viridis",
                        featureidkey="properties.LocationID", projection="mercator")

taxifig.update_geos(fitbounds="locations", visible=False)
taxifig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=choroplethHeight)

def get_covidfig_highlights(selections, covidgj=covidgj, zip_lookup=zip_lookup):
    covidgj_highlights = dict()
    for k in covidgj.keys():
        if k != "features":
            covidgj_highlights[k] = covidgj[k]
        else:
            covidgj_highlights[k] = [zip_lookup[selection] for selection in selections]

    return covidgj_highlights
            
def get_covidfig(selectedZips):
    covidfig = px.choropleth(coviddf, geojson=covidgj,
                                locations="zip_code", color="hospitalization_rate",
                                color_continuous_scale="Viridis",
                                featureidkey="properties.postalCode", projection="mercator")
    if (len(selectedZips) > 0):
        highlights = get_covidfig_highlights(selectedZips)
        covidHighlights = px.choropleth(coviddf, geojson=highlights,
                                        locations="zip_code", color="hospitalization_rate",
                                        color_continuous_scale="Viridis",
                                        featureidkey="properties.postalCode",
                                        projection="mercator")
        covidHighlights.update_traces(marker_line=dict(color="red", width=5))
        covidfig.add_trace(covidHighlights.data[0])

    covidfig.update_geos(fitbounds="locations", visible=False)
    covidfig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=choroplethHeight)

    return covidfig

# layout
app.layout = html.Div([
    html.Div([ 
        html.Div([
            dcc.Graph(id="covid-choropleth")
        ], className="six columns"),

        html.Div([
            dcc.Graph(id="taxi-choropleth",
                        figure=taxifig),
        ], className="six columns"),
    ], className="row")
])

# interactions
@app.callback(
    Output("covid-choropleth", "figure"),
    [Input("covid-choropleth", "clickData")])
def update_choropleths(clickData):
    location = None
    selectedZips = []
    if clickData is not None:
        location = clickData["points"][0]["location"]

    if location and location not in selectedZips:
        selectedZips = [location]

    return get_covidfig(selectedZips)

# main
if __name__ == "__main__":
    app.run_server(debug=True)
