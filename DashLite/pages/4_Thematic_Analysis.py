import streamlit as st
import streamlit as st
import pandas as pd
import string
import plotly.graph_objects as go
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import datetime
from utils import TABLE, theme_colors, login
from streamlit_plotly_events import plotly_events
import plotly.express as px
from dateutil.relativedelta import relativedelta
from utils import inject_telkom_styling, render_telkom_footer,render_telkom_sidebar_logo
inject_telkom_styling()

# -------------------- Navbar --------------------
st.markdown("""
<nav class="navbar navbar-expand-lg" style="background-color: #0099D8;">
  <div class="container-fluid">
    <a class="navbar-brand" href="#" "color: white important;" "underline: none;" "text-decoration: none !important;">Thematic Analysis of Mentions</a>
  </div>
</nav>
""", unsafe_allow_html=True)


#st.header('Thematic Analysis of Mentions')
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
    st.stop()




MONTHLY_COLOR = "#1f77b4"  # Blue (Plotly default)
DAILY_COLOR = "#ff7f0e"    # Orange
UNFILTERED_COLOR = "#90ee90" #Light green 
total_records = 378490

min_date = datetime.date(2022, 3, 1)
max_date = datetime.date(2025, 2, 28)

df = pd.read_parquet("thematic_df.parquet")
start_date = min_date
end_date = max_date

normalized_start_date = min_date
normalized_end_date = end_date

model_names = df['PromptName'].dropna().unique()
model_names.sort()  # Optional: sort alphabetically
# Create two columns side by side
st.sidebar.header("Filter Options")

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


selected_model = st.sidebar.radio("Select a Model:", model_names)

df_filtered = df[
        (df['PromptName'] == selected_model) &
        (df['PublishedDate'] >= pd.to_datetime(user_start_date)) &
        (df['PublishedDate'] <= pd.to_datetime(user_end_date))
    ].copy()
# Group total counts by Theme
if df_filtered.empty:
    st.warning("⚠️ No data found in df_filtered for the selected model and date range.")
    st.stop()
# Aggregate and reindex to ensure all themes are present in fixed order
theme_totals = df_filtered.groupby('ThemeName')['ThemeCount'].sum() #no sorting!!!
theme_totals = theme_totals.reindex(theme_colors.keys(), fill_value=0)  # Preserve theme order

#Ensure color mapping matches the theme order in the pie
ordered_colors = [theme_colors[theme] for theme in theme_totals.index]

fig_pie = go.Figure(data=[go.Pie(
    labels=theme_totals.index,
    values=theme_totals.values,
    pull=[0.05]*len(theme_totals),  # Slight pull-out effect
    hole=0,  # Set between 0 (pie) and 1 (donut)
    marker=dict(
        colors=ordered_colors,
        line=dict(color='#000000', width=1)
    ),
    textinfo='percent+label'
)])

days = (user_end_date - user_start_date).days
fig_pie.update_layout(
    title=f"Overall Theme Distribution over Selected Period ({days} days)",
    height=600,
    showlegend=True
)

st.plotly_chart(fig_pie, use_container_width=True)

if (user_end_date - user_start_date).days < 31:
    df_filtered['Period'] = df_filtered['PublishedDate']  # Daily granularity
    tick_format = '%d-%b-%y'
else:
    df_filtered['Period'] = df_filtered['PublishedDate'].dt.to_period('M').apply(lambda r: r.start_time)
    tick_format = '%b-%y'

pivot_df = df_filtered.pivot_table(
    index='Period',
    columns='ThemeName',
    values='ThemeCount',
    aggfunc='sum',
    fill_value=0
).sort_index()

#st.markdown(f"### 📊 Change in Theme Distribution by Percentage Points over ({days} days)")

# Normalize first and last periods to percentages
first_pct = pivot_df.iloc[0] / pivot_df.iloc[0].sum() * 100
last_pct = pivot_df.iloc[-1] / pivot_df.iloc[-1].sum() * 100

