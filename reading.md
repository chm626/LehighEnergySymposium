# Activate virtual environment
source symposium_env/Scripts/activate

# Verify it's working
python --version
which python  # Should show path to symposium_env/Scripts/python

# Run your Streamlit app
streamlit run interface.py