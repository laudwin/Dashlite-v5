import streamlit as st
import datetime
import calendar
import pandas as pd
import plotly.express as px

from sqlalchemy import create_engine
import plotly.graph_objects as go
from utils import TABLE, login
from utils import inject_telkom_styling, render_telkom_footer,render_telkom_sidebar_logo
inject_telkom_styling()


#st.set_page_config(layout="wide")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
    st.stop()

# -------------------- Navbar --------------------
st.markdown("""
<nav class="navbar navbar-expand-lg" style="background-color: #0099D8;">
  <div class="container-fluid">
    <a class="navbar-brand" href="#" "color: white important;" "underline: none;" "text-decoration: none !important;">TISL Social Media Mentions Visualisation</a>
  </div>
</nav>
""", unsafe_allow_html=True)

#st.header('TISL Social Media Mentions Visualisation')

# ✅ Define the month_diff function first
def month_diff(start_date, end_date):
    return (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1

MONTHLY_COLOR = "#2ca02c"  # Green
WEEKLY_COLOR = "#1f77b4"  # Blue (Plotly default)
DAILY_COLOR = "#ff7f0e"    # Orange
UNFILTERED_COLOR = "#d3d3d3" #Light grey 

min_date = datetime.date(2022, 3, 1)
max_date = datetime.date(2025, 2, 28)

start_date = min_date
end_date = max_date

normalized_start_date = min_date
normalized_end_date = end_date

df = pd.read_parquet("DashLite/time_series_df.parquet")
df_unfiltered = pd.read_parquet("DashLite/time_series_df_unfiltered.parquet")
# Create two columns side by side
col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    user_start_date = st.date_input(
        "Select Start Date:", 
        start_date, 
        min_value=min_date, 
        max_value=max_date
    )

with col2:
    user_end_date = st.date_input(
        "Select End Date:", 
        end_date, 
        min_value=min_date, 
        max_value=max_date
    )

with col3:
    # UI: Radio buttons
    overview_option = st.radio(
        "Select Time Granularity:",
        options=["Monthly", "Weekly", "Daily"],
        index=1,  # Default is "Weekly"
        horizontal=True
    )
# 🔄 Normalize start to first of month
normalized_start_date = user_start_date.replace(day=1)

# 🔄 Normalize end to last of month
last_day = calendar.monthrange(user_end_date.year, user_end_date.month)[1]
normalized_end_date = user_end_date.replace(day=last_day)

if normalized_end_date <= normalized_start_date:
    st.error("❌ Error: endDate must be after startDate.")

num_months = month_diff(normalized_start_date, normalized_end_date)
st.write(f"📅 Plot range from {normalized_start_date} to {normalized_end_date} spanning {num_months} months.")
df_plot = df[
        (df['PublishedDate'] >= pd.to_datetime(normalized_start_date)) & 
        (df['PublishedDate'] <= pd.to_datetime(normalized_end_date))
    ]
df_unfiltered_plot = df_unfiltered[
        (df_unfiltered['PublishedDate'] >= pd.to_datetime(normalized_start_date)) & 
        (df_unfiltered['PublishedDate'] <= pd.to_datetime(normalized_end_date))
    ]

# Create Period columns
if overview_option == "Monthly":
    df_plot['Period'] = df_plot['PublishedDate'].dt.to_period('M').apply(lambda r: r.start_time)
    df_unfiltered_plot['Period'] = df_unfiltered_plot['PublishedDate'].dt.to_period('M').apply(lambda r: r.start_time)
    tick_format = '%b-%y'
    filtered_color = MONTHLY_COLOR

elif overview_option == "Weekly":
    df_plot['Period'] = df_plot['PublishedDate'].dt.to_period('W').apply(lambda r: r.start_time)
    df_unfiltered_plot['Period'] = df_unfiltered_plot['PublishedDate'].dt.to_period('W').apply(lambda r: r.start_time)
    tick_format = '%d-%b-%y'
    filtered_color = WEEKLY_COLOR

elif overview_option == "Daily":
    df_plot['Period'] = df_plot['PublishedDate']
    df_unfiltered_plot['Period'] = df_unfiltered_plot['PublishedDate']
    tick_format = '%d-%b-%y'
    filtered_color = DAILY_COLOR

pivot_filtered = df_plot.groupby('Period')['PostCount'].sum().sort_index()
pivot_unfiltered = df_unfiltered_plot.groupby('Period')['PostCount'].sum().sort_index()

fig = go.Figure()

# Filtered posts (main)
fig.add_trace(go.Scatter(
    x=pivot_filtered.index,
    y=pivot_filtered.values,
    mode='lines',
    name='Filtered',
    line=dict(color=filtered_color, width=2),
    marker=dict(size=6)
))

# Unfiltered posts (background/secondary)
fig.add_trace(go.Scatter(
    x=pivot_unfiltered.index,
    y=pivot_unfiltered.values,
    mode='lines',
    name='Unfiltered',
    line=dict(color=UNFILTERED_COLOR, width=1),
    marker=dict(size=4)
))

fig.update_layout(
    title=f"Mention Count Over Time ({overview_option})",
    xaxis_title="Period",
    yaxis_title="Mention Count",
    legend_title="Dataset",
    hovermode='x unified',
    xaxis_tickformat=tick_format
)

st.plotly_chart(fig, use_container_width=True)


st.markdown("""
<div>
    <h5>Summary of the Plot</h5>
</div>
<p >
   This chart shows the number of mentions over time. It helps identify periods of high and low activity. Use this visualization to spot trends, spikes, or patterns in user engagement across the selected date range..
</p>
""", unsafe_allow_html=True)



df_time = df[
        (df['PublishedDate'] >= pd.to_datetime(normalized_start_date)) & 
        (df['PublishedDate'] <= pd.to_datetime(normalized_end_date))
    ]

st.markdown("""
            ##### 📦 How to Interpret a Box Plot
            A **box plot** (also known as a **box-and-whisker plot**) is a compact way to visualize the **distribution, spread, and potential outliers** of a dataset. Here's what each part represents:


            ##### 📏 Key Components

            - **Box (Middle 50%)**:  
            The box spans from the **1st quartile (Q1)** to the **3rd quartile (Q3)**.  
            This range is called the **interquartile range (IQR)** and contains the **middle 50%** of the data.

            - **Line inside the box (Median)**:  
            This is the **median (Q2)** — the value that divides the data in half.  
            If the line is centered, the distribution is symmetric. If it's skewed, the line will lean left or right.

            - **Whiskers**:  
            These extend from the box to show the range of the data that’s **not considered an outlier**.  
            Typically, whiskers reach to the **smallest and largest values within 1.5×IQR** from Q1 and Q3.

            - **Dots (Outliers)**:  
            Points beyond the whiskers are **potential outliers** — unusually high or low values worth investigating.




            ##### 🔍 How to Read One

            - **Shorter box** → lower spread in the middle 50% of values.  
            - **Long whiskers or many outliers** → more variability or unusual data points.  
            - **Shifted median line** → skewed distribution (e.g., right-skewed if the median is closer to the left side of the box).
            ---
            """)

# UI: Radio buttons
view_option = st.radio(
    "Select Time Granularity:",
    options=["Annual", "Monthly", "Weekly"],
    index=0,  # Default is "Annual"
    horizontal=True
)

# Dynamic Period grouping
if view_option == "Annual":
    df_time['Period'] = df_time['PublishedDate'].dt.year
    df_time['MonthShort'] = df_time['PublishedDate'].dt.strftime('%b')  # e.g., Jan, Feb, etc.
    # Fiscal month ordering
    fiscal_months = ['Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 
                     'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb']
    
    df_time['MonthShort'] = pd.Categorical(df_time['MonthShort'], categories=fiscal_months, ordered=True)
    
    
  
    
    group_label = "MonthShort"
    tick_format = None  # No need to format, it's just short month names
    fig = px.box(
        df_time,
        x='MonthShort',
        y='PostCount',
        points="all",
        title="📦 Distribution of Daily Post Counts by Month (Mar–Feb Fiscal Year)",
        labels={'MonthShort': 'Month', 'PostCount': 'Post Count'}
    )

    fig.update_layout(
        height=500,
        xaxis_title="Month",
        yaxis_title="Post Count",
        boxmode='group',
        plot_bgcolor='white',
        yaxis=dict(showgrid=True)
    )

    

    st.plotly_chart(fig, use_container_width=True)
    # 📈 Trend line: Mean Post Count per Fiscal Month
    trend_df = df_time.groupby('MonthShort', observed=True)['PostCount'].mean().reset_index()

    trend_fig = go.Figure()

    trend_fig.add_trace(go.Scatter(
        x=trend_df['MonthShort'],
        y=trend_df['PostCount'],
        mode='lines+markers',
        name='Monthly Mean',
        line=dict(color='green', width=3),
        marker=dict(size=8),
        hovertemplate='Month: %{x}<br>Mean: %{y:.2f}<extra></extra>'
    ))


    st.markdown("""
##### 📊 Why Use Box Plots?


- Quickly compare distributions across categories.
- Spot **outliers**, **skewness**, and **data spread** at a glance.
- Ideal for summarizing large datasets without plotting every point.
                
 <div style='height: 3px; background-color: #4F8BF9; margin-top: 0; margin-bottom: 10px;'></div>               
""", unsafe_allow_html=True)


    
    trend_fig.update_layout(
        title="📈 Trend: Mean Daily Post Count per Month (Fiscal Year)",
        xaxis_title="Month (Mar–Feb Fiscal)",
        yaxis_title="Mean Post Count",
        height=400,
        xaxis=dict(
            categoryorder='array',
            categoryarray=['Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 
                        'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb'],
            showgrid=True
        ),
        yaxis=dict(showgrid=True),
        plot_bgcolor='white'
    )

    

    st.markdown("""
                

##### 📈 Interpreting the Trend Line

The chart above displays a **trend line** showing the **average number of mentions over a year/month/week** across the selected period.


##### 🔍 What the Trend Line Shows

- Each point on the line represents the **mean number of mentions** made on a particular calendar day.
- The line helps smooth out daily fluctuations and highlights the **underlying pattern** in the data.





##### 🔮 Using the Trend Line for Prediction

- The trend line can act as a **baseline for forecasting future behavior**.
- For example, if Wednesdays regularly show high post volume, you can anticipate similar activity on upcoming Wednesdays unless new variables intervene.
- It's especially helpful for planning, resource allocation, or detecting **anomalies** when actual activity diverges significantly from the expected mean.


This makes the trend line a powerful tool not only for **understanding historical patterns**, but also for making **data-informed predictions** going forward.
""")

    st.plotly_chart(trend_fig, use_container_width=True)

    



elif view_option == "Monthly":
    df_time['Period'] = df_time['PublishedDate'].dt.to_period('M').apply(lambda r: r.start_time)
    group_label = "Month"
    tick_format = '%b-%y'
    df_time['CalendarDay'] = df_time['PublishedDate'].dt.day
    # 🔥 Additional calendar day distribution plot
    box_fig = px.box(
        df_time,
        x='CalendarDay',
        y='PostCount',
        points='all',
        title="📦 Distribution of Post Counts by Calendar Day (Monthly View)",
        labels={'CalendarDay': 'Day of Month', 'PostCount': 'Post Count'}
    )

    box_fig.update_layout(
        height=500,
        xaxis=dict(dtick=1, title='Day of Month'),
        yaxis_title="Post Count",
        plot_bgcolor='white',
        yaxis=dict(showgrid=True),
    )

    st.plotly_chart(box_fig, use_container_width=True)
    # 📈 Trend line: Mean Post Count per Calendar Day
    trend_df = df_time.groupby('CalendarDay', observed=True)['PostCount'].mean().reset_index()

    trend_fig = go.Figure()

    trend_fig.add_trace(go.Scatter(
        x=trend_df['CalendarDay'],
        y=trend_df['PostCount'],
        mode='lines+markers',
        name='Calendar Day Mean',
        line=dict(color='green', width=3),
        marker=dict(size=8),
        hovertemplate='Day: %{x}<br>Mean: %{y:.2f}<extra></extra>'
    ))



    trend_fig.update_layout(
        title="📈 Trend: Mean Post Count per Calendar Day",
        xaxis_title="Day of Month",
        yaxis_title="Mean Post Count",
        height=400,
        xaxis=dict(
            dtick=1,
            title='Day of Month',
            showgrid=True
        ),
        yaxis=dict(showgrid=True),
        plot_bgcolor='white'
    )

    st.plotly_chart(trend_fig, use_container_width=True)

elif view_option == "Weekly":
    df_time['Period'] = df_time['PublishedDate'].dt.to_period('W').apply(lambda r: r.start_time)
    group_label = "Week"
    tick_format = '%d-%b-%y'
    # Weekday box plot
    week_order = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    df_time['WeekdayShort'] = df_time['PublishedDate'].dt.strftime('%a')
    df_time['WeekdayShort'] = pd.Categorical(df_time['WeekdayShort'], categories=week_order, ordered=True)

    weekday_box = px.box(
        df_time,
        x='WeekdayShort',
        y='PostCount',
        points='all',
        title="📦 Distribution of Post Counts by Weekday (Sat–Fri Week)",
        labels={'WeekdayShort': 'Day of Week', 'PostCount': 'Post Count'}
    )

    weekday_box.update_layout(
        xaxis=dict(
            categoryorder='array',  # 💥 Manual order!
            categoryarray=week_order,  # 💥 Use your defined week_order
            title='Day of Week'
        ),
        height=500,
        xaxis_title="Day of Week",
        yaxis_title="Post Count",
        boxmode='group',
        plot_bgcolor='white',
        yaxis=dict(showgrid=True),
    )

    st.plotly_chart(weekday_box, use_container_width=True)

    # 📈 Trend line: Mean Post Count per Weekday
    trend_df = df_time.groupby('WeekdayShort', observed=True)['PostCount'].mean().reset_index()

    trend_fig = go.Figure()

    trend_fig.add_trace(go.Scatter(
        x=trend_df['WeekdayShort'],
        y=trend_df['PostCount'],
        mode='lines+markers',
        name='Weekday Mean',
        line=dict(color='green', width=3),
        marker=dict(size=8),
        hovertemplate='Day: %{x}<br>Mean: %{y:.2f}<extra></extra>'
    ))

    trend_fig.update_layout(
        title="📈 Trend: Mean Post Count per Weekday",
        xaxis_title="Day of Week",
        yaxis_title="Mean Post Count",
        height=400,
        xaxis=dict(
            categoryorder='array',
            categoryarray=['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],  # Force Sun–Sat order
            showgrid=True
        ),
        yaxis=dict(showgrid=True),
        plot_bgcolor='white'
    )

    st.plotly_chart(trend_fig, use_container_width=True)

else:
    st.error("Invalid view option selected.")
    st.stop()


st.markdown("""
#### 📊 Why This is Useful

- By focusing on averages, the trend line reduces the impact of short-term spikes or drops, offering a **clearer view of central tendencies**.
- It can help identify:
  - Days with consistently higher or lower activity.
  - Weekly cycles or posting habits.
  - Outlier behavior when compared to the mean.

<div style='height: 3px; background-color: #4F8BF9; margin-top: 10px; margin-bottom: 10px;'></div>
""", unsafe_allow_html=True)



fig_snr = go.Figure()

# ⚡ Important: align data by Period
# Replace 0s in unfiltered counts to avoid division by zero
pivot_unfiltered_safe = pivot_unfiltered.replace(0, 1e-9)

# Calculate Signal-to-Noise Ratio (Filtered / Unfiltered)
snr = pivot_filtered / pivot_unfiltered_safe

# Plot SNR
fig_snr.add_trace(go.Scatter(
    x=snr.index,
    y=snr.values,
    mode='lines',
    name='Signal-to-Noise Ratio',
    line=dict(color='darkgreen', width=2),
    marker=dict(size=6, color='lightgreen'),
    hovertemplate="<b>Period:</b> %{x|%d-%b-%Y}<br><b>SNR:</b> %{y:.2f}<extra></extra>"
))

fig_snr.update_layout(
    title='📈 Signal-to-Noise Ratio Over Time',
    xaxis_title='Period',
    yaxis_title='SNR (Filtered / Unfiltered)',
    height=450,
    plot_bgcolor='white',
    xaxis=dict(showgrid=True, tickformat=tick_format),
    yaxis=dict(showgrid=True, rangemode='tozero'),
    margin=dict(t=60, b=40),
    hovermode='x unified'
)

st.plotly_chart(fig_snr, use_container_width=True)

st.markdown("""
###  Signal-to-Noise Ratio (SNR) Explained
This ratio helps quantify how prominently the filtered signal (e.g., posts meeting specific criteria) stands out against the total volume of activity (unfiltered posts).

High SNR (>1) indicates a stronger presence of relevant or filtered content on that date.

SNR near 1 suggests that filtered and unfiltered posts occur at similar rates.

Low SNR (<1) may point to lower relative signal strength, possibly due to a surge in irrelevant or less targeted posts.

This view can be especially helpful in tracking when certain themes, topics, or classification criteria gain prominence relative to overall discussion volume.
""")

render_telkom_sidebar_logo()
render_telkom_footer()
