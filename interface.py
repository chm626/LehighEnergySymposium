import altair as alt
import pandas as pd
import streamlit as st
from database import get_mysql_connection, execute_query, get_pjm_average_lmp, get_pjm_data

@st.cache_data
def get_data():
    """Get PJM data from database"""
    try:
        source = get_pjm_data()
        return source
    except Exception as e:
        st.error(f"Failed to load PJM data: {e}")
        return pd.DataFrame()

source = get_data()

# Get unique zones for checkbox selection
available_zones = sorted(source['zone'].unique()) if not source.empty else []

# Create zone selection checkboxes
st.sidebar.header("Select Zones to Display")
selected_zones = []
for zone in available_zones:
    if st.sidebar.checkbox(zone, value=True, key=f"checkbox_{zone}"):
        selected_zones.append(zone)

# Filter data based on selected zones
if selected_zones and not source.empty:
    filtered_source = source[source['zone'].isin(selected_zones)]
else:
    if not source.empty:
        st.warning("Please select at least one zone to display.")
    filtered_source = source

def get_chart(data):
    hover = alt.selection_point(
        fields=["date"],
        nearest=True,
        on="mouseover",
        empty=False,
    )

    lines = (
        alt.Chart(data, title="PJM Monthly Average LMP by Zone")
        .mark_line()
        .encode(
            x=alt.X("date", title="Date"),
            y=alt.Y("lmp_cents_per_kwh", title="Average LMP (¢/kWh)"),
            color="zone",
            tooltip=[
                alt.Tooltip("date", title="Month"),
                alt.Tooltip("lmp_cents_per_kwh", title="Average LMP (¢/kWh)", format=".2f"),
                alt.Tooltip("zone", title="Zone"),
            ],
        )
        .add_params(hover)
        .properties(height=500)
    )

    return lines.resolve_scale(color="independent")

# Create chart with filtered data
if not filtered_source.empty:
    chart = get_chart(filtered_source)
    
    # Display data summary with better spacing
    st.subheader("Data Summary")
    col1, col2, col3, col4 = st.columns([1, 2, 1, 1.5])
    
    with col1:
        st.metric("Total Records", len(filtered_source))
    with col2:
        date_range = f"{filtered_source['date'].min().strftime('%Y-%m')} to {filtered_source['date'].max().strftime('%Y-%m')}"
        st.metric("Date Range", date_range)
    with col3:
        st.metric("Zones Displayed", len(selected_zones))
    with col4:
        avg_lmp = filtered_source['lmp_cents_per_kwh'].mean()
        st.metric("Overall Avg LMP", f"{avg_lmp:.2f} ¢/kWh")

    # Display the chart
    st.altair_chart(chart, use_container_width=True)
else:
    st.warning("No data available to display. Please check your database connection.")

# Database section
st.header("Database Connection")
if st.button("Test Database Connection"):
    try:
        engine = get_mysql_connection()
        st.success("✅ Database connection successful!")
        
        # Example query - replace with your actual query
        sample_query = "SELECT COUNT(*) as total_records FROM your_table_name"
        st.write("**Sample Query:**")
        st.code(sample_query)
        
        # Uncomment the line below when you have actual data to query
        # df = execute_query(engine, sample_query)
        # st.dataframe(df)
        
    except Exception as e:
        st.error(f"Database connection failed: {e}")

# PJM Average LMP section
st.subheader("PJM Average LMP")
if st.button("Get PJM Average LMP"):
    try:
        avg_lmp_dollars = get_pjm_average_lmp()
        avg_lmp_cents = avg_lmp_dollars * 0.1  # Convert to cents/kWh
        st.success(f"Average LMP: ${avg_lmp_dollars:.2f}/MWh ({avg_lmp_cents:.2f} ¢/kWh)")
        
        # Display as a metric
        col1, col2, col3 = st.columns(3)
        with col2:
            st.metric(
                label="Average LMP", 
                value=f"{avg_lmp_cents:.2f} ¢/kWh",
                help="Average Locational Marginal Price from PJM_daily table (converted to cents per kWh)"
            )
            
    except Exception as e:
        st.error(f"Failed to get PJM Average LMP: {e}")

