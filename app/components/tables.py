import streamlit as st


def show_dataframe(df, title: str, hide_id: bool = True):
    """Render a styled dataframe table. By default hides id column (long internal IDs)."""
    st.subheader(title)
    display_df = df.copy()
    if hide_id and "id" in display_df.columns:
        display_df = display_df.drop(columns=["id"])
    elif "id" in display_df.columns:
        display_df["id"] = display_df["id"].astype(str)
    st.dataframe(display_df, use_container_width=True)
