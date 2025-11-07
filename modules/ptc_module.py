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
    
    def preload_egs_data_for_edc(self, edc):
        """Preload both regular and conformed EGS data for seamless switching"""
        if edc is None:
            return None, None
        
        # Get both datasets
        regular_egs = shared_data_manager.get_egs_data_for_ptc_module(edc=edc, conform=False)
        conformed_egs = shared_data_manager.get_egs_data_for_ptc_module(edc=edc, conform=True)
        
        return regular_egs, conformed_egs
    
    def get_pjm_data_for_edc(self, edc):
        """Get monthly averaged PJM data for a specific EDC (uses shared cached data)"""
        return shared_data_manager.get_pjm_data_for_module(edc=edc)
    
    def get_all_edcs_average_data(self):
        """Get averaged data across all EDCs for the overview chart (mean and median)."""
        try:
            # Get all data from shared cache
            all_ptc_data = shared_data_manager.get_raw_ptc_data()
            all_egs_data = shared_data_manager.get_raw_egs_data()
            all_pjm_data = shared_data_manager.get_raw_pjm_data()
            
            chart_data_list_mean = []
            chart_data_list_median = []
            
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
                            'type': 'PTC',
                            'records_used': 1  # one PTC period record contributes to this month
                        })
                        # Use pandas date arithmetic to avoid day-of-month issues
                        current_date = current_date + pd.DateOffset(months=1)
                
                if ptc_monthly:
                    ptc_df = pd.DataFrame(ptc_monthly)
                    grouped = ptc_df.groupby('date')
                    ptc_mean = grouped['price'].mean().reset_index().rename(columns={'price': 'price_mean'})
                    ptc_median = grouped['price'].median().reset_index().rename(columns={'price': 'price_median'})
                    ptc_counts = grouped['records_used'].sum().reset_index().rename(columns={'records_used': 'records_used'})
                    ptc_mean['type'] = 'PTC'
                    ptc_median['type'] = 'PTC'
                    ptc_mean = ptc_mean.merge(ptc_counts, on='date', how='left')
                    ptc_median = ptc_median.merge(ptc_counts, on='date', how='left')
                    chart_data_list_mean.append(ptc_mean)
                    chart_data_list_median.append(ptc_median)
            
            # Process EGS data - average across all EDCs
            if not all_egs_data.empty:
                grouped = all_egs_data.groupby('date')
                egs_mean = grouped['rate'].mean().reset_index().rename(columns={'rate': 'price_mean'})
                egs_median = grouped['rate'].median().reset_index().rename(columns={'rate': 'price_median'})
                egs_counts = grouped['rate'].size().reset_index().rename(columns={'rate': 'records_used'})
                egs_mean['type'] = 'EGS'
                egs_median['type'] = 'EGS'
                egs_mean = egs_mean.merge(egs_counts, on='date', how='left')
                egs_median = egs_median.merge(egs_counts, on='date', how='left')
                chart_data_list_mean.append(egs_mean[['date', 'price_mean', 'type', 'records_used']])
                chart_data_list_median.append(egs_median[['date', 'price_median', 'type', 'records_used']])
            
            # Process PJM data - average across all zones
            if not all_pjm_data.empty:
                grouped = all_pjm_data.groupby('date')
                pjm_mean = grouped['lmp_cents_per_kwh'].mean().reset_index().rename(columns={'lmp_cents_per_kwh': 'price_mean'})
                pjm_median = grouped['lmp_cents_per_kwh'].median().reset_index().rename(columns={'lmp_cents_per_kwh': 'price_median'})
                pjm_counts = grouped.size().reset_index().rename(columns={0: 'records_used'})
                pjm_mean['type'] = 'PJM'
                pjm_median['type'] = 'PJM'
                pjm_mean = pjm_mean.merge(pjm_counts, on='date', how='left')
                pjm_median = pjm_median.merge(pjm_counts, on='date', how='left')
                chart_data_list_mean.append(pjm_mean[['date', 'price_mean', 'type', 'records_used']])
                chart_data_list_median.append(pjm_median[['date', 'price_median', 'type', 'records_used']])
            
            mean_df = pd.concat(chart_data_list_mean, ignore_index=True) if chart_data_list_mean else pd.DataFrame()
            median_df = pd.concat(chart_data_list_median, ignore_index=True) if chart_data_list_median else pd.DataFrame()
            return mean_df, median_df
                
        except Exception as e:
            st.error(f"Failed to create all-EDCs average data: {e}")
            return pd.DataFrame()
    
    def create_edc_selector(self, data):
        """Create EDC selection interface with session state"""
        if data.empty:
            return None
        
        available_edcs = sorted(data['edc'].unique())
        
        # Initialize session state for EDC selection
        if 'selected_edc' not in st.session_state:
            st.session_state.selected_edc = None
        
        st.subheader("Select EDC to Analyze")
        
        # Create columns for EDC selection
        cols = st.columns(3)
        
        for i, edc in enumerate(available_edcs):
            col_idx = i % 3
            with cols[col_idx]:
                if st.button(edc, key=f"ptc_edc_{edc}"):
                    st.session_state.selected_edc = edc
        
        return st.session_state.selected_edc
    
    def create_chart_options(self):
        """Create chart options with conform checkbox integrated"""
        st.subheader("Chart Options")
        
        show_all_edcs = st.checkbox(
            "Show All EDCs Average",
            value=False,
            help="Display averaged data across all EDCs instead of individual EDC analysis"
        )
        
        return show_all_edcs
    
    def create_conform_checkbox(self):
        """Create conform checkbox right above the chart with session state"""
        # Initialize session state for conform checkbox
        if 'conform_egs' not in st.session_state:
            st.session_state.conform_egs = False
        
        conform_egs = st.checkbox(
            "Conform EGS Data",
            value=st.session_state.conform_egs,
            help="Filter EGS data to match PTC characteristics: 12-month terms, no cancel fees, fixed rates"
        )
        
        # Update session state
        st.session_state.conform_egs = conform_egs
        return conform_egs
    
    def create_all_edcs_chart(self):
        """Create charts showing averages (mean and median) across all EDCs."""
        mean_df, median_df = self.get_all_edcs_average_data()
        
        if mean_df.empty and median_df.empty:
            st.warning("No data available for all-EDCs average chart.")
            return
        
        import altair as alt
        
        tab_mean, tab_median = st.tabs(["Average (Mean)", "Median"])
        
        with tab_mean:
            chart_data = mean_df.rename(columns={'price_mean': 'price'})
            if chart_data.empty:
                st.info("No mean data available.")
            else:
                min_price = chart_data['price'].min()
                max_price = chart_data['price'].max()
                y_min = max(0, min_price * 0.9)
                y_max = max_price * 1.1
                base = alt.Chart(chart_data).encode(
                    x=alt.X('date:T', title='Date'),
                    y=alt.Y('price:Q', title='Price (¢/kWh)', scale=alt.Scale(domain=[y_min, y_max])),
                    color=alt.Color('type:N', 
                                    scale=alt.Scale(domain=['PTC', 'EGS', 'PJM'],
                                                    range=['#FF6B6B', '#4ECDC4', '#45B7D1']),
                                    sort=['PTC', 'EGS', 'PJM']),
                    strokeWidth=alt.condition(alt.datum.type == 'PTC', alt.value(2), alt.value(1))
                )
                chart = base.mark_line().properties(
                    title="PTC vs EGS vs PJM (Mean) - All EDCs",
                    width='container',
                    height=500
                )
                st.altair_chart(chart, use_container_width=True)
        
        with tab_median:
            chart_data = median_df.rename(columns={'price_median': 'price'})
            if chart_data.empty:
                st.info("No median data available.")
            else:
                min_price = chart_data['price'].min()
                max_price = chart_data['price'].max()
                y_min = max(0, min_price * 0.9)
                y_max = max_price * 1.1
                base = alt.Chart(chart_data).encode(
                    x=alt.X('date:T', title='Date'),
                    y=alt.Y('price:Q', title='Price (¢/kWh)', scale=alt.Scale(domain=[y_min, y_max])),
                    color=alt.Color('type:N', 
                                    scale=alt.Scale(domain=['PTC', 'EGS', 'PJM'],
                                                    range=['#FF6B6B', '#4ECDC4', '#45B7D1']),
                                    sort=['PTC', 'EGS', 'PJM']),
                    strokeWidth=alt.condition(alt.datum.type == 'PTC', alt.value(2), alt.value(1))
                )
                chart = base.mark_line().properties(
                    title="PTC vs EGS vs PJM (Median) - All EDCs",
                    width='container',
                    height=500
                )
                st.altair_chart(chart, use_container_width=True)
    
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
                total_offers = int(egs_filtered['count_offers'].sum()) if 'count_offers' in egs_filtered.columns else len(egs_filtered)
                stats['egs'] = {
                    'min_price': egs_filtered['avg_rate'].min(),
                    'max_price': egs_filtered['avg_rate'].max(),
                    'median_price': egs_filtered['avg_rate'].median(),
                    'average_price': egs_filtered['avg_rate'].mean(),
                    'total_records': total_offers
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
        """Create charts comparing PTC, EGS, and PJM using mean and median for the EGS/PJM aggregates."""
        if ptc_data.empty and egs_data.empty and pjm_data.empty:
            st.warning("No data available to display.")
            return
        
        chart_data_list_mean = []
        chart_data_list_median = []
        
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
                    # For PTC (single value per month), mean == median after monthly collapse
                    ptc_mean = ptc_chart_data.groupby('date')['price'].mean().reset_index().rename(columns={'price':'price_mean'})
                    ptc_median = ptc_chart_data.groupby('date')['price'].median().reset_index().rename(columns={'price':'price_median'})
                    for df, lst in [(ptc_mean, chart_data_list_mean), (ptc_median, chart_data_list_median)]:
                        df['type'] = 'PTC'
                        df['line_width'] = 2
                        df['sort_order'] = 0
                        lst.append(df)
        
        # Prepare EGS data for chart
        if not egs_data.empty:
            egs_filtered = egs_data[egs_data['edc'] == selected_edc]
            if not egs_filtered.empty:
                # EGS dataset may be pre-aggregated to avg_rate; compute mean and median across offers
                egs_mean = egs_filtered.groupby('date')['avg_rate'].mean().reset_index().rename(columns={'avg_rate':'price_mean'})
                egs_median = egs_filtered.groupby('date')['avg_rate'].median().reset_index().rename(columns={'avg_rate':'price_median'})
                for df, lst in [(egs_mean, chart_data_list_mean), (egs_median, chart_data_list_median)]:
                    df['type'] = egs_label
                    df['line_width'] = 1
                    df['sort_order'] = 1
                    lst.append(df)
        
        # Prepare PJM data for chart
        if not pjm_data.empty:
            # If pjm_data has multiple records per month, compute mean and median; otherwise both identical
            pjm_mean = pjm_data.groupby('date')['lmp_cents_per_kwh'].mean().reset_index().rename(columns={'lmp_cents_per_kwh':'price_mean'})
            pjm_median = pjm_data.groupby('date')['lmp_cents_per_kwh'].median().reset_index().rename(columns={'lmp_cents_per_kwh':'price_median'})
            for df, lst in [(pjm_mean, chart_data_list_mean), (pjm_median, chart_data_list_median)]:
                df['type'] = 'PJM'
                df['line_width'] = 1
                df['sort_order'] = 2
                lst.append(df)
        
        if not chart_data_list_mean and not chart_data_list_median:
            st.warning("No data available for the selected EDC.")
            return
        
        import altair as alt
        
        tab_mean, tab_median = st.tabs(["Average (Mean)", "Median"])
        
        def render_chart(df, title_suffix):
            if df.empty:
                st.info(f"No {title_suffix.lower()} data available.")
                return
            df = df.sort_values(['sort_order', 'date'])
            min_price = df.iloc[:, df.columns.get_loc('price_' + title_suffix.lower())].min()
            max_price = df.iloc[:, df.columns.get_loc('price_' + title_suffix.lower())].max()
            y_min = max(0, min_price * 0.9)
            y_max = max_price * 1.1
            chart_df = df.rename(columns={f'price_{title_suffix.lower()}': 'price'})
            base = alt.Chart(chart_df).encode(
                x=alt.X('date:T', title='Date'),
                y=alt.Y('price:Q', title='Price (¢/kWh)', scale=alt.Scale(domain=[y_min, y_max])),
                color=alt.Color('type:N', 
                                scale=alt.Scale(domain=['PTC', egs_label, 'PJM'],
                                                range=['#FF6B6B', '#4ECDC4', '#45B7D1']),
                                sort=['PTC', egs_label, 'PJM']),
                strokeWidth=alt.condition(alt.datum.type == 'PTC', alt.value(2), alt.value(1))
            )
            chart = base.mark_line().properties(
                title=f"PTC vs EGS vs PJM ({title_suffix}) - {selected_edc}",
                width='container',
                height=500
            )
            st.altair_chart(chart, use_container_width=True)
        
        with tab_mean:
            chart_data_mean = pd.concat(chart_data_list_mean, ignore_index=True) if chart_data_list_mean else pd.DataFrame()
            render_chart(chart_data_mean, 'Mean')
        with tab_median:
            chart_data_median = pd.concat(chart_data_list_median, ignore_index=True) if chart_data_list_median else pd.DataFrame()
            render_chart(chart_data_median, 'Median')
    
    def render(self):
        """Main render function for PTC module"""
        st.header("PTC Analysis")
        st.write("Compare PTC rates to EGS retail prices and PJM wholesale prices by EDC")
        
        # Create chart options
        show_all_edcs = self.create_chart_options()
        
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
        
        # Preload both EGS datasets for seamless switching
        regular_egs_data, conformed_egs_data = self.preload_egs_data_for_edc(selected_edc)
        pjm_data = self.get_pjm_data_for_edc(selected_edc)
        
        # Calculate statistics using regular EGS data
        stats = self.calculate_statistics(ptc_data, regular_egs_data, pjm_data, selected_edc)
        
        # Create data summary
        self.create_data_summary(stats, selected_edc)
        
        # Create conform checkbox right above the chart
        conform_egs = self.create_conform_checkbox()
        
        # Switch between preloaded datasets based on checkbox state
        if conform_egs:
            egs_data = conformed_egs_data
            egs_label = "Conformed EGS"
        else:
            egs_data = regular_egs_data
            egs_label = "EGS Average"
        
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
