import requests
import sys


class MLB_API:

    API_BASE_URL = "http://statsapi.mlb.com/api"
    API_BOXSCORE_URL = API_BASE_URL + "/v1/game/{}/boxscore"
    API_LINESCORE_URL = API_BASE_URL + "/v1/game/{}/linescore"
    API_PLAYBYPLAY_URL = API_BASE_URL + "/v1/game/{}/playByPlay"
    API_LIVEFEED_URL = API_BASE_URL + "/v1.1/game/{}/feed/live"
    API_TEAMS_URL = API_BASE_URL + "/v1/teams?sportId=1&activeStatus=ACTIVE"
    API_SCHEDULE_URL = API_BASE_URL + "/v1/schedule?sportId=1&date={}"
    API_SCHEDULE_GAMEPK_URL = API_BASE_URL + "/v1/schedule?sportId=1&gamePk={}"
    API_PERSON_CURRENT_STATS_URL = API_BASE_URL + "/v1/people/{}/stats/game/current"

    #def __init__(self):


    def get_data(self, url):
        try:
            results = requests.get(url).json()
        except Exception as err:
            sys.exit('An unhandled exception occurred retrieving data from MLB.\n{}'.format(err))
        return results

    def get_team_data(self):
        # only retrieve certain fields
        fields = '&fields=teams,0,id,name,abbreviation,teamName'
        team_data = self.get_data(self.API_TEAMS_URL + fields)['teams']
        return team_data

    def get_schedule_data(self, game_date):
        # only retrieve certain fields
        #fields = '&fields=dates,games,gamePk,teams,team,name,id,doubleHeader'
        fields = ''
        schedule_data = self.get_data(self.API_SCHEDULE_URL.format(game_date) + fields)
        return schedule_data

    # def get_player_data(self, game_pk):
    #     # only retrieve certain fields
    #     fields = '?fields=teams,away,home,players,fullName,id,jerseyNumber'
    #     player_data = self.get_data(self.API_BOXSCORE_URL.format(game_pk) + fields)
    #     return player_data

    def get_home_away_team_id(self, game_pk):
        # only retrieve certain fields
        fields = '?fields=teams,home,away,team,id'
        team_id = self.get_data(self.API_BOXSCORE_URL.format(game_pk) + fields)
        return team_id

    def get_live_feed(self, game_pk):
        live_data = self.get_data(self.API_LIVEFEED_URL.format(game_pk))
        return live_data

