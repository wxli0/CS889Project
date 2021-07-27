import dash
import numpy as np
import pandas as pd
import json
import geojson
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objs as go
   
map_data_path = "map_data/"
covid_data_path = "covid_data/"
taxi_data_path = "taxi_data/"

# taxi zones
with open(map_data_path + "taxi_zones_2_simpler.json") as f:
    taxigj = geojson.load(f)
nzones = len(taxigj["features"])
taxi_lookup = {int(feature["properties"]["location_id"]) : feature
                for feature in taxigj["features"]}

# taxi data
taxidf = pd.read_csv(taxi_data_path + "taxi_data_2020-3.csv")[:nzones]

# covid zones (zip codes)
with open(map_data_path + "zip_codes_simpler.json") as f:
    covidgj = geojson.load(f)
nzips = len(covidgj["features"])
zip_lookup = {int(feature["properties"]["postalCode"]) : feature
                for feature in covidgj["features"]}

# covid data
coviddf = pd.read_csv(covid_data_path + "covid_data-2020-3.csv")[:nzips]

# zone overlap
overlapdf = pd.read_csv(map_data_path + "taxi_zip_overlap.csv")

# taxi bivariate color map
nbiv_colors = 9
biv_colors = [  "#e8e8e8", "#b5c0da", "#6c83b5",
                "#b8d6be", "#90b2b3", "#567994",
                "#73ae80", "#5a9178", "#2a5a5b"]
bivcmap = {clr : clr for clr in biv_colors}

def colors_to_colorscale(biv_colors):
    # biv_colors: list of n**2 color codes in hexa or RGB255
    # returns a discrete colorscale  defined by biv_colors
    n = len(biv_colors)
    biv_colorscale = []
    for k, col in enumerate(biv_colors):
        biv_colorscale.extend([[round(k/n, 2) , col], [round((k+1)/n, 2), col]])
    return biv_colorscale

def colorsquare(text_x, text_y, colorscale, n=3):
    # text_x : list of n strings, representing intervals of values for the
    #   first variable or its n percentiles
    # text_y : list of n strings, representing intervals of values for the
    #   second variable or its n percentiles
    # colorscale: Plotly bivariate colorscale
    # returns the colorsquare as alegend for the bivariate choropleth, heatmap and more

    z = [[j+n*i for j in range(n)] for i in range(n)]
    n = len(text_x)
    if len(text_x) != n   or len(text_y) != n  or len(colorscale) != 2*n**2:
        raise ValueError(
            'Your lists of strings  must have the length {n} and the colorscale, {n**2}')

    text = [[text_x[j]+'<br>'+text_y[i] for j in range(len(text_x))] for i in range(len(text_y))]
    return go.Heatmap(x=list(range(n)),
                      y=list(range(n)),
                      z=z,
                      text=text,
                      hoverinfo='text',
                      colorscale=colorscale,
                      showscale=False)

# dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[
        'https://codepen.io/chriddyp/pen/bWLwgP.css'
    ]
)

# figures
choroplethHeight = 1300
taxifig = px.choropleth_mapbox(taxidf, geojson=taxigj,
                            locations="PULocationID", color="biv_ratio_color",
                            color_discrete_map=bivcmap,
                            hover_name="Zone",
                            hover_data={
                                "yellow_total_amount": ":.2f",
                                "green_total_amount" : ":.2f",
                                "yellow_change_percent": ":.2f",
                                "green_change_percent": ":.2f",
                                "Borough" : True,
                                "service_zone" : True,
                                "biv_amount_color" : False,
                                "biv_ratio_color" : False},
                            # featureidkey="properties.LocationID",
                            featureidkey="properties.location_id",
                            center={"lat":40.7, "lon":-73.97}, zoom=10.62)

# bivariate legend
legendHeight = legendWidth = 500
text_x = ['yellow revenue<P_33', 'P_33<=yellow revenue<=P_66', 'yellow_revenue>P_66']
text_y = ['green revenue<P_33', 'P_33<=green revenue<=P_66', 'green revenue>P_66']
legend_axis = dict(showline=False, zeroline=False, showgrid=False,  ticks='', showticklabels=False)
taxilegend = go.Figure(
                data=colorsquare(text_x, text_y, colors_to_colorscale(biv_colors)),
                layout=dict(xaxis=dict(legend_axis, side="bottom"),
                            yaxis=legend_axis,
                            height=legendHeight, width=legendWidth))
taxilegend.update_xaxes(
        tickangle = 90,
        title_text = "yellow taxi revenue",
        title_font = {"size": 15},
        title_standoff = 25,
        showline=True, 
        linewidth=2, 
        linecolor='black', 
        ticks="inside", 
        ticktext=["33rd", "66th", "100th"],
        tickvals=[0.5, 1.5, 2.5],
        showticklabels=True)
taxilegend.update_yaxes(
        tickangle = 0,
        title_text = "green taxi revenue",
        title_font = {"size": 15},
        title_standoff = 25,
        showline=True, 
        linewidth=2, 
        linecolor='black', 
        ticks="inside", 
        ticktext=["0", "33rd", "66th", "100th"], 
        tickvals=[-0.5, 0.5, 1.5, 2.5], 
        showticklabels=True)

covidfig = px.choropleth_mapbox(coviddf, geojson=covidgj,
                            locations="zip_code", color="hospitalization_rate",
                            color_continuous_scale="Viridis",
                            hover_name="zip_code",
                            hover_data={
                                "hospitalization_rate" : ":.2f",
                                "zip_code" : False},
                            featureidkey="properties.postalCode",
                            center={"lat":40.7, "lon":-73.97},
                            zoom=10.62)
                        
