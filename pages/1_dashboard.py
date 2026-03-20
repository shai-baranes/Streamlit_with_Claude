import pandas as pd
import streamlit as st
import numpy as np

st.write("# Dashboard Page")

chart_data = pd.DataFrame(np.random.randn(20, 3), columns=['a', 'b', 'c'])
st.bar_chart(chart_data)
st.line_chart(chart_data)
print(chart_data)

# st.area_chart(chart_data) # need to understand what is it good for?
st.write("### Data Summary")
st.write(chart_data.describe())