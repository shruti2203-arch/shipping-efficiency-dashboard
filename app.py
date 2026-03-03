import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

# ======================================================
# PROFESSIONAL CLEAN THEME
# ======================================================
st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF; }
        section[data-testid="stSidebar"] { background-color: #F3F6F9; }
        span[data-baseweb="tag"] {
            background-color: #2E8B57 !important;
            color: white !important;
        }
    </style>
""", unsafe_allow_html=True)

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Shipping Efficiency Dashboard", layout="wide")

st.title("📦 Nassau Candy Distributor – Shipping Efficiency Dashboard")
st.markdown("""
This dashboard analyzes shipping route efficiency, identifies geographic bottlenecks,
and evaluates ship mode performance across U.S. regions.
""")

# ======================================================
# LOAD DATA
# ======================================================
df = pd.read_csv("Nassau Candy Distributor.csv")
df.columns = df.columns.str.strip()

df['Order Date'] = pd.to_datetime(df['Order Date'], dayfirst=True)
df['Ship Date'] = pd.to_datetime(df['Ship Date'], dayfirst=True)

df['Lead Time'] = (df['Ship Date'] - df['Order Date']).dt.days
df = df[df['Lead Time'] >= 0].copy()

# ======================================================
# FACTORY MAPPING
# ======================================================
factory_map = {
    "Everlasting Gobstopper": "Secret Factory",
    "Lickable Wallpaper": "Secret Factory",
    "Wonka Gum": "Secret Factory",
    "Hair Toffee": "The Other Factory",
    "Kazookles": "The Other Factory"
}

df['Factory'] = df['Product Name'].map(factory_map)
df['Factory'] = df['Factory'].fillna("Wicked Choccy's")

# ======================================================
# SIDEBAR FILTERS
# ======================================================
st.sidebar.header("🔎 Filters")

date_range = st.sidebar.date_input(
    "Select Date Range",
    [df['Order Date'].min(), df['Order Date'].max()]
)

selected_regions = st.sidebar.multiselect(
    "Select Region",
    df['Region'].unique(),
    default=df['Region'].unique()
)

selected_states = st.sidebar.multiselect(
    "Select State",
    df['State/Province'].unique(),
    default=df['State/Province'].unique()
)

selected_ship_modes = st.sidebar.multiselect(
    "Select Ship Mode",
    df['Ship Mode'].unique(),
    default=df['Ship Mode'].unique()
)

lead_time_threshold = st.sidebar.slider(
    "Lead Time Delay Threshold (Days)",
    int(df['Lead Time'].min()),
    int(df['Lead Time'].max()),
    int(df['Lead Time'].mean())
)

# ======================================================
# APPLY FILTERS
# ======================================================
filtered_df = df[
    (df['Order Date'] >= pd.to_datetime(date_range[0])) &
    (df['Order Date'] <= pd.to_datetime(date_range[1])) &
    (df['Region'].isin(selected_regions)) &
    (df['State/Province'].isin(selected_states)) &
    (df['Ship Mode'].isin(selected_ship_modes))
].copy()

filtered_df['Delayed'] = filtered_df['Lead Time'] > lead_time_threshold

# ======================================================
# KPI SECTION
# ======================================================
col1, col2, col3 = st.columns(3)

col1.metric("Total Shipments", filtered_df.shape[0])
col2.metric("Average Lead Time (Days)", round(filtered_df['Lead Time'].mean(), 2))
col3.metric("Delay Rate (%)", round(filtered_df['Delayed'].mean() * 100, 2))

st.divider()

# ======================================================
# ROUTE EFFICIENCY OVERVIEW
# ======================================================
st.subheader("🚚 Route Efficiency Overview")

filtered_df['Route'] = (
    filtered_df['Factory'] + " → " + filtered_df['State/Province']
)

route_kpi = filtered_df.groupby('Route').agg(
    Total_Shipments=('Order ID', 'count'),
    Avg_Lead_Time=('Lead Time', 'mean'),
    Lead_Time_Std=('Lead Time', 'std'),  # ✅ Variability Added
    Delay_Rate=('Delayed', 'mean')
).reset_index()

route_kpi = route_kpi[route_kpi['Total_Shipments'] >= 20].copy()

if not route_kpi.empty:

    min_lt = route_kpi['Avg_Lead_Time'].min()
    max_lt = route_kpi['Avg_Lead_Time'].max()

    route_kpi['Lead_Time_Normalized'] = (
        (route_kpi['Avg_Lead_Time'] - min_lt) / (max_lt - min_lt)
        if max_lt != min_lt else 0
    )

    route_kpi['Efficiency_Score'] = (
        (1 - route_kpi['Lead_Time_Normalized']) * 0.6 +
        (1 - route_kpi['Delay_Rate']) * 0.4
    )

    route_kpi_sorted = route_kpi.sort_values(
        'Efficiency_Score', ascending=False
    )

    col1, col2 = st.columns(2)

    col1.write("### 🏆 Top 10 Efficient Routes")
    col1.dataframe(route_kpi_sorted.head(10))

    col2.write("### ⚠ Bottom 10 Least Efficient Routes")
    col2.dataframe(route_kpi_sorted.tail(10))

st.divider()

# ======================================================
# GEOGRAPHIC BOTTLENECK ANALYSIS
# ======================================================
st.subheader("🌎 Geographic Bottleneck Analysis")

region_kpi = filtered_df.groupby('Region').agg(
    Total_Shipments=('Order ID', 'count'),
    Avg_Lead_Time=('Lead Time', 'mean'),
    Delay_Rate=('Delayed', 'mean')
).reset_index()

region_kpi['Congestion_Flag'] = (
    (region_kpi['Total_Shipments'] > region_kpi['Total_Shipments'].mean()) &
    (region_kpi['Delay_Rate'] > region_kpi['Delay_Rate'].mean())
)

st.write("### Region Performance")
st.dataframe(region_kpi)

state_kpi = filtered_df.groupby('State/Province').agg(
    Total_Shipments=('Order ID', 'count'),
    Avg_Lead_Time=('Lead Time', 'mean'),
    Delay_Rate=('Delayed', 'mean')
).reset_index()

state_kpi['Congestion_Flag'] = (
    (state_kpi['Total_Shipments'] > state_kpi['Total_Shipments'].mean()) &
    (state_kpi['Delay_Rate'] > state_kpi['Delay_Rate'].mean())
)

st.write("### Congestion-Prone States")
st.dataframe(state_kpi[state_kpi['Congestion_Flag']])

st.divider()

# ======================================================
# GEOGRAPHIC SHIPPING MAP (HEATMAP)
# ======================================================
st.subheader("🗺 US Shipping Efficiency Heatmap")

# Aggregate state performance
state_map = filtered_df.groupby('State/Province').agg(
    Avg_Lead_Time=('Lead Time', 'mean'),
    Delay_Rate=('Delayed', 'mean'),
    Total_Shipments=('Order ID', 'count')
).reset_index()

# Convert state names to abbreviations (basic mapping)
us_state_abbrev = {
    'Alabama': 'AL', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT',
    'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
    'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA',
    'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA',
    'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
    'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE',
    'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC',
    'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
    'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI',
    'South Carolina': 'SC', 'South Dakota': 'SD',
    'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
    'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA',
    'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
}

state_map['State_Code'] = state_map['State/Province'].map(us_state_abbrev)

fig = px.choropleth(
    state_map,
    locations='State_Code',
    locationmode="USA-states",
    color='Avg_Lead_Time',
    scope="usa",
    color_continuous_scale="Reds",
    labels={'Avg_Lead_Time': 'Avg Lead Time'}
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("📊 Regional Bottleneck Visualization")

region_chart = region_kpi.sort_values('Delay_Rate', ascending=False)

fig2 = px.bar(
    region_chart,
    x='Region',
    y='Delay_Rate',
    color='Delay_Rate',
    color_continuous_scale='Reds',
    title="Delay Rate by Region"
)

st.plotly_chart(fig2, use_container_width=True)
# ======================================================
# ROUTE DRILL-DOWN
# ======================================================
st.subheader("🔍 Route Drill-Down Analysis")

if not route_kpi.empty:

    selected_route = st.selectbox(
        "Select Route",
        route_kpi['Route'].unique()
    )

    route_details = filtered_df[
        filtered_df['Route'] == selected_route
    ]

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Shipments", route_details.shape[0])
    col2.metric("Average Lead Time", round(route_details['Lead Time'].mean(), 2))
    col3.metric("Delay Rate (%)", round(route_details['Delayed'].mean() * 100, 2))

    st.dataframe(
        route_details[['Order Date', 'Ship Date', 'Lead Time', 'Ship Mode']]
        .sort_values('Order Date')
        .head(50)
    )

st.divider()

# ======================================================
# SHIP MODE PERFORMANCE
# ======================================================
st.subheader("🚛 Ship Mode Performance")

ship_mode_kpi = filtered_df.groupby('Ship Mode').agg(
    Total_Shipments=('Order ID', 'count'),
    Avg_Lead_Time=('Lead Time', 'mean'),
    Delay_Rate=('Delayed', 'mean')
).reset_index()

st.dataframe(ship_mode_kpi)

fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(ship_mode_kpi['Ship Mode'], ship_mode_kpi['Avg_Lead_Time'])
ax.set_ylabel("Average Lead Time (Days)")
ax.set_title("Lead Time by Ship Mode")
plt.xticks(rotation=45)
st.pyplot(fig)

# ======================================================
# EXECUTIVE INSIGHTS
# ======================================================
st.divider()
st.subheader("📌 Executive Insights")

if not region_kpi.empty and not route_kpi.empty:

    worst_region = region_kpi.sort_values(
        'Delay_Rate', ascending=False
    ).iloc[0]['Region']

    best_route = route_kpi.sort_values(
        'Efficiency_Score', ascending=False
    ).iloc[0]['Route']

    worst_route = route_kpi.sort_values(
        'Efficiency_Score'
    ).iloc[0]['Route']

    st.write(f"""
    • **{worst_region} region** shows the highest delay tendency.

    • Most efficient route: **{best_route}**

    • Least efficient route: **{worst_route}**

    • High-volume + high-delay states require congestion mitigation strategy.

    • Ship mode optimization opportunity exists in high-delay segments.
    """)