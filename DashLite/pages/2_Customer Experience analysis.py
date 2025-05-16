import streamlit as st
import streamlit as st
import pandas as pd
import string
import plotly.graph_objects as go
import fastparquet
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import datetime
from utils import TABLE, theme_colors, login, IS_DEBUG
from streamlit_plotly_events import plotly_events
import plotly.express as px
from dateutil.relativedelta import relativedelta
from utils import inject_telkom_styling, render_telkom_footer,render_telkom_sidebar_logo
inject_telkom_styling()


# -------------------- Navbar --------------------
st.markdown("""
<nav class="navbar navbar-expand-lg" style="background-color: #0099D8;">
  <div class="container-fluid">
    <a class="navbar-brand" href="#" "color: white important;" "underline: none;" "text-decoration: none !important;">Issue (Code) Level Analysis of Mentions</a>
  </div>
</nav>
""", unsafe_allow_html=True)


#st.header('Issue (Code) Level Analysis of Mentions')
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
    st.stop()

MONTHLY_COLOR = "#1f77b4"  # Blue (Plotly default)
DAILY_COLOR = "#ff7f0e"    # Orange

total_records = 378490

min_date = datetime.date(2022, 3, 1)
max_date = datetime.date(2025, 2, 28)

start_date = min_date
end_date = max_date

normalized_start_date = min_date
normalized_end_date = end_date

df_filtered = pd.read_parquet("DashLite/issue_df.parquet")


model_names = df_filtered['PromptName'].dropna().unique()
model_names.sort()  # Optional: sort alphabetically
Theme_names = df_filtered['ThemeName'].dropna().unique()
Theme_names.sort()  # Optional: sort alphabetically
# Create two columns side by side
#col1, col2 = st.columns([1, 5])
# Sidebar inputs
st.sidebar.header("Filter Options")

#with col1:
user_start_date = st.sidebar.date_input(
    "Select Start Date:", 
    start_date, 
    min_value=min_date, 
    max_value=max_date
)

user_end_date = st.sidebar.date_input(
    "Select End Date:", 
    end_date, 
    min_value=min_date, 
    max_value=max_date
)
#    threshold_percent = st.slider("Percent Threshold", 0, 10, 0)

#with col2:
selected_model = st.sidebar.radio("Select a Model:", model_names)
# Checkbox to exclude "Unclassified" CodeNames
exclude_unclassified = st.sidebar.checkbox("Exclude 'Unclassified' issues", value=True)

if exclude_unclassified:
    df_filtered = df_filtered[~df_filtered['CodeName'].str.contains("Unclassified", case=False, na=False)]

if df_filtered.empty:
    st.warning("⚠️ No data found in df_filtered for the selected model and date range.")
    st.stop()

# Calculate total CodeCount
#max_code_count = df_filtered['CodeCount'].max()
#threshold = (threshold_percent / 100) * max_code_count
#df_star = df_filtered[df_filtered['CodeCount'] >= threshold]
# if df_star.empty:
#     st.warning("⚠️ No data found in df_star burst for the selected model and date range.")
#     st.stop()

fig = px.sunburst(
    df_filtered,
    path=['ThemeName', 'SubThemeName', 'CodeName'],  # Hierarchy: inside → out
    values='CodeCount',  # Size the segments by count
    color='ThemeName',   # Optional: color by Theme
    color_discrete_map=theme_colors,  # Use fixed color dict directly
    title=f'Theme → SubTheme → Code Breakdown',# (showing {100.0-threshold_percent}% of counts)',
    height=700
)

fig.update_layout(
    margin=dict(t=50, l=25, r=25, b=25)
)

st.plotly_chart(fig, use_container_width=True)

#Display the top 10 problematic codes
top_codes = (
    df_filtered[['CodeName', 'ThemeName', 'CodeCount']]
    .groupby(['CodeName', 'ThemeName'], as_index=False)
    .sum()
    .nlargest(10, 'CodeCount')
    .sort_values(by='CodeCount', ascending=False)  # Sort for horizontal bar plot with highest at the top
)

top_codes['Color'] = top_codes['ThemeName'].map(theme_colors)

# Step 2: Create horizontal bar chart
fig = px.bar(
    top_codes,
    x='CodeCount',
    y='CodeName',
    orientation='h',
    color='ThemeName',
    color_discrete_map=theme_colors,
    title='Top 10 Issues (codes)',
    labels={'CodeCount': 'Count', 'CodeName': 'Code Name'},
    height=500,
    category_orders={'CodeName': top_codes['CodeName'].tolist()}  # <--- Enforces order
 )

# Step 3: Improve layout
fig.update_layout(
    xaxis_title='Number of Issues',
    yaxis_title='',
    margin=dict(l=100, r=20, t=50, b=20)
)

# Step 4: Display in Streamlit
st.plotly_chart(fig, use_container_width=True)

