import streamlit
import pandas
import numpy

streamlit.write("Streamlit supports a wide range of data visualizations, including [Plotly, Altair, and Bokeh charts](https://docs.streamlit.io/develop/api-reference/charts). 📊 And with over 20 input widgets, you can easily make your data interactive!")

all_users = ["Alice", "Bob", "Charlie"]
with streamlit.container(border=True):
    users = streamlit.multiselect("Users", all_users, default=all_users)
    rolling_average = streamlit.toggle("Rolling average")

numpy.random.seed(42)
data = pandas.DataFrame(numpy.random.randn(20, len(users)), columns=users)
if rolling_average:
    data = data.rolling(7).mean().dropna()

tab1, tab2 = streamlit.tabs(["Chart", "Dataframe"])
tab1.line_chart(data, height=250)
