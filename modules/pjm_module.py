import pandas as pd
import streamlit as st
from core.database import db_manager
from core.chart_utils import ChartBuilder, DataSummary

class PJMModule:
    """PJM-specific functionality for LMP analysis"""
    
    def __init__(self):
        self.module_name = "PJM LMP Analysis"
        self.description = "Analyze PJM Locational Marginal Prices by zone"
    
    @st.cache_data
    def get_pjm_data(_self):
        """Load daily PJM LMP data and compute monthly mean and median per zone."""
        try:
            query = """
            SELECT 
                date,
                zone,
                average_lmp
            FROM PJM_daily
            ORDER BY date, zone
            """
            df = db_manager.execute_query(query)

            if df.empty:
                return pd.DataFrame()

            # Ensure correct dtypes
            df['date'] = pd.to_datetime(df['date'])
            df['average_lmp'] = df['average_lmp'].astype(float)

            # Compute monthly aggregates (mean and median) per zone
            df['month'] = df['date'].values.astype('datetime64[M]')
            monthly = (
                df.groupby(['month', 'zone'])['average_lmp']
                .agg(mean='mean', median='median', records_used='size')
                .reset_index()
            )

            # Convert $/MWh to ¢/kWh
            monthly['lmp_mean_c_per_kwh'] = monthly['mean'] * 0.1
            monthly['lmp_median_c_per_kwh'] = monthly['median'] * 0.1

            # Standardize date column name used by charts
            monthly = monthly.rename(columns={'month': 'date'})

            return monthly

        except Exception as e:
            st.error(f"Failed to load PJM data: {e}")
            return pd.DataFrame()
    
    def get_pjm_average_lmp(self):
        """Get overall average LMP from PJM data"""
        try:
            query = "SELECT AVG(average_lmp) as avg_lmp FROM PJM_daily"
            df = db_manager.execute_query(query)
            avg_lmp = float(df.iloc[0]['avg_lmp'])
            return avg_lmp
        except Exception as e:
            st.error(f"Failed to get PJM average LMP: {e}")
            return 0.0
    
    def create_zone_filters(self, data):
        """Create PJM-specific zone filters in main content area"""
        if data.empty:
            return []
        
        available_zones = sorted(data['zone'].unique())
        
        st.subheader("Select Zones to Display")
        
        # Create columns for zone checkboxes
        cols = st.columns(3)  # 3 columns for 6 zones (2 rows)
        
        selected_zones = []
        for i, zone in enumerate(available_zones):
            col_idx = i % 3  # Cycle through columns
            with cols[col_idx]:
                if st.checkbox(zone, value=True, key=f"pjm_zone_{zone}"):
                    selected_zones.append(zone)
        
        return selected_zones
    
    def create_data_summary(self, data, selected_zones, measure: str):
        """Create PJM-specific data summary for selected measure (mean|median)."""
        if data.empty:
            return
        
        metrics_config = [
            {
                'label': 'Total Records',
                'value': lambda df: len(df),
                'width': 1
            },
            {
                'label': 'Date Range',
                'value': lambda df: f"{df['date'].min().strftime('%Y-%m')} to {df['date'].max().strftime('%Y-%m')}",
                'width': 2
            },
            {
                'label': 'Underlying Records Used',
                'value': lambda df: int(df['records_used'].sum()) if 'records_used' in df.columns else len(df),
                'width': 1.5
            },
            {
                'label': 'Zones Displayed',
                'value': lambda df: len(selected_zones),
                'width': 1
            },
            {
                'label': 'Overall LMP (selected)',
                'value': (lambda df: f"{df['lmp_mean_c_per_kwh'].mean():.2f} ¢/kWh") if measure == 'mean' else (lambda df: f"{df['lmp_median_c_per_kwh'].median():.2f} ¢/kWh"),
                'width': 1.5
            }
        ]
        
        DataSummary.create_summary_metrics(data, metrics_config)
    
    def create_chart(self, data, measure: str):
        """Create PJM LMP chart for the selected measure (mean|median)."""
        if data.empty:
            st.warning("No data available to display.")
            return

        if measure == 'mean':
            y_col = 'lmp_mean_c_per_kwh'
            title = 'PJM Monthly Average (Mean) LMP by Zone'
            y_title = 'Mean LMP (¢/kWh)'
        else:
            y_col = 'lmp_median_c_per_kwh'
            title = 'PJM Monthly Median LMP by Zone'
            y_title = 'Median LMP (¢/kWh)'

        chart = ChartBuilder.create_line_chart(
            data=data,
            x_col="date",
            y_col=y_col,
            color_col="zone",
            title=title,
            x_title="Date",
            y_title=y_title
        )

        st.altair_chart(chart, use_container_width=True)
    
    def render(self):
        """Main render function for PJM module"""
        st.header("PJM LMP Analysis")
        st.write("Analyze PJM Locational Marginal Prices by zone over time")
        
        # Get data (monthly mean and median per zone)
        data = self.get_pjm_data()
        
        if data.empty:
            st.error("No PJM data available. Please check your database connection.")
            return
        
        # Create zone filters in main content area
        selected_zones = self.create_zone_filters(data)
        
        # Filter data based on selected zones
        if selected_zones:
            filtered_data = data[data['zone'].isin(selected_zones)]
        else:
            st.warning("Please select at least one zone to display.")
            filtered_data = data
        
        # Prebuild both datasets for charts to minimize switch lag
        mean_data = filtered_data[['date', 'zone', 'lmp_mean_c_per_kwh', 'records_used']].copy()
        median_data = filtered_data[['date', 'zone', 'lmp_median_c_per_kwh', 'records_used']].copy()

        # Show both charts in tabs (load both on first render for instant switching)
        tabs = st.tabs(["Average (Mean)", "Median"])

        with tabs[0]:
            self.create_data_summary(mean_data, selected_zones, measure='mean')
            self.create_chart(mean_data, measure='mean')

        with tabs[1]:
            self.create_data_summary(median_data, selected_zones, measure='median')
            self.create_chart(median_data, measure='median')
        
        # Additional PJM-specific functionality
        st.subheader("PJM Average LMP")
        if st.button("Get Overall PJM Average LMP"):
            try:
                avg_lmp_dollars = self.get_pjm_average_lmp()
                avg_lmp_cents = avg_lmp_dollars * 0.1
                st.success(f"Average LMP: ${avg_lmp_dollars:.2f}/MWh ({avg_lmp_cents:.2f} ¢/kWh)")
                
                col1, col2, col3 = st.columns(3)
                with col2:
                    st.metric(
                        label="Average LMP", 
                        value=f"{avg_lmp_cents:.2f} ¢/kWh",
                        help="Average Locational Marginal Price from PJM_daily table"
                    )
                    
            except Exception as e:
                st.error(f"Failed to get PJM Average LMP: {e}")
