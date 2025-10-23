import streamlit as st
import pandas as pd
from core.database import db_manager
from core.chart_utils import ChartBuilder, DataSummary
from core.shared_data import shared_data_manager

class PTCModule:
    """PTC (Price to Compare) analysis compared to EGS and PJM data"""
    
    def __init__(self):
        self.module_name = "PTC Analysis"
        self.description = "Analyze PTC rates vs EGS retail prices and PJM wholesale prices by EDC"
        
        # Use shared EDC mapping and normalization
        self.edc_mapping = shared_data_manager.edc_mapping
        self.edc_normalization = shared_data_manager.edc_normalization
    
    def get_ptc_data(self, edc=None):
        """Get PTC data for specific EDC (uses shared cached data)"""
        all_data = shared_data_manager.get_raw_ptc_data()
        if edc and not all_data.empty:
            return all_data[all_data['edc'] == edc]
        return all_data
    
    
    def get_egs_data_averaged(self, edc=None):
        """Get monthly averaged EGS data for specific EDC (uses shared cached data)"""
        return shared_data_manager.get_egs_data_for_ptc_module(edc=edc, conform=False)
    
    def get_conformed_egs_data(self, edc=None):
        """Get EGS data conformed to PTC-like characteristics (uses shared cached data)"""
        return shared_data_manager.get_egs_data_for_ptc_module(edc=edc, conform=True)
    
    
    def get_pjm_data_for_edc(self, edc):
        """Get monthly averaged PJM data for a specific EDC (uses shared cached data)"""
        return shared_data_manager.get_pjm_data_for_module(edc=edc)
    
    def get_all_edcs_average_data(self):
        """Get averaged data across all EDCs for the overview chart"""
        try:
            # Get all data from shared cache
            all_ptc_data = shared_data_manager.get_raw_ptc_data()
            all_egs_data = shared_data_manager.get_raw_egs_data()
            all_pjm_data = shared_data_manager.get_raw_pjm_data()
            
            chart_data_list = []
            
            # Process PTC data - create monthly averages across all EDCs
            if not all_ptc_data.empty:
                # Create monthly data points for PTC periods
                ptc_monthly = []
                for _, row in all_ptc_data.iterrows():
                    current_date = row['start_date']
                    end_date = row['end_date']
                    while current_date <= end_date:
                        ptc_monthly.append({
                            'date': current_date.replace(day=1),
                            'price': row['rate'],
                            'type': 'PTC Average'
                        })
                        # Use pandas date arithmetic to avoid day-of-month issues
                        current_date = current_date + pd.DateOffset(months=1)
                
                if ptc_monthly:
                    ptc_df = pd.DataFrame(ptc_monthly)
                    ptc_average = ptc_df.groupby('date')['price'].mean().reset_index()
                    ptc_average['type'] = 'PTC Average'
                    chart_data_list.append(ptc_average)
            
            # Process EGS data - average across all EDCs
            if not all_egs_data.empty:
                egs_average = all_egs_data.groupby('date')['rate'].mean().reset_index()
                egs_average['price'] = egs_average['rate']
                egs_average['type'] = 'EGS Average'
                chart_data_list.append(egs_average[['date', 'price', 'type']])
            
            # Process PJM data - average across all zones
            if not all_pjm_data.empty:
                pjm_average = all_pjm_data.groupby('date')['lmp_cents_per_kwh'].mean().reset_index()
                pjm_average['price'] = pjm_average['lmp_cents_per_kwh']
                pjm_average['type'] = 'PJM Average'
                chart_data_list.append(pjm_average[['date', 'price', 'type']])
            
            if chart_data_list:
                return pd.concat(chart_data_list, ignore_index=True)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            st.error(f"Failed to create all-EDCs average data: {e}")
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
                if st.button(edc, key=f"ptc_edc_{edc}"):
                    selected_edc = edc
        
        return selected_edc
    
    def create_conform_button(self):
        """Create conform EGS data button"""
        st.subheader("EGS Data Options")
        col1, col2 = st.columns(2)
        
        with col1:
            conform_egs = st.button("Conform EGS Data", 
                                  help="Filter EGS data to match PTC characteristics: 12-month terms, no cancel fees, fixed rates")
        
        with col2:
            show_all_edcs = st.button("Show All EDCs Average", 
                                    help="Display averaged data across all EDCs")
        
        return conform_egs, show_all_edcs
    
    def create_all_edcs_chart(self):
        """Create chart showing averages across all EDCs"""
        chart_data = self.get_all_edcs_average_data()
        
        if chart_data.empty:
            st.warning("No data available for all-EDCs average chart.")
            return
        
        # Create chart with custom styling
        import altair as alt
        
        # Calculate reasonable y-axis bounds
        min_price = chart_data['price'].min()
        max_price = chart_data['price'].max()
        y_min = max(0, min_price * 0.9)
        y_max = max_price * 1.1
        
        # Create base chart
        base = alt.Chart(chart_data).encode(
            x=alt.X('date:T', title='Date'),
            y=alt.Y('price:Q', title='Price (¢/kWh)', 
                   scale=alt.Scale(domain=[y_min, y_max])),
            color=alt.Color('type:N', 
                          scale=alt.Scale(
                              domain=['PTC Average', 'EGS Average', 'PJM Average'],
                              range=['#FF6B6B', '#4ECDC4', '#45B7D1']
                          ),
                          sort=['PTC Average', 'EGS Average', 'PJM Average']
            ),
            strokeWidth=alt.condition(
                alt.datum.type == 'PTC Average',
                alt.value(2),  # Thicker line for PTC
                alt.value(1)   # Normal thickness for others
            )
        )
        
        # Create line chart
        chart = base.mark_line().add_selection(
            alt.selection_interval()
        ).properties(
            title="PTC vs EGS vs PJM Pricing Comparison - All EDCs Average",
            width='container',
            height=500
        )
        
        st.altair_chart(chart)
    
    def calculate_statistics(self, ptc_data, egs_data, pjm_data, selected_edc):
        """Calculate statistics for PTC, EGS, and PJM data"""
        if not selected_edc:
            return {}
        
        stats = {}
        
        # PTC statistics
        if not ptc_data.empty:
            ptc_filtered = ptc_data[ptc_data['edc'] == selected_edc]
            if not ptc_filtered.empty:
                stats['ptc'] = {
                    'min_price': ptc_filtered['rate'].min(),
                    'max_price': ptc_filtered['rate'].max(),
                    'median_price': ptc_filtered['rate'].median(),
                    'average_price': ptc_filtered['rate'].mean(),
                    'total_records': len(ptc_filtered)
                }
        
        # EGS statistics
        if not egs_data.empty:
            egs_filtered = egs_data[egs_data['edc'] == selected_edc]
            if not egs_filtered.empty:
                stats['egs'] = {
                    'min_price': egs_filtered['avg_rate'].min(),
                    'max_price': egs_filtered['avg_rate'].max(),
                    'median_price': egs_filtered['avg_rate'].median(),
                    'average_price': egs_filtered['avg_rate'].mean(),
                    'total_records': len(egs_filtered)
                }
        
        # PJM statistics
        if not pjm_data.empty:
            stats['pjm'] = {
                'min_price': pjm_data['lmp_cents_per_kwh'].min(),
                'max_price': pjm_data['lmp_cents_per_kwh'].max(),
                'median_price': pjm_data['lmp_cents_per_kwh'].median(),
                'average_price': pjm_data['lmp_cents_per_kwh'].mean(),
                'total_records': len(pjm_data)
            }
        
        return stats
    
    def create_data_summary(self, stats, selected_edc):
        """Create data summary metrics"""
        if not stats:
            return
        
        st.subheader(f"Price Statistics for {selected_edc}")
        
        # Create tabs for each data source
        tab1, tab2, tab3 = st.tabs(["PTC", "EGS Average", "PJM Average"])
        
        with tab1:
            if 'ptc' in stats:
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric(
                        label="Min Price",
                        value=f"{stats['ptc']['min_price']:.2f} ¢/kWh"
                    )
                
                with col2:
                    st.metric(
                        label="Max Price", 
                        value=f"{stats['ptc']['max_price']:.2f} ¢/kWh"
                    )
                
                with col3:
                    st.metric(
                        label="Median Price",
                        value=f"{stats['ptc']['median_price']:.2f} ¢/kWh"
                    )
                
                with col4:
                    st.metric(
                        label="Average Price",
                        value=f"{stats['ptc']['average_price']:.2f} ¢/kWh"
                    )
                
                with col5:
                    st.metric(
                        label="Total Records",
                        value=f"{stats['ptc']['total_records']:,}"
                    )
            else:
                st.info("No PTC data available for this EDC.")
        
        with tab2:
            if 'egs' in stats:
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric(
                        label="Min Price",
                        value=f"{stats['egs']['min_price']:.2f} ¢/kWh"
                    )
                
                with col2:
                    st.metric(
                        label="Max Price", 
                        value=f"{stats['egs']['max_price']:.2f} ¢/kWh"
                    )
                
                with col3:
                    st.metric(
                        label="Median Price",
                        value=f"{stats['egs']['median_price']:.2f} ¢/kWh"
                    )
                
                with col4:
                    st.metric(
                        label="Average Price",
                        value=f"{stats['egs']['average_price']:.2f} ¢/kWh"
                    )
                
                with col5:
                    st.metric(
                        label="Total Records",
                        value=f"{stats['egs']['total_records']:,}"
                    )
            else:
                st.info("No EGS data available for this EDC.")
        
        with tab3:
            if 'pjm' in stats:
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric(
                        label="Min Price",
                        value=f"{stats['pjm']['min_price']:.2f} ¢/kWh"
                    )
                
                with col2:
                    st.metric(
                        label="Max Price", 
                        value=f"{stats['pjm']['max_price']:.2f} ¢/kWh"
                    )
                
                with col3:
                    st.metric(
                        label="Median Price",
                        value=f"{stats['pjm']['median_price']:.2f} ¢/kWh"
                    )
                
                with col4:
                    st.metric(
                        label="Average Price",
                        value=f"{stats['pjm']['average_price']:.2f} ¢/kWh"
                    )
                
                with col5:
                    st.metric(
                        label="Total Records",
                        value=f"{stats['pjm']['total_records']:,}"
                    )
            else:
                st.info("No PJM data available for this EDC.")
    
    def create_comparison_chart(self, ptc_data, egs_data, pjm_data, selected_edc, egs_label="EGS Average"):
        """Create chart comparing PTC, EGS average, and PJM average"""
        if ptc_data.empty and egs_data.empty and pjm_data.empty:
            st.warning("No data available to display.")
            return
        
        chart_data_list = []
        
        # Prepare PTC data for chart
        if not ptc_data.empty:
            ptc_filtered = ptc_data[ptc_data['edc'] == selected_edc]
            if not ptc_filtered.empty:
                # For PTC data, we need to create monthly averages from the date ranges
                ptc_monthly = []
                for _, row in ptc_filtered.iterrows():
                    # Create monthly data points for the duration of each PTC period
                    current_date = row['start_date']
                    end_date = row['end_date']
                    while current_date <= end_date:
                        ptc_monthly.append({
                            'date': current_date.replace(day=1),  # First day of month
                            'price': row['rate'],
                            'type': 'PTC',
                            'line_width': 2,
                            'sort_order': 0
                        })
                        # Use pandas date arithmetic to avoid day-of-month issues
                        current_date = current_date + pd.DateOffset(months=1)
                
                if ptc_monthly:
                    ptc_chart_data = pd.DataFrame(ptc_monthly)
                    # Average by month to avoid duplicate points
                    ptc_chart_data = ptc_chart_data.groupby('date')['price'].mean().reset_index()
                    ptc_chart_data['type'] = 'PTC'
                    ptc_chart_data['line_width'] = 2
                    ptc_chart_data['sort_order'] = 0
                    chart_data_list.append(ptc_chart_data)
        
        # Prepare EGS data for chart
        if not egs_data.empty:
            egs_filtered = egs_data[egs_data['edc'] == selected_edc]
            if not egs_filtered.empty:
                egs_chart_data = egs_filtered.groupby('date')['avg_rate'].mean().reset_index()
                egs_chart_data['type'] = egs_label
                egs_chart_data['price'] = egs_chart_data['avg_rate']
                egs_chart_data['line_width'] = 1
                egs_chart_data['sort_order'] = 1
                chart_data_list.append(egs_chart_data[['date', 'price', 'type', 'line_width', 'sort_order']])
        
        # Prepare PJM data for chart
        if not pjm_data.empty:
            pjm_chart_data = pjm_data[['date', 'lmp_cents_per_kwh']].copy()
            pjm_chart_data['type'] = 'PJM Average'
            pjm_chart_data['price'] = pjm_chart_data['lmp_cents_per_kwh']
            pjm_chart_data['line_width'] = 1
            pjm_chart_data['sort_order'] = 2
            chart_data_list.append(pjm_chart_data[['date', 'price', 'type', 'line_width', 'sort_order']])
        
        if not chart_data_list:
            st.warning("No data available for the selected EDC.")
            return
        
        # Combine all data
        chart_data = pd.concat(chart_data_list, ignore_index=True)
        
        # Sort data to ensure proper legend order
        chart_data = chart_data.sort_values(['sort_order', 'date'])
        
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
            color=alt.Color('type:N', 
                          scale=alt.Scale(
                              domain=['PTC', egs_label, 'PJM Average'],
                              range=['#FF6B6B', '#4ECDC4', '#45B7D1']
                          ),
                          sort=['PTC', egs_label, 'PJM Average']
            ),
            strokeWidth=alt.condition(
                alt.datum.type == 'PTC',
                alt.value(2),  # Thicker line for PTC
                alt.value(1)   # Normal thickness for others
            )
        )
        
        # Create line chart
        chart = base.mark_line().add_selection(
            alt.selection_interval()
        ).properties(
            title=f"PTC vs EGS vs PJM Pricing Comparison - {selected_edc}",
            width='container',
            height=500
        )
        
        st.altair_chart(chart)
    
    def render(self):
        """Main render function for PTC module"""
        st.header("PTC Analysis")
        st.write("Compare PTC rates to EGS retail prices and PJM wholesale prices by EDC")
        
        # Create conform button and all-EDCs option
        conform_egs, show_all_edcs = self.create_conform_button()
        
        # Show all-EDCs average chart if requested
        if show_all_edcs:
            st.subheader("All EDCs Average Comparison")
            self.create_all_edcs_chart()
            return
        
        # Get PTC data
        ptc_data = self.get_ptc_data()
        
        if ptc_data.empty:
            st.error("No PTC data available. Please check your database connection.")
            return
        
        # Create EDC selector
        selected_edc = self.create_edc_selector(ptc_data)
        
        if not selected_edc:
            st.info("Please select an EDC to begin analysis.")
            return
        
        # Get EGS and PJM data for comparison
        if conform_egs:
            egs_data = self.get_conformed_egs_data(selected_edc)
            egs_label = "Conformed EGS"
        else:
            egs_data = self.get_egs_data_averaged(selected_edc)
            egs_label = "EGS Average"
        
        pjm_data = self.get_pjm_data_for_edc(selected_edc)
        
        # Calculate statistics
        stats = self.calculate_statistics(ptc_data, egs_data, pjm_data, selected_edc)
        
        # Create data summary
        self.create_data_summary(stats, selected_edc)
        
        # Create comparison chart
        self.create_comparison_chart(ptc_data, egs_data, pjm_data, selected_edc, egs_label)
        
        # Show data source information
        st.subheader("Data Sources")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("**PTC Data Source:**")
            st.write("- v_ptc_agg Table")
        
        with col2:
            st.info("**EGS Data Sources:**")
            st.write("- WattBuy Simple View")
            st.write("- OCAP Plans Simple View")
            if conform_egs:
                st.write("- **Filtered for:** 12-month terms, no cancel fees, fixed rates")
        
        with col3:
            st.info("**PJM Data Source:**")
            st.write("- PJM Daily Table")
            st.write(f"- Zone: {self.edc_mapping.get(selected_edc, 'N/A')}")
