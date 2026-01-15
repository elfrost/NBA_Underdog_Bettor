"""Team name matching utilities for cross-API compatibility."""

# Mapping of team identifiers to normalized names
# Keys: various forms (city, nickname, abbreviation)
# Value: normalized team name used by The Odds API
TEAM_MAPPING = {
    # Atlanta Hawks
    "atlanta": "Atlanta Hawks",
    "hawks": "Atlanta Hawks",
    "atl": "Atlanta Hawks",
    "atlanta hawks": "Atlanta Hawks",
    # Boston Celtics
    "boston": "Boston Celtics",
    "celtics": "Boston Celtics",
    "bos": "Boston Celtics",
    "boston celtics": "Boston Celtics",
    # Brooklyn Nets
    "brooklyn": "Brooklyn Nets",
    "nets": "Brooklyn Nets",
    "bkn": "Brooklyn Nets",
    "brooklyn nets": "Brooklyn Nets",
    # Charlotte Hornets
    "charlotte": "Charlotte Hornets",
    "hornets": "Charlotte Hornets",
    "cha": "Charlotte Hornets",
    "charlotte hornets": "Charlotte Hornets",
    # Chicago Bulls
    "chicago": "Chicago Bulls",
    "bulls": "Chicago Bulls",
    "chi": "Chicago Bulls",
    "chicago bulls": "Chicago Bulls",
    # Cleveland Cavaliers
    "cleveland": "Cleveland Cavaliers",
    "cavaliers": "Cleveland Cavaliers",
    "cavs": "Cleveland Cavaliers",
    "cle": "Cleveland Cavaliers",
    "cleveland cavaliers": "Cleveland Cavaliers",
    # Dallas Mavericks
    "dallas": "Dallas Mavericks",
    "mavericks": "Dallas Mavericks",
    "mavs": "Dallas Mavericks",
    "dal": "Dallas Mavericks",
    "dallas mavericks": "Dallas Mavericks",
    # Denver Nuggets
    "denver": "Denver Nuggets",
    "nuggets": "Denver Nuggets",
    "den": "Denver Nuggets",
    "denver nuggets": "Denver Nuggets",
    # Detroit Pistons
    "detroit": "Detroit Pistons",
    "pistons": "Detroit Pistons",
    "det": "Detroit Pistons",
    "detroit pistons": "Detroit Pistons",
    # Golden State Warriors
    "golden state": "Golden State Warriors",
    "warriors": "Golden State Warriors",
    "gsw": "Golden State Warriors",
    "gs": "Golden State Warriors",
    "golden state warriors": "Golden State Warriors",
    # Houston Rockets
    "houston": "Houston Rockets",
    "rockets": "Houston Rockets",
    "hou": "Houston Rockets",
    "houston rockets": "Houston Rockets",
    # Indiana Pacers
    "indiana": "Indiana Pacers",
    "pacers": "Indiana Pacers",
    "ind": "Indiana Pacers",
    "indiana pacers": "Indiana Pacers",
    # Los Angeles Clippers
    "la clippers": "Los Angeles Clippers",
    "clippers": "Los Angeles Clippers",
    "lac": "Los Angeles Clippers",
    "los angeles clippers": "Los Angeles Clippers",
    # Los Angeles Lakers
    "la lakers": "Los Angeles Lakers",
    "lakers": "Los Angeles Lakers",
    "lal": "Los Angeles Lakers",
    "los angeles lakers": "Los Angeles Lakers",
    # Memphis Grizzlies
    "memphis": "Memphis Grizzlies",
    "grizzlies": "Memphis Grizzlies",
    "mem": "Memphis Grizzlies",
    "memphis grizzlies": "Memphis Grizzlies",
    # Miami Heat
    "miami": "Miami Heat",
    "heat": "Miami Heat",
    "mia": "Miami Heat",
    "miami heat": "Miami Heat",
    # Milwaukee Bucks
    "milwaukee": "Milwaukee Bucks",
    "bucks": "Milwaukee Bucks",
    "mil": "Milwaukee Bucks",
    "milwaukee bucks": "Milwaukee Bucks",
    # Minnesota Timberwolves
    "minnesota": "Minnesota Timberwolves",
    "timberwolves": "Minnesota Timberwolves",
    "wolves": "Minnesota Timberwolves",
    "min": "Minnesota Timberwolves",
    "minnesota timberwolves": "Minnesota Timberwolves",
    # New Orleans Pelicans
    "new orleans": "New Orleans Pelicans",
    "pelicans": "New Orleans Pelicans",
    "nop": "New Orleans Pelicans",
    "no": "New Orleans Pelicans",
    "new orleans pelicans": "New Orleans Pelicans",
    # New York Knicks
    "new york": "New York Knicks",
    "knicks": "New York Knicks",
    "nyk": "New York Knicks",
    "ny": "New York Knicks",
    "new york knicks": "New York Knicks",
    # Oklahoma City Thunder
    "oklahoma city": "Oklahoma City Thunder",
    "thunder": "Oklahoma City Thunder",
    "okc": "Oklahoma City Thunder",
    "oklahoma city thunder": "Oklahoma City Thunder",
    # Orlando Magic
    "orlando": "Orlando Magic",
    "magic": "Orlando Magic",
    "orl": "Orlando Magic",
    "orlando magic": "Orlando Magic",
    # Philadelphia 76ers
    "philadelphia": "Philadelphia 76ers",
    "76ers": "Philadelphia 76ers",
    "sixers": "Philadelphia 76ers",
    "phi": "Philadelphia 76ers",
    "philadelphia 76ers": "Philadelphia 76ers",
    # Phoenix Suns
    "phoenix": "Phoenix Suns",
    "suns": "Phoenix Suns",
    "phx": "Phoenix Suns",
    "phoenix suns": "Phoenix Suns",
    # Portland Trail Blazers
    "portland": "Portland Trail Blazers",
    "trail blazers": "Portland Trail Blazers",
    "blazers": "Portland Trail Blazers",
    "por": "Portland Trail Blazers",
    "portland trail blazers": "Portland Trail Blazers",
    # Sacramento Kings
    "sacramento": "Sacramento Kings",
    "kings": "Sacramento Kings",
    "sac": "Sacramento Kings",
    "sacramento kings": "Sacramento Kings",
    # San Antonio Spurs
    "san antonio": "San Antonio Spurs",
    "spurs": "San Antonio Spurs",
    "sas": "San Antonio Spurs",
    "sa": "San Antonio Spurs",
    "san antonio spurs": "San Antonio Spurs",
    # Toronto Raptors
    "toronto": "Toronto Raptors",
    "raptors": "Toronto Raptors",
    "tor": "Toronto Raptors",
    "toronto raptors": "Toronto Raptors",
    # Utah Jazz
    "utah": "Utah Jazz",
    "jazz": "Utah Jazz",
    "uta": "Utah Jazz",
    "utah jazz": "Utah Jazz",
    # Washington Wizards
    "washington": "Washington Wizards",
    "wizards": "Washington Wizards",
    "was": "Washington Wizards",
    "washington wizards": "Washington Wizards",
}


def normalize_team_name(name: str) -> str:
    """Normalize a team name to standard format."""
    return TEAM_MAPPING.get(name.lower().strip(), name)


def teams_match(team1: str, team2: str) -> bool:
    """Check if two team names refer to the same team."""
    norm1 = normalize_team_name(team1)
    norm2 = normalize_team_name(team2)
    return norm1.lower() == norm2.lower()


def find_odds_for_game(game, odds_data: list[dict]) -> dict | None:
    """Find matching odds data for a game using normalized team names."""
    home_normalized = normalize_team_name(game.home_team.name)
    away_normalized = normalize_team_name(game.away_team.name)

    for odds in odds_data:
        odds_home = odds.get("home_team", "")
        odds_away = odds.get("away_team", "")

        # Check if both teams match
        home_match = teams_match(home_normalized, odds_home)
        away_match = teams_match(away_normalized, odds_away)

        if home_match and away_match:
            return odds

    return None
