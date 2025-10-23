# Activate virtual environment
source symposium_env/Scripts/activate

# Verify it's working
python --version
which python  # Should show path to symposium_env/Scripts/python

# Run your Streamlit app
streamlit run interface.py




CROSS MODULE CHACHING!!!!!! takes a minute to start but holy moly <3
┌─────────────────────────────────────────────────────────────┐
│                    SharedDataManager                        │
├─────────────────────────────────────────────────────────────┤
│  @st.cache_data get_raw_egs_data()                         │
│  @st.cache_data get_raw_pjm_data()                         │
│  @st.cache_data get_raw_ptc_data()                         │
├─────────────────────────────────────────────────────────────┤
│  get_egs_data_for_future_module()                          │
│  get_egs_data_for_ptc_module()                             │
│  get_egs_data_for_fees_module()                            │
│  get_pjm_data_for_module()                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Individual Modules                          │
├─────────────────────────────────────────────────────────────────────┤
│  FutureModule    │  PTCModule    │  FeesModule    │    PJMModule    │
│  (uses shared)   │  (uses shared)│  (uses shared) │  (uses shared)  │
└─────────────────────────────────────────────────────────────────────┘