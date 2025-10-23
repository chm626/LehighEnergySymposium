# Landing Page Module
import streamlit as st
import pandas as pd
from core.shared_data import shared_data_manager

class LandingModule:
    """Landing page module providing overview of ERES Energy Analytics platform"""
    
    def __init__(self):
        self.edc_mapping = shared_data_manager.edc_mapping
        self.edc_normalization = shared_data_manager.edc_normalization
    
    def create_header(self):
        """Create the main header section"""
        st.title("ERES Energy Analytics")
        st.markdown("""
        ### Comprehensive Energy Market Analysis Platform
        
        Welcome to ERES Energy Analytics, your comprehensive platform for analyzing Pennsylvania's competitive electricity market. 
        Our platform provides deep insights into electricity pricing, market dynamics, and consumer choice patterns across 
        Electric Distribution Companies (EDCs) in Pennsylvania.
        """)
    
    def create_data_overview(self):
        """Create data sources overview section"""
        st.header("Data Sources")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("EGS Retail Data")
            st.markdown("""
            **Sources:** WattBuy & OCAP Plans  
            **Coverage:** 2010 - Present  
            **Records:** Individual electricity offers  
            **Key Metrics:** Rates, terms, fees, suppliers  
            **EDCs:** All major Pennsylvania utilities
            """)
        
        with col2:
            st.subheader("PJM Wholesale Data")
            st.markdown("""
            **Source:** PJM Daily LMP  
            **Coverage:** 2017 - Present  
            **Records:** Daily wholesale prices  
            **Key Metrics:** Locational Marginal Prices  
            **EDCs:** APS, DUQ, METED, PECO, PENELEC, PPL
            """)
        
        with col3:
            st.subheader("PTC Benchmark Data")
            st.markdown("""
            **Source:** Price to Compare  
            **Coverage:** 2016 - Present  
            **Records:** Utility default rates  
            **Key Metrics:** Monthly PTC rates  
            **EDCs:** All major Pennsylvania utilities
            """)
    
    def create_module_previews(self):
        """Create module functionality previews"""
        st.header("Analysis Modules")
        
        # Module 1: PJM LMP Analysis
        with st.expander("PJM LMP Analysis", expanded=False):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("""
                **Purpose:** Analyze wholesale electricity market prices  
                **Key Features:**
                - Daily LMP trends by PJM zone
                - Seasonal price patterns
                - Price volatility analysis
                - EDC-specific wholesale cost analysis
                
                **Use Cases:**
                - Understanding wholesale market dynamics
                - Identifying price trends and patterns
                - Analyzing cost basis for retail pricing
                """)
            with col2:
                st.info("**Best For:** Market researchers, utility analysts, energy traders")
        
        # Module 2: EGS Pricing Analysis
        with st.expander("EGS Pricing Analysis", expanded=False):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("""
                **Purpose:** Compare retail electricity prices to wholesale costs  
                **Key Features:**
                - EGS vs PJM price comparisons
                - Supplier-specific pricing analysis
                - Retail margin calculations
                - EDC-specific market analysis
                
                **Use Cases:**
                - Evaluating retail market competitiveness
                - Understanding pricing strategies
                - Identifying market opportunities
                """)
            with col2:
                st.info("**Best For:** Retail suppliers, market analysts, regulators")
        
        # Module 3: PTC, EGS, PJM Comparison
        with st.expander("PTC, EGS, PJM Comparison", expanded=False):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("""
                **Purpose:** Three-way comparison of pricing benchmarks  
                **Key Features:**
                - PTC vs EGS vs PJM trends
                - All-EDCs average analysis
                - EDC-specific comparisons
                - Conformed EGS data filtering
                
                **Use Cases:**
                - Comprehensive market overview
                - Benchmark analysis
                - Policy impact assessment
                """)
            with col2:
                st.info("**Best For:** Policy makers, regulators, market researchers")
        
        # Module 4: EGS Fee Analysis
        with st.expander("EGS Fee Analysis", expanded=False):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("""
                **Purpose:** Analyze signup fees and charges  
                **Key Features:**
                - Enrollment fee analysis
                - Monthly charge patterns
                - Early termination fees
                - Supplier-specific fee structures
                
                **Use Cases:**
                - Understanding total cost of service
                - Fee structure analysis
                - Consumer protection insights
                """)
            with col2:
                st.info("**Best For:** Consumer advocates, regulators, market analysts")
        
        # Module 5: EGS Plans vs PTC
        with st.expander("EGS Plans vs PTC", expanded=False):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("""
                **Purpose:** Individual offer comparison to PTC benchmark  
                **Key Features:**
                - Above/below PTC offer identification
                - Individual plan analysis
                - Aggregate vs individual views
                - Color-coded visualization
                
                **Use Cases:**
                - Consumer choice analysis
                - Market competitiveness assessment
                - Individual offer evaluation
                """)
            with col2:
                st.info("**Best For:** Consumers, consumer advocates, market researchers")
    
    def create_edc_coverage(self):
        """Create EDC coverage information"""
        st.header("Electric Distribution Company Coverage")
        
        # Normalize EDC names for display
        normalized_edcs = []
        for edc in self.edc_mapping.keys():
            normalized_name = self.edc_normalization.get(edc, edc)
            if normalized_name not in normalized_edcs:
                normalized_edcs.append(normalized_name)
        
        normalized_edcs.sort()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Covered EDCs")
            for edc in normalized_edcs[:3]:
                st.write(f"• {edc}")
        
        with col2:
            st.subheader("")
            for edc in normalized_edcs[3:]:
                st.write(f"• {edc}")
    
    def create_data_statistics(self):
        """Create data statistics section"""
        st.header("Data Statistics")
        
        try:
            # Get data statistics
            egs_data = shared_data_manager.get_raw_egs_data()
            pjm_data = shared_data_manager.get_raw_pjm_data()
            ptc_data = shared_data_manager.get_raw_ptc_data()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "EGS Offers",
                    f"{len(egs_data):,}" if not egs_data.empty else "0",
                    help="Total individual electricity offers"
                )
                if not egs_data.empty:
                    date_range = f"{egs_data['date'].min().strftime('%Y-%m')} to {egs_data['date'].max().strftime('%Y-%m')}"
                    st.caption(f"Date Range: {date_range}")
            
            with col2:
                st.metric(
                    "PJM Records",
                    f"{len(pjm_data):,}" if not pjm_data.empty else "0",
                    help="Daily wholesale price records"
                )
                if not pjm_data.empty:
                    date_range = f"{pjm_data['date'].min().strftime('%Y-%m')} to {pjm_data['date'].max().strftime('%Y-%m')}"
                    st.caption(f"Date Range: {date_range}")
            
            with col3:
                st.metric(
                    "PTC Records",
                    f"{len(ptc_data):,}" if not ptc_data.empty else "0",
                    help="Price to Compare records"
                )
                if not ptc_data.empty:
                    date_range = f"{ptc_data['start_date'].min().strftime('%Y-%m')} to {ptc_data['end_date'].max().strftime('%Y-%m')}"
                    st.caption(f"Date Range: {date_range}")
        
        except Exception as e:
            st.warning(f"Unable to load data statistics: {e}")
    
    def create_navigation_guide(self):
        """Create navigation guide"""
        st.header("How to Navigate")
        
        st.markdown("""
        ### Getting Started
        
        1. **Choose Your Analysis:** Select a module from the sidebar based on your research needs
        2. **Select EDC:** Most modules allow you to focus on specific Electric Distribution Companies
        3. **Apply Filters:** Use checkboxes and selectors to refine your analysis
        4. **Explore Data:** Hover over charts for detailed information, zoom and pan for deeper insights
        
        ### Tips for Effective Analysis
        
        - **Start with the Home page** to understand data sources and module capabilities
        - **Use conformed data** when comparing EGS offers to PTC rates for apples-to-apples comparison
        - **Switch between chart types** to see different perspectives (aggregate vs individual)
        - **Compare across EDCs** to understand regional market differences
        - **Look for seasonal patterns** in wholesale and retail pricing
        """)
    
    def create_technical_info(self):
        """Create technical information section"""
        st.header("Technical Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Data Processing")
            st.markdown("""
            - **Caching:** All data is cached for optimal performance
            - **Normalization:** EDC names are standardized across sources
            - **Filtering:** Outliers and invalid records are automatically removed
            - **Aggregation:** Data is aggregated by month for consistent analysis
            """)
        
        with col2:
            st.subheader("Platform Features")
            st.markdown("""
            - **Interactive Charts:** Built with Altair for rich interactivity
            - **Session State:** Selections persist across interactions
            - **Real-time Updates:** Data refreshes automatically
            - **Responsive Design:** Works on desktop and mobile devices
            """)
    
    def render(self):
        """Render the landing page"""
        self.create_header()
        st.markdown("---")
        
        self.create_data_overview()
        st.markdown("---")
        
        self.create_module_previews()
        st.markdown("---")
        
        self.create_edc_coverage()
        st.markdown("---")
        
        self.create_data_statistics()
        st.markdown("---")
        
        self.create_navigation_guide()
        st.markdown("---")
        
        self.create_technical_info()
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; padding: 20px;'>
            <p>ERES Energy Analytics Platform | Comprehensive Pennsylvania Electricity Market Analysis</p>
        </div>
        """, unsafe_allow_html=True)