# Calculate percentage point change
change_df = pd.DataFrame({
    'Start %': first_pct,
    'End %': last_pct,
    'Change (pp)': (last_pct - first_pct)
}).sort_values(by='Change (pp)', ascending=False)

# Optional: round for readability
change_df = change_df.round(2)
styled_df = change_df.style \
    .format({
        'Start %': '{:.1f}', 
        'End %': '{:.1f}', 
        'Change (pp)': '{:+.1f}'  # + sign shows ↑↓ effect nicely
    }) \
    .background_gradient(cmap='coolwarm', subset=['Change (pp)'])

# Display as a table
#st.dataframe(styled_df, height=400)

fig_change = px.bar(
    change_df.reset_index(),
    x='Change (pp)',
    y='ThemeName',
    orientation='h',
    color='Change (pp)',
    color_continuous_scale='RdBu',
    text='Change (pp)',
    title=f"Change in Themes by Percentage Points over ({days} days)",
)

fig_change.update_layout(
    xaxis_title='Change in Share (%)',
    yaxis_title='Theme',
    coloraxis_colorbar=dict(title='Δ (pp)'),
    height=500
)

st.plotly_chart(fig_change, use_container_width=True)

# Assume min_date and max_date are already defined
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
    df_filtered['Period'] = df_filtered['PublishedDate'].dt.to_period('Y').apply(lambda r: r.start_time)
    tick_format = '%Y'  # or '%y' for two-digit year
elif interval == "Weekly":
    df_filtered['Period'] = df_filtered['PublishedDate'].dt.to_period('W').apply(lambda r: r.start_time)
    tick_format = '%d-%b-%y'
elif interval == "Daily":
    df_filtered['Period'] = df_filtered['PublishedDate']
    tick_format = '%d/%m/%y'
elif interval == "Monthly":
    df_filtered['Period'] = df_filtered['PublishedDate'].dt.to_period('M').apply(lambda r: r.start_time)
    tick_format = '%b-%y'    

# --- Pivot for stacked chart ---
pivot_df = df_filtered.pivot_table(
    index='Period',
    columns='ThemeName',
    values='ThemeCount',
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
        marker_color=theme_colors.get(theme, '#d3d3d3')  # Use dict for fixed color
    ))

fig.update_layout(
    barmode='stack',
    title=f'Theme Count by {interval}',
    xaxis_title=interval,
    yaxis_title='Theme Count',
    legend_title='Theme Name',
    xaxis_tickformat=tick_format,
    hovermode='x unified'
)

st.plotly_chart(fig, use_container_width=True)

# --- Trend Line Chart ---
fig_trend = go.Figure()

for theme in pivot_df.columns:
    fig_trend.add_trace(go.Scatter(
        x=pivot_df.index,
        y=pivot_df[theme],
        mode='lines+markers',
        name=theme,
        line=dict(width=2, color=theme_colors.get(theme, '#d3d3d3')),  # Set line color)
        marker=dict(size=5),
        hovertemplate=f"<b>{theme}</b><br>%{{x|%d-%b-%Y}}<br>Count: %{{y}}<extra></extra>"
    ))

fig_trend.update_layout(
    title=f'Theme Trends by {interval}',
    xaxis_title=interval,
    yaxis_title='Theme Count',
    legend_title='Theme Name',
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
        marker_color=theme_colors.get(theme, '#d3d3d3'),
        hovertemplate='%{y:.1f}%<br>Theme: %{text}<extra></extra>'
    ))

fig_percent.update_layout(
    barmode='stack',
    title=f'Theme Distribution by {interval} (100% Stacked)',
    xaxis_title=interval,
    yaxis_title='Percentage (%)',
    legend_title='Theme Name',
    xaxis_tickformat=tick_format,
    hovermode='x unified',
    yaxis=dict(range=[0, 100])
)

st.plotly_chart(fig_percent, use_container_width=True)
st.stop()

#row_dict = df_LLM_progress.iloc[0].to_dict()

