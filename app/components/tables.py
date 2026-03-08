import streamlit as st


def show_dataframe(df, title: str):
    """Render a styled dataframe table."""
    st.subheader(title)
    st.dataframe(df, use_container_width=True)
