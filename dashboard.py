import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc

# -----------------------
# Load Data
# -----------------------
df = pd.read_csv("us_accidents_stratified_sample.csv")

# Ensure Hour_Group exists
if "Hour" not in df.columns:
    df["Hour"] = pd.to_datetime(df["Start_Time"]).dt.hour
df["Hour_Group"] = pd.cut(df["Hour"],
                          bins=[-1, 5, 11, 17, 23],
                          labels=["Night", "Morning", "Afternoon", "Evening"])

# Precipitation bin
if "Precipitation(in)" in df.columns:
    df["Precipitation_Bin"] = pd.cut(df["Precipitation(in)"],
                                     bins=[-0.01, 0.01, 0.1, 0.5, 1, 5, 50],
                                     labels=["None", "Trace", "Light", "Moderate", "Heavy", "Extreme"])

# -----------------------
# App Layout
# -----------------------
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([

    html.H1("US Accidents Dashboard", className="text-center my-4"),

    # Filters
    dbc.Row([
        dbc.Col([
            html.Label("Select State"),
            dcc.Dropdown(
                options=[{"label": s, "value": s} for s in sorted(df["State"].unique())],
                id="state-filter",
                multi=True
            )
        ], md=4),
        dbc.Col([
            html.Label("Select Hour Group"),
            dcc.Dropdown(
                options=[{"label": h, "value": h} for h in df["Hour_Group"].dropna().unique()],
                id="hour-filter",
                multi=True
            )
        ], md=4),
        dbc.Col([
            html.Label("Select Precipitation Bin"),
            dcc.Dropdown(
                options=[{"label": p, "value": p} for p in df["Precipitation_Bin"].dropna().unique()],
                id="precip-filter",
                multi=True
            )
        ], md=4),
    ], className="mb-4"),

    # KPI Row
    dbc.Row(id="kpi-row", className="mb-4"),

    # Charts Row 1
    dbc.Row([
        dbc.Col(dcc.Graph(id="severity-chart"), md=6),
        dbc.Col(dcc.Graph(id="hour-chart"), md=6)
    ]),

    # Charts Row 2
    dbc.Row([
        dbc.Col(dcc.Graph(id="precip-chart"), md=6),
        dbc.Col(dcc.Graph(id="state-chart"), md=6)
    ]),

    # Scatter Map
    dbc.Row([
        dbc.Col(dcc.Graph(id="map-chart"), md=12)
    ])

], fluid=True)


# -----------------------
# Callbacks
# -----------------------
@app.callback(
    Output("kpi-row", "children"),
    Output("severity-chart", "figure"),
    Output("hour-chart", "figure"),
    Output("precip-chart", "figure"),
    Output("state-chart", "figure"),
    Output("map-chart", "figure"),
    Input("state-filter", "value"),
    Input("hour-filter", "value"),
    Input("precip-filter", "value")
)
def update_dashboard(selected_states, selected_hour_groups, selected_precip_bins):
    filtered_df = df.copy()

    if selected_states:
        filtered_df = filtered_df[filtered_df["State"].isin(selected_states)]
    if selected_hour_groups:
        filtered_df = filtered_df[filtered_df["Hour_Group"].isin(selected_hour_groups)]
    if selected_precip_bins:
        filtered_df = filtered_df[filtered_df["Precipitation_Bin"].astype(str).isin(selected_precip_bins)]

    # KPI calculations
    total_accidents = len(filtered_df)
    most_common_severity = filtered_df["Severity"].mode()[0] if total_accidents > 0 else "N/A"
    busiest_hour_group = filtered_df["Hour_Group"].value_counts().idxmax() if total_accidents > 0 else "N/A"
    avg_precip = filtered_df["Precipitation(in)"].mean() if "Precipitation(in)" in filtered_df else 0

    kpi_cards = [
        dbc.Col(dbc.Card(dbc.CardBody([html.H4("Total Accidents"), html.H2(f"{total_accidents:,}")]), color="light"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H4("Most Common Severity"), html.H2(most_common_severity)]), color="light"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H4("Busiest Hour Group"), html.H2(str(busiest_hour_group))]), color="light"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H4("Avg. Precipitation (in)"), html.H2(f"{avg_precip:.2f}")]), color="light"), md=3),
    ]

    # Chart 1: Severity distribution
    severity_counts = filtered_df["Severity"].value_counts(normalize=True) * 100
    fig_severity = px.pie(
        values=severity_counts.values,
        names=severity_counts.index,
        title="Accident Severity Distribution (%)",
        hole=0.5
    )

    # Chart 2: Accidents by Hour Group
    accidents_by_hour = filtered_df.groupby("Hour_Group", observed=True).size().reset_index(name="count")
    fig_hour = px.bar(accidents_by_hour.sort_values(by='count', ascending=True),
                      y="Hour_Group", x="count", orientation="h",
                      title="Accidents by Hour Group")

    # Chart 4: Accidents by Precipitation Bin
    accidents_by_precip = filtered_df.groupby("Precipitation_Bin", observed=True).size().reset_index(name="count")
    fig_precip_bin = px.bar(accidents_by_precip, y="Precipitation_Bin", x="count", orientation="h",
                            title="Accidents by Precipitation Bin")

    # Chart 5: Top States by Accidents
    accidents_by_state = filtered_df.groupby("State").size().reset_index(name="count").sort_values("count", ascending=False).head(10)
    fig_state = px.bar(accidents_by_state, x="State", y="count", title="Top 10 States by Accidents")

    # Scatter Map (your version)
    fig_map = px.scatter_mapbox(
        filtered_df,
        lat="Start_Lat",
        lon="Start_Lng",
        hover_name="City",
        color="Severity",
        zoom=3,
        height=500,
        title="Accident Hotspots (by Severity)"
    )
    fig_map.update_layout(mapbox_style="open-street-map")

    return kpi_cards, fig_severity, fig_hour, fig_precip_bin, fig_state, fig_map


if __name__ == "__main__":
    app.run(debug=True)
