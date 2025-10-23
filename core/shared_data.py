# Shared data cache manager for all modules
import streamlit as st
import pandas as pd
from core.database import db_manager

class SharedDataManager:
    """Centralized data caching system for all modules"""
    
    def __init__(self):
        # EDC mapping between views and PJM zones (shared across all modules)
        self.edc_mapping = {
            'West Penn Power': 'APS',
            'Duquesne Light': 'DUQ', 
            'Met Ed': 'METED',
            'Met-Ed': 'METED',  # Normalized
            'PECO Energy': 'PECO',
            'Penelec': 'PENELEC',
            'PPL Electric Utilities': 'PPL',
            'Pike County Light and Power': 'PPL',
            'Pike County Light': 'PPL'  # Normalized
        }
        
        # EDC name normalization - combine duplicate EDC names
        self.edc_normalization = {
            'Met-Ed': 'Met Ed',
            'Met Ed': 'Met Ed',
            'Pike County Light': 'Pike County Light and Power',
            'Pike County Light and Power': 'Pike County Light and Power',
        }
    
    def normalize_edc_names(self, df, edc_column='edc'):
        """Normalize EDC names to combine duplicates"""
        if df.empty:
            return df
        
        df = df.copy()
        df[edc_column] = df[edc_column].map(self.edc_normalization).fillna(df[edc_column])
        return df
    
    @st.cache_data
    def get_raw_egs_data(_self):
        """Get ALL raw EGS data from both views - comprehensive cached dataset"""
        try:
            # Query for v_wattbuy_simple with ALL columns
            wattbuy_query = """
            SELECT 
                YEAR(date) as year,
                MONTH(date) as month,
                edc,
                egs,
                rate,
                term,
                rate_type,
                enrollment_fee,
                monthly_charge,
                early_term_fee_min
            FROM v_wattbuy_simple 
            WHERE edc IS NOT NULL AND egs IS NOT NULL AND rate IS NOT NULL
            AND YEAR(date) >= 2010
            """
            
            # Query for v_ocaplans_simple with ALL columns
            ocaplans_query = """
            SELECT 
                YEAR(date) as year,
                MONTH(date) as month,
                edc,
                egs,
                rate,
                term,
                rate_type,
                cancel_fee
            FROM v_ocaplans_simple 
            WHERE edc IS NOT NULL AND egs IS NOT NULL AND rate IS NOT NULL
            AND YEAR(date) >= 2010
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
            combined_df['rate'] = combined_df['rate'].astype(float)
            
            # Convert fee columns to float (different structures for each source)
            # WattBuy columns
            combined_df['enrollment_fee'] = pd.to_numeric(combined_df['enrollment_fee'], errors='coerce')
            combined_df['monthly_charge'] = pd.to_numeric(combined_df['monthly_charge'], errors='coerce')
            combined_df['early_term_fee_min'] = pd.to_numeric(combined_df['early_term_fee_min'], errors='coerce')
            # OCAP columns
            combined_df['cancel_fee'] = pd.to_numeric(combined_df['cancel_fee'], errors='coerce')
            
            # Remove negative values and outliers
            combined_df = combined_df[
                (combined_df['rate'] > 0) & 
                (combined_df['rate'] <= 50)
            ]
            
            # Normalize EDC names to combine duplicates
            combined_df = _self.normalize_edc_names(combined_df)
            
            return combined_df
            
        except Exception as e:
            st.error(f"Failed to load EGS data: {e}")
            return pd.DataFrame()
    
    @st.cache_data
    def get_raw_pjm_data(_self):
        """Get ALL raw PJM data - comprehensive cached dataset"""
        try:
            query = """
            SELECT 
                YEAR(date) as year,
                MONTH(date) as month,
                zone,
                AVG(average_lmp) as average_lmp
            FROM PJM_daily 
            WHERE YEAR(date) >= 2010
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
            
            # Remove negative values and outliers
            df = df[
                (df['lmp_cents_per_kwh'] > 0) & 
                (df['lmp_cents_per_kwh'] <= 50)
            ]
            
            return df
            
        except Exception as e:
            st.error(f"Failed to load PJM data: {e}")
            return pd.DataFrame()
    
    @st.cache_data
    def get_raw_ptc_data(_self):
        """Get ALL raw PTC data - comprehensive cached dataset"""
        try:
            query = """
            SELECT 
                start_date,
                end_date,
                edc,
                rate
            FROM v_ptc_agg 
            WHERE edc IS NOT NULL AND rate IS NOT NULL
            AND start_date IS NOT NULL AND end_date IS NOT NULL
            AND YEAR(start_date) >= 2010
            ORDER BY edc, start_date
            """
            
            df = db_manager.execute_query(query)
            
            if df.empty:
                return pd.DataFrame()
            
            # Convert date columns
            df['start_date'] = pd.to_datetime(df['start_date'])
            df['end_date'] = pd.to_datetime(df['end_date'])
            df['rate'] = df['rate'].astype(float)
            
            # Remove negative values and outliers
            df = df[
                (df['rate'] > 0) & 
                (df['rate'] <= 50)
            ]
            
            # Normalize EDC names to combine duplicates
            df = _self.normalize_edc_names(df)
            
            return df
            
        except Exception as e:
            st.error(f"Failed to load PTC data: {e}")
            return pd.DataFrame()
    
    # Convenience methods for modules to get filtered data
    def get_egs_data_for_future_module(self, edc=None):
        """Get EGS data formatted for future module (2017-2022, grouped by EGS)"""
        raw_data = self.get_raw_egs_data()
        if raw_data.empty:
            return pd.DataFrame()
        
        # Filter date range
        filtered_data = raw_data[
            (raw_data['date'] >= '2017-01-01') & 
            (raw_data['date'] <= '2022-12-31')
        ]
        
        # Group by EGS and calculate averages
        if edc:
            filtered_data = filtered_data[filtered_data['edc'] == edc]
        
        grouped_data = filtered_data.groupby(['date', 'edc', 'egs'])['rate'].mean().reset_index()
        grouped_data['avg_rate'] = grouped_data['rate']
        
        return grouped_data[['date', 'edc', 'egs', 'avg_rate', 'source']]
    
    def get_egs_data_for_ptc_module(self, edc=None, conform=False):
        """Get EGS data formatted for PTC module"""
        raw_data = self.get_raw_egs_data()
        if raw_data.empty:
            return pd.DataFrame()
        
        # Filter by EDC if specified
        if edc:
            raw_data = raw_data[raw_data['edc'] == edc]
        
        if conform:
            # Apply conforming logic
            wattbuy_no_fees = (
                ((raw_data['enrollment_fee'].isna()) | (raw_data['enrollment_fee'] == 0)) &
                ((raw_data['monthly_charge'].isna()) | (raw_data['monthly_charge'] == 0)) &
                ((raw_data['early_term_fee_min'].isna()) | (raw_data['early_term_fee_min'] == 0))
            )
            
            ocap_no_fees = (raw_data['cancel_fee'].isna())
            
            conformed_data = raw_data[
                (raw_data['term'] == 12) &
                (raw_data['rate_type'].str.lower().str.contains('fixed', na=False)) &
                (
                    ((raw_data['source'] == 'WattBuy') & wattbuy_no_fees) |
                    ((raw_data['source'] == 'OCAP') & ocap_no_fees)
                )
            ]
            
            if not conformed_data.empty:
                averaged_data = conformed_data.groupby(['date', 'edc'])['rate'].mean().reset_index()
                averaged_data['avg_rate'] = averaged_data['rate']
                averaged_data['source'] = 'Conformed EGS'
                return averaged_data[['date', 'edc', 'avg_rate', 'source']]
            return pd.DataFrame()
        else:
            # Regular averaging
            averaged_data = raw_data.groupby(['date', 'edc'])['rate'].mean().reset_index()
            averaged_data['avg_rate'] = averaged_data['rate']
            averaged_data['source'] = 'Combined Average'
            return averaged_data[['date', 'edc', 'avg_rate', 'source']]
    
    def get_egs_data_for_fees_module(self, edc=None):
        """Get EGS data formatted for fees module (WattBuy only, all fee columns)"""
        raw_data = self.get_raw_egs_data()
        if raw_data.empty:
            return pd.DataFrame()
        
        # Filter to WattBuy only (fees module only uses WattBuy)
        fees_data = raw_data[raw_data['source'] == 'WattBuy'].copy()
        
        # Filter by EDC if specified
        if edc:
            fees_data = fees_data[fees_data['edc'] == edc]
        
        return fees_data
    
    def get_pjm_data_for_module(self, edc=None, date_range=None):
        """Get PJM data formatted for specific module needs"""
        raw_data = self.get_raw_pjm_data()
        if raw_data.empty:
            return pd.DataFrame()
        
        # Filter by EDC if specified
        if edc:
            pjm_zone = self.edc_mapping.get(edc)
            if pjm_zone:
                raw_data = raw_data[raw_data['zone'] == pjm_zone]
            else:
                return pd.DataFrame()
        
        # Filter by date range if specified
        if date_range:
            start_date, end_date = date_range
            raw_data = raw_data[
                (raw_data['date'] >= start_date) & 
                (raw_data['date'] <= end_date)
            ]
        
        return raw_data

# Global shared data manager instance
shared_data_manager = SharedDataManager()
