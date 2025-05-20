import streamlit as st
import pandas as pd
from openai import AzureOpenAI
from sqlalchemy import create_engine
from urllib.parse import quote_plus
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from utils import inject_telkom_styling, render_telkom_footer, render_telkom_sidebar_logo

inject_telkom_styling()

# --- Streamlit Page Config ---
st.title("💬 Ask TISL AI")

# --- Azure OpenAI Config ---
client = AzureOpenAI(
    api_key="db4c85906b5047419a733719992b649e",
    azure_endpoint="https://tisl-openaiservice.openai.azure.com",
    api_version="2025-01-01-preview"
)
DEPLOYMENT_NAME = "gpt-4o"

from sqlalchemy import create_engine
from urllib.parse import quote_plus

database = 'VerbatimData'
table = 'Post'
uid = 'someadmin'
pwd = 'Gx9#vTq2Lm'
server = 'sqlserverlogical.database.windows.net'

# Use pymssql instead of pyodbc
connect_str = f"mssql+pytds://{uid}:{pwd}@{server}/{database}?encrypt=yes"
AzureDB = create_engine(connect_str)


# --- Load Data in Chunks from SQL via SQLAlchemy ---
def load_post_data_chunked(offset=0, chunk_size=1000):
    try:
        query = f"""
            SELECT PostId, PostText, Published, Category, Gender, Engagement, Sentiment
            FROM dbo.{table}
            WHERE PostText IS NOT NULL
            ORDER BY PostId
            OFFSET {offset} ROWS FETCH NEXT {chunk_size} ROWS ONLY;
        """
        df = pd.read_sql(query, AzureDB)
        df["Published"] = pd.to_datetime(df["Published"], errors='coerce')
        df["Engagement"] = pd.to_numeric(df["Engagement"], errors='coerce')
        df["Sentiment"] = pd.to_numeric(df["Sentiment"], errors='coerce')
        return df
    except Exception as e:
        st.error(f"❌ Failed to load data: {str(e)}")
        return pd.DataFrame()

# --- Search by Keyword using SQLAlchemy ---
def search_posts_by_keyword(keyword):
    try:
        query = f"""
            SELECT PostId, PostText, Published, Category, Gender, Engagement, Sentiment
            FROM dbo.{table}
            WHERE PostText LIKE :keyword
            ORDER BY Published DESC;
        """
        df = pd.read_sql(query, AzureDB, params={"keyword": f"%{keyword}%"})
        return df
    except Exception as e:
        st.error(f"🔍 Search failed: {str(e)}")
        return pd.DataFrame()

# --- Azure GPT Response ---
def ask_azure_openai(prompt, followup=False):
    try:
        system_message = "You are a TISL Customer Feedback Assistant using social media data from the Post table."
        if followup:
            prompt = (
                f"Based on this user query:\n'{prompt}'\n"
                "Generate 3 helpful follow-up questions. Return only the questions as plain bullet points."
            )
            system_message = "You are a helpful assistant suggesting follow-up questions."

        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ GPT Error: {str(e)}"

# --- Load Initial Sample Data ---
df = load_post_data_chunked(offset=0, chunk_size=1500)
if df.empty:
    st.stop()

# --- Chat History ---
if "chat" not in st.session_state:
    st.session_state.chat = []

clicked_question = st.session_state.get("clicked_question", None)

for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_query = st.chat_input("Ask about Telkom complaints...")

if clicked_question:
    user_query = clicked_question
    st.session_state.clicked_question = None

if user_query:
    st.session_state.chat.append({"role": "user", "content": user_query})
    lower_query = user_query.lower().strip()
    response = None

    if any(lower_query.startswith(greet) for greet in ["hi", "hello", "hey"]):
        response = "👋 Hi! I'm your TISL Customer Feedback Assistant. How can I help today?"

    elif "summary" in lower_query or "summarize" in lower_query:
        samples = df["PostText"].dropna().sample(min(15, len(df))).tolist()
        prompt = "Summarize the themes in these Telkom complaints:\n" + "\n".join(f"- {t}" for t in samples)
        response = ask_azure_openai(prompt)

    elif "search" in lower_query or "find" in lower_query:
        keyword = lower_query.split("search")[-1].strip() or lower_query.split("find")[-1].strip()
        matches = search_posts_by_keyword(keyword)
        count = len(matches)
        response = f"🔍 Found **{count}** complaints containing '**{keyword}**' in `PostText`."
        st.session_state.chat.append({"role": "assistant", "content": response})
        st.write(response)
        st.dataframe(matches[["Published", "PostText", "Category", "Gender", "Engagement"]], use_container_width=True)

    elif "top category" in lower_query:
        top_cat = df["Category"].value_counts().idxmax()
        response = f"🏷️ Most common complaint category is **{top_cat}**."

    elif "average engagement" in lower_query:
        avg = df["Engagement"].mean()
        response = f"📊 The average post engagement is **{avg:.2f}**."

    elif any(word in lower_query for word in ["chart", "graph", "visualize", "table", "word cloud"]):
        if "engagement" in lower_query:
            chart_data = df.groupby("Category")["Engagement"].mean().sort_values(ascending=False).head(10)
            st.markdown("### 📊 Average Engagement by Category")
            st.bar_chart(chart_data)
            response = "Here's a chart showing average engagement by category."

        elif "sentiment" in lower_query:
            st.markdown("### 📈 Sentiment Distribution")
            st.bar_chart(df["Sentiment"].value_counts())
            response = "Here's a sentiment distribution chart."

        elif "table" in lower_query:
            st.markdown("### 📋 Sample Complaints Table")
            st.dataframe(df[["Published", "PostText", "Category", "Gender", "Engagement"]].head(10))
            response = "Here is a sample table of Telkom complaints."

        elif "word cloud" in lower_query:
            text = " ".join(df["PostText"].dropna().tolist())
            wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
            st.markdown("### ☁️ Word Cloud of Complaint Keywords")
            fig, ax = plt.subplots()
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis("off")
            st.pyplot(fig)
            response = "Here's a word cloud showing common complaint terms."

        else:
            response = "I can generate charts, tables, or word clouds based on engagement, sentiment, categories, etc. Try asking something more specific!"

    else:
        sample_context = df["PostText"].dropna().sample(min(15, len(df))).tolist()
        context = "\n".join(f"- {line}" for line in sample_context)
        prompt = f"User asked: '{user_query}'. Use this data to answer:\n{context}"
        response = ask_azure_openai(prompt)

    if response:
        st.session_state.chat.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(f"**You asked:** {user_query}")
            st.write(response)

        followup_raw = ask_azure_openai(user_query, followup=True)
        suggestions = [q.strip("-• ") for q in followup_raw.split("\n") if q.strip()]
        if suggestions:
            st.markdown("### 💡 You can also ask:")
            for i, suggestion in enumerate(suggestions):
                if st.button(suggestion, key=f"suggestion_{i}"):
                    st.session_state.clicked_question = suggestion
                    st.rerun()

# --- Footer ---
st.markdown("---")
st.markdown(
    """
    <style>
    button[kind="secondary"] {
        background-color: #e0f7fa !important;
        color: #007c91 !important;
        font-weight: 600 !important;
        margin-bottom: 0.5rem;
        border-radius: 8px;
    }
    </style>
    <div class="footer">
        <p>Powered by TISL WIC | Ask TISL AI</p>
    </div>
    """,
    unsafe_allow_html=True,
)

render_telkom_sidebar_logo()
render_telkom_footer()
