# Shared chart utilities for all modules
import altair as alt
import pandas as pd
import streamlit as st

class ChartBuilder:
    """Base class for building charts with consistent styling"""
    
    @staticmethod
    def create_line_chart(data, x_col, y_col, color_col, title, x_title=None, y_title=None):
        """Create a standardized line chart"""
        hover = alt.selection_point(
            fields=[x_col],
            nearest=True,
            on="mouseover",
            empty=False,
        )

        chart = (
            alt.Chart(data, title=title)
            .mark_line()
            .encode(
                x=alt.X(x_col, title=x_title or x_col),
                y=alt.Y(y_col, title=y_title or y_col),
                color=color_col,
                tooltip=[
                    alt.Tooltip(x_col, title=x_title or x_col),
                    alt.Tooltip(y_col, title=y_title or y_col, format=".2f"),
                    alt.Tooltip(color_col, title=color_col),
                ],
            )
            .add_params(hover)
            .properties(height=500)
        )

        return chart.resolve_scale(color="independent")
    
    @staticmethod
    def create_bar_chart(data, x_col, y_col, color_col=None, title="Bar Chart", x_title=None, y_title=None):
        """Create a standardized bar chart"""
        chart = (
            alt.Chart(data, title=title)
            .mark_bar()
            .encode(
                x=alt.X(x_col, title=x_title or x_col),
                y=alt.Y(y_col, title=y_title or y_col),
                color=color_col if color_col else alt.value('steelblue'),
                tooltip=[
                    alt.Tooltip(x_col, title=x_title or x_col),
                    alt.Tooltip(y_col, title=y_title or y_col, format=".2f"),
                ],
            )
            .properties(height=500)
        )
        
        return chart
    
    @staticmethod
    def create_scatter_chart(data, x_col, y_col, color_col=None, title="Scatter Plot", x_title=None, y_title=None):
        """Create a standardized scatter plot"""
        chart = (
            alt.Chart(data, title=title)
            .mark_circle(size=60)
            .encode(
                x=alt.X(x_col, title=x_title or x_col),
                y=alt.Y(y_col, title=y_title or y_col),
                color=color_col if color_col else alt.value('steelblue'),
                tooltip=[
                    alt.Tooltip(x_col, title=x_title or x_col),
                    alt.Tooltip(y_col, title=y_title or y_col, format=".2f"),
                ],
            )
            .properties(height=500)
        )
        
        return chart

class DataSummary:
    """Utility class for creating data summary displays"""
    
    @staticmethod
    def create_summary_metrics(data, metrics_config):
        """Create a summary metrics display"""
        st.subheader("Data Summary")
        
        # Calculate column widths based on content length
        col_widths = []
        for config in metrics_config:
            if 'width' in config:
                col_widths.append(config['width'])
            else:
                col_widths.append(1)
        
        cols = st.columns(col_widths)
        
        for i, config in enumerate(metrics_config):
            with cols[i]:
                value = config['value'](data)
                st.metric(config['label'], value)
    
    @staticmethod
    def create_sidebar_filters(data, filter_config):
        """Create sidebar filters for data selection"""
        st.sidebar.header(filter_config['title'])
        
        selected_items = []
        for item in filter_config['items']:
            if st.sidebar.checkbox(item, value=True, key=f"filter_{item}"):
                selected_items.append(item)
        
        return selected_items
