# %%
import pandas as pd
import yahoo_fantasy_api as yfa
from yahoo_oauth import OAuth2
import os

# %%
#Auth
sc = OAuth2(
    None,
    None,
    from_file=None,
    CONSUMER_KEY=os.getenv("CONSUMER_KEY"),
    CONSUMER_SECRET=os.getenv("CONSUMER_SECRET"),
    REFRESH_TOKEN=os.getenv("REFRESH_TOKEN")
)

# %%
#Get Game object
gm = yfa.Game(sc, 'nba')

# %%
leagues = gm.league_ids()
league = gm.to_league(leagues[-1])

# %%
#Dict of categories
categories = {
    "5": "FG%",
    "8": "FT%",
    "10": "3PM",
    "12": "PTS",
    "15": "REB",
    "16": "AST",
    "17": "STL",
    "18": "BLK",
    "19": "TO"
}

# %%
all_weeks_data = []

# Loop over each week to gather data
for week in range(1, 24):  # Weeks 1 to 23
    # Fetch matchups data for the specific week
    data = league.matchups(week=week)['fantasy_content']['league'][1]['scoreboard']['0']['matchups']
    
    # Iterate over each matchup and team to extract stats
    for matchup_id, matchup_data in data.items():
        # Check that matchup_data is a dictionary
        if not isinstance(matchup_data, dict):
            continue  # Skip non-dictionary entries

        matchup = matchup_data.get('matchup')
        if not matchup:
            continue

        # Go through each team in the matchup, ensure '0' key exists and is a dictionary
        teams = matchup.get('0', {}).get('teams', {})
        if not isinstance(teams, dict):
            continue

        for team_key, team_data in teams.items():
            # Check that team_data is a dictionary and has the expected structure
            if not isinstance(team_data, dict) or 'team' not in team_data:
                continue
            if not isinstance(team_data['team'], list) or len(team_data['team']) < 2:
                continue

            team = team_data['team'][0]  # Access the team list
            team_name = team[2]['name']  # Extract team name

            # Initialize the row with the team name and the week
            team_row = {'Manager': team_name, 'Week': f"{week}"}

            # Fetch team stats for the week
            stats = team_data['team'][1].get('team_stats', {}).get('stats', [])
            
            # Extract relevant stats by stat_id
            for stat in stats:
                stat_id = stat['stat']['stat_id']
                if stat_id in categories:
                    stat_name = categories[stat_id]
                    team_row[stat_name] = stat['stat']['value']

            # Get the games played and remaining games
            games_info = team_data['team'][1].get('team_remaining_games', {}).get('total', {})
            games_played = games_info.get('completed_games', 0)
            remaining_games = games_info.get('remaining_games', 0)
            
            # Calculate total games and format as "games played / total games"
            total_games = games_played + remaining_games
            team_row['Games Played'] = f"{games_played}/{total_games}"

            # Add team row to the list for all weeks
            all_weeks_data.append(team_row)

# Convert the list of all weeks data to a single DataFrame
all_data = pd.DataFrame(all_weeks_data)

# %%
all_data

# %%
all_data.to_excel('output.xlsx',index=False)


