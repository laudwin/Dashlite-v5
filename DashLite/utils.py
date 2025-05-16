import streamlit as st
import re
import requests
import hashlib
from sqlalchemy import create_engine
from urllib.parse import quote_plus
from PIL import Image
#from azure.ai.inference import ChatCompletionsClient
#from azure.ai.inference.models import SystemMessage, UserMessage
#from azure.core.credentials import AzureKeyCredential

IS_DEBUG = False

theme_colors = {
    'Network Issues': '#636EFA',                     # Blue
    'Customer Service Issues': '#EF553B',            # Red-Orange
    'Pricing and Affordability': '#00CC96',          # Teal-Green
    'Product and Service Offerings': '#AB63FA',      # Purple
    'Brand Perception and Reputation': '#FFA15A',    # Orange
    'User Experience and Satisfaction': '#19D3F3',   # Cyan
    'Digital Inclusion and Accessibility': '#FF6692',# Pink
    'Market and Regulatory Factors': '#B6E880',      # Light Green
    'Other Theme' : "#d3d3d3"                        # Light Grey
}

SQL_API_URL = "https://flowise-210n.onrender.com/api/v1/prediction/dbd00d0f-dc26-4d07-9a99-ba4ea670ffed"
PY_CODE_API_URL = "https://flowise-210n.onrender.com/api/v1/prediction/4b48ba12-ee76-49bf-8e6d-892c20946441"
SIBUYI_URL = "https://flowise-210n.onrender.com/api/v1/prediction/8a883cd9-eb8f-4fb0-9bb3-c10d2a23e549"
JIDE_URL="https://flowise-210n.onrender.com/api/v1/prediction/1a47203a-a94d-4c9d-bccb-d6e9e42f0a0e"

TABLE = 'Post'
# -------------------- Styling Function ------------------ #



def render_telkom_sidebar_logo():
    st.sidebar.image("DashLite/telkom-logo.png", use_container_width=True)


def inject_telkom_styling():
    st.set_page_config(layout="wide")

    st.markdown("""
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            /* --- Restore sidebar and apply Telkom blue --- */
            [data-testid="stSidebar"] {
                background-color: #0099d9 !important;
            }

            [data-testid="stSidebar"] * {
                color: white !important;
            }

            /* --- Main layout --- */
            [data-testid="stAppViewContainer"] {
                padding-bottom: 80px !important;
            }

            [data-testid="stAppViewBlockContainer"] {
                background-color: white;
                padding: 2rem 4rem;
                max-width: 100% !important;
                width: 100% !important;
            }
                
            

            html, body {
                margin: 0;
                padding: 0;
                width: 100vw !important;
                overflow-x: hidden;
                background-color: white !important;
            }

            /* --- Button styles --- */
            .stButton > button, .btn-telkom {
                background-color: #e73f94 !important;
                color: white !important;
                font-weight: bold;
                border-radius: 8px;
                padding: 0.5rem 1.25rem;
                border: none;
                text-decoration: none;
                display: inline-block;
            }

            a {
                color: white !important;
                text-decoration: none !important;
                }
            .stButton > button:hover, .btn-telkom:hover {
                background-color: #c0287a !important;
                text-decoration: none;
            }

            /* --- Footer --- */
            .floating-footer {
                position: fixed;
                left: 0;
                bottom: 0;
                width: 100%;
                background-color: #0099d9;
                color: white;
                text-align: center;
                padding: 0.75rem 0.5rem;
                font-size: 0.85rem;
                z-index: 1000;
                box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
            }

            .footer-container {
                max-width: 1200px;
                margin: 0 auto;
                display: flex;
                justify-content: center;
                align-items: center;
                flex-wrap: wrap;
                gap: 1rem;
            }

            .footer-link {
                color: white !important;
                text-decoration: none;
                padding: 0.4rem 1rem;
                border-radius: 4px;
                display: flex;
                align-items: center;
                gap: 0.4rem;
                font-weight: 500;
            }

            .footer-link:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }

            @media (max-width: 768px) {
                .footer-container {
                    flex-direction: column;
                    padding-bottom: 0.5rem;
                }

                .footer-link {
                    justify-content: center;
                    width: 100%;
                }
            }
        </style>
    """, unsafe_allow_html=True)