#selected_theme = st.radio("Select a Theme", Theme_names)
selected_theme = st.radio("Select a Theme:", Theme_names[:-1], horizontal=True) #ignore the Other theme
df_sub_theme = df_filtered[(df_filtered['ThemeName'] == selected_theme)].copy()

# Group total counts by Theme
if df_sub_theme.empty:
    st.warning("⚠️ No data found in df_filtered for the selected model and date range.")
    st.stop()

fig = px.sunburst(
    df_sub_theme,
    path=['SubThemeName', 'CodeName'],  # Hierarchy: inside → out
    values='CodeCount',  # Size the segments by count
    color='ThemeName',  # This makes all segments inherit the same theme color
    color_discrete_map={selected_theme: theme_colors[selected_theme]},
    title='SubTheme → Code Breakdown',
    height=700
)

fig.update_layout(
    margin=dict(t=50, l=25, r=25, b=25)
)

st.plotly_chart(fig, use_container_width=True)

if (user_end_date - user_start_date).days < 31:
    df_sub_theme['Period'] = df_sub_theme['PublishedDate']  # Daily granularity
    tick_format = '%d-%b-%y'
else:
    df_sub_theme['Period'] = df_sub_theme['PublishedDate'].dt.to_period('M').apply(lambda r: r.start_time)
    tick_format = '%b-%y'

pivot_df = df_sub_theme.pivot_table(
    index='Period',
    columns='SubThemeName',
    values='CodeCount',
    aggfunc='sum',
    fill_value=0
).sort_index()

date_diff = relativedelta(user_end_date, user_start_date)

# Choose granularity options based on date range
if date_diff.years >= 1:
    granularity_options = ["Yearly", "Monthly", "Weekly"]
else:
    granularity_options = ["Monthly", "Weekly"]

if (date_diff.years == 0 and date_diff.months < 6):
    granularity_options.append("Daily")
# --- User control ---
interval = st.radio(
    "Choose time granularity:",
    options=granularity_options,
    index=granularity_options.index("Monthly"),  # Default to monthly if available
    horizontal=True
)

# Step 2: Add 'Period' based on selected granularity
if interval == "Yearly":
    df_sub_theme['Period'] = df_sub_theme['PublishedDate'].dt.to_period('Y').apply(lambda r: r.start_time)
    tick_format = '%Y'  # or '%y' for two-digit year
elif interval == "Weekly":
    df_sub_theme['Period'] = df_sub_theme['PublishedDate'].dt.to_period('W').apply(lambda r: r.start_time)
    tick_format = '%d-%b-%y'
elif interval == "Daily":
    df_sub_theme['Period'] = df_sub_theme['PublishedDate']
    tick_format = '%d/%m/%y'
elif interval == "Monthly":
    df_sub_theme['Period'] = df_sub_theme['PublishedDate'].dt.to_period('M').apply(lambda r: r.start_time)
    tick_format = '%b-%y'    

# --- Pivot for stacked chart ---
pivot_df = df_sub_theme.pivot_table(
    index='Period',
    columns='SubThemeName',
    values='CodeCount',
    aggfunc='sum',
    fill_value=0
).sort_index()

# --- Plotly stacked bar chart ---
fig = go.Figure()

for theme in pivot_df.columns:
    fig.add_trace(go.Bar(
        x=pivot_df.index,
        y=pivot_df[theme],
        name=theme,
    ))

fig.update_layout(
    barmode='stack',
    title=f'Sub-theme Count by {interval}',
    xaxis_title=interval,
    yaxis_title='Sub Theme Count',
    legend_title='Sub Theme Name',
    xaxis_tickformat=tick_format,
    hovermode='x unified'
)

st.plotly_chart(fig, use_container_width=True)

# --- Trend Line Chart ---
fig_trend = go.Figure()

for theme in sorted(pivot_df.columns):
    fig_trend.add_trace(go.Scatter(
        x=pivot_df.index,
        y=pivot_df[theme],
        mode='lines+markers',
        name=theme,
        line=dict(width=2),
        marker=dict(size=5),
        hovertemplate=f"<b>{theme}</b><br>%{{x|%d-%b-%Y}}<br>Count: %{{y}}<extra></extra>"
    ))

fig_trend.update_layout(
    title=f'Sub-theme Trends by {interval}',
    xaxis_title=interval,
    yaxis_title='Sub Theme Count',
    legend_title='Sub Theme Name',
    xaxis_tickformat=tick_format,
    hovermode='x unified'
)

st.plotly_chart(fig_trend, use_container_width=True)

# --- Normalize to get 100% stacked version ---
normalized_df = pivot_df.div(pivot_df.sum(axis=1), axis=0) * 100  # Convert to percentage
fig_percent = go.Figure()

for theme in normalized_df.columns:
    fig_percent.add_trace(go.Bar(
        x=normalized_df.index,
        y=normalized_df[theme],
        name=theme,
        text=[theme] * len(normalized_df),
        hovertemplate='%{y:.1f}%<br>Subtheme: %{text}<extra></extra>'
    ))

