import datetime
import config
import sys
import time
import os
import re
import textwrap
import argparse
# import configparser
import keyboard

import mlb_api
import scoreboard_data

"""
JSON viewer
http://jsonviewer.stack.hu/

Sample games for testing
2018-05-13 WSH ARI 1
2018-05-15 NYY WSH 1 -- suspended, resumed 2018-06-18
2018-05-19 LAD WSH 1 and 2 -- double header
2018-05-20 DET SEA 1 -- 11 innings
2018-06-02 WSH ATL 1 -- 14 innings
2018-05-18 LAD WSH 1 -- postponed

09/08/2019- WSH ATL -- gamePk = 567241

http://statsapi.mlb.com/api/v1.1/game/632970/feed/live
http://statsapi.mlb.com/api/v1/schedule?sportId=1&date=08/11/2021&fields?gamePk=632927


See MLB Stats API
https://github.com/toddrob99/MLB-StatsAPI/wiki


iPython
import statsapi
import logging
logger = logging.getLogger('statsapi')
logger.setLevel(logging.DEBUG)
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)8s - %(name)s(%(thread)s) - %(message)s")
ch.setFormatter(formatter)
rootLogger.addHandler(ch)

print( statsapi.player_stats(next(x['id'] for x in statsapi.get('sports_players',{'season':2008,'gameType':'W'})['people'] if x['fullName']=='Chase Utley'), 'hitting', 'career') )


"""

VERSION = '0.91'
COPYRIGHT = '(C) 2018-2024 MSRoth, MLB Live Scoreboard v{}'.format(VERSION)

GAME_STATUS_ENDED = ['GAME OVER', 'FINAL', 'POSTPONED', 'SUSPENDED']
GAME_STATUS_RUNNING = ['IN PROGRESS', 'DELAYED']
GAME_STATUS_NOT_STARTED = ['SCHEDULED', 'WARMUP', 'PRE-GAME']


