import streamlit as st
import pandas as pd
from core.database import db_manager
from core.chart_utils import ChartBuilder, DataSummary

class FutureModule:
    """EGS pricing analysis compared to PJM wholesale prices"""
    
    def __init__(self):
        self.module_name = "EGS Pricing Analysis"
        self.description = "Analyze EGS retail prices vs PJM wholesale prices by EDC"
        
        # EDC mapping between views and PJM zones
        self.edc_mapping = {
            'West Penn Power': 'APS',
            'Duquesne Light': 'DUQ', 
            'Met Ed': 'METED',
            'PECO Energy': 'PECO',
            'Penelec': 'PENELEC',
            'PPL Electric Utilities': 'PPL'
        }
    
    @st.cache_data
    def get_egs_data(_self, edc=None):
        """Get monthly averaged EGS data from both views"""
        try:
            # Query for v_wattbuy_simple
            wattbuy_query = """
            SELECT 
                YEAR(date) as year,
                MONTH(date) as month,
                edc,
                egs,
                AVG(rate) as avg_rate
            FROM v_wattbuy_simple 
            WHERE edc IS NOT NULL AND egs IS NOT NULL AND rate IS NOT NULL
            AND YEAR(date) BETWEEN 2017 AND 2022
            GROUP BY YEAR(date), MONTH(date), edc, egs
            ORDER BY year, month, edc, egs
            """
            
            # Query for v_ocaplans_simple  
            ocaplans_query = """
            SELECT 
                YEAR(date) as year,
                MONTH(date) as month,
                edc,
                egs,
                AVG(rate) as avg_rate
            FROM v_ocaplans_simple 
            WHERE edc IS NOT NULL AND egs IS NOT NULL AND rate IS NOT NULL
            AND YEAR(date) BETWEEN 2017 AND 2022
            GROUP BY YEAR(date), MONTH(date), edc, egs
            ORDER BY year, month, edc, egs
            """
            
            # Get data from both views
            wattbuy_df = db_manager.execute_query(wattbuy_query)
            ocaplans_df = db_manager.execute_query(ocaplans_query)
            
            # Add source column to distinguish data sources
            wattbuy_df['source'] = 'WattBuy'
            ocaplans_df['source'] = 'OCAP'
            
            # Combine both datasets
            combined_df = pd.concat([wattbuy_df, ocaplans_df], ignore_index=True)
            
            # Create date column from year and month
            combined_df['date'] = pd.to_datetime(combined_df[['year', 'month']].assign(day=1))
            combined_df['avg_rate'] = combined_df['avg_rate'].astype(float)
            
            # Remove negative values and outliers (rates > 50 cents/kWh are likely errors)
            combined_df = combined_df[
                (combined_df['avg_rate'] > 0) & 
                (combined_df['avg_rate'] <= 50)
            ]
            
            # Filter by EDC if specified
            if edc:
                combined_df = combined_df[combined_df['edc'] == edc]
            
            return combined_df
            
        except Exception as e:
            st.error(f"Failed to load EGS data: {e}")
            return pd.DataFrame()
    
    @st.cache_data
    def get_pjm_data_for_edc(_self, edc):
        """Get monthly averaged PJM data for a specific EDC"""
        try:
            # Get PJM zone code for the EDC
            pjm_zone = _self.edc_mapping.get(edc)
            if not pjm_zone:
                return pd.DataFrame()
            
            query = f"""
            SELECT 
                YEAR(date) as year,
                MONTH(date) as month,
                zone,
                AVG(average_lmp) as average_lmp
            FROM PJM_daily 
            WHERE zone = '{pjm_zone}'
            AND YEAR(date) BETWEEN 2017 AND 2022
            GROUP BY YEAR(date), MONTH(date), zone
            ORDER BY year, month, zone
            """
            
            df = db_manager.execute_query(query)
            
            if df.empty:
                return pd.DataFrame()
            
            # Create date column from year and month
            df['date'] = pd.to_datetime(df[['year', 'month']].assign(day=1))
            df['average_lmp'] = df['average_lmp'].astype(float)
            
            # Convert from $/MWh to cents/kWh
            df['lmp_cents_per_kwh'] = df['average_lmp'] * 0.1
            
            # Remove negative values and outliers (LMP > 50 cents/kWh are likely errors)
            df = df[
                (df['lmp_cents_per_kwh'] > 0) & 
                (df['lmp_cents_per_kwh'] <= 50)
            ]
            
            return df
            
        except Exception as e:
            st.error(f"Failed to load PJM data for {edc}: {e}")
            return pd.DataFrame()
    
    def create_edc_selector(self, data):
        """Create EDC selection interface"""
        if data.empty:
            return None
        
        available_edcs = sorted(data['edc'].unique())
        
        st.subheader("Select EDC to Analyze")
        
        # Create columns for EDC selection
        cols = st.columns(3)
        
        selected_edc = None
        for i, edc in enumerate(available_edcs):
            col_idx = i % 3
            with cols[col_idx]:
                if st.button(edc, key=f"edc_{edc}"):
                    selected_edc = edc
        
        return selected_edc
    
    
    def calculate_statistics(self, data, selected_edc, selected_egs):
        """Calculate min, max, median, average prices for selected EDC and EGS suppliers"""
        if data.empty or not selected_edc or not selected_egs:
            return {}
        
        filtered_data = data[
            (data['edc'] == selected_edc) & 
            (data['egs'].isin(selected_egs))
        ]
        
        if filtered_data.empty:
            return {}
        
        stats = {
            'min_price': filtered_data['avg_rate'].min(),
            'max_price': filtered_data['avg_rate'].max(),
            'median_price': filtered_data['avg_rate'].median(),
            'average_price': filtered_data['avg_rate'].mean(),
            'total_records': len(filtered_data)
        }
        
        return stats
    
    def create_data_summary(self, stats, selected_edc, selected_egs):
        """Create data summary metrics"""
        if not stats:
            return
        
        st.subheader(f"Price Statistics for {selected_edc}")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                label="Min Price",
                value=f"{stats['min_price']:.2f} ¢/kWh"
            )
        
        with col2:
            st.metric(
                label="Max Price", 
                value=f"{stats['max_price']:.2f} ¢/kWh"
            )
        
        with col3:
            st.metric(
                label="Median Price",
                value=f"{stats['median_price']:.2f} ¢/kWh"
            )
        
        with col4:
            st.metric(
                label="Average Price",
                value=f"{stats['average_price']:.2f} ¢/kWh"
            )
        
        with col5:
            st.metric(
                label="Total Records",
                value=f"{stats['total_records']:,}"
            )
    
    def create_comparison_chart(self, egs_data, pjm_data, selected_edc, selected_egs):
        """Create chart comparing EGS prices to PJM LMP"""
        if egs_data.empty:
            st.warning("No EGS data available to display.")
            return
        
        # Filter EGS data
        filtered_egs = egs_data[
            (egs_data['edc'] == selected_edc) & 
            (egs_data['egs'].isin(selected_egs))
        ]
        
        if filtered_egs.empty:
            st.warning("No data available for selected EGS suppliers.")
            return
        
        # Prepare EGS data for chart
        egs_chart_data = filtered_egs.groupby(['date', 'egs'])['avg_rate'].mean().reset_index()
        egs_chart_data['type'] = 'EGS Retail'
        egs_chart_data['price'] = egs_chart_data['avg_rate']
        egs_chart_data['line_width'] = 1
        egs_chart_data['sort_order'] = 1
        
        # Prepare PJM data for chart
        if not pjm_data.empty:
            pjm_chart_data = pjm_data[['date', 'lmp_cents_per_kwh']].copy()
            pjm_chart_data['egs'] = 'PJM Wholesale'
            pjm_chart_data['type'] = 'PJM Wholesale'
            pjm_chart_data['price'] = pjm_chart_data['lmp_cents_per_kwh']
            pjm_chart_data['line_width'] = 3  # Thicker line for PJM
            pjm_chart_data['sort_order'] = 0  # Sort order for legend (0 = top)
            
            # Combine data
            chart_data = pd.concat([
                egs_chart_data[['date', 'egs', 'type', 'price', 'line_width', 'sort_order']],
                pjm_chart_data[['date', 'egs', 'type', 'price', 'line_width', 'sort_order']]
            ], ignore_index=True)
        else:
            chart_data = egs_chart_data[['date', 'egs', 'type', 'price', 'line_width', 'sort_order']]
        
        # Sort data to ensure PJM appears first in legend
        chart_data = chart_data.sort_values(['sort_order', 'egs'])
        
        # Create chart with custom styling
        import altair as alt
        
        # Calculate reasonable y-axis bounds
        min_price = chart_data['price'].min()
        max_price = chart_data['price'].max()
        # Add some padding (10% on each side) but ensure minimum is at least 0
        y_min = max(0, min_price * 0.9)
        y_max = max_price * 1.1
        
        # Create base chart
        base = alt.Chart(chart_data).encode(
            x=alt.X('date:T', title='Date'),
            y=alt.Y('price:Q', title='Price (¢/kWh)', 
                   scale=alt.Scale(domain=[y_min, y_max])),
            color=alt.Color('egs:N', 
                          scale=alt.Scale(
                              domain=['PJM Wholesale'] + [egs for egs in chart_data['egs'].unique() if egs != 'PJM Wholesale'],
                              range=['#FF6B6B'] + ['#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE']
                          ),
                          sort=['PJM Wholesale'] + sorted([egs for egs in chart_data['egs'].unique() if egs != 'PJM Wholesale'])
            ),
            strokeWidth=alt.condition(
                alt.datum.egs == 'PJM Wholesale',
                alt.value(3),  # Thicker line for PJM
                alt.value(1)   # Normal thickness for EGS
            )
        )
        
        # Create line chart
        chart = base.mark_line().add_selection(
            alt.selection_interval()
        ).properties(
            title=f"EGS vs PJM Pricing Comparison - {selected_edc}",
            width='container',
            height=500
        )
        
        st.altair_chart(chart)
    
    def render(self):
        """Main render function for future module"""
        st.header("EGS Pricing Analysis")
        st.write("Compare EGS retail prices to PJM wholesale prices by EDC")
        
        # Get EGS data
        egs_data = self.get_egs_data()
        
        if egs_data.empty:
            st.error("No EGS data available. Please check your database connection.")
            return
        
        # Create EDC selector
        selected_edc = self.create_edc_selector(egs_data)
        
        if not selected_edc:
            st.info("Please select an EDC to begin analysis.")
            return
        
        # Get all EGS suppliers for the selected EDC
        edc_data = egs_data[egs_data['edc'] == selected_edc]
        selected_egs = sorted(edc_data['egs'].unique())
        
        if not selected_egs:
            st.warning("No EGS suppliers found for the selected EDC.")
            return
        
        # Calculate statistics
        stats = self.calculate_statistics(egs_data, selected_edc, selected_egs)
        
        # Create data summary
        self.create_data_summary(stats, selected_edc, selected_egs)
        
        # Get PJM data for comparison
        pjm_data = self.get_pjm_data_for_edc(selected_edc)
        
        # Create comparison chart
        self.create_comparison_chart(egs_data, pjm_data, selected_edc, selected_egs)
        
        # Show data source information
        st.subheader("Data Sources")
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("**EGS Data Sources:**")
            st.write("- WattBuy Simple View")
            st.write("- OCAP Plans Simple View")
        
        with col2:
            st.info("**PJM Data Source:**")
            st.write("- PJM Daily Table")
            st.write(f"- Zone: {self.edc_mapping.get(selected_edc, 'N/A')}")
