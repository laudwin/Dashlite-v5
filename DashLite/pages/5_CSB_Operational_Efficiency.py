import streamlit as st
import streamlit.components.v1 as components

from utils import (
    THOMAS_URL,
    query_flowise
)
from utils import TABLE, theme_colors, login
from utils import inject_telkom_styling, render_telkom_footer,render_telkom_sidebar_logo
inject_telkom_styling()
#from utils import THOMAS_URL


#inject_telkom_styling()

# -------------------- Navbar --------------------
st.markdown("""
<nav class="navbar navbar-expand-lg" style="background-color: #0099D8;">
  <div class="container-fluid">
    <a class="navbar-brand" href="#" "color: white important;" "underline: none;" "text-decoration: none !important;">CSB Operational Efficiency</a>
  </div>
</nav>
""", unsafe_allow_html=True)

#render_title_bar("CSB Operational Efficiency")
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
    st.stop()
    
st.markdown("""
### Chat and Converse with our AI assistant
Chat or click “Start a call” to chat with an AI assistant that has read the full report by Prof Thomas Anning. You can ask it questions about the findings, insights or any theory mentioned. It won't give personal opinions or new advice but only what's in the report.

It’s like having a helpful guide who knows the document inside out!
""")

#col1, col2 = st.columns([1, 1])

#with col1:
# Input box for the user to type messages
if input := st.chat_input("Ask your question..."):
    # Add user's message to chat history
    with st.chat_message("user"):
        st.markdown(input)

    # Call your API (replace with your actual API call)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            data_payload = {"question": input,}
            output = query_flowise(THOMAS_URL, data_payload, 90)
            reply = output.get("text", "Oops! No response 😅")
            st.markdown(reply)

render_telkom_sidebar_logo()
render_telkom_footer()