#st.subheader(f"🧭 LLM Processing rates of {row_dict['BaseRowCount']:,}")
# # Layout: One column per gauge (2 per row for clarity)
#cols = st.columns(3)
#gpt_percent = row_dict['GPT4o1'] / row_dict['GPT4o0'] * 100
# model_counts_df = df_LLM_progress['ModelName'].value_counts().reset_index()
# # Calculate percentages and add Percentage column
# df_LLM_progress['Percentage'] = (df_LLM_progress['PostCount'] / total_records) * 100
# df_LLM_progress['Percentage'] = df_LLM_progress['Percentage'].round(1)
# llama_percent = row_dict['Llama1'] / row_dict['Llama0'] * 100
# granite_percent = row_dict['GraniteLarge1'] / row_dict['GraniteLarge0'] * 100

# with cols[0]:
#     fig = go.Figure(go.Indicator(
#                 mode="gauge+number",
#                 value=gpt_percent,
#                 title={'text': 'GPT-4o'},
#                 gauge={
#                     'axis': {'range': [0, 100]},
#                     'bar': {'color': "royalblue"},
#                     'steps': [
#                         {'range': [0, 25], 'color': "#e0f3ff"},
#                         {'range': [25, 50], 'color': "#c7e9f1"},
#                         {'range': [50, 75], 'color': "#a8d5e2"},
#                         {'range': [75, 100], 'color': "#7fcdbb"}
#                     ],
#                 },
#                 number={'suffix': "%"}
#             ))
#     st.plotly_chart(fig, use_container_width=True)

# with cols[1]:
#     fig = go.Figure(go.Indicator(
#                 mode="gauge+number",
#                 value=llama_percent,
#                 title={'text': 'Llama 3.2 Large'},
#                 gauge={
#                     'axis': {'range': [0, 100]},
#                     'bar': {'color': "royalblue"},
#                     'steps': [
#                         {'range': [0, 25], 'color': "#e0f3ff"},
#                         {'range': [25, 50], 'color': "#c7e9f1"},
#                         {'range': [50, 75], 'color': "#a8d5e2"},
#                         {'range': [75, 100], 'color': "#7fcdbb"}
#                     ],
#                 },
#                 number={'suffix': "%"}
#             ))
#     st.plotly_chart(fig, use_container_width=True)

# with cols[2]:
#     fig = go.Figure(go.Indicator(
#                 mode="gauge+number",
#                 value=granite_percent,
#                 title={'text': 'Granite 3.2 Large'},
#                 gauge={
#                     'axis': {'range': [0, 100]},
#                     'bar': {'color': "royalblue"},
#                     'steps': [
#                         {'range': [0, 25], 'color': "#e0f3ff"},
#                         {'range': [25, 50], 'color': "#c7e9f1"},
#                         {'range': [50, 75], 'color': "#a8d5e2"},
#                         {'range': [75, 100], 'color': "#7fcdbb"}
#                     ],
#                 },
#                 number={'suffix': "%"}
#             ))
#     st.plotly_chart(fig, use_container_width=True)

# # Create gauges
# for i, row in df_LLM_progress.iterrows():
#     with cols[i % 2]:
#         fig = go.Figure(go.Indicator(
#             mode="gauge+number",
#             value=row['Percentage'],
#             title={'text': row['ModelName']},
#             gauge={
#                 'axis': {'range': [0, 100]},
#                 'bar': {'color': "royalblue"},
#                 'steps': [
#                     {'range': [0, 25], 'color': "#e0f3ff"},
#                     {'range': [25, 50], 'color': "#c7e9f1"},
#                     {'range': [50, 75], 'color': "#a8d5e2"},
#                     {'range': [75, 100], 'color': "#7fcdbb"}
#                 ],
#             },
#             number={'suffix': "%"}
#         ))
#         st.plotly_chart(fig, use_container_width=True)
render_telkom_sidebar_logo()
render_telkom_footer()