class MLBLiveScoreboard:
    api = None
    scoreboard_data = None
    game_pk = 0
    livedata = None
    refresh_rate = 30
    delay_refresh_rate = 60
    game_note = ''
    game_status = ''

    def __init__(self):
        self.api = mlb_api.MLB_API()
        self.scoreboard_data = scoreboard_data.ScoreboardData()
        self.refresh_rate = int(config.SB_CONFIG['refresh'])
        self.delay_refresh_rate = int(config.SB_CONFIG['delay'])

    def validate_team_name(self, team):
        return self.scoreboard_data.validate_team_name(team)

    def get_team_id(self, team):
        return self.scoreboard_data.return_team_id(team)

    def find_gamepk(self, team1, team2, game_date):
        game_pks = []
        game_details = []
        team1_id = 0
        team2_id = 0

        try:
            # validate team names
            if not self.validate_team_name(team1):
                sys.exit('ERROR: Invalid first team name: {}'.format(team1))
            else:
                team1_id = self.get_team_id(team1)

            if team2 != '':
                if not self.validate_team_name(team2):
                    sys.exit('ERROR: Invalid second team name: {}'.format(team2))
                else:
                    team2_id = self.get_team_id(team2)

            # get schedule of games today
            schedule = self.api.fetch_schedule_data(game_date)

            if schedule['totalGames'] == 0:
                return 0

            # loop through games looking for team(s)
            for games in schedule['dates'][0]['games']:

                # only one team specified -- could be home or away
                if team2_id == 0:
                    if games['teams']['away']['team']['id'] == team1_id:
                        team2_id = games['teams']['home']['team']['id']

                        game_pks.append(games['gamePk'])
                        game_details.append('{} @ {} {}'.format(games['teams']['away']['team']['name'],
                                                                games['teams']['home']['team']['name'],
                                                                games['gameDate']))

                    if games['teams']['home']['team']['id'] == team1_id:
                        team2_id = games['teams']['away']['team']['id']

                        game_pks.append(games['gamePk'])
                        game_details.append('{} @ {} {}'.format(games['teams']['away']['team']['name'],
                                                                games['teams']['home']['team']['name'],
                                                                games['gameDate']))

                # both teams specified
                else:
                    if (games['teams']['away']['team']['id'] == team1_id and
                        games['teams']['home']['team']['id'] == team2_id) or \
                            (games['teams']['away']['team']['id'] == team2_id and
                             games['teams']['home']['team']['id'] == team1_id):
                        game_pks.append(games['gamePk'])
                        game_details.append('{} @ {} {}'.format(games['teams']['away']['team']['name'],
                                                                games['teams']['home']['team']['name'],
                                                                games['gameDate']))

            if len(game_pks) == 0:
                return 0

            if len(game_pks) == 1:
                return game_pks[0]

            # print all game details and select game to show
            if len(game_pks) > 1:
                for i in range(len(game_pks)):
                    print('{}. {}'.format(i, game_details[i]))
                idx = input('Select game: ')
                return game_pks[int(idx)]

        except Exception as ex:
            sys.exit('ERROR: Could not find game PK. {}'.format(ex))

    def load_game_data(self, game_pk):
        self.game_pk = game_pk

        # load stats data
        self.refresh_live_data()

        # load game data
        self.scoreboard_data.load_game_data(game_pk)

    def get_game_status(self):
        return self.scoreboard_data.return_game_status()

    def refresh_live_data(self):
        return self.scoreboard_data.refresh_live_data(self.game_pk)

    def get_current_inning_half(self):
        return self.scoreboard_data.return_current_inning_half()

    def get_current_inning(self):
        return self.scoreboard_data.return_current_inning()

    def get_current_inning_state(self):
        return self.scoreboard_data.return_current_inning_state()

    def get_current_play_index(self):
        return self.scoreboard_data.return_current_play_index()

    def get_current_play_data(self):
        return self.scoreboard_data.return_current_play_data()

    def get_last_play_data(self):
        return self.scoreboard_data.return_last_play_data()

    def get_a_play_data(self, play_idx):
        return self.scoreboard_data.return_a_play_data(play_idx)

    def get_linescore_data(self):
        return self.scoreboard_data.return_linescore_data()

    def get_boxscore_data(self):
        return self.scoreboard_data.return_boxscore_data()

    def get_game_note(self):
        note = ''
        # linescore = self.livedata['liveData']['linescore']
        linescore = self.get_linescore_data()

        # if there is a note, return it
        if 'note' in linescore:
            note = linescore['note']

        return note

    def get_team_rhe(self):
        linescore = self.scoreboard_data.return_linescore_data()

        # get R - H - E for away team
        away_team_rhe = [linescore['teams']['away']['runs'],
                         linescore['teams']['away']['hits'],
                         linescore['teams']['away']['errors']]

        # get R - H - E for home team
        home_team_rhe = [linescore['teams']['home']['runs'],
                         linescore['teams']['home']['hits'],
                         linescore['teams']['home']['errors']]

        # return away and home team RHE as lists
        return away_team_rhe, home_team_rhe

    @staticmethod
    def clear_screen():
        # Try to clear the screen between each redraw of scoreboard
        if os.name.upper() == 'NT':
            os.system('cls')
        else:
            print('\n\n\n\n')

    @staticmethod
    def format_due_up_status(commentary, due_up_batters, sb_width):
        """
        Format commentary so it doesn't extend past width of scoreboard
        :param commentary:
        :param due_up_batters:
        :param sb_width:
        :return:
        """

        # out_lines = []
        formatted_line = ''
        out_lines = textwrap.wrap(commentary, sb_width)

        for line in out_lines:
            formatted_line += line + '\n'

        formatted_line.strip()
        formatted_line += due_up_batters

        return formatted_line

    def build_bso_line(self):
        """
        Build string containing current balls, strikes, and outs

        :return:
        """

        play_data = self.get_current_play_data()
        return 'B:{} S:{} O:{}'.format(play_data['count']['balls'], play_data['count']['strikes'],
                                       play_data['count']['outs'])

    def get_pitcher_stats(self, pitcher_id):
        """

        :param pitcher_id:
        :return:
        """
        # stats:  wins, losses, era
        stats = ['0', '0', '-.--']
        found = False

        pitcher_stats = self.get_boxscore_data()

        # away
        for pitcher in pitcher_stats['teams']['away']['players']:
            if 'ID' + str(pitcher_id) == pitcher:
                stats[2] = pitcher_stats['teams']['away']['players']['ID' + str(pitcher_id)]['seasonStats']['pitching'][
                    'era']
                stats[0] = pitcher_stats['teams']['away']['players']['ID' + str(pitcher_id)]['seasonStats']['pitching'][
                    'wins']
                stats[1] = pitcher_stats['teams']['away']['players']['ID' + str(pitcher_id)]['seasonStats']['pitching'][
                    'losses']
                found = True
                break

        # home
        if not found:
            for pitcher in pitcher_stats['teams']['home']['players']:
                if 'ID' + str(pitcher_id) == pitcher:
                    stats[2] = \
                        pitcher_stats['teams']['home']['players']['ID' + str(pitcher_id)]['seasonStats']['pitching'][
                            'era']
                    stats[0] = \
                        pitcher_stats['teams']['home']['players']['ID' + str(pitcher_id)]['seasonStats']['pitching'][
                            'wins']
                    stats[1] = \
                        pitcher_stats['teams']['home']['players']['ID' + str(pitcher_id)]['seasonStats']['pitching'][
                            'losses']
                    found = True
                    break

        return stats

    def build_sched_pitchers_line(self):
        """

        :return:
        """

        try:
            away_pitcher_name = self.livedata['gameData']['probablePitchers']['away']['fullName']
            away_pitcher_id = self.livedata['gameData']['probablePitchers']['away']['id']
            home_pitcher_name = self.livedata['gameData']['probablePitchers']['home']['fullName']
            home_pitcher_id = self.livedata['gameData']['probablePitchers']['home']['id']

            # use id to get record and ERA
            away_pitcher_stats = self.get_pitcher_stats(away_pitcher_id)
            home_pitcher_stats = self.get_pitcher_stats(home_pitcher_id)

            return '{} ({}-{}, {} ERA) vs. {} ({}-{}, {} ERA)'.format(away_pitcher_name, away_pitcher_stats[0],
                                                                      away_pitcher_stats[1], away_pitcher_stats[2],
                                                                      home_pitcher_name, home_pitcher_stats[0],
                                                                      home_pitcher_stats[1], home_pitcher_stats[2])
        except Exception as err:
            return 'TBD vs. TBD'

    def build_win_lose_pitcher_line(self):
        """

        :return:
        """

        decisions = self.livedata['liveData']
        winner = decisions['decisions']['winner']['fullName']
        winner_id = decisions['decisions']['winner']['id']
        loser = decisions['decisions']['loser']['fullName']
        loser_id = decisions['decisions']['loser']['id']

        # get pitchers wins, loses, and ERA
        winner_wl = self.get_pitcher_stats(winner_id)
        loser_wl = self.get_pitcher_stats(loser_id)
        return 'Winner: {} ({}-{}, {}) Loser: {} ({}-{}, {})'.format(winner, winner_wl[0],
                                                                     winner_wl[1], winner_wl[2],
                                                                     loser, loser_wl[0], loser_wl[1],
                                                                     loser_wl[2])

    @staticmethod
    def format_status_lines_with_diamond(base_runners, bso_line, matchup_line, commentary_line, last_pitch, sb_width):
        """


        :return:
        """

        out_lines = []

        # first line of output is BSO line
        out_lines.append('{} | {}'.format(bso_line, matchup_line))

        # wrap text with textwrap module
        commentary_out = textwrap.wrap(commentary_line, sb_width - len(base_runners[1]))

        t = max(len(commentary_out), len(base_runners))
        for i in range(0, t):
            if i <= len(base_runners) - 1 and i <= len(commentary_out) - 1:
                out_lines.append(base_runners[i] + commentary_out[i])
            elif i <= len(base_runners) - 1 and i > len(commentary_out) - 1:
                out_lines.append(base_runners[i])
            elif i > len(base_runners) - 1 and i <= len(commentary_out) - 1:
                out_lines.append(' ' * (len(base_runners[0]) - 2) + '| ' + commentary_out[i])

        # append last pitch info
        # TODO - wrap last_pitch if longer than sb_width
        out_lines.append(last_pitch)

        return out_lines

    def build_diamond_with_base_runners(self):
        """
        return list:  home = 0, first = 1, second = 2, third = 3
        ex. runner on second:  [o][][X][]
        home is always 'o' (for batter)

        :return:
        """

        bases = ['o', ' ', ' ', ' ']
        bases_lines = ['', '', '']

        linescore = self.scoreboard_data.return_linescore_data()
        if 'first' in linescore['offense']:
            bases[1] = 'X'
        if 'second' in linescore['offense']:
            bases[2] = 'X'
        if 'third' in linescore['offense']:
            bases[3] = 'X'

        # reformat base configuration
        bases_lines[0] = '    [' + bases[2] + ']     | '
        bases_lines[1] = ' [' + bases[3] + ']   [' + bases[1] + ']  | '
        bases_lines[2] = '    [' + bases[0] + ']     | '

        return bases_lines

    def build_pitcher_batter_matchup_line(self):
        """

        get pitcher-batter match up with stats

        :return:
        """

        data = self.get_current_play_data()
        pitcher_name = data['matchup']['pitcher']['fullName']
        pitcher_name = pitcher_name.split(' ')[1]
        batter_name = data['matchup']['batter']['fullName']
        batter_name = batter_name.split(' ')[1]
        pitcher_id = data['matchup']['pitcher']['id']
        batter_id = data['matchup']['batter']['id']

        pitcher_stats = []
        batter_stats = []

        # get stats
        # inning_half = data['about']['halfInning']
        # if inning_half.upper() == 'TOP':
        #     batter_stats = self.get_batter_stats(batter_id, 'away')
        # else:
        #     batter_stats = self.get_batter_stats(batter_id, 'home')
        batter_stats = self.get_batter_stats(batter_id)
        pitcher_stats = self.get_pitcher_stats(pitcher_id)

        # return pitcher-batter matchup line
        return 'Pitcher: {} ({} ERA) \n            | Batter : {} ({}-{}, {} AVG)'.format(pitcher_name, pitcher_stats[2],
                                                                                         batter_name,
                                                                                         batter_stats[1],
                                                                                         batter_stats[2],
                                                                                         batter_stats[3])

    def run(self):

        try:
            # loop until the game is over
            end_loop = False
            while not end_loop:

                self.clear_screen()

                # Init vars for redraw
                scoreboard_title = ''
                scoreboard_inning_headers = []
                away_line_score = []
                home_line_score = []
                scoreboard_totals_headers = ['R', 'H', 'E']
                away_totals = ['0', '0', '0']
                home_totals = ['0', '0', '0']

                # print update header
                print('Retrieving game data from MLB ({})...\n'.format(datetime.datetime.now().strftime('%m/%d/%Y %X')))

                # get updated data from MLB
                self.livedata = self.refresh_live_data()

                # get game status
                self.game_status = self.get_game_status()

                # Load team totals
                if self.game_status.upper() not in GAME_STATUS_NOT_STARTED:
                    away_totals, home_totals = self.get_team_rhe()

                # Get game note
                self.game_note = self.get_game_note()

                # Add team names and records to line scores
                away_line_score, home_line_score = self.build_team_names_with_record(away_line_score, home_line_score)

                # Enter inning half or game status in first element of inning header
                team_name_length = max(len(away_line_score[0]), len(home_line_score[0]))

                if self.game_status.upper() != 'IN PROGRESS' and self.game_status[
                                                                 :7].upper() != 'DELAYED' and self.game_status[
                                                                                              :9].upper() != 'SUSPENDED':
                    inning_half = ' '
                else:
                    inning_half = '{} {}'.format(self.get_current_inning_half(), self.get_current_inning())

                if team_name_length > len(inning_half):
                    inning_half += ' ' * (team_name_length - len(inning_half))

                # inning headers
                scoreboard_inning_headers.append(inning_half.upper())

                # fill innings
                scoreboard_inning_headers, \
                away_line_score, home_line_score = self.build_innings(scoreboard_inning_headers, away_line_score,
                                                                      home_line_score)
                # Append team totals to line scores
                scoreboard_inning_headers += scoreboard_totals_headers
                away_line_score += away_totals
                home_line_score += home_totals

                # Build bars according to lengths
                double_bar = '=' * ((len(scoreboard_inning_headers * 5) + len(scoreboard_inning_headers[0])) - 3)
                single_bar = '-' * len(double_bar)

                # build status output
                game_status_info = self.build_game_status_info(len(double_bar)).strip('\n')

                # ---- Print the scoreboard ----

                # print game info line
                print('{} @ {}: {} (Game #{})'.format(self.scoreboard_data.return_away_team(),
                                                      self.scoreboard_data.return_home_team(),
                                                      self.get_game_date_time(), game_pk))

                print(double_bar)

                # Print inning headers
                output = ''
                for x in scoreboard_inning_headers:
                    output += ' {:<3}|'.format(x)
                print(output)
                print(single_bar)

                # Print away line score
                output = ''
                for i, x in enumerate(away_line_score):
                    if scoreboard_inning_headers[i] == 'R':
                        output = output[:-1] + '|'
                    output += ' {:<3} '.format(x)
                print(output)

                # Print home line score
                output = ''
                for i, y in enumerate(home_line_score):
                    if scoreboard_inning_headers[i] == 'R':
                        output = output[:-1] + '|'
                    output += ' {:<3} '.format(y)
                print(output)

                print(single_bar)

                # TODO one call to build_game_status_info and print it
                # then set loop condition based on game_status

                # Game over
                # if self.game_status.upper() == 'GAME OVER':
                #     end_loop = True
                #
                # if self.game_status.upper() == 'FINAL':
                #     end_loop = True
                #
                # if self.game_status.upper() == 'POSTPONED':
                #     end_loop = True
                #
                # if self.game_status[:9].upper() == 'SUSPENDED':
                #     end_loop = True

                if self.game_status.upper() in GAME_STATUS_ENDED or self.game_status.upper()[:9] in GAME_STATUS_ENDED:
                    end_loop = True

                # Game not started
                # if self.game_status.upper() == 'SCHEDULED':
                #     end_loop = True

                # if self.game_status.upper() == 'PRE-GAME':
                #     end_loop = True

                if self.game_status.upper() in GAME_STATUS_NOT_STARTED:
                    end_loop = True

                # if self.game_status.upper() == 'WARMUP':
                #     end_loop = False

                if self.game_status.upper() in GAME_STATUS_RUNNING:
                    end_loop = False

                # any other not 'in progress' state
                # if self.game_status.upper() != 'IN PROGRESS':
                #     print(game_status_info)

                if self.game_status not in GAME_STATUS_RUNNING:
                    print(game_status_info)

                # Print game note if there is one
                if self.game_note:
                    if len(self.game_note) > len(double_bar):
                        print('Note: ' + self.game_note[:len(double_bar) - 5])
                        print('      ' + self.game_note[len(double_bar) - 5 + 1:])
                    else:
                        print('Note: ' + self.game_note)

                # if self.game_status.upper() == 'IN PROGRESS':
                #     print(game_status_info)

                print(double_bar)

                # Print (c) banner
                print(COPYRIGHT)
                sys.stdout.flush()

                # Sleep for a while and continue with loop
                if not end_loop:
                    if self.game_status.upper() in GAME_STATUS_RUNNING:
                        loop_cnt = 0
                        while loop_cnt < self.refresh_rate:
                            if keyboard.is_pressed('q') or keyboard.is_pressed('esc') or keyboard.is_pressed('ctrl+c'):
                                print(loop_cnt)
                                quit(0)

                            if keyboard.is_pressed('l'):
                                self.print_lineups()
                                break

                            if keyboard.is_pressed('b'):
                                # print formatted box score
                                print('box score')
                                break

                            time.sleep(1)
                            loop_cnt += 1

                    
                    
                    #if self.game_status.upper() in GAME_STATUS_RUNNING:
                        #time.sleep(self.refresh_rate)
                    else:
                        time.sleep(self.delay_refresh_rate)
                    #
                    # if self.game_status[:7].upper() == 'DELAYED' or \
                    #         self.game_status.upper() == 'WARMUP' or \
                    #         self.game_status.upper() == ' PRE-GAME':
                    #     time.sleep(self.delay_refresh_rate)
                    # else:
                    #     time.sleep(self.refresh_rate)
        except KeyboardInterrupt:
            print('Exit MLB Live Scoreboard')

    def build_game_status_info(self, sb_width):
        """
        :param sb_width:
        :return:
        """

        status_line = ''
        commentary_line = ''
        note = self.get_game_note()

        # get game status
        game_status = self.get_game_status()

        # if game_status.upper() != 'FINAL' and \
        #         game_status.upper() != 'GAME OVER' and \
        #         game_status.upper() != 'SCHEDULED' and \
        #         game_status.upper() != 'WARMUP' and \
        #         game_status.upper() != 'PRE-GAME' and \
        #         game_status.upper() != 'POSTPONED' and \
        #         game_status[:9].upper() != 'SUSPENDED':

        if game_status.upper() in GAME_STATUS_RUNNING:

            linescore = self.livedata['liveData']['linescore']
            # get play commentary
            commentary_line = self.get_last_play_description()

            # between innings show due up batters
            inning_state = self.get_current_inning_state()
            if inning_state.upper() == 'END' or inning_state.upper() == 'MIDDLE':
                due_up_batters = self.build_dueup_batters_line()
                status_line = self.format_due_up_status(commentary_line, due_up_batters, sb_width)

            else:

                # get last pitch info
                last_pitch = self.get_last_pitch()

                # get Balls-Strikes-Outs
                bso_line = self.build_bso_line()

                # get pitcher - batter match up
                match_up_line = self.build_pitcher_batter_matchup_line()

                # get the base runners as a formatted list
                base_runners = self.build_diamond_with_base_runners()

                # format status to fit on screen
                fmt_bases_commentary = self.format_status_lines_with_diamond(base_runners, bso_line, match_up_line,
                                                                             commentary_line,
                                                                             last_pitch, sb_width)

                # add the formatted lines to the output string
                for line in fmt_bases_commentary:
                    status_line += line + '\n'
                status_line.strip('\n')

            # !!! this seems to duplicate what is in run_scoreboard()

            # game delayed
            if game_status[:7].upper() == 'DELAYED' or game_status[:9].upper() == 'SUSPENDED':
                if len(note) > 0:
                    status_line += '{} - {}'.format(game_status, note)
                else:
                    status_line += game_status

        # game over
        # elif game_status.upper() == 'FINAL' or game_status.upper() == 'GAME OVER':
        elif game_status.upper() in GAME_STATUS_ENDED:
            status_line = '{}\n{}'.format(self.build_win_lose_pitcher_line(), game_status)

        # scheduled or warmup or some other delay
        # elif game_status.upper() == 'SCHEDULED' or game_status.upper() == 'WARMUP' or game_status.upper() == 'PRE-GAME':
        elif game_status.upper() in GAME_STATUS_NOT_STARTED:
            status_line = '{}\n{}'.format(self.build_sched_pitchers_line(), game_status)

        elif game_status.upper() == 'POSTPONED':
            if len(note) > 0:
                status_line = '{}: {}'.format(game_status, note)
            else:
                status_line = game_status

        # unknown status occurred
        else:
            if len(note) > 0:
                status_line = '{}: {}'.format(game_status, note)
            else:
                status_line = game_status

        return status_line

    def process_subs(self, player_id, batting_order, home_away):

        # update batting order with subs
        for play_idx in range(len(self.livedata['liveData']['plays']['allPlays'])):
            play_data = self.get_a_play_data(play_idx)
            for event_idx in range(len(play_data['playEvents'])):
                event_data = play_data['playEvents'][event_idx]
                if 'player' in event_data and 'playerReplaced' in event_data:
                    if player_id == event_data['player']['id']:
                        player_replaced_id = event_data['playerReplaced'][id]
                        batting_order[batting_order.index(player_replaced_id)] = player_id

        return batting_order

    def print_lineups(self):

        teams_data = self.return_boxscore_data()['teams']

        # away players
        away_team = self.return_a_team_name(teams_data['away']['team']['id'])[2]
        print()
        print(away_team + ' Lineup')
        print('-----------------------------')
        for player_id in teams_data['away']['players']:
            id = teams_data['away']['players'][str(player_id)]['person']['id']
            player_name = teams_data['away']['players'][str(player_id)]['person']['fullName']
            player_jersey_no = teams_data['away']['players'][str(player_id)]['jerseyNumber']
            print('#{} {}'.format(player_jersey_no, player_name))

        # home players
        home_team = self.return_a_team_name(teams_data['home']['team']['id'])[2]
        print()
        print(home_team + ' Lineup')
        print('-----------------------------')
        for player_id in teams_data['home']['players']:
            id = teams_data['home']['players'][str(player_id)]['person']['id']
            player_name = teams_data['home']['players'][str(player_id)]['person']['fullName']
            player_jersey_no = teams_data['home']['players'][str(player_id)]['jerseyNumber']
            print('#{} {}'.format(player_jersey_no, player_name))

        print()
        _ = input('Press [ENTER] to continue')

    def build_dueup_batters_line(self):
        """
        Return a string containing the names and averages of the next three due up
        hitters.  Only shown during inning breaks.

        :return:
        """

        # three element list to hold next three due up batters
        due_up_batters = []
        home_or_away = ''

        try:

            boxscore = self.get_boxscore_data()

            if self.get_current_inning() > 1:

                # get last batter id from previous inning
                inning_half = self.get_current_inning_half().lower()
                last_batter_inning = self.get_current_inning() - 1

                # screwy logic because sometimes the data doesn't update quickly

                outs = self.livedata['liveData']['plays']['currentPlay']['count']['outs']
                if outs == 3:  # we're still in this inning, the data didn't update
                    if inning_half == 'top':
                        home_or_away = 'home'
                        inning_half = 'bottom'
                    else:
                        home_or_away = 'away'
                        inning_half = 'top'
                else:
                    if inning_half == 'top':
                        home_or_away = 'away'
                    else:
                        home_or_away = 'home'

                if inning_half.lower() == 'top':
                    last_batter_id = self.scoreboard_data.return_last_batter_ids()[1]
                else:
                    last_batter_id = self.scoreboard_data.return_last_batter_ids()[0]

                # get list of batter ids in batting order
                batting_order = boxscore['teams'][home_or_away]['battingOrder']

                # update batting order if last batter was pinch hitter, etc.
                if last_batter_id not in batting_order:
                    batting_order = self.process_subs(last_batter_id, batting_order, home_or_away)

                # find batter id in bat_order list
                batting_order_idx = batting_order.index(last_batter_id)

                # start with next batter
                # batting_order_idx += 1
                for j in range(3):  # get next three batters, rotate to top of order if at end
                    batting_order_idx += 1
                    if batting_order_idx > 8:
                        batting_order_idx = 0
                    batter_id = batting_order[batting_order_idx]

                    # get the batters stats
                    batter_stats = self.get_batter_stats(batter_id)

                    # format each batters line
                    due_up_batters.append('{} ({}-{}), {} AVG'.format(batter_stats[0], batter_stats[1], batter_stats[2],
                                                                      batter_stats[3]))
            else:
                batting_order = boxscore['teams']['home']['battingOrder']

                for j in range(3):
                    # get the batters stats
                    batter_stats = self.get_batter_stats(batting_order[j])

                    # format each batters line
                    due_up_batters.append('{} ({}-{}), {} AVG'.format(batter_stats[0], batter_stats[1], batter_stats[2],
                                                                      batter_stats[3]))

            # build output line
            return '\nDue up:  {}\n         {}\n         {}\n'.format(due_up_batters[0], due_up_batters[1],
                                                                      due_up_batters[2])
        except Exception as ex:
            return 'Due up:  TBD'

    def get_batter_stats(self, batter_id):
        """

        :param batter_id:
        :return:
        """
        # stats: name, hits, atBats, avg
        stats = ['', '', '', '']
        found = False

        boxscore = self.get_boxscore_data()
        # boxscore = self.livedata['liveData']['boxscore']

        try:
            # # away
            # for player in boxscore['teams'][home_away]['players']:
            #     if player == 'ID' + str(batter_id):
            #         stats[0] = boxscore['teams'][home_away]['players']['ID' + str(batter_id)]['person']['fullName']
            #         stats[2] = boxscore['teams'][home_away]['players']['ID' + str(batter_id)]['stats']['batting']['atBats']
            #         stats[1] = boxscore['teams'][home_away]['players']['ID' + str(batter_id)]['stats']['batting']['hits']
            #         stats[3] = boxscore['teams'][home_away]['players']['ID' + str(batter_id)]['seasonStats']['batting']['avg']
            #         break

            # away
            for player in boxscore['teams']['away']['players']:
                if player == 'ID' + str(batter_id):
                    stats[0] = boxscore['teams']['away']['players']['ID' + str(batter_id)]['person']['fullName']
                    stats[2] = boxscore['teams']['away']['players']['ID' + str(batter_id)]['stats']['batting']['atBats']
                    stats[1] = boxscore['teams']['away']['players']['ID' + str(batter_id)]['stats']['batting']['hits']
                    stats[3] = boxscore['teams']['away']['players']['ID' + str(batter_id)]['seasonStats']['batting'][
                        'avg']
                    found = True
                    break

                # home
                if not found:
                    for player in boxscore['teams']['home']['players']:
                        if player == 'ID' + str(batter_id):
                            stats[0] = boxscore['teams']['home']['players']['ID' + str(batter_id)]['person']['fullName']
                            stats[2] = boxscore['teams']['home']['players']['ID' + str(batter_id)]['stats']['batting'][
                                'atBats']
                            stats[1] = boxscore['teams']['home']['players']['ID' + str(batter_id)]['stats']['batting'][
                                'hits']
                            stats[3] = \
                            boxscore['teams']['home']['players']['ID' + str(batter_id)]['seasonStats']['batting']['avg']
                            break

        except Exception as ex:
            stats = ['', '', '', '']

        return stats

    def get_last_play_description(self):
        """

        :return:
        """
        last_play = ''
        description = ''

        try:
            inning_state = self.get_current_inning_state()

            # first try to get current play.  If no description, get last play
            play_data = self.get_current_play_data()
            if 'description' in play_data['result']:
                description = play_data['result']['description']
            if len(description) == 0:
                play_data = self.get_last_play_data()
                description = play_data['result']['description']
            event = play_data['result']['event']
            play_inning = play_data['about']['inning']
            play_inning_half = str(play_data['about']['halfInning']).upper()

            # add inning to commentary
            current_inning = self.get_current_inning()
            current_inning_half = self.get_current_inning_half()
            inning_desc = ''
            if int(current_inning) != int(play_inning) or \
                    current_inning_half.upper() != play_inning_half.upper():
                inning_desc = '({} {})'.format(play_inning_half, play_inning)

            # clean if up
            re.sub(' +', ' ', description)
            re.sub('\n', ' ', description)

            last_play = 'Last play {}: {} - {}'.format(inning_desc, event, description)

        except Exception as ex:
            # sometimes there is a race condition and these fields don't exist yet.
            # just return blank string and pick up the commentary on the next refresh.
            last_play = ''

        return last_play

    def get_last_pitch(self):
        pitch_number = ''
        pitch_type = ''
        pitch_speed = ''
        pitch_str = ''

        play_data = self.get_current_play_data()

        # note:  endspeed is different than startspeed.  I suspect the TV reports
        #        startspeed.
        try:
            events = play_data['playEvents']
            last_event = len(events) - 1  # zero-based
            pitch_result = events[last_event]['details']['description']
            if 'type' in events[last_event]['details']:
                pitch_type = events[last_event]['details']['type']['description']
                pitch_speed = events[last_event]['pitchData']['startSpeed']
                pitch_number = events[last_event]['pitchNumber']

            if pitch_speed != '':
                pitch_str = 'Last pitch: #{} {} ({} MPH) - {}'.format(pitch_number, pitch_type, pitch_speed,
                                                                      pitch_result)

        except Exception as ex:
            return ''

        return pitch_str

    def get_team_abbrevs_list(self):
        team_str = ''
        teams = self.scoreboard_data.return_team_abbrevs()
        for i in range(len(teams)):
            team_str += teams[i][0] + ','
        return team_str[:-1]

    def get_game_date_time(self):

        try:
            game_date = str(self.livedata['gameData']['datetime']['originalDate']).replace('-', '/')
            game_time = self.livedata['gameData']['datetime']['time'] + self.livedata['gameData']['datetime']['ampm']
        except Exception as ex:
            return ''

        # return game date with time
        return '{} {}'.format(game_date, game_time)

    def build_team_names_with_record(self, away_line, home_line):
        """
        Build the team abbreviation and win-loss record as the 0th element of the
        away_line and home_line.

        Result should look like:
            away_line['WSH (1-1)']
            home_line['LAD (1-1)']

        :param away_line:
        :param home_line:
        :return:
        """

        teams = self.livedata['gameData']['teams']

        # get team wins and losses
        away_team_win = teams['away']['record']['wins']
        away_team_loss = teams['away']['record']['losses']
        home_team_win = teams['home']['record']['wins']
        home_team_loss = teams['home']['record']['losses']

        # get team abbrevs using team ids
        away_team_name = teams['away']['abbreviation']
        home_team_name = teams['home']['abbreviation']

        # return two lists containing a single element, the formatted team name with record
        # this ends up being the first (0th) element of the list containing the scoreboard
        # column values.
        away_line.append('{:<3} ({:>3}-{:<3})'.format(away_team_name, away_team_win, away_team_loss))
        home_line.append('{:<3} ({:>3}-{:<3})'.format(home_team_name, home_team_win, home_team_loss))

        return away_line, home_line

    def build_innings(self, header_line, away_line, home_line):
        """
        This function puts the score for each inning into the away or home team's list
        element for the appropriate inning.  There is logic to insert '-' in an inning
        that is being played with no score, and 'X' in the bottom half of the final
        inning if it is not played.  For unplayed innings, ' ' is entered.

        The function returns the list containing the inning numbers, the away team score,
        and the home team score (three lists).

        :param header_line:
        :param away_line:
        :param home_line:

        :return:
        """
        inning_num = 0

        # get game status to know how to handle final inning
        game_status = self.get_game_status()

        # if game not started, ensure blank scoreboard by skipping all of this logic
        if game_status.upper() == 'IN PROGRESS' or \
                game_status[:7].upper() == 'DELAYED' or \
                game_status.upper() == 'FINAL' or game_status.upper() == 'GAME OVER' or \
                game_status[:9].upper() == 'SUSPENDED':

            # get inning status, etc.
            inning_half = self.get_current_inning_half()
            current_inning = self.get_current_inning()

            # process each inning
            linescore = self.livedata['liveData']['linescore']
            for inning in linescore['innings']:

                inning_num = int(inning['num'])
                inning_state = self.get_current_inning_state()

                # populate inning header with this inning
                header_line.append('{:<3}'.format(inning_num))

                # away team runs this inning if the key exists
                if 'runs' in inning['away']:
                    away_line.append('{:<3}'.format(inning['away']['runs']))
                else:
                    away_line.append('')

                # home team runs this inning if the key exists
                if 'runs' in inning['home']:
                    home_line.append('{:<3}'.format(inning['home']['runs']))
                else:
                    home_line.append('')

                # handle current inning in progress with no score
                if inning_num == current_inning:
                    if game_status.upper() == 'IN PROGRESS' or game_status[:7].upper() == 'DELAYED':
                        if inning_half.upper() == 'TOP':
                            if 'runs' in inning['away']:
                                if int(inning['away']['runs']) == 0 and inning_state.upper() != 'MIDDLE':
                                    away_line[inning_num] = '{:<3}'.format('-')
                                else:
                                    away_line[inning_num] = '{:<3}'.format(inning['away']['runs'])
                            else:
                                away_line[inning_num] = '{:<3}'.format('-')

                        else:
                            # if inning_state.upper() != 'MIDDLE' and inning_state.upper() != 'END':
                            if 'runs' in inning['home']:
                                if int(inning['home']['runs']) == 0:
                                    home_line[inning_num] = '{:<3}'.format('-')
                                else:
                                    home_line[inning_num] = '{:<3}'.format(inning['home']['runs'])
                            else:
                                home_line[inning_num] = '{:<3}'.format('-')

                # Handle unplayed bottom of ninth
                if game_status.upper() == 'FINAL' or game_status.upper() == 'GAME OVER':
                    if home_line[inning_num] == '':
                        home_line[inning_num] = '{:<3}'.format('X')

        # fill out rest of scoreboard for unplayed innings
        if inning_num < 9:
            for i in range(inning_num + 1, 10):
                header_line.append(i)  # inning number
                home_line.append('')  # blank home runs
                away_line.append('')  # blank away runs

        # return three main scoreboard lines as lists
        return header_line, away_line, home_line


