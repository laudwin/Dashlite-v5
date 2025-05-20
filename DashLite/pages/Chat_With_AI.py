import streamlit as st
import pandas as pd
from openai import AzureOpenAI
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from urllib.parse import quote_plus
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import pyodbc
from tenacity import retry, stop_after_attempt, wait_exponential
import os
from utils import inject_telkom_styling, render_telkom_footer, render_telkom_sidebar_logo

# --- Initialize Streamlit Styling ---
inject_telkom_styling()

# --- Streamlit Page Config ---
st.set_page_config(page_title="TISL AI Assistant", layout="wide")
st.title("💬 Ask TISL AI")

# --- Configuration ---
@st.cache_resource
def get_db_engine():
    """Create and cache database engine with retry logic"""
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _create_engine():
        # Using pyodbc instead of pymssql for better reliability
        connection_string = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={st.secrets.db.server};"
            f"Database={st.secrets.db.database};"
            f"UID={st.secrets.db.username};"
            f"PWD={st.secrets.db.password};"
            f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        )
        engine = create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(connection_string)}")
        # Test the connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    
    try:
        return _create_engine()
    except Exception as e:
        st.error(f"❌ Failed to establish database connection: {str(e)}")
        st.stop()

# Initialize database engine
try:
    AzureDB = get_db_engine()
except Exception as e:
    st.error(f"Database connection error: {str(e)}")
    st.stop()

# --- Azure OpenAI Config ---
@st.cache_resource
def get_openai_client():
    return AzureOpenAI(
        api_key=st.secrets.openai.api_key,
        azure_endpoint=st.secrets.openai.endpoint,
        api_version=st.secrets.openai.api_version
    )

client = get_openai_client()
DEPLOYMENT_NAME = "gpt-4o"

