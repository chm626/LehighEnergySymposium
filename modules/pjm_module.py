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
        """Get monthly averaged PJM data from database"""
        try:
            query = """
            SELECT 
                YEAR(date) as year,
                MONTH(date) as month,
                zone,
                AVG(average_lmp) as average_lmp
            FROM PJM_daily 
            GROUP BY YEAR(date), MONTH(date), zone
            ORDER BY year, month, zone
            """
            
            df = db_manager.execute_query(query)
            
            # Create date column from year and month, convert average_lmp to float
            df['date'] = pd.to_datetime(df[['year', 'month']].assign(day=1))
            df['average_lmp'] = df['average_lmp'].astype(float)
            
            # Convert from $/MWh to cents/kWh
            df['lmp_cents_per_kwh'] = df['average_lmp'] * 0.1
            
            return df
            
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
    
    def create_data_summary(self, data, selected_zones):
        """Create PJM-specific data summary"""
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
                'label': 'Zones Displayed',
                'value': lambda df: len(selected_zones),
                'width': 1
            },
            {
                'label': 'Overall Avg LMP',
                'value': lambda df: f"{df['lmp_cents_per_kwh'].mean():.2f} ¢/kWh",
                'width': 1.5
            }
        ]
        
        DataSummary.create_summary_metrics(data, metrics_config)
    
    def create_chart(self, data):
        """Create PJM LMP chart"""
        if data.empty:
            st.warning("No data available to display.")
            return
        
        chart = ChartBuilder.create_line_chart(
            data=data,
            x_col="date",
            y_col="lmp_cents_per_kwh",
            color_col="zone",
            title="PJM Monthly Average LMP by Zone",
            x_title="Date",
            y_title="Average LMP (¢/kWh)"
        )
        
        st.altair_chart(chart, use_container_width=True)
    
    def render(self):
        """Main render function for PJM module"""
        st.header("PJM LMP Analysis")
        st.write("Analyze PJM Locational Marginal Prices by zone over time")
        
        # Get data
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
        
        # Create data summary
        self.create_data_summary(filtered_data, selected_zones)
        
        # Create chart
        self.create_chart(filtered_data)
        
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
