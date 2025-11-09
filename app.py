import pandas as pd
import streamlit as st
import plotly.express as px

# Load data
all_data = pd.read_excel('output.xlsx')

# Configure Streamlit for wide layout
st.set_page_config(layout="wide")

# Filter out unplayed weeks (where Games Played has "0/X") and define available weeks
completed_weeks = all_data[all_data['Games Played'].str.split('/').apply(lambda x: int(x[0]) > 0)]
available_weeks = sorted(completed_weeks['Week'].unique())

# Set current week as the latest available completed or in-progress week
current_week = available_weeks[-1] if available_weeks else None  # Independent of selected_week filter

# Display Filters at the Top
st.subheader("Filter Options")
selected_week = st.selectbox("Select Week", available_weeks, index=available_weeks.index(current_week) if current_week else 0)
selected_managers = st.multiselect("Select Managers (optional)", options=all_data['Manager'].unique())

# Filter all_data based on selected week and managers, remove "Week" column for display
filtered_df = all_data[all_data['Week'] == selected_week].drop(columns=['Week']).copy()
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
# Conditional formatting function to highlight winning categories
def highlight_winners(df):
    # Create a copy of the DataFrame and convert to numeric
    numeric_df = df.copy()

    # Convert columns to numeric, handling potential string representations
    for col in numeric_df.columns:
        if col not in ['Manager', 'Games Played']:
            numeric_df[col] = pd.to_numeric(numeric_df[col], errors='coerce')
    
    # Create styles DataFrame
    styles = pd.DataFrame('', index=df.index, columns=df.columns)
    
    for idx in numeric_df.index:
        if idx == 'TO':  # Special case for turnovers, highlight the minimum value
            min_col = numeric_df.loc[idx].idxmin()
            styles.at[idx, min_col] = 'background-color: green'
        elif idx == 'Manager' or idx == 'Games Played':  # Ignore manager name and games played
            continue 
        else:
            max_col = numeric_df.loc[idx].idxmax()
            styles.at[idx, max_col] = 'background-color: green'
    
    return styles


# Display the filtered DataFrame with conditional formatting, no index, and optimized for mobile
view_type1 = st.radio("View Type",['Weekly Stats', 'Weekly Rank'])

if view_type1 == 'Weekly Stats':
    if not filtered_df.empty:
        #Transpose rows and columns
        filtered_df = filtered_df.transpose().copy()
        filtered_df.columns = filtered_df.iloc[0].reset_index(drop=True)
        filtered_df = filtered_df.drop(filtered_df.index[0]).astype(str)

        st.subheader(f"Comparison for Week {selected_week}")
        st.write("Managers:", ', '.join(selected_managers) if selected_managers else "All Managers")
        st.dataframe(filtered_df.style.apply(lambda _: highlight_winners(filtered_df), axis=None), use_container_width=False, hide_index=False)


# Add a new condition for the ranking view
else:
    # Prepare data for ranking using ALL data for the selected week
    all_week_data = all_data[all_data['Week'] == selected_week].copy()
    all_week_data = all_week_data.drop(columns='Week').copy()
    
    # Numeric columns to rank (excluding 'Manager' and 'Games Played')
    rank_columns = [col for col in all_week_data.columns if col not in ['Manager', 'Games Played']]
    
    # Convert to numeric for proper ranking
    for col in rank_columns:
        all_week_data[col] = pd.to_numeric(all_week_data[col], errors='coerce')
    
    # Calculate dense rankings for each statistic
    rankings = {}
    for col in rank_columns:
        # Sort in descending order for most stats (except TO where lower is better)
        ascending = True if col == 'TO' else False
        
        # Calculate dense rank
        col_ranks = all_week_data.sort_values(by=col, ascending=ascending).reset_index()
        col_ranks['Rank'] = col_ranks[col].rank(method='dense', ascending=ascending)
        
        # Store rankings in a dictionary
        rankings[col] = col_ranks.set_index('Manager')['Rank']
    
    # Combine rankings into a single DataFrame
    ranking_df = pd.DataFrame(rankings)
    
    # Display ranking view
    st.subheader(f"Weekly Rankings for Week {selected_week}")
    
    # Filter DataFrame for selected managers if any
    display_df = ranking_df.loc[selected_managers] if selected_managers else ranking_df
    
    # Display the ranking DataFrame
    st.dataframe(display_df, use_container_width=True)

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
    .reset_index(name='AVG GP')
)

season_averages = season_averages.merge(average_games_played, on="Manager", how="left")

# Ensure all float columns are displayed with 3 decimal points
# Define a mapping of decimal precision for each group of columns
columns_by_decimals = {
    3: ['FG%', 'FT%'],
    1: ['3PM', 'STL', 'BLK', 'TO', 'AVG GP'],         
    0: ['PTS', 'REB', 'AST']
}

