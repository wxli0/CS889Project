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
taxi_lookup = {int(feature["properties"]["LocationID"]) : feature
                for feature in taxigj["features"]}

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

# zone overlap
overlapdf = pd.read_csv(map_data_path + "taxi_zip_overlap.csv")

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

covidfig = px.choropleth(coviddf, geojson=covidgj,
                            locations="zip_code", color="hospitalization_rate",
                            color_continuous_scale="Viridis",
                            featureidkey="properties.postalCode", projection="mercator")

def get_highlights(selections, geojson, lookup_dict):
    highlights = dict()
    for k in geojson.keys():
        if k != "features":
            highlights[k] = geojson[k]
        else:
            highlights[k] = [lookup_dict[selection] for selection in selections]

    return highlights

def get_taxifig(selectedLocs):
    # clear traces
    taxifig.data = [taxifig.data[0]]

    if (len(selectedLocs) > 0):
        highlights = get_highlights(selectedLocs, taxigj, taxi_lookup)
        taxiHighlights = px.choropleth(taxidf.loc[taxidf["PULocationID"].isin(selectedLocs)],
                                        geojson=highlights,
                                        locations="PULocationID", color="yellow_log_total_amount",
                                        color_continuous_scale="Viridis",
                                        featureidkey="properties.LocationID",
                                        projection="mercator")
        taxiHighlights.update_traces(marker_line=dict(color="red", width=5))
        taxifig.add_trace(taxiHighlights.data[0])

    taxifig.update_geos(fitbounds="locations", visible=False)
    taxifig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=choroplethHeight)

    return taxifig
            
def get_covidfig(selectedZips):
    # clear traces
    covidfig.data = [covidfig.data[0]]

    if (len(selectedZips) > 0):
        highlights = get_highlights(selectedZips, covidgj, zip_lookup)
        covidHighlights = px.choropleth(coviddf.loc[coviddf["zip_code"].isin(selectedZips)],
                                        geojson=highlights,
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
            dcc.Graph(id="covid-choropleth",
            figure=covidfig)
        ], className="six columns"),

        html.Div([
            dcc.Graph(id="taxi-choropleth",
            figure=taxifig)
        ], className="six columns"),
    ], className="row")
])

# interactions
covidTriggerStr = "covid-choropleth.clickData"
taxiTriggerStr = "taxi-choropleth.clickData"

@app.callback([
    Output("covid-choropleth", "figure"),
    Output("taxi-choropleth", "figure")
], [
    Input("covid-choropleth", "clickData"),
    Input("taxi-choropleth", "clickData")])
def update_plots(covidClickData, taxiClickData):
    ctx = dash.callback_context
    #ctx_msg = json.dumps({
    #    'states': ctx.states,
    #    'triggered': ctx.triggered,
    #    'inputs': ctx.inputs
    #}, indent=2)

    # vars to be filled in
    covidLocation = None
    taxiLocation = None
    selectedZips = []
    selectedLocs = []

    # figure out which map triggered the callback
    if ctx.triggered[0]["prop_id"] == covidTriggerStr:
        if covidClickData is not None:
            covidLocation = covidClickData["points"][0]["location"]
    elif ctx.triggered[0]["prop_id"] == taxiTriggerStr:
        if taxiClickData is not None:
            taxiLocation = taxiClickData["points"][0]["location"]

    if covidLocation:
        selectedZips = [covidLocation]
        selectedLocs = list(overlapdf[overlapdf["zip_code"] == covidLocation]["LocationID"])
    elif taxiLocation:
        selectedLocs = [taxiLocation]
        selectedZips = list(overlapdf[overlapdf["LocationID"] == taxiLocation]["zip_code"])

    return get_covidfig(selectedZips), get_taxifig(selectedLocs)

# main
if __name__ == "__main__":
    app.run_server(debug=True)
