import streamlit as st
import pandas as pd
from core.database import db_manager
from core.chart_utils import ChartBuilder, DataSummary

class FeesModule:
    """EGS signup fees analysis by EDC"""
    
    def __init__(self):
        self.module_name = "EGS Signup Fees Analysis"
        self.description = "Analyze EGS signup fees by EDC and supplier"
        
        # EDC mapping between views and PJM zones (same as future module)
        self.edc_mapping = {
            'West Penn Power': 'APS',
            'Duquesne Light': 'DUQ', 
            'Met Ed': 'METED',
            'PECO Energy': 'PECO',
            'Penelec': 'PENELEC',
            'PPL Electric Utilities': 'PPL'
        }
    
    @st.cache_data
    def get_fees_data(_self, edc=None):
        """Get fees data from WattBuy view with time series data"""
        try:
            # Query for v_wattbuy_simple with all fee types and date
            query = """
            SELECT 
                YEAR(date) as year,
                MONTH(date) as month,
                edc,
                egs,
                enrollment_fee,
                monthly_charge,
                early_term_fee_min
            FROM v_wattbuy_simple 
            WHERE edc IS NOT NULL AND egs IS NOT NULL
            """
            
            # Get data from WattBuy view
            df = db_manager.execute_query(query)
            
            # Create date column from year and month
            df['date'] = pd.to_datetime(df[['year', 'month']].assign(day=1))
            
            # Convert fee columns to float
            df['enrollment_fee'] = pd.to_numeric(df['enrollment_fee'], errors='coerce')
            df['monthly_charge'] = pd.to_numeric(df['monthly_charge'], errors='coerce')
            df['early_term_fee_min'] = pd.to_numeric(df['early_term_fee_min'], errors='coerce')
            
            # Remove negative values and extreme outliers (fees > $500 are likely errors)
            # Only filter rows where ALL fee columns are invalid, not just one
            df = df[
                ~(
                    ((df['enrollment_fee'] < 0) | (df['enrollment_fee'] > 500)) &
                    ((df['monthly_charge'] < 0) | (df['monthly_charge'] > 500)) &
                    ((df['early_term_fee_min'] < 0) | (df['early_term_fee_min'] > 500))
                )
            ]
            
            # Filter by EDC if specified
            if edc:
                df = df[df['edc'] == edc]
            
            # Remove EGS suppliers that have never had any fees of any type
            # Keep only EGS suppliers that have at least one non-null, non-zero fee
            df = df[
                (df['enrollment_fee'].notna() & (df['enrollment_fee'] > 0)) |
                (df['monthly_charge'].notna() & (df['monthly_charge'] > 0)) |
                (df['early_term_fee_min'].notna() & (df['early_term_fee_min'] > 0))
            ]
            
            return df
            
        except Exception as e:
            st.error(f"Failed to load fees data: {e}")
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
                if st.button(edc, key=f"fees_edc_{edc}"):
                    selected_edc = edc
        
        return selected_edc
    
    def create_fee_type_selector(self):
        """Create fee type selection interface"""
        st.subheader("Select Fee Type to Analyze")
        
        fee_types = {
            'Signup Fee': 'enrollment_fee',
            'Monthly Fee': 'monthly_charge', 
            'Termination Fee': 'early_term_fee_min'
        }
        
        selected_fee_type = st.selectbox(
            "Choose the fee type to analyze:",
            options=list(fee_types.keys()),
            key="fee_type_selector"
        )
        
        return fee_types[selected_fee_type], selected_fee_type
    
    def calculate_fees_statistics(self, data, selected_edc, fee_column):
        """Calculate average and median fees for selected EDC and fee type"""
        if data.empty or not selected_edc:
            return {}
        
        edc_data = data[data['edc'] == selected_edc]
        
        if edc_data.empty:
            return {}
        
        # Filter out null values for the specific fee column
        fee_data = edc_data[edc_data[fee_column].notna()]
        
        if fee_data.empty:
            return {}
        
        # Calculate overall statistics for the EDC
        overall_stats = {
            'average_fee': fee_data[fee_column].mean(),
            'median_fee': fee_data[fee_column].median(),
            'min_fee': fee_data[fee_column].min(),
            'max_fee': fee_data[fee_column].max(),
            'total_records': len(fee_data)
        }
        
        # Calculate statistics by EGS supplier
        egs_stats = fee_data.groupby('egs')[fee_column].agg([
            'mean', 'median', 'min', 'max', 'count'
        ]).round(2)
        egs_stats.columns = ['Average Fee', 'Median Fee', 'Min Fee', 'Max Fee', 'Count']
        
        return {
            'overall': overall_stats,
            'by_egs': egs_stats
        }
    
    def create_fees_summary(self, stats, selected_edc, fee_type_name):
        """Create fees summary metrics"""
        if not stats or 'overall' not in stats:
            return
        
        overall_stats = stats['overall']
        
        st.subheader(f"{fee_type_name} Summary for {selected_edc}")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                label="Average Fee",
                value=f"${overall_stats['average_fee']:.2f}"
            )
        
        with col2:
            st.metric(
                label="Median Fee", 
                value=f"${overall_stats['median_fee']:.2f}"
            )
        
        with col3:
            st.metric(
                label="Min Fee",
                value=f"${overall_stats['min_fee']:.2f}"
            )
        
        with col4:
            st.metric(
                label="Max Fee",
                value=f"${overall_stats['max_fee']:.2f}"
            )
        
        with col5:
            st.metric(
                label="Total Records",
                value=f"{overall_stats['total_records']:,}"
            )
    
    def create_fees_table(self, stats, selected_edc, fee_type_name):
        """Create detailed fees table by EGS supplier"""
        if not stats or 'by_egs' not in stats:
            return
        
        egs_stats = stats['by_egs']
        
        st.subheader(f"{fee_type_name} by EGS Supplier - {selected_edc}")
        
        # Format the dataframe for display
        display_df = egs_stats.copy()
        display_df['Average Fee'] = display_df['Average Fee'].apply(lambda x: f"${x:.2f}")
        display_df['Median Fee'] = display_df['Median Fee'].apply(lambda x: f"${x:.2f}")
        display_df['Min Fee'] = display_df['Min Fee'].apply(lambda x: f"${x:.2f}")
        display_df['Max Fee'] = display_df['Max Fee'].apply(lambda x: f"${x:.2f}")
        
        st.dataframe(display_df, width='stretch')
    
    def create_fees_chart(self, data, selected_edc, fee_column, fee_type_name):
        """Create time series chart showing fees over time for each EGS in selected EDC"""
        if data.empty or not selected_edc:
            st.warning("No fees data available to display.")
            return
        
        edc_data = data[data['edc'] == selected_edc]
        
        if edc_data.empty:
            st.warning("No data available for the selected EDC.")
            return
        
        # Filter out null values for the specific fee column
        fee_data = edc_data[edc_data[fee_column].notna()]
        
        if fee_data.empty:
            st.warning(f"No {fee_type_name.lower()} data available for the selected EDC.")
            return
        
        # Calculate average fees by EGS and date for the chart
        chart_data = fee_data.groupby(['date', 'egs'])[fee_column].mean().reset_index()
        
        # Create time series chart
        import altair as alt
        
        # Create color palette for EGS suppliers
        unique_egs = sorted(chart_data['egs'].unique())
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE']
        
        chart = alt.Chart(chart_data).mark_line(point=True, strokeWidth=2).encode(
            x=alt.X('date:T', title='Date'),
            y=alt.Y(f'{fee_column}:Q', title=f'{fee_type_name} ($)'),
            color=alt.Color('egs:N', 
                          scale=alt.Scale(domain=unique_egs, range=colors[:len(unique_egs)]),
                          sort=unique_egs)
        ).properties(
            title=f"{fee_type_name} Over Time by EGS Supplier - {selected_edc}",
            width='container',
            height=500
        )
        
        st.altair_chart(chart)
    
    def render(self):
        """Main render function for fees module"""
        st.header("EGS Fees Analysis")
        st.write("Analyze signup, monthly, and termination fees by EDC and EGS supplier")
        
        # Create fee type selector
        fee_column, fee_type_name = self.create_fee_type_selector()
        
        # Get fees data
        fees_data = self.get_fees_data()
        
        if fees_data.empty:
            st.error("No fees data available. Please check your database connection.")
            return
        
        # Create EDC selector
        selected_edc = self.create_edc_selector(fees_data)
        
        if not selected_edc:
            st.info("Please select an EDC to begin analysis.")
            return
        
        # Create time series chart first
        st.subheader(f"{fee_type_name} Over Time - {selected_edc}")
        self.create_fees_chart(fees_data, selected_edc, fee_column, fee_type_name)
        
        # Debug information below the chart
        st.subheader("Data Debug Information")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_records = len(fees_data)
            st.metric("Total Records", total_records)
        
        with col2:
            edc_records = len(fees_data[fees_data['edc'] == selected_edc])
            st.metric(f"Records for {selected_edc}", edc_records)
        
        with col3:
            fee_records = len(fees_data[fees_data[fee_column].notna()])
            st.metric(f"Non-null {fee_type_name}", fee_records)
        
        # Show sample data
        if not fees_data.empty:
            sample_data = fees_data[fees_data['edc'] == selected_edc][['date', 'egs', fee_column]].head(10)
            st.write("Sample data:")
            st.dataframe(sample_data, width='stretch')
        
        # Calculate statistics for selected EDC
        stats = self.calculate_fees_statistics(fees_data, selected_edc, fee_column)
        
        # Create fees summary
        self.create_fees_summary(stats, selected_edc, fee_type_name)
        
        # Create detailed table
        self.create_fees_table(stats, selected_edc, fee_type_name)
        
        # Show data source information
        st.subheader("Data Sources")
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("**Fees Data Source:**")
            st.write("- WattBuy Simple View Only")
            st.write(f"- Column: {fee_column}")
            st.write("- Fee Types: Signup, Monthly, Termination")
        
        with col2:
            st.info("**Analysis Period:**")
            st.write("- All available data")
            st.write("- Filtered for valid fees ($0-$500)")
            st.write("- Data cleaned for outliers")
