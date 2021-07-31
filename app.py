import dash
import numpy as np
import pandas as pd
import json
import geojson
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objs as go

import datetime
from dateutil.relativedelta import *
   
map_data_path = "map_data/"
covid_data_path = "covid_data/"
taxi_data_path = "taxi_data/"
taxi_zone_path = "taxi_data/by_zone/"

# taxi zones
with open(map_data_path + "taxi_zones_2_simpler.json") as f:
    taxigj = geojson.load(f)
nzones = len(taxigj["features"])
taxi_lookup = {int(feature["properties"]["location_id"]) : feature
                for feature in taxigj["features"]}

# taxi data
taxidfMonths = []
for monthID in range(1, 13):
    dfmonth = pd.read_csv(taxi_data_path + "taxi_data_2019-" + f"{monthID:02}" + ".csv")
    taxidfMonths.append(dfmonth)
for monthID in range(1, 13):
    dfmonth = pd.read_csv(taxi_data_path + "taxi_data_2020-" + f"{monthID:02}" + ".csv")
    taxidfMonths.append(dfmonth)

# covid zones (zip codes)
with open(map_data_path + "zip_codes_simpler.json") as f:
    covidgj = geojson.load(f)
nzips = len(covidgj["features"])
zip_lookup = {int(feature["properties"]["postalCode"]) : feature
                for feature in covidgj["features"]}

# covid data
coviddfMonths = []
for monthID in range(1, 13):
    dfmonth = pd.read_csv(covid_data_path + "covid_data-2020-" + str(monthID) + ".csv")
    coviddfMonths.append(dfmonth)

# zone overlap
overlapdf = pd.read_csv(map_data_path + "taxi_zip_overlap.csv")

# taxi bivariate color map
nbiv_colors = 9
biv_colors = [  "#e8e8e8", "#b5c0da", "#6c83b5",
                "#b8d6be", "#90b2b3", "#567994",
                "#73ae80", "#5a9178", "#2a5a5b"]
bivcmap = {clr : clr for clr in biv_colors}

# slider marks
ratio_marks = { 0  : {"label": "Jan."},
                1  : {"label": "Feb."},
                2  : {"label": "2020 Mar.", "style":{"color": "#77b0b1"}},
                3  : {"label": "Apr."},
                4  : {"label": "May"},
                5  : {"label": "Jun."},
                6  : {"label": "Jul."},
                7  : {"label": "Aug."},
                8  : {"label": "Sep."},
                9  : {"label": "Oct."},
                10 : {"label": "Nov."},
                11 : {"label": "Dec."},}
rawrevenue_marks = {0  : {"label": "2019", "style":{"color": "#77b0b1"}},
                    1  : {"label": "Feb."},
                    2  : {"label": "Mar."},
                    3  : {"label": "Apr."},
                    4  : {"label": "May"},
                    5  : {"label": "Jun."},
                    6  : {"label": "Jul."},
                    7  : {"label": "Aug."},
                    8  : {"label": "Sep."},
                    9  : {"label": "Oct."},
                    10 : {"label": "Nov."},
                    11 : {"label": "Dec."},
                    12 : {"label": "2020", "style":{"color": "#77b0b1"}},
                    13 : {"label": "Feb."},
                    14 : {"label": "Mar."},
                    15 : {"label": "Apr."},
                    16 : {"label": "May"},
                    17 : {"label": "Jun."},
                    18 : {"label": "Jul."},
                    19 : {"label": "Aug."},
                    20 : {"label": "Sep."},
                    21 : {"label": "Oct."},
                    22 : {"label": "Nov."},
                    23 : {"label": "Dec."},}

# helper funcs. about data
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

def myLog(x):
    return np.log(x) if (x > 0) else 0

def set_interval_value(x, a, b):
    # function that associate to a float x, 
    # a value encoding its position with respect to the interval [a, b]
    #  the associated values are 0, 1, 2 assigned as follows:
    if x <= a: 
        return 0
    elif a < x <= b: 
        return 1
    else: 
        return 2
    
