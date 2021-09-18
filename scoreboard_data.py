import database
import mlb_api
import os
import datetime


class ScoreboardData:
    scoreboard_db = None
    api = None
    db_file = 'MLB-live-scoreboard.db'
    # db_file = ':memory:'
    live_data = None

    table_status = 'status'
    table_game = 'game'
    table_players = 'players'
    table_teams = 'teams'

    def __init__(self):

        # delete old db file
        if os.path.exists(self.db_file):
            os.remove(self.db_file)

        # create new database and API objects
        self.scoreboard_db = database.Database(self.db_file)
        self.api = mlb_api.MLB_API()

        # create database tables and load non-game specific tables
        self.create_scoreboard_db_tables()
        self.load_all_mlb_teams()

    def create_scoreboard_db_tables(self):
        STATS = '''CREATE TABLE status (current_inning INTEGER,
                                       current_inning_half INTEGER,
                                       current_inning_state TEXT,
                                       current_play_idx INTEGER,
                                       home_last_batter_id INTEGER,
                                       away_last_batter_id INTEGER,
                                       game_status TEXT,
                                       last_update TEXT);'''

        GAME = '''CREATE TABLE game (home_team_id TEXT,
                                     home_team_abbrev TEXT,
                                     home_team_name TEXT,
                                     away_team_id TEXT,
                                     away_team_abbrev TEXT,
                                     away_team_name TEXT,
                                     game_pk INTEGER);'''

        PLAYERS = '''CREATE TABLE players (player_name TEXT,
                                           player_number INTEGER,
                                           player_id INTEGER,
                                           player_team_abbrev TEXT,
                                           batting_order INTEGER);'''

        TEAMS = '''CREATE TABLE teams (team_name TEXT,
                                       team_abbrev TEXT,
                                       team_short_name TEXT,
                                       team_id INTEGER);'''

        self.scoreboard_db.db_query(STATS)
        self.scoreboard_db.db_query(GAME)
        self.scoreboard_db.db_query(PLAYERS)
        self.scoreboard_db.db_query(TEAMS)

    def load_all_mlb_teams(self):
        team_data = self.api.fetch_teams_data()

        # load all MLB teams into database
        for team in team_data:
            self.scoreboard_db.db_insert(self.table_teams, {'team_name': team['name'],
                                                            'team_abbrev': team['abbreviation'],
                                                            'team_short_name': team['teamName'],
                                                            'team_id': team['id']})

    def refresh_live_data(self, game_pk):
        current_play = ''
        current_inning = ''
        inning_half = ''
        inning_state = ''
        last_home_batter_id = ''
        last_away_batter_id = ''

        # get new data from MLB
        self.live_data = self.api.fetch_live_feed_data(game_pk)

        # update stats data in database
        game_status = self.live_data['gameData']['status']['detailedState']

        if game_status.upper() not in ['FINAL', 'GAME OVER', 'SCHEDULED', 'WARMUP', 'PRE-GAME', 'POSTPONED']:
            current_play = self.live_data['liveData']['plays']['currentPlay']['atBatIndex']
            current_inning = self.live_data['liveData']['linescore']['currentInning']
            inning_half = self.live_data['liveData']['linescore']['inningHalf']
            inning_state = self.live_data['liveData']['linescore']['inningState']

        # update last batter
        if game_status.upper() in ['IN PROGRESS', 'DELAYED']:
            last_home_batter_id, last_away_batter_id = self.return_last_batter_ids()

        # update current game status
        self.update_status_table({'current_inning': current_inning,
                                  'current_inning_half': inning_half,
                                  'current_inning_state': inning_state,
                                  'current_play_idx': current_play,
                                  'home_last_batter_id' : last_home_batter_id,
                                  'away_last_batter_id': last_away_batter_id,
                                  'game_status': game_status,
                                  'last_update': datetime.datetime.now()})

        return self.live_data

    def load_player_data(self):
        teams_data = self.return_boxscore_data()['teams']

        # load database with player data for this game

        # away players
        away_team = self.return_a_team_name(teams_data['away']['team']['id'])[2]
        for player_id in teams_data['away']['players']:
            id = teams_data['away']['players'][str(player_id)]['person']['id']
            player_name = teams_data['away']['players'][str(player_id)]['person']['fullName']
            player_jersey_no = teams_data['away']['players'][str(player_id)]['jerseyNumber']
            self.scoreboard_db.db_insert('players', {'player_name': player_name,
                                                  'player_number': player_jersey_no,
                                                  'player_id': id,
                                                  'player_team_abbrev': away_team})

        # home players
        home_team = self.return_a_team_name(teams_data['home']['team']['id'])[2]
        for player_id in teams_data['home']['players']:
            id = teams_data['home']['players'][str(player_id)]['person']['id']
            name = teams_data['home']['players'][str(player_id)]['person']['fullName']
            jersey = teams_data['home']['players'][str(player_id)]['jerseyNumber']
            self.scoreboard_db.db_insert('players', {'player_name': name,
                                                     'player_number': jersey,
                                                     'player_id': id,
                                                     'player_team_abbrev': home_team})

    def return_last_batter_ids(self):
        home_batter_id = 0
        away_batter_id = 0

        last_batter_inning = self.return_current_inning() - 1  # 0-based list
        plays_data = self.live_data['liveData']['plays']

        if self.return_current_inning() > 1:

            if len(plays_data['playsByInning'][int(last_batter_inning)]['top']) > 0:
                last_away_batter_play_idx = plays_data['playsByInning'][int(last_batter_inning)]['top'][-1]
            else:
                # drop back to last inning
                last_away_batter_play_idx = plays_data['playsByInning'][int(last_batter_inning) - 1]['top'][-1]
            away_batter_id = plays_data['allPlays'][last_away_batter_play_idx]['matchup']['batter']['id']

            if len(plays_data['playsByInning'][int(last_batter_inning)]['bottom']) > 0:
                last_home_batter_play_idx = plays_data['playsByInning'][int(last_batter_inning)]['bottom'][-1]
            else:
                # drop back to last inning
                last_home_batter_play_idx = plays_data['playsByInning'][int(last_batter_inning) - 1]['bottom'][-1]
            home_batter_id = plays_data['allPlays'][last_home_batter_play_idx]['matchup']['batter']['id']

        return home_batter_id, away_batter_id

    def return_home_team(self):
        sql = 'SELECT t.team_name, g.home_team_name from game g, teams t WHERE g.home_team_id = t.team_id'
        results = self.scoreboard_db.db_query(sql)
        if results is not None and len(results) > 0:
            return results[0][0]
        else:
            return 'UNK'

    def return_away_team(self):
        sql = 'SELECT t.team_name, g.away_team_name from game g, teams t WHERE g.away_team_id = t.team_id'
        results = self.scoreboard_db.db_query(sql)
        if results is not None and len(results) > 0:
            return results[0][0]
        else:
            return 'UNK'

    def return_team_id(self, team):
        sql = 'SELECT team_id FROM teams WHERE team_abbrev=\'{}\' or team_name=\'{}\' or ' \
              'team_short_name=\'{}\' or team_id=\'{}\''.format(team, team, team, team)

        results = self.scoreboard_db.db_query(sql)
        if results is not None and len(results[0]) > 0:
            return results[0][0]
        else:
            return ''

    def return_team_abbrevs(self):
        sql = 'SELECT team_abbrev FROM teams ORDER BY team_abbrev'
        results = self.scoreboard_db.db_query(sql)
        if results is not None and len(results[0]) > 0:
            return results
        else:
            return []

    def return_a_team_name(self, key):
        sql = 'SELECT team_name, team_short_name, team_abbrev FROM teams WHERE ' \
              'team_name = \'{}\' OR team_short_name = \'{}\' OR team_abbrev = \'{}\' OR team_id = {}' \
              .format(key, key, key, key)
        results = self.scoreboard_db.db_query(sql)
        if results is not None and len(results[0]) > 0:
            return results[0]
        else:
            return []

    def validate_team_name(self, team):
        sql = 'SELECT COUNT(team_abbrev) FROM teams WHERE team_abbrev=\'{}\' or team_name=\'{}\' or ' \
              'team_short_name=\'{}\' or team_id=\'{}\''.format(team, team, team, team)
        results = self.scoreboard_db.db_query(sql)
        if results is not None and len(results[0]) > 0:
            if results[0][0] == 1:
                return True
        else:
            return False

    def update_game_table(self, items):
        self.scoreboard_db.db_delete('game')
        self.scoreboard_db.db_insert('game', items)

    def update_status_table(self, items):
        self.scoreboard_db.db_delete('status')
        self.scoreboard_db.db_insert('status', items)

    # def set_batting_order(self):
    #     boxscore = self.get_boxscore_data()
    #     home_batting_order = boxscore['teams']['home']['battingOrder']
    #     for player_id in home_batting_order:
    #         self.scoreboard_db.db_update('players', 'batting_order={}'.format(home_batting_order.index(player_id) + 1),
    #                                      'player_id={}'.format(player_id))
    #     away_batting_order = boxscore['teams']['away']['battingOrder']
    #     for player_id in away_batting_order:
    #         self.scoreboard_db.db_update('players', 'batting_order={}'.format(away_batting_order.index(player_id) + 1),
    #                                      'player_id={}'.format(player_id))

    # def update_batting_order(self, player_id, player_replaced_id):
    #     self.scoreboard_db.db_update(self.table_players, 'player_id={}'.format(player_id), 'player_id={}'.format(player_replaced_id))

    def return_current_inning_data(self):
        return [self.live_data['liveData']['linescore']['currentInning'],
                str(self.live_data['liveData']['linescore']['inningHalf']).lower(),
                str(self.live_data['liveData']['linescore']['inningState']).lower()]

    def return_current_inning_half(self):
        inning_data = self.return_current_inning_data()
        return inning_data[1]

    def return_current_inning(self):
        inning_data = self.return_current_inning_data()
        return inning_data[0]

    def return_current_inning_state(self):
        inning_data = self.return_current_inning_data()
        return inning_data[2]

    def return_current_play_index(self):
        sql = 'SELECT current_play_idx FROM status'
        results = self.scoreboard_db.db_query(sql)
        if results is not None and len(results[0]) > 0:
            return results[0][0]
        else:
            return 0

    def return_game_status(self):
        sql = 'SELECT game_status FROM status'
        results = self.scoreboard_db.db_query(sql)
        if results is not None and len(results[0]) > 0:
            return results[0][0]
        else:
            return 'UNK'

    def return_last_play_data(self):
        play_idx = self.return_current_play_index() - 1
        data = self.return_a_play_data(play_idx)
        return data

    def return_a_play_data(self, play_idx):
        data = self.live_data['liveData']['plays']['allPlays'][int(play_idx)]
        return data

    def return_current_play_data(self):
        data = self.live_data['liveData']['plays']['currentPlay']
        return data

    def return_linescore_data(self):
        data = self.live_data['liveData']['linescore']
        return data

    def return_boxscore_data(self):
        data = self.live_data['liveData']['boxscore']
        return data

    def load_game_data(self, game_pk):

        # load data for this game into database

        # load player data
        self.load_player_data()

        # get home and away team ids
        teams_data = self.return_boxscore_data()['teams']
        home_team_id = teams_data['home']['team']['id']
        away_team_id = teams_data['away']['team']['id']

        # write game data to database
        self.update_game_table({'home_team_id': home_team_id,
                                'away_team_id': away_team_id,
                                'home_team_abbrev': self.return_a_team_name(home_team_id)[2],
                                'away_team_abbrev': self.return_a_team_name(away_team_id)[2],
                                'home_team_name': self.return_a_team_name(home_team_id)[0],
                                'away_team_name': self.return_a_team_name(away_team_id)[0],
                                'game_pk': game_pk})

