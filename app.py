import pandas as pd
import streamlit as st
from datetime import datetime

# Configure Streamlit for wide layout
st.set_page_config(layout="wide")

@st.cache_data(ttl="1h")
def load_data():
    """Load and cache the data with error handling"""
    try:
        return pd.read_excel('output.xlsx')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def process_data(all_data):
    """Process the loaded data and return filtered weeks"""
    # Filter out unplayed weeks (where Games Played has "0/X")
    completed_weeks = all_data[all_data['Games Played'].str.split('/').apply(lambda x: int(x[0]) > 0)]
    available_weeks = sorted(completed_weeks['Week'].unique())
    current_week = available_weeks[-1] if available_weeks else None
    return completed_weeks, available_weeks, current_week

def highlight_winners(df):
    """Conditional formatting function to highlight winning categories"""
    numeric_cols = [col for col in df.columns if col not in ['Manager', 'Games Played']]
    styles = pd.DataFrame('', index=df.index, columns=df.columns)
    for col in numeric_cols:
        if col == 'TO':
            min_idx = df[col].idxmin()
            styles.at[min_idx, col] = 'background-color: lightgreen'
        else:
            max_idx = df[col].idxmax()
            styles.at[max_idx, col] = 'background-color: lightgreen'
    return styles

def main():
    # Load data
    all_data = load_data()
    
    if all_data is None:
        st.error("Unable to load data. Please try again later.")
        return
        
    # Add last update timestamp
    st.sidebar.info(f"Data last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Process data
    completed_weeks, available_weeks, current_week = process_data(all_data)
    
    # Display Filters at the Top
    st.subheader("Filter Options")
    selected_week = st.selectbox(
        "Select Week", 
        available_weeks, 
        index=available_weeks.index(current_week) if current_week else 0
    )
    selected_managers = st.multiselect(
        "Select Managers (optional)", 
        options=all_data['Manager'].unique()
    )

    # Filter data based on selections
    filtered_df = all_data[all_data['Week'] == selected_week].drop(columns=['Week'])
    if selected_managers:
        filtered_df = filtered_df[filtered_df['Manager'].isin(selected_managers)]

    # Convert columns to appropriate data types
    for col in filtered_df.columns:
        if col in ["FG%", "FT%"]:
            filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce').round(3).apply(lambda x: f"{x:.3f}")
        elif col != "Manager" and col != "Games Played":
            filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce').fillna(0).astype(int)

    # Display weekly comparison
    if not filtered_df.empty:
        st.subheader(f"Comparison for Week {selected_week}")
        st.write("Managers:", ', '.join(selected_managers) if selected_managers else "All Managers")
        st.dataframe(
            filtered_df.style.apply(lambda _: highlight_winners(filtered_df), axis=None),
            use_container_width=True,
            hide_index=True
        )

    # Calculate and display season averages
    completed_weeks_df = completed_weeks.drop(columns=['Week'])
    season_averages = completed_weeks_df.groupby('Manager').mean(numeric_only=True).round(3).reset_index()

    # Calculate Average Games Played
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

    # Format float columns
    for col in season_averages.columns:
        if season_averages[col].dtype == 'float64':
            season_averages[col] = season_averages[col].apply(lambda x: f"{x:.3f}")

    st.subheader("Season Averages")
    st.markdown("<small>Completed Weeks Only</small>", unsafe_allow_html=True)
    st.dataframe(
        season_averages.style.apply(lambda _: highlight_winners(season_averages), axis=None),
        use_container_width=True,
        hide_index=True
    )

    # Calculate and display season highs and lows
    numeric_cols = [col for col in filtered_df.columns if col not in ['Manager', 'Games Played']]
    highs_lows_data = all_data[
        (all_data['Week'] != current_week) & 
        (all_data['Week'] != '1') & 
        (all_data['Week'] != '16')
    ]
    
    integer_categories = ['3PM', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TO']
    
    highs_lows = pd.DataFrame({
        'Category': numeric_cols,
        'Season High': [
            f"{int(highs_lows_data[col].max()) if col in integer_categories else f'{highs_lows_data[col].max():.3f}'} - {highs_lows_data.loc[highs_lows_data[col].idxmax(), 'Manager']} - Week {highs_lows_data.loc[highs_lows_data[col].idxmax(), 'Week']}" 
            for col in numeric_cols
        ],
        'Season Low': [
            f"{int(highs_lows_data[col].min()) if col in integer_categories else f'{highs_lows_data[col].min():.3f}'} - {highs_lows_data.loc[highs_lows_data[col].idxmin(), 'Manager']} - Week {highs_lows_data.loc[highs_lows_data[col].idxmin(), 'Week']}"
            for col in numeric_cols
        ]
    })

    st.subheader("Season Highs and Lows")
    st.markdown("<small>Excluding Current Week, Week 1, Week 16 (All-Star)</small>", unsafe_allow_html=True)
    st.dataframe(highs_lows, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()