def data2color(x, y, a, b, c, d, biv_colors):
    # This function works only with a list of 9 bivariate colors,
    # because of the definition of set_interval_value()
    # x, y: lists or 1d arrays, containing values of the two variables
    #  each x[k], y[k] is mapped to an int  value xv, respectively yv, representing its category,
    # from which we get their corresponding color  in the list of bivariate colors
    if len(x) != len(y):
        raise ValueError('the list of x and y-coordinates must have the same length')
    n_colors = len(biv_colors)
    if n_colors != 9:
        raise ValueError('the list of bivariate colors must have the length eaqual to 9')
    n = 3    
    xcol = [set_interval_value(v, a, b) for v in x]
    ycol = [set_interval_value(v, c, d) for v in y]
    # index of the corresponding color in the list of bivariate colors
    idxcol = [int(xc + n*yc) for xc, yc in zip(xcol,ycol)]
    colors = np.array(biv_colors)[idxcol]
    return list(colors)

# dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[
        'https://codepen.io/chriddyp/pen/bWLwgP.css'
    ]
)

# figures
choroplethHeight = 1300

# bivariate legend
@app.callback(
    Output("taxi-legend", "figure")
, [
    Input("is-bivariate-view", "data"),
])
def update_taxilegend(isBivariateView):
    taxilegend = go.Figure(layout=dict(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'))
    taxilegend.update_xaxes(visible=False)
    taxilegend.update_yaxes(visible=False)
    if isBivariateView:
        taxilegend = None
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
    return taxilegend

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

def get_taxifig(selectedLocs, tdf, hover_data, coloring, isBivariateView):
    # clear traces
    taxifig = None
    if isBivariateView:
        taxifig = px.choropleth_mapbox(tdf, geojson=taxigj,
                                locations="PULocationID", 
                                color=coloring,
                                color_discrete_map=bivcmap,
                                hover_name="Zone",
                                hover_data=hover_data,
                                featureidkey="properties.location_id",
                                center={"lat":40.7, "lon":-73.97}, zoom=10.62)
    else:
        taxifig = px.choropleth_mapbox(tdf, geojson=taxigj,
                               locations="PULocationID", 
                                color=coloring,
                                color_continuous_scale="Viridis",
                                hover_name="Zone",
                                hover_data=hover_data,
                                featureidkey="properties.location_id",
                                center={"lat":40.7, "lon":-73.97}, zoom=10.62)

    if (len(selectedLocs) > 0):
        highlights = get_highlights(selectedLocs, taxigj, taxi_lookup)
        taxiHighlights = px.choropleth_mapbox(tdf.loc[tdf["PULocationID"].isin(selectedLocs)],
                                        geojson=highlights,
                                        locations="PULocationID", color=coloring,
                                        color_discrete_map=bivcmap,
                                        hover_name="Zone",
                                        hover_data=hover_data,
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
        showlegend=False,
        modebar_remove=["pan", "select2d", "lasso2d"])

    return taxifig
            
def get_covidfig(selectedZips, cdf):
    # clear traces
    covidfig = px.choropleth_mapbox(cdf, geojson=covidgj,
                            locations="zip_code", color="hospitalization_rate",
                            color_continuous_scale="Viridis",
                            hover_name="zip_code",
                            hover_data={
                                "hospitalization_rate" : ":.2f",
                                "zip_code" : False},
                            featureidkey="properties.postalCode",
                            center={"lat":40.7, "lon":-73.97},
                            zoom=10.62)

    if (len(selectedZips) > 0):
        highlights = get_highlights(selectedZips, covidgj, zip_lookup)
        covidHighlights = px.choropleth_mapbox(cdf.loc[cdf["zip_code"].isin(selectedZips)],
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
        height=choroplethHeight,
        modebar_remove=["pan", "select2d", "lasso2d"])

    return covidfig

def compute_dates(start, end, isRatio):
    if not isRatio:
        startDate = datetime.datetime(2019, 1, 1)+relativedelta(months=+start)
        endDate = datetime.datetime(2019, 1, 1) + relativedelta(months=+end)
        dates = []
        while startDate <= endDate:
            dates.append(startDate)
            startDate = startDate + relativedelta(months=+1)
        return dates
    else:
        startDate = datetime.datetime(2019, 1, 1)+relativedelta(months=+start)
        endDate = datetime.datetime(2019, 1, 1) + relativedelta(months=+end)
        dates = []
        while startDate <= endDate:
            dates.append(startDate)
            startDate = startDate + relativedelta(months=+1)
        startDate = datetime.datetime(2020, 1, 1)+relativedelta(months=+start)
        endDate = datetime.datetime(2020, 1, 1) + relativedelta(months=+end)
        while startDate <= endDate:
            dates.append(startDate)
            startDate = startDate + relativedelta(months=+1)
        return dates


def compute_dates_covid(start, end, isRatio):
    # when not in Ratio view, the slider being completely out of the March-December 2020 range causes the whole range to be shown.
    # otherwise only the part of the range that's part of the slider will be shown (i.e. March-X 2020)
    if not isRatio:
        if end <= 14:
            start = 0
            end = 11
        else:
            if start < 14:
                start = 2
            else:
                start = max(2, start%12)
            end %= 12
    elif start < 2:
        start = 2
    dates = []
    startDate = datetime.datetime(2020, 1, 1)+relativedelta(months=+start)
    endDate = datetime.datetime(2020, 1, 1) + relativedelta(months=+end)
    while startDate <= endDate:
        dates.append(startDate)
        startDate = startDate + relativedelta(months=+1)
    return dates


def get_covid_drilldown(selectedZips, start, end, isRatio):
    if (len(selectedZips) == 0):
        return dash.no_update
    covid_data = []
    dates = compute_dates_covid(start, end, isRatio)
    for date in dates:
        df = pd.read_csv(covid_data_path + "covid_data-2020-"+str(date.month)+".csv")
        df.insert(0, "date", date)
        covid_data.append(df)
    all_data = pd.concat(covid_data)
    location_mask = all_data["zip_code"].isin(selectedZips)
    covid_drilldown = px.line(all_data[location_mask], x='date', y='hospitalization_rate', line_group = 'zip_code', color='zip_code', hover_name="zip_code")
    return covid_drilldown
        

def get_taxi_drilldown(selectedLocs, start, end, isRatio):
    if (len(selectedLocs) == 0):
        return dash.no_update
    taxi_zone_data = []
    dates = compute_dates(start, end, isRatio)
    for location_id in selectedLocs:
        df = pd.read_csv(taxi_zone_path + "taxi_data_"+str(location_id)+".csv", parse_dates=['date'])
        taxi_zone_data.append(df)
    all_data = pd.concat(taxi_zone_data)
    mask = all_data['date'].isin(dates)

    taxi_drilldown = None
    ctx = dash.callback_context
    if ctx.triggered[0]["prop_id"] == covidTriggerStr:
        taxi_drilldown = px.bar(all_data[mask], x='date', y='total_cost', barmode='group', color='zone_name')
    elif ctx.triggered[0]["prop_id"] == taxiTriggerStr:
        taxi_drilldown = px.bar(all_data[mask], x='date', y='total_cost', barmode='group', color='taxi_type')
    return taxi_drilldown

# layout
app.layout = html.Div([
    html.Div([
        html.Div([
            dcc.RangeSlider(
                id='month-slider',
                min=2,
                max=11,
                step=None,
                marks=ratio_marks,
                value= [2, 2],
        )], className="ten columns"),

        html.Div([
            html.Button('Ratio view', id='btn-change-view', n_clicks=0),
        ]),
    ]),

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
            html.Button('Bivariate View', id='btn-bu-change-view', n_clicks=0),
        ]),

        html.Div([
            dcc.Graph(id="taxi-legend")
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
    ], className="row", id="drilldown", style= {'display': 'block'}),

    html.Div(id="hidden-div", style={"display":"none"}),

    dcc.Store("current-taxidf"),
    dcc.Store("current-coviddf"),
    dcc.Store("is-bivariate-view"),
    dcc.Store("is-ratio-view"),
    dcc.Store("current-hover-formatting"),
    dcc.Store("current-coloring")
])