def render_telkom_footer():
    footer_html = """
    <div class="floating-footer">
        <div class="footer-container">
            <a href="/?page=main" class="footer-link">
                <i class="fas fa-comments"></i>Main
            </a>
            <a href="/?page=4_Thematic_Analysis" class="footer-link">
                <i class="fas fa-qrcode"></i> Thematic Analysis
            </a>
            <a href="/?page=coverage" class="footer-link">
                <i class="fas fa-broadcast-tower"></i> Issue Analysis
            </a>
            <a href="/?page=stores" class="footer-link">
                <i class="fas fa-store"></i> Data Sci Report
            </a>
           <a href="/?page=5_Qualitative_Report" class="footer-link">
            <i class="fas fa-newspaper"></i> Qualitative Report
            </a>
            <a href="/?page=6_Time_Series" class="footer-link">
                <i class="fas fa-clock"></i> Time Series
            </a>
        </div>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)

def show_page_content():
    # Get current page from query parameters
    current_page = st.experimental_get_query_params().get("page", ["home"])[0]
    
    # Main content container with proper spacing
    with st.container():
        if current_page == "home":
            st.title("Home Page")
            st.write("Welcome to Telkom Analytics")
            # Your home page content here
            
        elif current_page == "help":
            st.title("Get Help")
            st.write("Contact our support team")
            # Help page content
            
        elif current_page == "coverage":
            st.title("Coverage Checker")
            st.write("Check your area coverage")
            # Coverage page content
            
        elif current_page == "stores":
            st.title("Store Locator")
            st.write("Find Telkom stores near you")
            # Stores page content
            
        elif current_page == "blog":
            st.title("InTouch Blog")
            st.write("Latest news and updates")
            # Blog page content

USER_CREDENTIALS = {
    "tisluser": hashlib.sha256("Telkom@TISL2025".encode()).hexdigest()
}

def clean_sql(sql_text: str) -> str:
    """
    Cleans a SQL string generated by GPT by removing any Markdown-style
    code blocks like ```sql ... ``` or ``` ... ```
    """
    # Remove all code fences like ```sql or ```
    cleaned = re.sub(r"^```(?:sql)?\s*|```$", "", sql_text.strip(), flags=re.IGNORECASE | re.MULTILINE)
    return cleaned.strip()

def clean_generated_code(code: str) -> str:
    """
    Cleans AI-generated code for safe execution in a pre-imported environment.
    - Removes markdown code fencing (```python or ```)
    - Strips leading/trailing whitespace
    - Removes all import statements (e.g., import plotly.express as px)
    """
    # Step 1: Remove ```python and ``` fences
    code = re.sub(r"```python|```", "", code).strip()

    # Step 2: Remove import statements (whole lines starting with 'import' or 'from')
    code_lines = code.splitlines()
    cleaned_lines = [
        line for line in code_lines
        if not line.strip().startswith("import") and not line.strip().startswith("from")
    ]

    # Step 3: Join back the cleaned code
    cleaned_code = "\n".join(cleaned_lines).strip()
    return cleaned_code

def query_flowise(url_string: str, payload: dict, timeout: int = 60):
    """
    Sends a POST request with JSON payload to the Flowise Agent.
    Automatically times out after `timeout` seconds (default 60).
    """
    try:
        response = requests.post(url_string, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.Timeout:
        raise RuntimeError("⏱️ Request timed out after {timeout} seconds.")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"❌ Request failed: {e}")
    
def login():
    st.title("Login Required")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        hashed_input_pw = hashlib.sha256(password.encode()).hexdigest()

        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == hashed_input_pw:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid username or password")
