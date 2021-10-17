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

    @staticmethod
    def fetch_data(url):
        try:
            results = requests.get(url).json()
        except Exception as err:
            sys.exit('An unhandled exception occurred retrieving data from MLB.\n{}'.format(err))
        return results

    def fetch_teams_data(self):
        team_data = self.fetch_data(self.API_TEAMS_URL)['teams']
        return team_data

    def fetch_schedule_data(self, game_date):
        schedule_data = self.fetch_data(self.API_SCHEDULE_URL.format(game_date))
        return schedule_data

    def fetch_live_feed_data(self, game_pk):
        live_data = self.fetch_data(self.API_LIVEFEED_URL.format(game_pk))
        return live_data

# <SDG><