dummy_df = pd.DataFrame({
    "Fruit": ["Apples", "Oranges", "Bananas", "Apples", "Oranges", "Bananas"],
    "Amount": [4, 1, 2, 2, 4, 5],
    "City": ["SF", "SF", "SF", "Montreal", "Montreal", "Montreal"]
})

dummy_fig = px.bar(dummy_df, x="Fruit", y="Amount", color="City", barmode="group")

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
    taxifig.data = taxifig.data[:nbiv_colors]

    if (len(selectedLocs) > 0):
        highlights = get_highlights(selectedLocs, taxigj, taxi_lookup)
        taxiHighlights = px.choropleth_mapbox(taxidf.loc[taxidf["PULocationID"].isin(selectedLocs)],
                                        geojson=highlights,
                                        locations="PULocationID", color="biv_ratio_color",
                                        color_discrete_map=bivcmap,
                                        hover_name="Zone",
                                        hover_data={
                                            "yellow_total_amount": ":.2f",
                                            "green_total_amount" : ":.2f",
                                            "yellow_change_percent": ":.2f",
                                            "green_change_percent": ":.2f",
                                            "Borough" : True,
                                            "service_zone" : True,
                                            "biv_amount_color" : False,
                                            "biv_ratio_color" : False},
                                        # featureidkey="properties.LocationID",
                                        featureidkey="properties.location_id",
                                        center={"lat":40.7, "lon":-73.97})
        taxiHighlights.update_traces(marker_line=dict(color="red", width=5))
        for i in range(len(taxiHighlights.data)):
            taxifig.add_trace(taxiHighlights.data[i])

    taxifig.update_geos(fitbounds="locations", visible=False)
    taxifig.update_layout(
        mapbox_style="carto-positron",
        margin={"r":0,"t":0,"l":0,"b":0},
        height=choroplethHeight,
        showlegend=False)

    return taxifig
            
def get_covidfig(selectedZips):
    # clear traces
    covidfig.data = [covidfig.data[0]]

    if (len(selectedZips) > 0):
        highlights = get_highlights(selectedZips, covidgj, zip_lookup)
        covidHighlights = px.choropleth_mapbox(coviddf.loc[coviddf["zip_code"].isin(selectedZips)],
                                        geojson=highlights,
                                        locations="zip_code", color="hospitalization_rate",
                                        color_continuous_scale="Viridis",
                                        hover_name="zip_code",
                                        hover_data={
                                            "hospitalization_rate" : ":.2f",
                                            "zip_code" : False},
                                        featureidkey="properties.postalCode",
                                        center={"lat":40.7, "lon":-73.97})
        covidHighlights.update_traces(marker_line=dict(color="red", width=5))
        covidfig.add_trace(covidHighlights.data[0])

    covidfig.update_geos(fitbounds="locations", visible=False)
    covidfig.update_layout(
        mapbox_style="carto-positron",
        margin={"r":0,"t":0,"l":0,"b":0},
        height=choroplethHeight)

    return covidfig

def get_covid_drilldown(selectedZips):
    if (len(selectedZips) > 0):
        df = pd.read_csv(covid_data_path + "processed_data.csv", parse_dates=["date"])
        mask = df["zip_code"].isin(selectedZips)
        covid_drilldown = px.line(df[mask], x='date', y='hospitalization_rate', line_group = 'zip_code', color='zip_code', hover_name="zip_code")
        return covid_drilldown
    return dash.no_update
        

def get_taxi_drilldown(selectedLocs):
    return dummy_fig

# layout
app.layout = html.Div([
    html.Div([ 
        html.Div([
            html.H1(
                children='COVID-19 Choropleth',
                style={
                    'textAlign': 'center',
                    'color': 'black'
                }
            ),
            dcc.Graph(id="covid-choropleth")
        ], className="five columns"),

        html.Div([
            html.H1(
                children='Taxi Choropleth',
                style={
                    'textAlign': 'center',
                    'color': 'black'
                }
            ),
            dcc.Graph(id="taxi-choropleth")
        ], className="five columns"),

        html.Div([
            dcc.Graph(id="taxi-legend",
            figure=taxilegend)
        ], className="one column")
    ], className="row"),

    html.Div([ 
        html.Div([
            html.H1(
                children='COVID-19 Drilldown',
                style={
                    'textAlign': 'center',
                    'color': 'black'
                }
            ),
            dcc.Graph(id='covid-drilldown'),
        ], className="five columns"),

        html.Div([
            html.H1(
                children='Taxi Drilldown',
                style={
                    'textAlign': 'center',
                    'color': 'black'
                }
            ),
            dcc.Graph(id='taxi-drilldown'),
        ], className="five columns"),
    ], className="row", id="drilldown", style= {'display': 'block'})
])

# interactions
covidTriggerStr = "covid-choropleth.clickData"
taxiTriggerStr = "taxi-choropleth.clickData"

@app.callback([
    Output("covid-choropleth", "figure"),
    Output("taxi-choropleth", "figure"),
    Output("drilldown", "style")
], [
    Input("covid-choropleth", "clickData"),
    Input("taxi-choropleth", "clickData"),
    Input("drilldown", "style")])
def update_plots(covidClickData, taxiClickData, currentVisibility):
    # print(currentVisibility)
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

    newVisibility = "block"
    if currentVisibility["display"] == "block":
        newVisibility = "none"

    return get_covidfig(selectedZips), get_taxifig(selectedLocs), {"display": newVisibility}


@app.callback([
    Output("covid-drilldown", "figure"),
    Output("taxi-drilldown", "figure"),
], [
    Input("covid-choropleth", "clickData"),
    Input("taxi-choropleth", "clickData"),
])
def update_drilldowns(covidClickData, taxiClickData):
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

    return get_covid_drilldown(selectedZips), get_taxi_drilldown(selectedLocs)

# main
if __name__ == "__main__":
    app.run_server(debug=True)