# --- Data Loading Functions ---
@st.cache_data(ttl=3600, show_spinner="Loading complaint data...")
def load_post_data_chunked(offset=0, chunk_size=1000):
    """Load data in chunks with proper error handling"""
    try:
        query = text(f"""
            SELECT PostId, PostText, Published, Category, Gender, Engagement, Sentiment
            FROM dbo.Post
            WHERE PostText IS NOT NULL
            ORDER BY PostId
            OFFSET {offset} ROWS FETCH NEXT {chunk_size} ROWS ONLY;
        """)
        
        with AzureDB.connect() as connection:
            df = pd.read_sql(query, connection)
        
        # Data cleaning
        df["Published"] = pd.to_datetime(df["Published"], errors='coerce')
        df["Engagement"] = pd.to_numeric(df["Engagement"], errors='coerce')
        df["Sentiment"] = pd.to_numeric(df["Sentiment"], errors='coerce')
        
        return df
    
    except SQLAlchemyError as e:
        st.error(f"❌ Database error: {str(e)}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        return pd.DataFrame()

def search_posts_by_keyword(keyword, limit=100):
    """Search posts with keyword filtering and limit"""
    try:
        query = text("""
            SELECT PostId, PostText, Published, Category, Gender, Engagement, Sentiment
            FROM dbo.Post
            WHERE PostText LIKE :keyword
            ORDER BY Published DESC
            OFFSET 0 ROWS FETCH NEXT :limit ROWS ONLY;
        """)
        
        with AzureDB.connect() as connection:
            df = pd.read_sql(
                query, 
                connection, 
                params={"keyword": f"%{keyword}%", "limit": limit}
            )
        
        return df
    
    except Exception as e:
        st.error(f"🔍 Search failed: {str(e)}")
        return pd.DataFrame()

# --- AI Response Functions ---
def ask_azure_openai(prompt, context=None, followup=False):
    """Get response from Azure OpenAI with proper error handling"""
    try:
        system_message = (
            "You are a TISL Customer Feedback Assistant analyzing social media complaints. "
            "Be concise, professional, and focus on actionable insights."
        )
        
        if followup:
            prompt = (
                f"Based on this user query about Telkom complaints:\n'{prompt}'\n"
                "Generate 3 relevant follow-up questions that would help analyze the complaints better. "
                "Return only the questions as bullet points without any additional text."
            )
            system_message = "You generate helpful follow-up questions about customer complaints."
        
        messages = [{"role": "system", "content": system_message}]
        
        if context:
            messages.append({
                "role": "assistant",
                "content": f"Context from database:\n{context}"
            })
        
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        return f"⚠️ Error getting AI response: {str(e)}"

# --- Visualization Functions ---
def plot_word_cloud(df):
    """Generate word cloud visualization"""
    text = " ".join(df["PostText"].dropna().astype(str).tolist())
    wordcloud = WordCloud(
        width=800, 
        height=400, 
        background_color='white',
        colormap='viridis',
        stopwords=['telkom', 'tis', 'tis', 'please']
    ).generate(text)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis("off")
    return fig

# --- Main App Logic ---
# Initialize chat history
if "chat" not in st.session_state:
    st.session_state.chat = []

# Load initial data
df = load_post_data_chunked(offset=0, chunk_size=1500)
if df.empty:
    st.warning("No complaint data loaded. Please check database connection.")
    st.stop()

# Display chat history
for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Handle user input
user_query = st.chat_input("Ask about Telkom complaints...")

# Check for clicked follow-up questions
clicked_question = st.session_state.pop("clicked_question", None)
if clicked_question:
    user_query = clicked_question

if user_query:
    # Add user message to chat history
    st.session_state.chat.append({"role": "user", "content": user_query})
    
    # Process query
    lower_query = user_query.lower().strip()
    response = None
    
    # Handle different query types
    if any(lower_query.startswith(greet) for greet in ["hi", "hello", "hey"]):
        response = "👋 Hi! I'm your TISL Customer Feedback Assistant. I can help analyze Telkom customer complaints from social media."
    
    elif "summary" in lower_query or "summarize" in lower_query:
        samples = df["PostText"].dropna().sample(min(15, len(df))).tolist()
        prompt = "Summarize the main themes in these Telkom complaints:\n" + "\n".join(f"- {t}" for t in samples)
        response = ask_azure_openai(prompt)
    
    elif "search" in lower_query or "find" in lower_query:
        keyword = lower_query.replace("search", "").replace("find", "").strip()
        if not keyword:
            response = "Please specify what you'd like to search for."
        else:
            matches = search_posts_by_keyword(keyword, limit=50)
            count = len(matches)
            response = f"🔍 Found {count} complaints containing '{keyword}'."
            
            st.session_state.chat.append({"role": "assistant", "content": response})
            st.write(response)
            
            if not matches.empty:
                st.dataframe(
                    matches[["Published", "PostText", "Category", "Gender", "Engagement"]],
                    use_container_width=True,
                    hide_index=True
                )
    
    elif "top category" in lower_query:
        top_cat = df["Category"].value_counts().idxmax()
        count = df["Category"].value_counts().max()
        response = f"🏷️ Most common complaint category is **{top_cat}** with {count} complaints."
    
    elif "average engagement" in lower_query:
        avg = df["Engagement"].mean()
        response = f"📊 The average post engagement is **{avg:.2f}** (higher means more likes/shares/comments)."
    
    elif any(word in lower_query for word in ["chart", "graph", "visualize", "table", "word cloud"]):
        if "engagement" in lower_query:
            chart_data = df.groupby("Category")["Engagement"].mean().sort_values(ascending=False).head(10)
            st.markdown("### 📊 Average Engagement by Category")
            st.bar_chart(chart_data)
            response = "This chart shows which complaint categories get the most engagement (likes/shares/comments)."
        
        elif "sentiment" in lower_query:
            st.markdown("### 📈 Sentiment Distribution (Higher = More Positive)")
            st.bar_chart(df["Sentiment"].value_counts().sort_index())
            response = "Sentiment analysis of complaints (higher scores are more positive)."
        
        elif "table" in lower_query:
            st.markdown("### 📋 Recent Complaints")
            st.dataframe(
                df[["Published", "PostText", "Category", "Gender", "Engagement"]]
                .sort_values("Published", ascending=False)
                .head(10),
                use_container_width=True,
                hide_index=True
            )
            response = "Here are some recent complaints from the database."
        
        elif "word cloud" in lower_query:
            st.markdown("### ☁️ Common Complaint Terms")
            fig = plot_word_cloud(df)
            st.pyplot(fig)
            response = "Word cloud showing frequently mentioned terms in complaints."
        
        else:
            response = (
                "I can visualize complaint data in different ways. Try asking for:\n"
                "- Engagement by category\n"
                "- Sentiment distribution\n"
                "- Recent complaints table\n"
                "- Word cloud of common terms"
            )
    
    else:
        # General query - provide context from database
        sample_context = df["PostText"].dropna().sample(min(15, len(df))).tolist()
        context = "\n".join(f"- {line}" for line in sample_context)
        prompt = f"User asked: '{user_query}'. Use this complaint data to answer:\n{context}"
        response = ask_azure_openai(prompt)
    
    # Display response
    if response:
        st.session_state.chat.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.write(response)
        
        # Generate follow-up suggestions
        if not any(word in lower_query for word in ["hi", "hello", "hey"]):
            followup_raw = ask_azure_openai(user_query, followup=True)
            suggestions = [q.strip("-• ") for q in followup_raw.split("\n") if q.strip()]
            
            if suggestions:
                st.markdown("**💡 You might want to ask:**")
                cols = st.columns(len(suggestions))
                for i, (col, suggestion) in enumerate(zip(cols, suggestions)):
                    with col:
                        if st.button(suggestion, key=f"suggestion_{i}"):
                            st.session_state.clicked_question = suggestion
                            st.rerun()

# --- Footer ---
render_telkom_sidebar_logo()
render_telkom_footer()