# Apply formatting dynamically based on the mapping
for decimals, columns in columns_by_decimals.items():
    for col in columns:
        if col in season_averages.columns:
            season_averages[col] = season_averages[col].apply(lambda x: f"{x:.{decimals}f}")




# After creating season_averages DataFrame
st.subheader("Season Averages")
st.markdown("<small>Completed Weeks Only</small>", unsafe_allow_html=True)

# Create a toggle for view type
view_type2 = st.radio("View Type", ["Overall Averages", "Average Comparison"])

season_averages = season_averages.transpose().copy()
season_averages.columns = season_averages.iloc[0].reset_index(drop=True)
season_averages = season_averages.drop(season_averages.index[0]).astype(str)


if view_type2 == "Average Comparison":
    # Scatter Plot View
    # First, reset index and convert to regular DataFrame
    plot_df = season_averages.reset_index()
    
    # Stat selection for scatter plot
    stat_categories = ['FG%', 'FT%', '3PM', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'AVG GP']
    
    # Select stat for scatter plot
    selected_stat = st.selectbox("Select Stat Category", stat_categories)
    
    # Prepare data for plotting
    plot_data = []
    
    # Iterate through managers (assuming they start from the third column)
    for manager in plot_df.columns[1:]:
        stat_value = plot_df.loc[plot_df['index'] == selected_stat, manager].values[0]
    
        # Convert to float, handling potential string representations
        stat_value = float(stat_value)
        plot_data.append({'Manager': manager, 'Value': stat_value})

    plot_df_scatter = pd.DataFrame(plot_data)
    plot_df_scatter = plot_df_scatter.sort_values('Value', ascending=False).reset_index(drop=True)
    plot_df_scatter['Rank'] = plot_df_scatter.index + 1

    # Create scatter plot using Plotly
    fig = px.scatter(plot_df_scatter, x='Manager', y='Value', 
                    title=f'Average {selected_stat} by Manager',
                    hover_data=['Rank'],  # This adds rank to hover information
                    labels={'Value': selected_stat})

    # Customize the plot
    fig.update_traces(marker=dict(size=10, color='green', symbol='circle'))
    fig.update_layout(
    xaxis_title='Manager',
    yaxis_title=f'Average {selected_stat}',
    height=500,
    # Disable zooming and panning
    xaxis=dict(fixedrange=True),
    yaxis=dict(fixedrange=True),
    # Prevent touch interactions from zooming
    dragmode=False)

    # Ensure hover is still enabled
    fig.update_traces(hovertemplate='<b>%{x}</b><br>Value: %{y:.2f}<extra></extra>')
    
    st.plotly_chart(fig, use_container_width=True)

else:
    st.dataframe(season_averages.style.apply(lambda _: highlight_winners(season_averages), axis=None), 
                column_config={column: st.column_config.TextColumn(width="small") for column in season_averages.columns}, 
                use_container_width=True)

# Season Highs and Lows (excluding current week, Week 1 for lows, Week 7 (NBA Cup) and Week 16 for highs)
# Ensure season highs and lows are calculated independently of current filters
highs_lows_data = all_data[~(all_data['Week'].isin([current_week, 1, 7, 16]))].copy()

integer_categories = ['3PM', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TO']

# Safely compute highs and lows
records = []
for col in numeric_cols:
    # Skip if column missing or all NaN
    if col not in highs_lows_data.columns or highs_lows_data[col].dropna().empty:
        continue

    max_idx = highs_lows_data[col].idxmax()
    min_idx = highs_lows_data[col].idxmin()

    # Skip if idxmax/idxmin return NaN
    if pd.isna(max_idx) or pd.isna(min_idx):
        continue

    # Build strings
    max_val = int(highs_lows_data.loc[max_idx, col]) if col in integer_categories else round(highs_lows_data.loc[max_idx, col], 3)
    min_val = int(highs_lows_data.loc[min_idx, col]) if col in integer_categories else round(highs_lows_data.loc[min_idx, col], 3)

    max_str = f"{max_val} - {highs_lows_data.loc[max_idx, 'Manager']} - Week {highs_lows_data.loc[max_idx, 'Week']}"
    min_str = f"{min_val} - {highs_lows_data.loc[min_idx, 'Manager']} - Week {highs_lows_data.loc[min_idx, 'Week']}"

    records.append({'Category': col, 'Season High': max_str, 'Season Low': min_str})

# Create DataFrame
highs_lows = pd.DataFrame(records)

st.subheader("Season Highs and Lows")
st.markdown("<small>Excluding Current Week, Week 1, Week 7 (NBA Cup), Week 16 (All-Star)</small>", unsafe_allow_html=True)
st.dataframe(highs_lows, use_container_width=True, hide_index=True)
