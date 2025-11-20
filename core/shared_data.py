# Shared data cache manager for all modules
import streamlit as st
import pandas as pd
import numpy as np
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

        # Mapping used by notebook-style data preparation
        self.service_type_map = {
            "R": "default_rate",
            "R - Regular Residential Service": "default_rate",
            "RS": "default_rate",
            "RS - Regular Residential Service": "default_rate",
            "RH": "default_rh_rate",
            "RH - Residential Heating Service": "default_rh_rate",
            "RA": "default_ra_rate",
            "RA - Residential Add - on Heat Pump Service": "default_ra_rate",
            "GS - General Service Small Non - Demand Metered": "default_rate_without_demand_meter",
            "GS - General Service Small (under 50kW)": "default_rate_without_demand_meter",
            "default_rate": "default_rate",
            "default_heat_rate": "default_rh_rate",
            "default_heat_pump_rate": "default_ra_rate",
        }

        self.utility_replace_map = {
            'Pike County Light & Power': 'Pike County Light and Power',
            'Pike County Light': 'Pike County Light and Power',
            'Met-Ed': 'Met Ed',
            'Met Ed': 'Met Ed',
        }

        self.plan_type_display_map = {
            "default_rate": "R - Regular Residential Service",
            "default_rh_rate": "RH - Residential Heating Service",
            "default_ra_rate": "RA - Residential Add-on Heat Pump Service",
            "default_rate_without_demand_meter": "RWD - Regular Residential Service without Demand Meter",
            "default_rate_with_demand_meter": "RD - Regular Residential Service with Demand Meter",
            "R": "R - Regular Residential Service",
            "RS": "R - Regular Residential Service",
            "RH": "RH - Residential Heating Service",
            "RA": "RA - Residential Add-on Heat Pump Service",
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

    # ------------------------------------------------------------------
    # Notebook-style data preparation (WattBuy-only, 12-month, no fees)
    # ------------------------------------------------------------------
    @st.cache_data
    def get_wattbuy_offer_rows(_self):
        """Direct WattBuy offer feed with daily timestamps."""
        query = "SELECT * FROM v_wattbuy_simple"
        df = db_manager.execute_query(query)
        if df.empty:
            return df

        expected_columns = [
            'entry_id',
            'utility_name',
            'supplier_name',
            'rate_type',
            'plan_type',
            'term',
            'rate_amount',
            'created_at',
            'enrollment_fee',
            'monthly_charge',
            'early_term_fee',
            'green_percentage',
            'green_details',
            'is_green'
        ]
        df = df.iloc[:, :len(expected_columns)]
        df.columns = expected_columns

        df = df[
            df['utility_name'].notna() &
            df['created_at'].notna() &
            df['rate_amount'].notna()
        ].copy()
        df = df[pd.to_datetime(df['created_at']).dt.year >= 2010]

        df['created_at'] = pd.to_datetime(df['created_at'])
        df['rate_amount'] = pd.to_numeric(df['rate_amount'], errors='coerce') / 100.0
        df['enrollment_fee'] = pd.to_numeric(df['enrollment_fee'], errors='coerce')
        df['monthly_charge'] = pd.to_numeric(df['monthly_charge'], errors='coerce')
        df['early_term_fee'] = pd.to_numeric(df['early_term_fee'], errors='coerce')
        df['plan_type'] = df['plan_type'].fillna('default_rate')
        df['plan_type'] = df['plan_type'].map(_self.plan_type_display_map).fillna(df['plan_type'])
        df['utility_name'] = df['utility_name'].replace(_self.utility_replace_map)
        return df

    @st.cache_data
    def get_wattbuy_ptc_rows(_self):
        """PTC feed from v_ptc_wattbuyplans, filtered to base residential rows."""
        query = "SELECT * FROM v_ptc_wattbuyplans"
        df = db_manager.execute_query(query)
        if df.empty:
            return df

        expected_columns = [
            'entry_id',
            'utility_name',
            'created_at',
            'plan_type',
            'rate_type_utility',
            'rate_value_utility_amount',
            'rate_min_limit',
            'rate_max_limit',
            'rate_seq'
        ]
        df = df.iloc[:, :len(expected_columns)]
        df.columns = expected_columns

        df = df[
            df['utility_name'].notna() &
            df['created_at'].notna() &
            df['rate_value_utility_amount'].notna()
        ].copy()

        df['created_at'] = pd.to_datetime(df['created_at'])
        df = df[df['created_at'].dt.year >= 2010]

        df['rate_value_utility_amount'] = pd.to_numeric(
            df['rate_value_utility_amount'], errors='coerce'
        ) / 100.0
        df['plan_type'] = df['plan_type'].fillna(df['rate_type_utility'])
        df['plan_type'] = df['plan_type'].fillna('default_rate')
        df['plan_type'] = df['plan_type'].map(_self.plan_type_display_map).fillna(df['plan_type'])
        df['utility_name'] = df['utility_name'].replace(_self.utility_replace_map)
        df['rate_min_limit'] = pd.to_numeric(df['rate_min_limit'], errors='coerce')
        df['rate_max_limit'] = pd.to_numeric(df['rate_max_limit'], errors='coerce')
        df = df[
            ((df['rate_min_limit'].isna()) | (df['rate_min_limit'] == 0)) &
            ((df['rate_max_limit'].isna()) | (df['rate_max_limit'] == 0))
        ]
        df['source_priority'] = 0  # prefer WattBuy records
        return df[['utility_name', 'created_at', 'plan_type', 'rate_value_utility_amount', 'source_priority']]

    @st.cache_data
    def get_ptc_agg_daily_rows(_self):
        """Daily-expanded PTC rows derived from v_ptc_agg to mirror notebook logic."""
        query = """
        SELECT
            edc,
            service_type,
            source,
            rate,
            start_date,
            end_date
        FROM v_ptc_agg
        WHERE edc IS NOT NULL
          AND rate IS NOT NULL
          AND start_date IS NOT NULL
          AND end_date IS NOT NULL
          AND YEAR(start_date) >= 2010
        """
        df = db_manager.execute_query(query)
        if df.empty:
            return df

        df['start_date'] = pd.to_datetime(df['start_date'])
        df['end_date'] = pd.to_datetime(df['end_date'])
        swap_mask = df['end_date'] < df['start_date']
        if swap_mask.any():
            df.loc[swap_mask, ['start_date', 'end_date']] = df.loc[
                swap_mask, ['end_date', 'start_date']
            ].to_numpy()

        df['service_type'] = df['service_type'].map(_self.service_type_map).fillna(df['service_type'])
        df['rate'] = pd.to_numeric(df['rate'], errors='coerce') / 100.0
        df['edc'] = df['edc'].replace(_self.utility_replace_map)
        df = df.dropna(subset=['rate'])

        df['date_range'] = [
            pd.date_range(s, e, freq='D')
            for s, e in zip(df['start_date'], df['end_date'])
        ]
        exploded = (
            df[['edc', 'service_type', 'rate', 'date_range']]
            .explode('date_range', ignore_index=True)
            .rename(columns={
                'edc': 'utility_name',
                'service_type': 'plan_type',
                'date_range': 'created_at',
                'rate': 'rate_value_utility_amount'
            })
        )
        exploded['plan_type'] = exploded['plan_type'].map(_self.plan_type_display_map).fillna(exploded['plan_type'])
        exploded['source_priority'] = 1  # fallback priority
        return exploded[['utility_name', 'created_at', 'plan_type', 'rate_value_utility_amount', 'source_priority']]

    @st.cache_data
    def get_notebook_style_ptc_rates(_self):
        """Combined PTC rates with WattBuy priority, matching notebook behaviour."""
        wattbuy_ptc = _self.get_wattbuy_ptc_rows()
        agg_ptc = _self.get_ptc_agg_daily_rows()

        if wattbuy_ptc.empty and agg_ptc.empty:
            return pd.DataFrame()

        combined = pd.concat([wattbuy_ptc, agg_ptc], ignore_index=True)
        combined = combined.dropna(subset=['utility_name', 'created_at', 'plan_type'])
        combined = combined.sort_values(
            by=['utility_name', 'plan_type', 'created_at', 'source_priority']
        )
        combined = combined.drop_duplicates(
            subset=['utility_name', 'plan_type', 'created_at'],
            keep='first'
        )
        return combined[['utility_name', 'created_at', 'plan_type', 'rate_value_utility_amount']]

    @st.cache_data
    def get_notebook_style_dataset(_self):
        """Replicate the WattBuy-only, 12-month, fee-free dataset used in the notebook."""
        offers = _self.get_wattbuy_offer_rows()
        ptc = _self.get_notebook_style_ptc_rates()

        if offers.empty or ptc.empty:
            return pd.DataFrame()

        offers = offers.copy()
        offers['plan_type'] = offers['plan_type'].fillna('default_rate')
        offers['created_at'] = offers['created_at'].dt.floor('D')

        # Apply notebook-style filters
        offers = offers[
            (offers['rate_type'].str.lower().str.contains('fixed', na=False)) &
            (offers['term'] == 12)
        ].copy()

        offers['enrollment_fee'] = offers['enrollment_fee'].fillna(0)
        offers['monthly_charge'] = offers['monthly_charge'].fillna(0)
        offers['early_term_fee'] = offers['early_term_fee'].fillna(0)

        offers = offers[
            (offers['enrollment_fee'] == 0) &
            (offers['monthly_charge'] == 0) &
            (offers['early_term_fee'] == 0)
        ]

        offers['utility_name'] = offers['utility_name'].replace(_self.utility_replace_map)

        merged = pd.merge(
            offers,
            ptc,
            on=['utility_name', 'created_at', 'plan_type'],
            how='left',
            validate='many_to_one'
        )

        merged = merged.dropna(subset=['rate_value_utility_amount'])
        merged['below_equal'] = merged['rate_amount'] <= merged['rate_value_utility_amount']
        merged['cat_term'] = merged['term'].apply(
            lambda x: '<12' if pd.notna(x) and x < 12 else ('12' if x == 12 else '>12')
        )
        merged['cat_term'] = merged['cat_term'].fillna('Unknown')
        merged['created_at'] = pd.to_datetime(merged['created_at'])
        return merged

# Global shared data manager instance
shared_data_manager = SharedDataManager()
