import pandas as pd
import streamlit as st

all_data = pd.read_excel('output.xlsx')

# Configure Streamlit for wide layout
st.set_page_config(layout="wide")

# Filter out unplayed weeks (where Games Played has "0/X") and define available weeks
completed_weeks = all_data[all_data['Games Played'].str.split('/').apply(lambda x: int(x[0]) > 0)]
available_weeks = sorted(completed_weeks['Week'].unique())

# Sidebar for filtering options
st.sidebar.header("Filter Options")
selected_week = st.sidebar.selectbox("Select Week", available_weeks, index=0)
selected_managers = st.sidebar.multiselect("Select Managers (optional)", options=all_data['Manager'].unique())

# Filter all_data based on selected week and managers, remove "Week" column for display
filtered_df = all_data[all_data['Week'] == selected_week].drop(columns=['Week'])
if selected_managers:
    filtered_df = filtered_df[filtered_df['Manager'].isin(selected_managers)]

# Convert columns to appropriate data types: integers, floats (3 decimal points), and strings
for col in filtered_df.columns:
    if col in ["FG%", "FT%"]:
        filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce').round(3).apply(lambda x: f"{x:.3f}")
    elif col != "Manager" and col != "Games Played":
        filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce').fillna(0).astype(int)

# Identify numeric columns for conditional formatting
numeric_cols = [col for col in filtered_df.columns if col not in ['Manager', 'Games Played']]

# Conditional formatting function to highlight winning categories
def highlight_winners(df):
    styles = pd.DataFrame('', index=df.index, columns=df.columns)
    for col in numeric_cols:
        if col == 'TO':
            min_idx = df[col].idxmin()
            styles.at[min_idx, col] = 'background-color: lightgreen'
        else:
            max_idx = df[col].idxmax()
            styles.at[max_idx, col] = 'background-color: lightgreen'
    return styles

# Display the filtered DataFrame with conditional formatting, no index
if not filtered_df.empty:
    st.header(f"Comparison for Week {selected_week}")
    st.write("Managers:", ', '.join(selected_managers) if selected_managers else "All Managers")
    st.dataframe(filtered_df.style.apply(lambda _: highlight_winners(filtered_df), axis=None), use_container_width=True)

# Season Averages for Completed Weeks
completed_weeks_df = completed_weeks.drop(columns=['Week'])
season_averages = completed_weeks_df.groupby('Manager').mean(numeric_only=True).round(3).reset_index()  # Round to 3 decimal points

# Calculate Average Games Played (ignoring weeks where games are incomplete)
average_games_played = (
    completed_weeks_df['Games Played']
    .str.split('/')
    .apply(lambda x: int(x[0]))
    .groupby(completed_weeks_df['Manager'])
    .mean()
    .round(1)
    .reset_index(name='Average Games Played')
)
season_averages = season_averages.merge(average_games_played, on="Manager", how="left")

# Ensure all float columns are displayed with 3 decimal points
for col in season_averages.columns:
    if season_averages[col].dtype == 'float64':
        season_averages[col] = season_averages[col].apply(lambda x: f"{x:.3f}")

st.header("Season Averages for Completed Weeks")
st.dataframe(season_averages.style.apply(lambda _: highlight_winners(season_averages), axis=None), use_container_width=True)

# Season Highs and Lows (excluding current week, Week 1 for lows, and Week 16 for highs)
highs_lows_data = all_data[(all_data['Week'] != selected_week) & (all_data['Week'] != 'Week 1') & (all_data['Week'] != 'Week 16')]

# Calculate highs and lows with corresponding managers
highs_lows = pd.DataFrame({
    'Category': numeric_cols,
    'Season High': [highs_lows_data[col].max() for col in numeric_cols],
    'High Manager': [highs_lows_data.loc[highs_lows_data[col].idxmax(), 'Manager'] for col in numeric_cols],
    'Season Low': [highs_lows_data[col].min() for col in numeric_cols],
    'Low Manager': [highs_lows_data.loc[highs_lows_data[col].idxmin(), 'Manager'] for col in numeric_cols]
})

st.header("Season Highs and Lows (Excluding Current Week, Week 1 for Lows, Week 16 for Highs)")
st.dataframe(highs_lows, use_container_width=True)