# interactions
covidTriggerStr = "covid-choropleth.clickData"
taxiTriggerStr = "taxi-choropleth.clickData"
covidRelayoutStr = "covid-choropleth.relayoutData"
taxiRelayoutStr = "taxi-choropleth.relayoutData"

@app.callback([
    Output("btn-change-view", "children"),
    Output("is-ratio-view", "data"),
    Output("month-slider", "min"),
    Output("month-slider", "max"),
    Output("month-slider", "marks"),
    Output("month-slider", "value"),
], [
    Input("btn-change-view", "n_clicks"),
])
def update_slider_view(n_clicks):
    if (n_clicks % 2):
        return "Raw Revenue View", False, 0, 23, rawrevenue_marks, [12, 12]
    else:
        return "Ratio View", True, 2, 11, ratio_marks, [2, 2]

@app.callback([
    Output("btn-bu-change-view", "children"),
    Output("is-bivariate-view", "data"),
], [
    Input("btn-bu-change-view", "n_clicks"),
])
def update_bivariate_view(n_clicks):
    if (n_clicks % 2):
        return "Univariate View", True
    else:
        return "Bivariate View", False



@app.callback([
    Output("current-coviddf", "data"),
    Output("current-taxidf", "data"),
    Output("current-hover-formatting", "data"),
    Output("current-coloring", "data")],
    [Input("month-slider", "value"),
    Input("is-ratio-view", "data"),
    Input("is-bivariate-view", "data")])
