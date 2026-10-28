
import streamlit as st

st.set_page_config(
    page_title="ResumeIT | Product Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("ResumeIT")
st.subheader("Product Analytics & Insights")
st.write(
    "An analytical view of user acquisition, activation, feature journeys, "
    "monetization, reliability, and customer feedback for the ResumeIT app."
)

st.divider()
st.markdown("### Explore the dashboard")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**01 — Executive Overview**")
    st.caption("Track user growth, activation, downloads, and revenue.")
    st.markdown("**02 — User Journeys**")
    st.caption("Find conversion gaps and the largest funnel drop-offs.")

with col2:
    st.markdown("**03 — Monetization & Reliability**")
    st.caption("Evaluate purchases, paywall conversion, and key success rates.")
    st.markdown("**04 — Customer Voice**")
    st.caption("Explore actual collected reviews, sentiment, and repeat usage.")

st.divider()
st.info("Choose a section from the sidebar to begin exploring the dashboard.")
st.caption(
    "Data note: Customer reviews are collected data. Product events and "
    "transactions are synthetic and illustrative, not actual app telemetry."
)