fig_percent.update_layout(
    barmode='stack',
    title=f'Sub-theme Distribution by {interval} (100% Stacked)',
    xaxis_title=interval,
    yaxis_title='Percentage (%)',
    legend_title='Sub-theme Name',
    xaxis_tickformat=tick_format,
    hovermode='x unified',
    yaxis=dict(range=[0, 100])
)

st.plotly_chart(fig_percent, use_container_width=True)

# --- Dropdown to go deeper into SubTheme ---
available_subthemes = df_sub_theme['SubThemeName'].dropna().unique()
available_subthemes.sort()

selected_subtheme = st.radio("Select a Sub-theme to drill down into Codes:", available_subthemes)
df_code_level = df_sub_theme[df_sub_theme['SubThemeName'] == selected_subtheme].copy()
fig_code = px.sunburst(
    df_code_level,
    path=['CodeName'],
    values='CodeCount',
    color='CodeName',
    title=f'Code Breakdown within Sub-theme: {selected_subtheme}',
    height=500
)

fig_code.update_layout(
    margin=dict(t=50, l=25, r=25, b=25)
)

st.plotly_chart(fig_code, use_container_width=True)

# --- Pivot for stacked chart (by CodeName) ---
pivot_df = df_sub_theme.pivot_table(
    index='Period',
    columns='CodeName',  # 🔥 Change here
    values='CodeCount',
    aggfunc='sum',
    fill_value=0
).sort_index()

# --- Plotly stacked bar chart (by CodeName) ---
fig = go.Figure()

for code in sorted(pivot_df.columns):
    fig.add_trace(go.Bar(
        x=pivot_df.index,
        y=pivot_df[code],
        name=code,
    ))

fig.update_layout(
    barmode='stack',
    title=f'Code Count by {interval}',
    xaxis_title=interval,
    yaxis_title='Code Count',
    legend_title='Code Name',  # 🔥 Change title
    xaxis_tickformat=tick_format,
    hovermode='x unified'
)

st.plotly_chart(fig, use_container_width=True)

# --- Trend Line Chart (by CodeName) ---
fig_trend = go.Figure()

for code in sorted(pivot_df.columns):
    fig_trend.add_trace(go.Scatter(
        x=pivot_df.index,
        y=pivot_df[code],
        mode='lines+markers',
        name=code,
        line=dict(width=2),
        marker=dict(size=5),
        hovertemplate=f"<b>{code}</b><br>%{{x|%d-%b-%Y}}<br>Count: %{{y}}<extra></extra>"
    ))

fig_trend.update_layout(
    title=f'Code Trends by {interval}',
    xaxis_title=interval,
    yaxis_title='Code Count',
    legend_title='Code Name',
    xaxis_tickformat=tick_format,
    hovermode='x unified'
)

st.plotly_chart(fig_trend, use_container_width=True)

# --- Normalize to get 100% stacked version (by CodeName) ---
normalized_df = pivot_df.div(pivot_df.sum(axis=1), axis=0) * 100  # Convert to percentage

fig_percent = go.Figure()

for code in sorted(normalized_df.columns):
    fig_percent.add_trace(go.Bar(
        x=normalized_df.index,
        y=normalized_df[code],
        name=code,
        text=[code] * len(normalized_df),
        hovertemplate='%{y:.1f}%<br>Code: %{text}<extra></extra>'
    ))

fig_percent.update_layout(
    barmode='stack',
    title=f'Code Distribution by {interval} (100% Stacked)',
    xaxis_title=interval,
    yaxis_title='Percentage (%)',
    legend_title='Code Name',  # 🔥 Updated
    xaxis_tickformat=tick_format,
    hovermode='x unified',
    yaxis=dict(range=[0, 100])
)

st.plotly_chart(fig_percent, use_container_width=True)

available_codes = sorted(df_sub_theme['CodeName'].dropna().unique())

selected_code = st.radio(
    "Select a Code for Detailed Analysis:", 
    options=available_codes,
    index=0, 
    horizontal=True  # Vertical listing (default)
)

df_issue = df_sub_theme[df_sub_theme['CodeName'] == selected_code]

trend_df = df_issue.pivot_table(
    index='Period',
    values='CodeCount',
    aggfunc='sum'
).sort_index()

# --- Trend Line Chart for selected CodeName ---
fig_trend = go.Figure()

fig_trend.add_trace(go.Scatter(
    x=trend_df.index,
    y=trend_df['CodeCount'],
    mode='lines+markers',
    name=selected_code,
    line=dict(width=3),
    marker=dict(size=6),
    hovertemplate=f"<b>{selected_code}</b><br>%{{x|%d-%b-%Y}}<br>Count: %{{y}}<extra></extra>"
))

fig_trend.update_layout(
    title=f'Trend for "{selected_code}" by {interval}',
    xaxis_title=interval,
    yaxis_title='Code Count',
    hovermode='x unified',
    xaxis_tickformat=tick_format,
)

st.plotly_chart(fig_trend, use_container_width=True)
render_telkom_sidebar_logo()
render_telkom_footer()