def update_current_dataframe(value, isRatioView, isBivariateView):
    start, end = value

    if isRatioView:
        if start == end:
            tdf = taxidfMonths[12 + end].copy()
            tdf.drop(columns=["biv_amount_color"], inplace=True)

            cdf = coviddfMonths[end].copy()
        else:
            tdf2020 = taxidfMonths[12 + end].copy()
            tdf2019 = taxidfMonths[end].copy()
            for i in range(start, end):
                tdf2020["yellow_total_amount"] += taxidfMonths[12 + i]["yellow_total_amount"]
                tdf2020["green_total_amount"] += taxidfMonths[12 + i]["green_total_amount"]
                tdf2019["yellow_total_amount"] += taxidfMonths[i]["yellow_total_amount"]
                tdf2019["green_total_amount"] += taxidfMonths[i]["green_total_amount"]
            yellowratio = pd.DataFrame({"ratio":\
                (tdf2019["yellow_total_amount"] - tdf2020["yellow_total_amount"]) \
                            / tdf2019["yellow_total_amount"]}).replace([np.nan, np.inf, -np.inf], 0) \
                                / (end - start + 1)
            greenratio = pd.DataFrame({"ratio":\
                (tdf2019["green_total_amount"] - tdf2020["green_total_amount"]) \
                            / tdf2019["green_total_amount"]}).replace([np.nan, np.inf, -np.inf], 0) \
                                / (end - start + 1)
            totalratio = pd.DataFrame({"ratio":\
              (tdf2019["green_total_amount"] - tdf2020["green_total_amount"] \
                   + tdf2019["yellow_total_amount"] - tdf2020["yellow_total_amount"]) \
                            / (tdf2019["green_total_amount"]+tdf2019["yellow_total_amount"])}).replace([np.nan, np.inf, -np.inf], 0) \
                                / (end - start + 1)

            yellow_percentiles = np.percentile(yellowratio["ratio"], [33, 66])
            green_percentiles = np.percentile(greenratio["ratio"], [33, 66])
            colors = data2color( yellowratio["ratio"],
                                    greenratio["ratio"],
                                    a=yellow_percentiles[0],  b=yellow_percentiles[1], 
                                    c=green_percentiles[0],  d=green_percentiles[1],
                                    biv_colors=biv_colors)
            tdf2020["yellow_change_percent"] = -yellowratio["ratio"] * 100
            tdf2020["green_change_percent"] = -greenratio["ratio"] * 100
            tdf2020["total_change_percent"] = -totalratio["ratio"]*100
            tdf2020["biv_ratio_color"] = colors
            
            tdf = tdf2020
            tdf.drop(columns=["biv_amount_color"], inplace=True)
            tdf['total_amount'] =  tdf["yellow_total_amount"]+tdf["green_total_amount"]
            tdf["log_total_amount"] = \
                np.array(list(map(myLog, tdf["total_amount"])))
            tdf["log_total_change_percent"] = \
                np.array(list(map(myLog, tdf["total_change_percent"])))

            cdf = coviddfMonths[end].copy()
            for i in range(start, end):
                cdf["hospitalization_rate"] += coviddfMonths[i]["hospitalization_rate"]
            cdf["hospitalization_rate"] /= (end - start + 1)

        hover_data = {"yellow_total_amount": ":.2f",
                        "green_total_amount" : ":.2f",
                        "log_total_amount": ":.2f",
                        "yellow_change_percent" : ":.2f",
                        "green_change_percent" : ":.2f",
                        "log_total_change_percent": ":.2f",
                        "Borough" : True,
                        "service_zone" : True,
                        "biv_ratio_color" : False}
        coloring = "biv_ratio_color"
        if not isBivariateView:
            coloring = "log_total_change_percent"

    else:
        if start == end:
            tdf = taxidfMonths[end].copy()
            if (end >= 12):
                # 2020
                tdf.drop(columns=["yellow_change_percent", \
                                    "green_change_percent", \
                                    "biv_ratio_color"], inplace=True)

                cdf = coviddfMonths[end - 12].copy()
            else:
                # 2019
                cdf = coviddfMonths[0].copy()
                cdf["hospitalization_rate"] = 0
        else:
            tdf = taxidfMonths[end].copy()
            for i in range(start, end):
                tdf["yellow_total_amount"] += taxidfMonths[i]["yellow_total_amount"]
                tdf["green_total_amount"] += taxidfMonths[i]["green_total_amount"]
            tdf["yellow_log_total_amount"] = \
                np.array(list(map(myLog, tdf["yellow_total_amount"])))
            tdf["green_log_total_amount"] = \
                np.array(list(map(myLog, tdf["green_total_amount"])))
            yellow_percentiles = np.percentile(tdf["yellow_log_total_amount"], [33, 66])
            green_percentiles = np.percentile(tdf["green_log_total_amount"], [33, 66])
            colors = data2color(tdf["yellow_log_total_amount"],
                                tdf["green_log_total_amount"],
                                a=yellow_percentiles[0],  b=yellow_percentiles[1], 
                                c=green_percentiles[0],  d=green_percentiles[1],
                                biv_colors=biv_colors)
            tdf["biv_amount_color"] = colors
            tdf.drop(columns=["yellow_log_total_amount", "green_log_total_amount"], inplace=True)
            tdf['total_amount'] =  tdf["yellow_total_amount"]+tdf["green_total_amount"]
            tdf["log_total_amount"] = \
                np.array(list(map(myLog, tdf["total_amount"])))
            if (end >= 12):
                # 2020
                tdf.drop(columns=["yellow_change_percent", \
                                    "green_change_percent", \
                                    "total_change_percent", \
                                    "biv_ratio_color"], inplace=True)

                cdf = coviddfMonths[end - 12].copy()
            else:
                # 2019
                cdf = coviddfMonths[0].copy()
                cdf["hospitalization_rate"] = 0

            for i in range(start, end):
                if i >= 12:
                    cdf["hospitalization_rate"] += coviddfMonths[i - 12]["hospitalization_rate"]
            cdf["hospitalization_rate"] /= (end - start + 1)

        hover_data = {"yellow_total_amount": ":.2f",
                        "green_total_amount" : ":.2f",
                        "log_total_amount" : ":.2f",
                        "Borough" : True,
                        "service_zone" : True,
                        "biv_amount_color" : False}
        coloring = "biv_amount_color"
        if not isBivariateView:
            coloring = "log_total_amount"

    return cdf.to_json(), tdf.to_json(), hover_data, coloring

