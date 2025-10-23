# EGS vs PTC Comparison Module
import streamlit as st
import pandas as pd
import altair as alt
from core.shared_data import shared_data_manager
from core.database import db_manager

class EGSvsPTCModule:
    """Module for comparing EGS offers to PTC rates"""
    
    def __init__(self):
        self.edc_mapping = shared_data_manager.edc_mapping
        self.edc_normalization = shared_data_manager.edc_normalization
    
    @st.cache_data
    def get_ptc_data_for_edc(_self, edc):
        """Get PTC data for a specific EDC"""
        raw_ptc = shared_data_manager.get_raw_ptc_data()
        if raw_ptc.empty:
            return pd.DataFrame()
        
        edc_data = raw_ptc[raw_ptc['edc'] == edc].copy()
        if edc_data.empty:
            return pd.DataFrame()
        
        # Create monthly PTC rates by expanding date ranges
        monthly_ptc = []
        for _, row in edc_data.iterrows():
            start_date = row['start_date']
            end_date = row['end_date']
            rate = row['rate']
            
            # Generate monthly dates between start and end
            current_date = start_date.replace(day=1)
            while current_date <= end_date:
                monthly_ptc.append({
                    'date': current_date,
                    'edc': edc,
                    'ptc_rate': rate
                })
                current_date = current_date + pd.DateOffset(months=1)
        
        return pd.DataFrame(monthly_ptc)
    
    @st.cache_data
    def get_egs_offers_for_edc(_self, edc, conform=False):
        """Get individual EGS offers for a specific EDC"""
        raw_egs = shared_data_manager.get_raw_egs_data()
        if raw_egs.empty:
            return pd.DataFrame()
        
        edc_data = raw_egs[raw_egs['edc'] == edc].copy()
        if edc_data.empty:
            return pd.DataFrame()
        
        if conform:
            # Apply conforming logic
            wattbuy_no_fees = (
                ((edc_data['enrollment_fee'].isna()) | (edc_data['enrollment_fee'] == 0)) &
                ((edc_data['monthly_charge'].isna()) | (edc_data['monthly_charge'] == 0)) &
                ((edc_data['early_term_fee_min'].isna()) | (edc_data['early_term_fee_min'] == 0))
            )
            
            ocap_no_fees = (edc_data['cancel_fee'].isna())
            
            conformed_data = edc_data[
                (edc_data['term'] == 12) &
                (edc_data['rate_type'].str.lower().str.contains('fixed', na=False)) &
                (
                    ((edc_data['source'] == 'WattBuy') & wattbuy_no_fees) |
                    ((edc_data['source'] == 'OCAP') & ocap_no_fees)
                )
            ]
            
            return conformed_data[['date', 'edc', 'egs', 'rate', 'source']]
        else:
            return edc_data[['date', 'edc', 'egs', 'rate', 'source']]
    
    def calculate_relative_rates(self, egs_data, ptc_data):
        """Calculate EGS rates relative to PTC rates"""
        if egs_data.empty or ptc_data.empty:
            return pd.DataFrame()
        
        # Merge EGS and PTC data on date
        merged_data = pd.merge(egs_data, ptc_data, on=['date', 'edc'], how='inner')
        
        # Calculate relative rate (EGS rate - PTC rate)
        merged_data['relative_rate'] = merged_data['rate'] - merged_data['ptc_rate']
        
        # Categorize offers
        merged_data['category'] = merged_data['relative_rate'].apply(
            lambda x: 'Below PTC' if x < 0 else 'Above PTC'
        )
        
        return merged_data[['date', 'edc', 'egs', 'rate', 'ptc_rate', 'relative_rate', 'category', 'source']]
    
    def create_aggregate_chart(self, relative_data, edc, conform_egs):
        """Create aggregate chart showing offers above and below PTC"""
        if relative_data.empty:
            st.warning(f"No data available for {edc}")
            return
        
        # Group by date and category to get counts
        aggregate_data = relative_data.groupby(['date', 'category']).agg({
            'relative_rate': ['count', 'mean', 'min', 'max']
        }).reset_index()
        
        # Flatten column names
        aggregate_data.columns = ['date', 'category', 'count', 'avg_relative', 'min_relative', 'max_relative']
        
        # Create the chart
        base = alt.Chart(aggregate_data).encode(
            x=alt.X('date:T', title='Date'),
            y=alt.Y('avg_relative:Q', title='Average Rate Relative to PTC (¢/kWh)'),
            color=alt.Color('category:N', 
                           scale=alt.Scale(domain=['Below PTC', 'Above PTC'], 
                                         range=['#2E8B57', '#DC143C']),
                           title='Offer Category')
        )
        
        # Create lines for each category
        lines = base.mark_line(strokeWidth=3).encode(
            opacity=alt.condition(alt.datum.category == 'Below PTC', alt.value(0.8), alt.value(0.8))
        )
        
        # Add points for data visibility
        points = base.mark_circle(size=60).encode(
            opacity=alt.condition(alt.datum.category == 'Below PTC', alt.value(0.6), alt.value(0.6))
        )
        
        chart = (lines + points).resolve_scale(color='independent')
        
        # Add zero line
        zero_line = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(
            color='black', strokeDash=[5, 5], strokeWidth=2
        ).encode(y='y:Q')
        
        final_chart = (chart + zero_line).resolve_scale(y='independent')
        
        # Configure chart
        final_chart = final_chart.properties(
            height=500,
            title=f"EGS Offers Relative to PTC - {edc}" + (" (Conformed)" if conform_egs else "")
        ).interactive()
        
        st.altair_chart(final_chart, use_container_width=True)
    
    def create_individual_offers_chart(self, relative_data, edc, conform_egs):
        """Create chart showing individual EGS offers"""
        if relative_data.empty:
            st.warning(f"No individual offers data available for {edc}")
            return
        
        # Create the chart with points for individual offers
        points = alt.Chart(relative_data).mark_circle(size=40).encode(
            x=alt.X('date:T', title='Date'),
            y=alt.Y('relative_rate:Q', title='Rate Relative to PTC (¢/kWh)'),
            color=alt.Color('category:N', 
                           scale=alt.Scale(domain=['Below PTC', 'Above PTC'], 
                                         range=['#2E8B57', '#DC143C']),
                           title='Offer Category'),
            tooltip=['egs:N', 'rate:Q', 'ptc_rate:Q', 'relative_rate:Q', 'source:N'],
            opacity=alt.value(0.7)
        )
        
        # Add zero line
        zero_line = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(
            color='black', strokeDash=[5, 5], strokeWidth=2
        ).encode(y='y:Q')
        
        # Combine charts
        final_chart = (points + zero_line).resolve_scale(y='independent')
        
        # Configure chart
        final_chart = final_chart.properties(
            height=500,
            title=f"Individual EGS Offers Relative to PTC - {edc}" + (" (Conformed)" if conform_egs else "")
        ).interactive()
        
        st.altair_chart(final_chart, use_container_width=True)
    
    def create_edc_selector(self, data):
        """Create EDC selection interface with session state"""
        if data.empty:
            return None
        
        available_edcs = sorted(data['edc'].unique())
        
        if 'egs_vs_ptc_selected_edc' not in st.session_state:
            st.session_state.egs_vs_ptc_selected_edc = None
        
        st.subheader("Select EDC to Analyze")
        cols = st.columns(3)
        
        for i, edc in enumerate(available_edcs):
            col_idx = i % 3
            with cols[col_idx]:
                if st.button(edc, key=f"egs_vs_ptc_edc_{edc}"):
                    st.session_state.egs_vs_ptc_selected_edc = edc
        
        return st.session_state.egs_vs_ptc_selected_edc
    
    def create_conform_checkbox(self):
        """Create conform checkbox with session state"""
        if 'egs_vs_ptc_conform_egs' not in st.session_state:
            st.session_state.egs_vs_ptc_conform_egs = False
        
        conform_egs = st.checkbox(
            "Conform EGS Data",
            value=st.session_state.egs_vs_ptc_conform_egs,
            help="Filter EGS data to match PTC characteristics: 12-month terms, no fees, fixed rates"
        )
        
        st.session_state.egs_vs_ptc_conform_egs = conform_egs
        return conform_egs
    
    def create_chart_type_selector(self):
        """Create chart type selector with session state"""
        if 'egs_vs_ptc_chart_type' not in st.session_state:
            st.session_state.egs_vs_ptc_chart_type = 'Aggregate'
        
        chart_type = st.selectbox(
            "Chart Type",
            ['Aggregate', 'Individual Offers'],
            index=0 if st.session_state.egs_vs_ptc_chart_type == 'Aggregate' else 1,
            help="Aggregate shows average offers by category, Individual shows all offers"
        )
        
        st.session_state.egs_vs_ptc_chart_type = chart_type
        return chart_type
    
    def preload_data_for_edc(self, edc):
        """Preload both regular and conformed EGS data for seamless switching"""
        if edc is None:
            return None, None, None
        
        # Get PTC data
        ptc_data = self.get_ptc_data_for_edc(edc)
        
        # Get both EGS datasets
        regular_egs = self.get_egs_offers_for_edc(edc, conform=False)
        conformed_egs = self.get_egs_offers_for_edc(edc, conform=True)
        
        return ptc_data, regular_egs, conformed_egs
    
    def create_data_summary(self, relative_data, edc, conform_egs):
        """Create summary statistics"""
        if relative_data.empty:
            return
        
        st.subheader(f"Data Summary - {edc}" + (" (Conformed)" if conform_egs else ""))
        
        # Calculate summary statistics
        below_ptc = relative_data[relative_data['category'] == 'Below PTC']
        above_ptc = relative_data[relative_data['category'] == 'Above PTC']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Offers", len(relative_data))
        
        with col2:
            st.metric("Below PTC", len(below_ptc), 
                     f"{len(below_ptc)/len(relative_data)*100:.1f}%" if len(relative_data) > 0 else "0%")
        
        with col3:
            st.metric("Above PTC", len(above_ptc),
                     f"{len(above_ptc)/len(relative_data)*100:.1f}%" if len(relative_data) > 0 else "0%")
        
        with col4:
            avg_relative = relative_data['relative_rate'].mean()
            st.metric("Avg Relative Rate", f"{avg_relative:.2f} ¢/kWh")
        
        # Show detailed statistics
        if not relative_data.empty:
            st.subheader("Detailed Statistics")
            
            stats_col1, stats_col2 = st.columns(2)
            
            with stats_col1:
                st.write("**Below PTC Offers:**")
                if not below_ptc.empty:
                    st.write(f"- Count: {len(below_ptc)}")
                    st.write(f"- Average: {below_ptc['relative_rate'].mean():.2f} ¢/kWh")
                    st.write(f"- Range: {below_ptc['relative_rate'].min():.2f} to {below_ptc['relative_rate'].max():.2f} ¢/kWh")
                else:
                    st.write("- No offers below PTC")
            
            with stats_col2:
                st.write("**Above PTC Offers:**")
                if not above_ptc.empty:
                    st.write(f"- Count: {len(above_ptc)}")
                    st.write(f"- Average: {above_ptc['relative_rate'].mean():.2f} ¢/kWh")
                    st.write(f"- Range: {above_ptc['relative_rate'].min():.2f} to {above_ptc['relative_rate'].max():.2f} ¢/kWh")
                else:
                    st.write("- No offers above PTC")
    
    def render(self):
        """Render the EGS vs PTC comparison module"""
        st.title("EGS vs PTC Comparison")
        st.markdown("Compare individual EGS offers to PTC rates to see which offers are above or below the PTC benchmark.")
        
        # Get all PTC data for EDC selection
        all_ptc_data = shared_data_manager.get_raw_ptc_data()
        
        if all_ptc_data.empty:
            st.error("No PTC data available")
            return
        
        # Create EDC selector
        selected_edc = self.create_edc_selector(all_ptc_data)
        
        if not selected_edc:
            st.info("Please select an EDC to begin analysis.")
            return
        
        # Preload all data for the selected EDC
        ptc_data, regular_egs_data, conformed_egs_data = self.preload_data_for_edc(selected_edc)
        
        if ptc_data.empty:
            st.warning(f"No PTC data available for {selected_edc}")
            return
        
        # Create controls
        col1, col2 = st.columns(2)
        
        with col1:
            conform_egs = self.create_conform_checkbox()
        
        with col2:
            chart_type = self.create_chart_type_selector()
        
        # Switch between preloaded datasets based on checkbox state
        if conform_egs:
            egs_data = conformed_egs_data
        else:
            egs_data = regular_egs_data
        
        if egs_data.empty:
            st.warning(f"No EGS data available for {selected_edc}")
            return
        
        # Calculate relative rates
        relative_data = self.calculate_relative_rates(egs_data, ptc_data)
        
        if relative_data.empty:
            st.warning(f"No overlapping data between EGS offers and PTC rates for {selected_edc}")
            return
        
        # Create data summary
        self.create_data_summary(relative_data, selected_edc, conform_egs)
        
        # Create charts based on selected type
        if chart_type == 'Aggregate':
            self.create_aggregate_chart(relative_data, selected_edc, conform_egs)
        else:
            self.create_individual_offers_chart(relative_data, selected_edc, conform_egs)
        
        # Show data source information
        st.subheader("Data Sources")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**PTC Data:**")
            st.write("- Source: v_ptc_agg table")
            st.write("- Date Range: 2016 onwards")
            st.write("- Rate: Price to Compare")
        
        with col2:
            st.write("**EGS Data:**")
            st.write("- Sources: v_wattbuy_simple, v_ocaplans_simple")
            st.write("- Date Range: 2010 onwards")
            st.write("- Rate: Individual offer rates")
            if conform_egs:
                st.write("- **Conformed:** 12-month terms, fixed rates, no fees")