def _validate_date(game_date):
    """
    Validate the date entered.

    :param game_date:
    :return:
    """
    try:
        month, day, year = game_date.split('/')
        datetime.datetime(int(year), int(month), int(day))
    except ValueError:
        return False
    return True


def _usage():
    print(USAGE_DOC)


USAGE_DOC = """
Usage:
  MLB-live-scoreboard.py [--team favorite_team] [--away away_team, --home home_team, --date game_date]')

For example:
  >python MLB-live-scorebaord.py
      reads configuration variables from config.py
      
  >python MLB-live-scoreboard.py --team WSH
      shows today's scoreboard for listed team
      
  >python MLB-live-scoreboard.py --away WSH --home PHI --date 04/10/2019')
      shows scoreboard for specific game
      
Date format:  MM/DD/YYYY

Valid team names:
  Arizona Diamondbacks	= ARI
  Atlanta Braves	    = ATL
  Baltimore Orioles	    = BAL
  Boston Red Sox	    = BOS
  Chicago Cubs	        = CHC
  Cincinnati Reds	    = CIN
  Cleveland Indians	    = CLE
  Colorado Rockies	    = COL
  Chicago White Sox	    = CWS
  Detroit Tigers	    = DET
  Houston Astros	    = HOU
  Kansas City Royals	= KC
  Los Angeles Angels	= LAA
  Los Angeles Dodgers	= LAD
  Miami Marlins	        = MIA
  Milwaukee Brewers	    = MIL
  Minnesota Twins	    = MIN
  New York Mets	        = NYM
  New York Yankees	    = NYY
  Oakland Athletics	    = OAK
  Philadelphia Phillies	= PHI
  Pittsburgh Pirates	= PIT
  San Diego Padres	    = SD
  Seattle Mariners	    = SEA
  San Francisco Giants	= SF
  St. Louis Cardinals	= STL
  Tampa Bay Rays	    = TB
  Texas Rangers	        = TEX
  Toronto Blue Jays	    = TOR
  Washington Nationals	= WSH
"""