@app.callback([
    Output("covid-choropleth", "figure"),
    Output("taxi-choropleth", "figure"),
], [
    Input("covid-choropleth", "clickData"),
    Input("taxi-choropleth", "clickData"),
    Input("current-coviddf", "data"),
    Input("current-taxidf", "data"),
    Input("current-hover-formatting", "data"),
    Input("current-coloring", "data"),
    Input("is-bivariate-view", "data"),
    Input('covid-choropleth', 'relayoutData'),
    Input('taxi-choropleth', 'relayoutData')
], [
    State('covid-choropleth', 'figure'),
    State('taxi-choropleth', 'figure')
])
def update_plots(covidClickData, taxiClickData, cdf, tdf, hover_data, coloring, isBivariateView, covidRelayout, taxiRelayout, covidFig, taxiFig):
    ctx = dash.callback_context
    #ctx_msg = json.dumps({
    #    'states': ctx.states,
    #    'triggered': ctx.triggered,
    #    'inputs': ctx.inputs
    #}, indent=2)
    taxidata = pd.DataFrame.from_dict(json.loads(tdf))
    coviddata = pd.DataFrame.from_dict(json.loads(cdf))

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
    elif ctx.triggered[0]["prop_id"] == covidRelayoutStr:
        if covidRelayout is not None and "mapbox.center" in covidRelayout:
            taxiFig["layout"]["mapbox"]["center"] = covidRelayout["mapbox.center"]
            taxiFig["layout"]["mapbox"]["zoom"] = covidRelayout["mapbox.zoom"]
        return covidFig, taxiFig
    elif ctx.triggered[0]["prop_id"] == taxiRelayoutStr:
        if taxiRelayout is not None and "mapbox.center" in taxiRelayout:
            covidFig["layout"]["mapbox"]["center"] = taxiRelayout["mapbox.center"]
            covidFig["layout"]["mapbox"]["zoom"] = taxiRelayout["mapbox.zoom"]
        return covidFig, taxiFig

    if covidLocation:
        selectedZips = [covidLocation]
        selectedLocs = list(overlapdf[overlapdf["zip_code"] == covidLocation]["LocationID"])
    elif taxiLocation:
        selectedLocs = [taxiLocation]
        selectedZips = list(overlapdf[overlapdf["LocationID"] == taxiLocation]["zip_code"])

    return get_covidfig(selectedZips, coviddata), \
            get_taxifig(selectedLocs, taxidata, hover_data, coloring, isBivariateView)


@app.callback([
    Output("covid-drilldown", "figure"),
    Output("taxi-drilldown", "figure"),
], [
    Input("covid-choropleth", "clickData"),
    Input("taxi-choropleth", "clickData"),
    Input("month-slider", "value"),
    Input("is-ratio-view", "data"),
])
def update_drilldowns(covidClickData, taxiClickData, value, isRatio):
    ctx = dash.callback_context

    start, end = value
    if start == end and isRatio:
        start = 0
        end = 11
    if start == end and not isRatio:
        start = 0
        end = 23

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

    return get_covid_drilldown(selectedZips, start, end, isRatio), get_taxi_drilldown(selectedLocs, start, end, isRatio)

# main
if __name__ == "__main__":
    app.run_server(debug=True)
