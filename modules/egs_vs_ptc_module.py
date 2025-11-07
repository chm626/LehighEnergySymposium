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
        
        # Filter by EDC and date (2016 onwards)
        edc_data = raw_egs[
            (raw_egs['edc'] == edc) & 
            (raw_egs['date'] >= pd.Timestamp('2016-01-01'))
        ].copy()
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
        """Create aggregate chart showing percentage of offers above and below PTC"""
        if relative_data.empty:
            st.warning(f"No data available for {edc}")
            return
        
        # Group by date to calculate percentages
        monthly_totals = relative_data.groupby('date').size().reset_index(name='total_offers')
        monthly_categories = relative_data.groupby(['date', 'category']).size().reset_index(name='category_count')

        # Merge to calculate percentages
        monthly_percentages = pd.merge(monthly_categories, monthly_totals, on='date')
        monthly_percentages['percentage'] = (monthly_percentages['category_count'] / monthly_percentages['total_offers'] * 100).round(2)

        # Keep only "Below PTC" series for a single green line
        below_df = monthly_percentages[monthly_percentages['category'] == 'Below PTC'].copy()

        # Single-line percentage chart for Below PTC
        percentage_chart = alt.Chart(below_df).mark_line(point=False, strokeWidth=3, color='#2E8B57').encode(
            x=alt.X('date:T', title='Date'),
            y=alt.Y('percentage:Q', title='Offers Below PTC (%)'),
            tooltip=['date:T', 'percentage:Q', 'category_count:Q', 'total_offers:Q']
        ).properties(
            height=500,
            title=f"Percentage of EGS Offers Below PTC - {edc}" + (" (Conformed)" if conform_egs else "")
        ).interactive()

        st.altair_chart(percentage_chart, use_container_width=True)
        
        # Add explanation
        st.info("""
        **Chart Explanation:**
        - **Green Line**: Percentage of offers priced below the PTC benchmark (potential savings)
        """)

    def get_pjm_data_for_edc(self, edc):
        """Get PJM monthly data for a specific EDC from shared cache if available."""
        try:
            # Reuse shared data manager method used elsewhere
            if hasattr(shared_data_manager, 'get_pjm_data_for_module'):
                return shared_data_manager.get_pjm_data_for_module(edc=edc)
        except Exception:
            pass
        return pd.DataFrame()

    def create_price_over_time_tabs(self, ptc_data, egs_data, selected_edc, conform_egs):
        """Create mean/median price-over-time charts for PTC, EGS and PJM."""
        st.subheader("Price Over Time (Mean vs Median)")

        # Prepare PTC monthly series (mean/median are identical per month after collapse)
        ptc_series = pd.DataFrame()
        if not ptc_data.empty:
            ptc_series = ptc_data.groupby('date')['ptc_rate'].mean().reset_index()
            ptc_series['PTC_mean'] = ptc_series['ptc_rate']
            ptc_series['PTC_median'] = ptc_data.groupby('date')['ptc_rate'].median().values

        # Prepare EGS series (filter selected edc, compute mean/median)
        egs_series_mean = pd.DataFrame()
        egs_series_median = pd.DataFrame()
        if not egs_data.empty:
            egs_filtered = egs_data[egs_data['edc'] == selected_edc]
            if not egs_filtered.empty:
                egs_series_mean = egs_filtered.groupby('date')['rate'].mean().reset_index().rename(columns={'rate': 'EGS'})
                egs_series_median = egs_filtered.groupby('date')['rate'].median().reset_index().rename(columns={'rate': 'EGS'})

        # Prepare PJM series (optional)
        pjm_data = self.get_pjm_data_for_edc(selected_edc)
        pjm_series_mean = pd.DataFrame()
        pjm_series_median = pd.DataFrame()
        if not pjm_data.empty:
            pjm_series_mean = pjm_data.groupby('date')['lmp_cents_per_kwh'].mean().reset_index().rename(columns={'lmp_cents_per_kwh': 'PJM'})
            pjm_series_median = pjm_data.groupby('date')['lmp_cents_per_kwh'].median().reset_index().rename(columns={'lmp_cents_per_kwh': 'PJM'})

        # Build mean and median chart datasets in long form
        def build_long(df_list, labels):
            frames = []
            for df, label in zip(df_list, labels):
                if df is not None and not df.empty:
                    tmp = df.copy()
                    if label == 'PTC_mean' or label == 'PTC_median':
                        # PTC series has columns: date, PTC_mean/PTC_median
                        value_col = label
                        tmp = tmp[['date', value_col]].rename(columns={value_col: 'price'})
                        tmp['type'] = 'PTC'
                    else:
                        # Generic series has columns: date, <label> where label is 'EGS' or 'PJM'
                        tmp = tmp[['date', label]].rename(columns={label: 'price'})
                        tmp['type'] = label
                    frames.append(tmp)
            if frames:
                return pd.concat(frames, ignore_index=True)
            return pd.DataFrame()

        mean_long = build_long(
            [ptc_series[['date', 'PTC_mean']] if not ptc_series.empty else None,
             egs_series_mean.rename(columns={'EGS': 'EGS'}) if not egs_series_mean.empty else None,
             pjm_series_mean.rename(columns={'PJM': 'PJM'}) if not pjm_series_mean.empty else None],
            ['PTC_mean', 'EGS', 'PJM']
        )
        median_long = build_long(
            [ptc_series[['date', 'PTC_median']] if not ptc_series.empty else None,
             egs_series_median.rename(columns={'EGS': 'EGS'}) if not egs_series_median.empty else None,
             pjm_series_median.rename(columns={'PJM': 'PJM'}) if not pjm_series_median.empty else None],
            ['PTC_median', 'EGS', 'PJM']
        )

        tab_mean, tab_median = st.tabs(["Average (Mean)", "Median"])
        import altair as alt

        def render_chart(df, title_suffix):
            if df.empty:
                st.info(f"No {title_suffix.lower()} data available.")
                return
            min_price = df['price'].min()
            max_price = df['price'].max()
            y_min = max(0, min_price * 0.9)
            y_max = max_price * 1.1
            chart = alt.Chart(df).mark_line().encode(
                x=alt.X('date:T', title='Date'),
                y=alt.Y('price:Q', title='Price (¢/kWh)', scale=alt.Scale(domain=[y_min, y_max])),
                color=alt.Color('type:N', scale=alt.Scale(domain=['PTC', 'EGS', 'PJM'], range=['#FF6B6B', '#4ECDC4', '#45B7D1'])),
                tooltip=['date:T', 'type:N', alt.Tooltip('price:Q', format='.2f')]
            ).properties(
                height=500,
                title=f"PTC vs EGS{' vs PJM' if 'PJM' in df['type'].unique() else ''} ({title_suffix}) - {selected_edc}" + (" (Conformed)" if conform_egs else "")
            )
            st.altair_chart(chart, use_container_width=True)

        with tab_mean:
            render_chart(mean_long, 'Mean')
        with tab_median:
            render_chart(median_long, 'Median')
    
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
        # Chart type selector removed - only aggregate chart available
        return 'Aggregate'
    
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
    
    def preload_all_data_combinations(self):
        """Preload all data combinations for seamless checkbox switching"""
        # Get all raw data
        raw_egs = shared_data_manager.get_raw_egs_data()
        raw_ptc = shared_data_manager.get_raw_ptc_data()
        
        if raw_egs.empty or raw_ptc.empty:
            return None, None, None, None
        
        # Create monthly PTC rates for all EDCs - more efficient approach
        ptc_records = []
        for _, row in raw_ptc.iterrows():
            start_date = row['start_date']
            end_date = row['end_date']
            rate = row['rate']
            edc = row['edc']
            
            # Generate monthly dates between start and end
            current_date = start_date.replace(day=1)
            while current_date <= end_date:
                ptc_records.append({
                    'date': current_date,
                    'edc': edc,
                    'ptc_rate': rate
                })
                current_date = current_date + pd.DateOffset(months=1)
        
        ptc_df = pd.DataFrame(ptc_records)
        
        # Filter EGS data from 2016 onwards
        raw_egs_2016 = raw_egs[raw_egs['date'] >= pd.Timestamp('2016-01-01')]
        
        # Apply conforming logic for conformed data
        wattbuy_no_fees = (
            ((raw_egs_2016['enrollment_fee'].isna()) | (raw_egs_2016['enrollment_fee'] == 0)) &
            ((raw_egs_2016['monthly_charge'].isna()) | (raw_egs_2016['monthly_charge'] == 0)) &
            ((raw_egs_2016['early_term_fee_min'].isna()) | (raw_egs_2016['early_term_fee_min'] == 0))
        )
        
        ocap_no_fees = (raw_egs_2016['cancel_fee'].isna())
        
        conformed_egs = raw_egs_2016[
            (raw_egs_2016['term'] == 12) &
            (raw_egs_2016['rate_type'].str.lower().str.contains('fixed', na=False)) &
            (
                ((raw_egs_2016['source'] == 'WattBuy') & wattbuy_no_fees) |
                ((raw_egs_2016['source'] == 'OCAP') & ocap_no_fees)
            )
        ]
        
        # Instead of merging everything upfront, return the raw data and do targeted merges
        # This prevents the massive memory allocation issue
        return raw_egs_2016, conformed_egs, ptc_df, None
    
    def create_dual_axis_chart(self, raw_egs, conformed_egs, ptc_df, conform_egs_state):
        """Create dual-axis chart showing offer counts and percentages"""
        st.subheader("Average Offer Counts and Percentages by Utility")
        
        # Use appropriate dataset based on conform state
        if conform_egs_state:
            egs_data = conformed_egs
        else:
            egs_data = raw_egs
        
        if egs_data.empty or ptc_df.empty:
            st.warning("No data available for analysis")
            return
        
        # Merge EGS and PTC data - targeted merge to avoid memory issues
        merged_data = pd.merge(egs_data, ptc_df, on=['date', 'edc'], how='inner')
        
        if merged_data.empty:
            st.warning("No overlapping data between EGS offers and PTC rates")
            return
        
        # Calculate relative rates
        merged_data['relative_rate'] = merged_data['rate'] - merged_data['ptc_rate']
        
        # Group by EDC and calculate statistics
        edc_stats = merged_data.groupby('edc').agg({
            'relative_rate': [
                'count',  # total offers
                lambda x: (x >= 0).sum(),  # offers above PTC
                lambda x: (x < 0).sum()     # offers below PTC
            ]
        }).reset_index()
        
        # Flatten column names
        edc_stats.columns = ['edc', 'total_offers', 'offers_above_ptc', 'offers_below_ptc']
        
        # Calculate percentages
        edc_stats['pct_above'] = (edc_stats['offers_above_ptc'] / edc_stats['total_offers'] * 100).round(2)
        edc_stats['pct_below'] = (edc_stats['offers_below_ptc'] / edc_stats['total_offers'] * 100).round(2)
        
        # Prepare data for dual-axis chart with normalization
        chart_data = []
        for _, row in edc_stats.iterrows():
            chart_data.extend([
                {
                    'edc': row['edc'],
                    'category': 'Above PTC',
                    'count': row['offers_above_ptc'],  # Positive values
                    'percentage': row['pct_above']
                },
                {
                    'edc': row['edc'],
                    'category': 'Below PTC',
                    'count': -row['offers_below_ptc'],  # Negative values for normalization
                    'percentage': row['pct_below']
                }
            ])
        
        df_chart = pd.DataFrame(chart_data)
        
        # Create separate datasets for bars and lines to avoid color conflicts
        bars_data = df_chart.copy()
        lines_data = df_chart.copy()
        
        # Add color columns to distinguish bars from lines
        bars_data['chart_type'] = 'bars'
        lines_data['chart_type'] = 'lines'
        
        # Create bars chart with fixed colors
        bars = alt.Chart(bars_data).mark_bar().encode(
            x=alt.X('edc:N', title='Utility', axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('count:Q', title='Number of Offers', axis=alt.Axis(orient='left')),
            color=alt.condition(
                alt.datum.category == 'Above PTC',
                alt.value('#DC143C'),  # Red for above PTC
                alt.value('#2E8B57')   # Green for below PTC
            ),
            tooltip=['edc:N', 'category:N', 'count:Q', 'percentage:Q']
        )
        
        # Just show bars without percentage lines
        chart = bars.configure_axis(
            labelFontSize=10,
            labelFontWeight='normal'
        ).properties(
            height=500,
            title="Offer Counts by Utility" + (" (Conformed)" if conform_egs_state else "")
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)
        
        # Add explanation
        st.info("""
        **Chart Explanation:**
        - **Bars (Left Y-axis):** Show the number of offers above/below PTC for each utility
        - **Lines (Right Y-axis):** Show the percentage of offers above/below PTC for each utility
        - **Red:** Offers above PTC (higher rates) - bars extend upward from 0 line
        - **Green:** Offers below PTC (lower rates/savings) - bars extend downward from 0 line
        """)

    def create_summary_table(self, raw_egs, conformed_egs, ptc_df, conform_egs_state):
        """Create summary table showing offers above/below PTC by term length for all EDCs"""
        st.subheader("Electric Utility Offers Compared to PTC (All Terms)")
        
        # Create term filter checkboxes with session state
        st.write("**Filter by Term Length:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'egs_vs_ptc_term_12' not in st.session_state:
                st.session_state.egs_vs_ptc_term_12 = True
            show_12_month = st.checkbox("12 months", key="egs_vs_ptc_term_12")
        
        with col2:
            if 'egs_vs_ptc_term_less_12' not in st.session_state:
                st.session_state.egs_vs_ptc_term_less_12 = True
            show_less_12 = st.checkbox("Less than 12 months", key="egs_vs_ptc_term_less_12")
        
        with col3:
            if 'egs_vs_ptc_term_more_12' not in st.session_state:
                st.session_state.egs_vs_ptc_term_more_12 = True
            show_more_12 = st.checkbox("More than 12 months", key="egs_vs_ptc_term_more_12")
        
        # Use appropriate dataset based on conform state
        if conform_egs_state:
            egs_data = conformed_egs
        else:
            egs_data = raw_egs
        
        if egs_data.empty or ptc_df.empty:
            st.warning("No data available for term analysis")
            return
        
        # Merge EGS and PTC data - targeted merge to avoid memory issues
        merged_data = pd.merge(egs_data, ptc_df, on=['date', 'edc'], how='inner')
        
        if merged_data.empty:
            st.warning("No overlapping data between EGS offers and PTC rates")
            return
        
        # Calculate relative rates
        merged_data['relative_rate'] = merged_data['rate'] - merged_data['ptc_rate']
        
        # Categorize terms
        def categorize_term(term):
            if pd.isna(term):
                return "Unknown"
            elif term == 12:
                return "12"
            elif term < 12:
                return "< 12"
            else:
                return "> 12"
        
        merged_data['term_category'] = merged_data['term'].apply(categorize_term)
        
        # Group by EDC and term category
        summary_stats = merged_data.groupby(['edc', 'term_category']).agg({
            'relative_rate': ['count', lambda x: (x < 0).sum(), lambda x: (x >= 0).sum()]
        }).reset_index()
        
        # Flatten column names
        summary_stats.columns = ['edc', 'term_category', 'total_offers', 'offers_below_ptc', 'offers_above_ptc']
        
        # Calculate percentages
        summary_stats['pct_above'] = (summary_stats['offers_above_ptc'] / summary_stats['total_offers'] * 100).round(2)
        summary_stats['pct_below'] = (summary_stats['offers_below_ptc'] / summary_stats['total_offers'] * 100).round(2)
        
        # Filter based on checkboxes
        term_filters = []
        if show_12_month:
            term_filters.append("12")
        if show_less_12:
            term_filters.append("< 12")
        if show_more_12:
            term_filters.append("> 12")
        
        if not term_filters:
            st.warning("Please select at least one term length to display")
            return
        
        filtered_stats = summary_stats[summary_stats['term_category'].isin(term_filters)]
        
        if filtered_stats.empty:
            st.warning("No data available for selected term lengths")
            return
        
        # Create the table
        table_data = []
        for edc in sorted(filtered_stats['edc'].unique()):
            edc_data = filtered_stats[filtered_stats['edc'] == edc]
            
            for _, row in edc_data.iterrows():
                table_data.append({
                    'Utility Name': edc,
                    'Term (months)': row['term_category'],
                    'Offers Below PTC': f"{row['offers_below_ptc']:,}",
                    'Offers Above PTC': f"{row['offers_above_ptc']:,}",
                    'Total Offers': f"{row['total_offers']:,}",
                    '% Above': f"{row['pct_above']:.2f}%",
                    '% Below': f"{row['pct_below']:.2f}%"
                })
        
        # Display the table
        if table_data:
            df_table = pd.DataFrame(table_data)
            st.dataframe(df_table, use_container_width=True, hide_index=True)
            
            # Add note about conformed data
            if conform_egs_state:
                st.info("**Note:** Data shown reflects conformed EGS offers (12-month terms, fixed rates, no fees)")
            else:
                st.info("**Note:** Data includes all EGS offers regardless of term length, rate type, or fees")
        
        # Add summary statistics by term length
        self.create_summary_statistics(merged_data, conform_egs_state)
    
    def create_summary_statistics(self, merged_data, conform_egs_state):
        """Create summary statistics table showing averages by term length"""
        if merged_data.empty:
            return
        
        st.subheader("Summary Statistics by Term Length")
        
        # Calculate statistics by term category
        summary_stats = merged_data.groupby('term_category').agg({
            'relative_rate': ['count', 'mean', 'median', 'std'],
            'rate': ['mean', 'median'],
            'ptc_rate': ['mean', 'median']
        }).round(3)
        
        # Flatten column names
        summary_stats.columns = [
            'Total Offers', 'Avg Relative Rate', 'Median Relative Rate', 'Std Dev Relative Rate',
            'Avg EGS Rate', 'Median EGS Rate', 'Avg PTC Rate', 'Median PTC Rate'
        ]
        
        # Calculate percentage above/below PTC
        percentage_stats = merged_data.groupby('term_category').agg({
            'relative_rate': lambda x: (x >= 0).sum() / len(x) * 100
        }).round(2)
        percentage_stats.columns = ['% Above PTC']
        percentage_stats['% Below PTC'] = 100 - percentage_stats['% Above PTC']
        
        # Combine statistics
        final_stats = pd.concat([summary_stats, percentage_stats], axis=1)
        
        # Format the display
        display_stats = final_stats.copy()
        display_stats['Avg Relative Rate'] = display_stats['Avg Relative Rate'].apply(lambda x: f"{x:.3f} ¢/kWh")
        display_stats['Median Relative Rate'] = display_stats['Median Relative Rate'].apply(lambda x: f"{x:.3f} ¢/kWh")
        display_stats['Std Dev Relative Rate'] = display_stats['Std Dev Relative Rate'].apply(lambda x: f"{x:.3f} ¢/kWh")
        display_stats['Avg EGS Rate'] = display_stats['Avg EGS Rate'].apply(lambda x: f"{x:.3f} ¢/kWh")
        display_stats['Median EGS Rate'] = display_stats['Median EGS Rate'].apply(lambda x: f"{x:.3f} ¢/kWh")
        display_stats['Avg PTC Rate'] = display_stats['Avg PTC Rate'].apply(lambda x: f"{x:.3f} ¢/kWh")
        display_stats['Median PTC Rate'] = display_stats['Median PTC Rate'].apply(lambda x: f"{x:.3f} ¢/kWh")
        display_stats['% Above PTC'] = display_stats['% Above PTC'].apply(lambda x: f"{x:.1f}%")
        display_stats['% Below PTC'] = display_stats['% Below PTC'].apply(lambda x: f"{x:.1f}%")
        
        # Display the table
        st.dataframe(display_stats, use_container_width=True)
        
        # Add interpretation note
        st.info("""
        **Statistics Interpretation:**
        - **Relative Rate**: EGS rate minus PTC rate (positive = above PTC, negative = below PTC)
        - **Std Dev**: Standard deviation shows variability in relative rates
        - **% Above/Below PTC**: Percentage of offers above or below the PTC benchmark
        """)
    
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
        
        # Preload all data combinations for seamless switching
        raw_egs, conformed_egs, ptc_df, _ = self.preload_all_data_combinations()
        
        if raw_egs is None:
            st.error("Failed to load data")
            return
        
        # Preload individual EDC data for charts
        ptc_data, regular_egs_data, conformed_egs_data = self.preload_data_for_edc(selected_edc)
        
        if ptc_data.empty:
            st.warning(f"No PTC data available for {selected_edc}")
            return
        
        # Create controls
        conform_egs = self.create_conform_checkbox()
        
        # Switch between preloaded datasets based on checkbox state
        if conform_egs:
            egs_data = conformed_egs_data
        else:
            egs_data = regular_egs_data
        
        if egs_data.empty:
            st.warning(f"No EGS data available for {selected_edc}")
            return
        
        # Calculate relative rates for individual EDC charts
        relative_data = self.calculate_relative_rates(egs_data, ptc_data)
        
        if relative_data.empty:
            st.warning(f"No overlapping data between EGS offers and PTC rates for {selected_edc}")
            return
        
        # Create aggregate chart
        self.create_aggregate_chart(relative_data, selected_edc, conform_egs)
        
        # Create dual-axis chart using preloaded data
        self.create_dual_axis_chart(raw_egs, conformed_egs, ptc_df, conform_egs)
        
        # Create summary table using preloaded data
        self.create_summary_table(raw_egs, conformed_egs, ptc_df, conform_egs)

        # Create price-over-time mean/median tabs
        self.create_price_over_time_tabs(ptc_data, egs_data, selected_edc, conform_egs)
        
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