##### MAIN #####
if __name__ == "__main__":

    # Print banner
    print(COPYRIGHT)

    # Init some stuff
    scoreboard = MLBLiveScoreboard()
    game_pk = 0
    favorite_team = None

    # use configParser to parse config file

    # add --teams to list team trigraphs
    # add --games with --date to list games
    # add --gamePk to load specific game

    parser = argparse.ArgumentParser(prog='MLB-live-scoreboard',
                                     # description='Use --team=<tri> to load current game for your favorite team, or ' +
                                     #              'combination of --away=<tri>, --home=<tri>, and --date=<mm/dd/yyyy> to ' +
                                     #              'load a specific game. --all_teams to list team tri-graphs, or --date=<mm/dd/yyyy> ' +
                                     #              'to list games for specific date.  --gamepk=<gamepk> to load a specific game.')
                                     description='''Valid team tri-graphs:
  Arizona Diamondbacks	= ARI
  Atlanta Braves	    = ATL
  Baltimore Orioles	    = BAL
  Boston Red Sox	    = BOS
  Chicago Cubs	        = CHC
  Cincinnati Reds	    = CIN
  Cleveland Indians	    = CLE
  Colorado Rockies	    = COL
  Chicago White Sox	    = CWS
  Detroit Tigers	    = DET
  Houston Astros	    = HOU
  Kansas City Royals	= KC
  Los Angeles Angels	= LAA
  Los Angeles Dodgers	= LAD
  Miami Marlins	        = MIA
  Milwaukee Brewers	    = MIL
  Minnesota Twins	    = MIN
  New York Mets	        = NYM
  New York Yankees	    = NYY
  Oakland Athletics	    = OAK
  Philadelphia Phillies	= PHI
  Pittsburgh Pirates	= PIT
  San Diego Padres	    = SD
  Seattle Mariners	    = SEA
  San Francisco Giants	= SF
  St. Louis Cardinals	= STL
  Tampa Bay Rays	    = TB
  Texas Rangers	        = TEX
  Toronto Blue Jays	    = TOR
  Washington Nationals	= WSH''')

    parser.add_argument('--team', required=False, dest='favorite_team',
                        help='Tri-graph for favorite team.')
    parser.add_argument('--away', required=False, dest='away_team',
                        help='Tri-graph for away team.')
    parser.add_argument('--home', required=False, dest='home_team',
                        help='Tri-graph for home team.')
    parser.add_argument('--date', required=False, dest='game_date',
                        help='Date of game MM/DD/YYYY.')
    parser.add_argument('--gamepk', required=False, dest='gamepk',
                        help='Load specific game')
    parser.add_argument('--all_teams', required=False, default=False, action='store_true',
                        help='List all team tri-graphs')
    args = parser.parse_args()

    # today's date
    game_date = datetime.datetime.now().strftime('%m/%d/%Y')

    # no args -- use team in config.py
    if len(sys.argv) == 1:
        favorite_team = config.SB_CONFIG['team']
        if not scoreboard.validate_team_name(favorite_team):
            _usage()
            sys.exit('ERROR: Invalid team name found in config.py: {}'.format(favorite_team))
        else:
            game_pk = scoreboard.find_gamepk(favorite_team, '', game_date)

    # use favorite team arg
    elif args.favorite_team is not None and args.game_date is None:
        favorite_team = args.favorite_team
        if not scoreboard.validate_team_name(favorite_team):
            _usage()
            sys.exit('ERROR: Invalid team name: {}'.format(favorite_team))
        else:
            game_pk = scoreboard.find_gamepk(favorite_team, '', game_date)

    # list trigraphs
    elif args.all_teams == True:
        print('\nMLB Team Tri-graphs:')
        print(scoreboard.get_team_abbrevs_list())
        sys.exit()

    # list games for specific date
    elif args.game_date is not None and args.favorite_team is None and args.home_team is None and args.away_team is None:
        if not _validate_date(args.game_date):
            _usage()
            sys.exit('ERROR:  Invalid date: {}'.format(args.game_date))
        else:
            schedule = scoreboard.api.fetch_schedule_data(args.game_date)
            if schedule['totalGames'] > 0:
                print('Games on {}:'.format(args.game_date))
                for games in schedule['dates'][0]['games']:
                    #print('{} - {} @ {}, {}'.format(games['gamePk'], games['teams']['away']['team']['name'],
                    #                                games['teams']['home']['team']['name'],
                    #                                datetime.datetime.strptime(games['gameDate'],
                    #                                                           '%Y-%m-%dT%H:%M:%S%z').time()))
                    zTime = datetime.datetime.strptime(games['gameDate'],'%Y-%m-%dT%H:%M:%S%z').astimezone(None).time()
                    print('{} - {} @ {} - {}'.format(games['gamePk'], games['teams']['away']['team']['name'],games['teams']['home']['team']['name'],zTime))
        sys.exit()

    # one team and a date
    elif args.game_date is not None and (
            args.favorite_team is not None or args.home_team is not None or args.away_team is not None):
        team = ''
        if args.favorite_team is not None:
            team = args.favorite_team
        elif args.home_team is not None:
            team = args.home_team
        elif args.away_team is not None:
            team = args.away_team

        if not scoreboard.validate_team_name(team):
            _usage()
            sys.exit('ERROR: Invalid team name: {}'.format(team))
        if not _validate_date(args.game_date):
            _usage()
            sys.exit('ERROR:  Invalid date: {}'.format(args.game_date))

        game_pk = scoreboard.find_gamepk(team, '', args.game_date)

    # use full command line
    elif args.away_team is not None and args.home_team is not None and args.game_date is not None:
        if not scoreboard.validate_team_name(args.away_team):
            _usage()
            sys.exit('ERROR: Invalid away team name: {}'.format(args.away_team))

        if not scoreboard.validate_team_name(args.home_team):
            _usage()
            sys.exit('ERROR: Invalid home team name: {}'.format(args.home_team))

        if not _validate_date(args.game_date):
            _usage()
            sys.exit('ERROR:  Invalid date: {}'.format(args.game_date))

        # config/args ok, find a game
        game_pk = scoreboard.find_gamepk(args.home_team, args.away_team, args.game_date)

    # load by gamepk
    elif args.gamepk is not None:
        game_pk = args.gamepk

    else:
        parser.print_usage()

    # run scoreboard
    if game_pk != 0:
        scoreboard.load_game_data(game_pk)
        scoreboard.run()

    else:
        schedule = scoreboard.api.fetch_schedule_data(game_date)
        if schedule['totalGames'] == 0:
            print('MLB day off; no games scheduled.\n')
            sys.exit()
        elif args.home_team is not None and args.away_team is not None and args.game_date:
            print('\nNo game found for {} at {} on {}'.format(args.away_team, args.home_team, args.game_date))
        elif favorite_team is not None:
            print('\n{} has no scheduled game(s) today.\n'.format(favorite_team))
        else:
            print('\nSomething went wrong.')
            sys.exit()

        # get schedule of games 
        if schedule['totalGames'] > 0:
            print('Today\'s games:')
            for games in schedule['dates'][0]['games']:
                print('{} - {} @ {}'.format(games['gamePk'], games['teams']['away']['team']['name'],
                                            games['teams']['home']['team']['name']))

# <SDG><
