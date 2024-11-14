import pandas as pd
import yahoo_fantasy_api as yfa
from yahoo_oauth import OAuth2
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.disabled = True

def get_oauth():
    """Initialize OAuth2 using credentials from environment variables."""
    try:
        # Log environment variable presence (without revealing values)
        logger.info("Checking for environment variables...")
        env_vars = {
            'YAHOO_CLIENT_ID': os.getenv('YAHOO_CLIENT_ID'),
            'YAHOO_CLIENT_SECRET': os.getenv('YAHOO_CLIENT_SECRET'),
            'YAHOO_REFRESH_TOKEN': os.getenv('YAHOO_REFRESH_TOKEN')
        }
        
        missing_vars = [key for key, value in env_vars.items() if not value]
        if missing_vars:
            raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")

        # Initialize OAuth2 with the correct mapping of environment variables
        sc = OAuth2(
            None,
            None,
            from_file=None,
            CONSUMER_KEY=env_vars['YAHOO_CLIENT_ID'],        # Map to CONSUMER_KEY
            CONSUMER_SECRET=env_vars['YAHOO_CLIENT_SECRET'], # Map to CONSUMER_SECRET
            REFRESH_TOKEN=env_vars['YAHOO_REFRESH_TOKEN']    # This one matches already
        )

        # Verify token validity
        if not sc.token_is_valid():
            logger.info("Token invalid, attempting refresh...")
            sc.refresh_access_token()
            
        logger.info("OAuth authentication successful")
        return sc

    except Exception as e:
        logger.error(f"OAuth initialization failed: {str(e)}")
        raise


def main():
    # Categories dictionary remains the same
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
    
    try:
        # Initialize OAuth
        sc = get_oauth()
        
        # Get Game object
        gm = yfa.Game(sc, 'nba')
        leagues = gm.league_ids()
        league = gm.to_league(leagues[-1])
        
        all_weeks_data = []
        
        # Rest of your data collection code remains the same
        for week in range(1, 24):
            data = league.matchups(week=week)['fantasy_content']['league'][1]['scoreboard']['0']['matchups']
            
            for matchup_id, matchup_data in data.items():
                if not isinstance(matchup_data, dict):
                    continue
                    
                matchup = matchup_data.get('matchup')
                if not matchup:
                    continue
                    
                teams = matchup.get('0', {}).get('teams', {})
                if not isinstance(teams, dict):
                    continue
                    
                for team_key, team_data in teams.items():
                    if not isinstance(team_data, dict) or 'team' not in team_data:
                        continue
                    if not isinstance(team_data['team'], list) or len(team_data['team']) < 2:
                        continue
                        
                    team = team_data['team'][0]
                    team_name = team[2]['name']
                    
                    team_row = {'Manager': team_name, 'Week': f"{week}"}
                    
                    stats = team_data['team'][1].get('team_stats', {}).get('stats', [])
                    
                    for stat in stats:
                        stat_id = stat['stat']['stat_id']
                        if stat_id in categories:
                            stat_name = categories[stat_id]
                            team_row[stat_name] = stat['stat']['value']
                            
                    games_info = team_data['team'][1].get('team_remaining_games', {}).get('total', {})
                    games_played = games_info.get('completed_games', 0)
                    remaining_games = games_info.get('remaining_games', 0)
                    
                    total_games = games_played + remaining_games
                    team_row['Games Played'] = f"{games_played}/{total_games}"
                    
                    all_weeks_data.append(team_row)
                    
        # Convert to DataFrame and save
        all_data = pd.DataFrame(all_weeks_data)
        all_data.to_excel('output.xlsx', index=False)
        
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()