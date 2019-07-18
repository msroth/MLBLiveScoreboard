import requests
import datetime
import config
import sys
import time
import os
import re

"""
MLB API docs and tester
http://statsapi-default-elb-prod-876255662.us-east-1.elb.amazonaws.com/docs/#!

JSON viewer
http://jsonviewer.stack.hu/

Sample games for testing
2018-05-13 WSH ARI 1
2018-05-15 NYY WSH 1 -- suspended, resumed 2018-06-18
2018-05-19 LAD WSH 1 and 2 -- double header
2018-05-20 DET SEA 1 -- 11 innings
2018-06-02 WSH ATL 1 -- 14 innings
2018-05-18 LAD WSH 1 -- postponed

"""

VERSION = '0.6'
COPYRIGHT = '(C) 2018-2019 MSRoth, MLB Live Scoreboard v{}'.format(VERSION)

API_BASE_URL = "http://statsapi.mlb.com/api"
API_BOXSCORE_URL = API_BASE_URL + "/v1/game/{}/boxscore"
API_LINESCORE_URL = API_BASE_URL + "/v1/game/{}/linescore"
API_PLAYBYPLAY_URL = API_BASE_URL + "/v1/game/{}/playByPlay"
API_LIVEFEED_URL = API_BASE_URL + "/v1.1/game/{}/feed/live"
API_TEAMS_URL = API_BASE_URL + "/v1/teams?sportId=1&activeStatus=ACTIVE"
API_SCHEDULE_URL = API_BASE_URL + "/v1/schedule?sportId=1&date={}"
API_SCHEDULE_GAMEPK_URL = API_BASE_URL + "/v1/schedule?sportId=1&gamePk={}"
API_PERSON_CURRENT_STATS_URL = API_BASE_URL + "/v1/people/{}/stats/game/current"

# Team name dictionaries
TEAM_NAMES_BY_ABBREV = {}
TEAM_ABBREVS_BY_NAME = {}
TEAM_ABBREVS_BY_ID = {}

# Player dictionary
AWAY_PLAYERS_BY_ID = {}
HOME_PLAYERS_BY_ID = {}

# Current batter index in batting order
AWAY_CURRENT_BATTER_IDX = 0
HOME_CURRENT_BATTER_IDX = 0


def get_data(url):
    """
    The data pump

    :param url:
    :return:
    """
    try:
        results = requests.get(url).json()
        if 'messageNumber' in results:
            sys.exit('ERROR:  {} - {}'.format(results['messageNumber'], results['message']))
    except:
        sys.exit('An unhandled exception occurred retrieving data from MLB.')

    return results


def load_teams():
    """
    Get all active MLB teams and load into dictionaries for cross-reference:
        TEAM_NAMES_BY_ABBREV(abbreviation -> full name)
        TEAM_ABBREVS_BY_NAME(full name -> abbreviation)
        TEAM_ABBREVS_BY_ID(id -> abbreviations)

    :return:  Nothing
    """

    # only retrieve certain fields
    fields = '&fields=teams,0,id,name,abbreviation'
    teams = get_data(API_TEAMS_URL + fields)['teams']

    # load dictionaries using specific attributes of teams
    for team in teams:
        TEAM_NAMES_BY_ABBREV.update({team['abbreviation']: team['name']})
        TEAM_ABBREVS_BY_NAME.update({team['name']: team['abbreviation']})
        TEAM_ABBREVS_BY_ID.update({team['id']: team['abbreviation']})

    return


def validate_team_name(team, attr='abbrev'):
    """

    :param team:
    :param attr:
    :return:
    """
    if attr == 'abbrev':
        return next((abbrev for abbrev in TEAM_NAMES_BY_ABBREV.keys() if abbrev == team.upper()), False)
    if attr == 'name':
        return next((name for name in TEAM_ABBREVS_BY_NAME.keys() if name == team.upper()), False)
    if attr == 'id':
        return next((id for id in TEAM_ABBREVS_BY_ID.keys() if int(id) == int(team)), False)


def find_gamepk(team1, team2, game_date, game_number=1):
    """
    Find the game id using team names and date.  Game number defaults to first game.
    :param team1:
    :param team2:
    :param game_date:
    :param game_number:
    :return:
    """
    game_pk = 0  # no game today

    try:
        # validate team names
        if not validate_team_name(team1):
            sys.exit('ERROR: Invalid first team name: {}'.format(team1))
        if team2 != '':
            if not validate_team_name(team2):
                sys.exit('ERROR: Invalid second team name: {}'.format(team2))

        # only retrieve certain fields
        fields = '&fields=dates,games,gamePk,teams,team,name,gameNumber'
        schedule = get_data(API_SCHEDULE_URL.format(game_date) + fields)

        # TODO use game_number for double-headers

        # loop through games looking for team(s)
        for games in schedule['dates'][0]['games']:

            # only one team specified -- could be home or away
            if team2 == '':
                if games['teams']['away']['team']['name'] == TEAM_NAMES_BY_ABBREV[team1] or \
                        games['teams']['home']['team']['name'] == TEAM_NAMES_BY_ABBREV[team1]:
                    game_pk = games['gamePk']
                    break
            else:
                # both teams specified
                if (games['teams']['away']['team']['name'] == TEAM_NAMES_BY_ABBREV[team1] and
                    games['teams']['home']['team']['name'] == TEAM_NAMES_BY_ABBREV[team2]) or \
                        (games['teams']['away']['team']['name'] == TEAM_NAMES_BY_ABBREV[team2] and
                         games['teams']['home']['team']['name'] == TEAM_NAMES_BY_ABBREV[team1]):
                    game_pk = games['gamePk']
                    break
    except:
        game_pk = 0  # no game found
    return game_pk


def find_todays_gamepk(team_abbrev):
    """
    Find today's game for specified team.  Formats date and calls find_gamepk()

    :param team_abbrev:
    :return:
    """
    today = datetime.datetime.today().strftime('%m/%d/%Y')
    game_id = find_gamepk(team_abbrev, '', today)
    return game_id


def load_game_players(game_pk):
    """
    Load the player dictionaries with the players in today's game.
    *_PLAYERS_BY_ID(id -> full name)

    :param game_pk:
    :return:
    """
    # only retrieve certain fields
    fields = '?fields=teams,away,home,players,fullName,id'
    boxscore = get_data(API_BOXSCORE_URL.format(game_pk) + fields)

    # away players
    for player_id in boxscore['teams']['away']['players']:
        id = boxscore['teams']['away']['players'][str(player_id)]['person']['id']
        name = boxscore['teams']['away']['players'][str(player_id)]['person']['fullName']
        AWAY_PLAYERS_BY_ID.update({id: name})

    # home players
    for player_id in boxscore['teams']['home']['players']:
        id = boxscore['teams']['home']['players'][str(player_id)]['person']['id']
        name = boxscore['teams']['home']['players'][str(player_id)]['person']['fullName']
        HOME_PLAYERS_BY_ID.update({id: name})

    return


def clear_screen():
    """
    Clears the screen before the scoreboard refreshes.

    :return:
    """
    # Try to clear the screen between each redraw of scoreboard
    if os.name.upper() == 'NT':
        os.system('cls')
    else:
        print('\n\n\n\n\n')
    return


def get_home_away_team_abbrevs(game_pk):
    """
    For a given team id, return away and home team abbrev.

    :param game_pk:
    :return:
    """

    # only retrieve certain fields
    fields = '?fields=teams,away,home,team,id'
    boxscore = get_data(API_BOXSCORE_URL.format(game_pk) + fields)

    # get away and home teams ids
    away_team_id = int(boxscore['teams']['away']['team']['id'])
    home_team_id = int(boxscore['teams']['home']['team']['id'])

    # return abbrevs for away and home team
    return TEAM_ABBREVS_BY_ID[away_team_id], TEAM_ABBREVS_BY_ID[home_team_id]


def get_team_rhe(game_pk):
    """
    Given a game id, return away and home teams' runs, hits, and errors as two lists

    :param game_pk:
    :return:
    """

    # TODO - should this use fields?

    # get linescore for specific game
    linescore = get_data(API_LINESCORE_URL.format(game_pk))

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


def get_game_status(game_pk):
    """
    Given a game id, determine the game's status

    :param game_pk:
    :return:
    """

    # TODO - should this use fields?
    # get data from livefeed
    livefeed = get_data(API_LIVEFEED_URL.format(game_pk))

    # IN PROGRESS, FINAL, GAME OVER, DELAYED, etc.
    return livefeed['gameData']['status']['detailedState']


def get_game_date_time(game_pk):
    """
    Get the local date and time the game will be/was scheduled

    :param game_pk:
    :return:
    """
    # only retrieve certain fields
    fields = '?fields=gameData,datetime,originalDate,time,ampm'
    livefeed = get_data(API_LIVEFEED_URL.format(game_pk) + fields)

    game_date = str(livefeed['gameData']['datetime']['originalDate']).replace('-', '/')
    game_time = livefeed['gameData']['datetime']['time'] + livefeed['gameData']['datetime']['ampm']

    # return game date with time
    return '{} {}'.format(game_date, game_time)


def build_team_names_with_record(away_line, home_line, game_pk):
    """
    Build the team abbreviation and win-loss record as the 0th element of the
    away_line and home_line.

    Result should look like:
        away_line['WSH (1-1)']
        home_line['LAD (1-1)']

    :param away_line:
    :param home_line:
    :param game_pk:
    :return:
    """

    # only retrieve certain fields
    fields = '?fields=teams,away,home,team,id,name,record,wins,losses'
    boxscore = get_data(API_BOXSCORE_URL.format(game_pk) + fields)

    # get team wins and losses
    away_team_win = boxscore['teams']['away']['team']['record']['wins']
    away_team_loss = boxscore['teams']['away']['team']['record']['losses']
    home_team_win = boxscore['teams']['home']['team']['record']['wins']
    home_team_loss = boxscore['teams']['home']['team']['record']['losses']

    # get team abbrevs using team ids
    away_team_name = TEAM_ABBREVS_BY_ID[int(boxscore['teams']['away']['team']['id'])]
    home_team_name = TEAM_ABBREVS_BY_ID[int(boxscore['teams']['home']['team']['id'])]

    # return two lists containing a single element, the formatted team name with record
    # this ends up being the first (0th) element of the list containing the scoreboard
    # column values.
    away_line.append('{:<3} ({:>3}-{:<3})'.format(away_team_name, away_team_win, away_team_loss))
    home_line.append('{:<3} ({:>3}-{:<3})'.format(home_team_name, home_team_win, home_team_loss))

    return away_line, home_line


def build_innings(header_line, away_line, home_line, game_pk):
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
    :param game_pk:
    :return:
    """
    inning_num = 0

    # get game status to know how to handle final inning
    game_status = get_game_status(game_pk)

    # if game not started, ensure blank scoreboard by skipping all of this logic
    if game_status.upper() == 'IN PROGRESS' or game_status[:7].upper() == 'DELAYED' or \
            game_status.upper() == 'FINAL' or game_status.upper() == 'GAME OVER':

        # only retrieve certain fields
        fields = '?fields=currentInning,inningHalf,inningState,isTopInning,innings,num,home,away,runs'
        linescore = get_data(API_LINESCORE_URL.format(game_pk) + fields)

        # get inning status, etc.
        inning_half = linescore['inningHalf']
        current_inning = int(linescore['currentInning'])
        inning_state = linescore['inningState']
        # is_top_inning = linescore['isTopInning']
        # inning_num = 0

        # process each inning
        for inning in linescore['innings']:

            inning_num = int(inning['num'])

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
                elif game_status.upper() == 'FINAL' or game_status.upper() == 'GAME OVER':
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


def get_game_note(game_pk):
    """
    Get any game notes (rare)

    :param game_pk:
    :return:
    """
    note = ''

    # only retrieve certain fields
    fields = '?fields=note'
    linescore = get_data(API_LINESCORE_URL.format(game_pk) + fields)

    # if there is a note, return it
    if 'note' in linescore:
        note = linescore['note']

    return note


def build_dueup_batters_line(game_pk, inning_half):
    """
    Return a string containing the names and averages of the next three due up
    hitters.  Only shown during inning breaks.

    :param game_pk:
    :param inning_half:
    :return:
    """

    # TODO - this does not return the correct batters

    # make sure to use global batter indexes
    global HOME_CURRENT_BATTER_IDX
    global AWAY_CURRENT_BATTER_IDX

    # three element list to hold next three due up batters
    due_up_batters = ['', '', '']

    # only retrieve certain fields
    fields = '?fields=teams,away,home,battingOrder'
    batting_order = get_data(API_BOXSCORE_URL.format(game_pk) + fields)

    # away
    if inning_half.upper() == 'TOP' or inning_half.upper() == 'END':
        # get a list of player ids representing batting order
        bat_order = batting_order['teams']['away']['battingOrder']
        # the current batter idx value is set in the build pitcher batter line function
        current_idx = AWAY_CURRENT_BATTER_IDX
    # home
    else:
        bat_order = batting_order['teams']['home']['battingOrder']
        current_idx = HOME_CURRENT_BATTER_IDX

    # rotate to top of order if necessary
    next_idx = current_idx + 1 if current_idx + 1 <= 8 else 0

    for i in range(0, 3):
        batter_id = bat_order[next_idx]

        # away
        if inning_half.upper() == 'TOP' or inning_half.upper() == 'END':
            batter_name = AWAY_PLAYERS_BY_ID[batter_id]
        # home
        else:
            batter_name = HOME_PLAYERS_BY_ID[batter_id]

        # get the batters stats
        batter_stats = get_batter_stats(game_pk, batter_id)

        # format each batters line
        due_up_batters[i] = '{} ({}-{}), {} AVG'.format(batter_name, batter_stats[0], batter_stats[1],
                                                        batter_stats[2])
        # cycle through line up
        next_idx = next_idx + 1 if next_idx + 1 <= 8 else 0

    # build output line
    return '\nDue up:  {}\n         {}\n         {}\n'.format(due_up_batters[0], due_up_batters[1],
                                                              due_up_batters[2])


def format_status_lines_with_diamond(base_runners, bso_line, matchup_line, commentary_line, last_pitch, sb_width):
    """

    :param base_runners:
    :param commentary_line:
    :param sb_width:
    :return:
    """

    out_lines = []

    # first line of output is BSO line
    out_lines.append('{}| {}'.format(bso_line, matchup_line))

    # commentary_line += '\n' + last_pitch

    # format commentary around diamond
    for i in range(0, len(base_runners)):
        if len(commentary_line) > 0:
            out_lines.append(base_runners[i] + commentary_line[:(sb_width - len(base_runners[i]))])
            commentary_line = commentary_line[(sb_width - len(base_runners[i])):]
        else:
            out_lines.append(base_runners[i])

        # if commentary does not take up all the lines needed for the diamond, break here
        # so last pitch info will go here
        # if len(commentary_line) == 0:
        #    break

    # format any remaining commentary lines
    while len(commentary_line) > sb_width:
        out_lines.append(commentary_line[:sb_width])
        commentary_line = commentary_line[sb_width:]

    # append last pitch info
    out_lines.append('             {}'.format(last_pitch.strip()))

    return out_lines


def get_last_play_description(game_pk, inning_state):
    """

    :param game_pk:
    :param inning_state:
    :return:
    """
    last_play = ''

    # only retrieve certain fields
    fields = '?fields=currentPlay,result,event,description,atBatIndex,allPlays'
    play_by_play = get_data(API_PLAYBYPLAY_URL.format(game_pk) + fields)

    try:
        # TODO - get strike outs when last play and plays during at bat like caught stealing
        # get play by play description
        current_play_index = int(play_by_play['currentPlay']['atBatIndex'])

        if current_play_index > 1:
            if inning_state.upper() != 'MIDDLE' and inning_state.upper() != 'END':
                current_play_index -= 1

            # clean up description
            description = play_by_play['allPlays'][current_play_index]['result']['description']
            re.sub(' +', ' ', description)
            re.sub('\n', ' ', description)

            last_play = 'Last play: {} - {}'.format(play_by_play['allPlays'][current_play_index]['result']['event'], description)

    except:
        last_play = ''

    return last_play


def build_win_lose_pitcher_line(game_pk):
    """

    :param game_pk:
    :return:
    """

    # only retrieve certain fields
    fields = '?fields=liveData,decisions,winner,loser,id,fullName,liveData,boxscore,teams,away,home,pitchers,players,seasonStats,pitching,wins,losses'
    decisions = get_data(API_LIVEFEED_URL.format(game_pk) + fields)

    winner = decisions['liveData']['decisions']['winner']['fullName']
    winner_id = decisions['liveData']['decisions']['winner']['id']
    loser = decisions['liveData']['decisions']['loser']['fullName']
    loser_id = decisions['liveData']['decisions']['loser']['id']

    # get pitchers wins, loses, and ERA
    winner_wl = get_pitcher_stats(game_pk, winner_id)
    loser_wl = get_pitcher_stats(game_pk, loser_id)
    return 'Winner: {} ({}-{}, {}) Loser: {} ({}-{}, {})'.format(winner, winner_wl[0],
                                                                 winner_wl[1], winner_wl[2],
                                                                 loser, loser_wl[0], loser_wl[1],
                                                                 loser_wl[2])


def get_batter_stats(game_pk, batter_id):
    """

    :param game_pk:
    :param batter_id:
    :return:
    """
    # stats: hits, atBats, avg
    stats = ['', '', '']

    # only retrieve certain fields
    fields = '?fields=teams,home,away,players,stats,batting,hits,atBats,seasonStats,avg'
    batter_stats = get_data(API_BOXSCORE_URL.format(game_pk) + fields)

    # away
    for player in batter_stats['teams']['away']['players']:
        if player == 'ID' + str(batter_id):
            stats[1] = batter_stats['teams']['away']['players']['ID' + str(batter_id)]['stats']['batting']['atBats']
            stats[0] = batter_stats['teams']['away']['players']['ID' + str(batter_id)]['stats']['batting']['hits']
            stats[2] = batter_stats['teams']['away']['players']['ID' + str(batter_id)]['seasonStats']['batting']['avg']
            break

    # home
    if stats[1] == '':
        for player in batter_stats['teams']['home']['players']:
            if player == 'ID' + str(batter_id):
                stats[1] = batter_stats['teams']['home']['players']['ID' + str(batter_id)]['stats']['batting']['atBats']
                stats[0] = batter_stats['teams']['home']['players']['ID' + str(batter_id)]['stats']['batting']['hits']
                stats[2] = batter_stats['teams']['home']['players']['ID' + str(batter_id)]['seasonStats']['batting'][
                    'avg']
                break

    return stats


def get_inning_half(game_pk):
    fields = '?fields=currentInningOrdinal,inningHalf,inningState'
    linescore = get_data(API_LINESCORE_URL.format(game_pk) + fields)
    inning_half = '{} {}'.format(linescore['inningState'], linescore['currentInningOrdinal'])
    return inning_half


def get_pitcher_stats(game_pk, pitcher_id):
    """

    :param game_pk:
    :param pitcher_id:
    :return:
    """
    # stats:  wins, losses, era
    stats = []

    # only retrieve certain fields
    fields = '?fields=teams,home,away,pitchers,players,seasonStats,pitching,era,wins,losses'
    pitcher_stats = get_data(API_BOXSCORE_URL.format(game_pk) + fields)

    stats = ['0', '0', '-.--']
    found = False

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
                stats[2] = pitcher_stats['teams']['home']['players']['ID' + str(pitcher_id)]['seasonStats']['pitching'][
                    'era']
                stats[0] = pitcher_stats['teams']['home']['players']['ID' + str(pitcher_id)]['seasonStats']['pitching'][
                    'wins']
                stats[1] = pitcher_stats['teams']['home']['players']['ID' + str(pitcher_id)]['seasonStats']['pitching'][
                    'losses']
                found = True
                break

    return stats


def save_current_batter(game_pk, batter_id, inning_half):
    """
    Save the index of the current batter in the batting order for use
    in the due up function.

    :param game_pk:
    :param batter_id:
    :param inning_half:
    :return:
    """

    # make sure to update the global batter indexes
    global AWAY_CURRENT_BATTER_IDX
    global HOME_CURRENT_BATTER_IDX

    # only retrieve certain fields
    fields = '?fields=teams,away,home,batters'
    bat_order = get_data(API_BOXSCORE_URL.format(game_pk) + fields)

    # away
    if inning_half.upper() == 'TOP':
        for i, batter in enumerate(bat_order['teams']['away']['batters']):
            if batter == batter_id:
                AWAY_CURRENT_BATTER_IDX = i
                break
    # home
    else:
        for i, batter in enumerate(bat_order['teams']['home']['batters']):
            if batter == batter_id:
                HOME_CURRENT_BATTER_IDX = i
                break
    return


def build_pitcher_batter_line(game_pk):
    """

    get pitcher-batter match up with stats

    :param game_pk:
    :return:
    """

    # only retrieve certain fields
    fields = '?fields=currentPlay,matchup,batter,pitcher,id,fullName,about,halfInning'
    play_by_play = get_data(API_PLAYBYPLAY_URL.format(game_pk))

    pitcher_name = play_by_play['currentPlay']['matchup']['pitcher']['fullName']
    pitcher_name = pitcher_name.split(' ')[1]
    batter_name = play_by_play['currentPlay']['matchup']['batter']['fullName']
    batter_name = batter_name.split(' ')[1]
    pitcher_id = play_by_play['currentPlay']['matchup']['pitcher']['id']
    batter_id = play_by_play['currentPlay']['matchup']['batter']['id']

    # get stats
    pitcher_stats = get_pitcher_stats(game_pk, pitcher_id)
    batter_stats = get_batter_stats(game_pk, batter_id)

    # save current batter for use in due up method
    inning_half = play_by_play['currentPlay']['about']['halfInning']
    save_current_batter(game_pk, batter_id, inning_half)

    # return pitcher-batter matchup line
    return 'Pitcher: {} ({} ERA) - Batter: {} ({}-{}, {} AVG)'.format(pitcher_name, pitcher_stats[2], batter_name,
                                                                      batter_stats[0], batter_stats[1],
                                                                      batter_stats[2])


def build_bso_line(game_pk):
    """
    Build string containing current balls, strikes, and outs

    :param game_pk:
    :return:
    """
    linescore = get_data(API_LINESCORE_URL.format(game_pk))
    # return 'Balls: {} Strikes: {} Outs: {}\n'.format(linescore['balls'],
    #                                                   linescore['strikes'], linescore['outs'])
    return 'B:{} S:{} O:{}'.format(linescore['balls'],
                                   linescore['strikes'], linescore['outs'])


def get_last_pitch(game_pk):
    # only retrieve certain fields
    fields = '?fields=currentPlay,playEvents,details,type,description,pitchData,endSpeed,pitchNumber'
    play_by_play = get_data(API_PLAYBYPLAY_URL.format(game_pk) + fields)
    result = 'Last pitch: {} - {} MPH'

    # TODO - not sure this returns the last pitch.  It doesn't line up with TV
    try:
        events = play_by_play['currentPlay']['playEvents']
        last_event = len(events) - 1
        # for event in events:
        type_of_pitch = events[last_event]['details']['type']['description']
        speed_of_pitch = events[last_event]['pitchData']['endSpeed']
        # pitch_number = events[last_event]['pitchNumber']

        return result.format(type_of_pitch, speed_of_pitch)
    except:
        return ''


def build_diamond_with_base_runners(game_pk):
    """

    :param game_pk:
    :return:
    """
    # return list:  home = 0, first = 1, second = 2, third = 3
    # ex. runner on second:  [o][][X][]
    # home is always 'o' (for batter)
    bases = ['o', ' ', ' ', ' ']
    base_lines = ['', '', '']

    # only retrieve certain fields
    fields = '?fields=liveData,plays,currentPlay,atBatIndex,allPlays,runners,movement,end,isOut'
    livedata = get_data(API_LIVEFEED_URL.format(game_pk) + fields)

    # the current play is the batter s subtract one to get runners before this batter
    current_play_index = int(livedata['liveData']['plays']['currentPlay']['atBatIndex']) - 1
    runners = livedata['liveData']['plays']['allPlays'][current_play_index]['runners']

    # TODO fix logic?
    # work back through the last 4 plays to find runners.  If the current play did not
    # result in runner movement, the runners field will be blank, thus 'losing' and
    # runners who were on base.  4 is just a guess.
    for p in range(current_play_index, current_play_index - 4, -1):
        runners = livedata['liveData']['plays']['allPlays'][current_play_index]['runners']
        if runners is not None:
            for runner in runners:
                if runner['movement']['isOut'] is None or runner['movement']['isOut'] is False:
                    abase = runner['movement']['end']
                    if abase != 'score':
                        base_idx = int(abase[:1])
                        bases[base_idx] = 'X'


    # reformat base configuration
    base_lines[0] = '   [' + bases[2] + ']     | '
    base_lines[1] = '[' + bases[3] + ']   [' + bases[1] + ']  | '
    base_lines[2] = '   [' + bases[0] + ']     | '

    return base_lines


def build_sched_pitchers_line(game_pk):
    """

    :param game_pk:
    :return:
    """
    # only retrieve certain fields
    fields = '?fields=gameData,probablePitchers,away,fullName,id,home'
    livedata = get_data(API_LIVEFEED_URL.format(game_pk) + fields)

    away_pitcher_name = livedata['gameData']['probablePitchers']['away']['fullName']
    away_pitcher_name = '{} {}'.format(str(away_pitcher_name.split(',')[1]).strip(),
                                       str(away_pitcher_name.split(',')[0]).strip())
    away_pitcher_id = livedata['gameData']['probablePitchers']['away']['id']
    home_pitcher_name = livedata['gameData']['probablePitchers']['home']['fullName']
    home_pitcher_name = '{} {}'.format(str(home_pitcher_name.split(',')[1]).strip(),
                                       str(home_pitcher_name.split(',')[0]).strip())
    home_pitcher_id = livedata['gameData']['probablePitchers']['home']['id']

    # use id to get record and ERA
    away_pitcher_stats = get_pitcher_stats(game_pk, away_pitcher_id)
    home_pitcher_stats = get_pitcher_stats(game_pk, home_pitcher_id)

    return '{} ({}-{}, {} ERA) vs. {} ({}-{}, {} ERA)'.format(away_pitcher_name, away_pitcher_stats[0],
                                                              away_pitcher_stats[1], away_pitcher_stats[2],
                                                              home_pitcher_name, home_pitcher_stats[0],
                                                              home_pitcher_stats[1], home_pitcher_stats[2])


def format_due_up_status(commentary, due_up_batters, sb_width):
    """
    Format commentary so it doesn't extend past width of scoreboard
    :param commentary:
    :param due_up_batters:
    :param sb_width:
    :return:
    """

    out_lines = []
    formated_line = ''
    if len(commentary) > sb_width:
        while len(commentary) > sb_width:
            out_lines.append(commentary[:sb_width])
            commentary = commentary[sb_width:]

    # catch short commentary or last line of long commentary
    out_lines.append(commentary)

    for line in out_lines:
        formated_line += line + '\n'

    formated_line.strip()
    formated_line += due_up_batters

    return formated_line


def build_game_status_info(game_pk, sb_width):
    """

    :param game_pk:
    :param sb_width:
    :return:
    """

    status_line = ''
    commentary_line = ''

    # get game status
    game_status = get_game_status(game_pk)

    if game_status.upper() != 'FINAL' and game_status.upper() != 'GAME OVER' and game_status.upper() != 'SCHEDULED' and \
            game_status.upper() != 'WARMUP' and game_status.upper() != 'PRE-GAME':

        # get game status
        fields = '?fields=currentInningOrdinal,inningHalf,inningState'
        linescore = get_data(API_LINESCORE_URL.format(game_pk) + fields)

        # get play commentary
        # TODO - loop if commentary longer than two lines.  See elsewhere for logic
        commentary_line = get_last_play_description(game_pk, linescore['inningState'])

        # between innings show due up batters
        if linescore['inningState'].upper() == 'END' or linescore['inningState'].upper() == 'MIDDLE':
            due_up_batters = build_dueup_batters_line(game_pk, linescore['inningState'])
            # status_line = commentary_line + due_up_batters
            status_line = format_due_up_status(commentary_line, due_up_batters, sb_width)

        else:

            # get last pitch info
            last_pitch = get_last_pitch(game_pk)

            # get Balls-Strikes-Outs
            bso_line = build_bso_line(game_pk)
            # status_line += bso_line

            # get pitcher - batter match up
            match_up_line = build_pitcher_batter_line(game_pk)
            # status_line += match_up_line

            # get the base runners as a formatted list
            base_runners = build_diamond_with_base_runners(game_pk)

            # format status to fit on screen
            fmt_bases_commentary = format_status_lines_with_diamond(base_runners, bso_line, match_up_line, commentary_line,
                                                                    last_pitch, sb_width)

            # add the formatted lines to the output string
            for line in fmt_bases_commentary:
                status_line += line + '\n'
            status_line.strip('\n')


    # !!! this seems to duplicate what is in run_scoreboard()

    # game delayed
        if game_status[:7].upper() == 'DELAYED':
            note = get_game_note(game_pk)
            if len(note) > 0:
                status_line += '{} - {}'.format(game_status, note)
            else:
                status_line += game_status

    # game over
    elif game_status.upper() == 'FINAL' or game_status.upper() == 'GAME OVER':
        status_line = '{}\n{}'.format(build_win_lose_pitcher_line(game_pk), game_status)

    # scheduled or warmup
    elif game_status.upper() == 'SCHEDULED' or game_status.upper() == 'WARMUP' or game_status.upper() == 'PRE-GAME':
        status_line = '{}\n{}'.format(build_sched_pitchers_line(game_pk), game_status)

    # unknown status occurred
    else:
        note = get_game_note(game_pk)
        if len(note) > 0:
            status_line = '{}: {}'.format(game_status, note)
        else:
            status_line = game_status

    return status_line


def run_scoreboard(game_pk):
    """

    :param gamePk:
    :return:
    """
    global away_team
    global home_team

    refresh_rate = int(config.SB_CONFIG['refresh'])
    delay_refresh_rate = int(config.SB_CONFIG['delay'])

    # Load player dictionaries
    load_game_players(game_pk)

    # Loop until the game is over
    end_loop = False
    while not end_loop:

        clear_screen()

        # Init vars for redraw
        scoreboard_title = ''
        game_note = ''
        game_status = ''
        scoreboard_inning_headers = []
        away_line_score = []
        home_line_score = []
        scoreboard_totals_headers = ['R', 'H', 'E']
        away_totals = ['0', '0', '0']
        home_totals = ['0', '0', '0']

        # print update header
        print('Retrieving game data from MLB (' + datetime.datetime.now().strftime('%m/%d/%Y %X') + ')...\n')

        # Get away and home teams
        away_team, home_team = get_home_away_team_abbrevs(game_pk)

        # TODO get boxscore/live once and send to previous and next functions?

        # Get game status
        game_status = get_game_status(game_pk)

        # Load team totals
        if game_status.upper() == 'IN PROGRESS' or game_status.upper() == 'FINAL' or game_status.upper() == 'GAME OVER' \
                or game_status[:7].upper() == 'DELAYED':
            away_totals, home_totals = get_team_rhe(game_pk)

        # Get game note
        game_note = get_game_note(game_pk)

        # Add team names and records to line scores
        away_line_score, home_line_score = build_team_names_with_record(away_line_score, home_line_score, game_pk)

        # TODO - move this to the build_innings
        # Enter inning half or game status in first element of inning header
        team_name_length = max(len(away_line_score[0]), len(home_line_score[0]))

        if game_status.upper() != 'IN PROGRESS' and game_status[:7].upper() != 'DELAYED':
            inning_half = ' '
        else:
            inning_half = get_inning_half(game_pk)

        if team_name_length > len(inning_half):
            inning_half += ' ' * (team_name_length - len(inning_half))

        scoreboard_inning_headers.append(inning_half)

        # Fill innings
        scoreboard_inning_headers, away_line_score, home_line_score \
            = build_innings(scoreboard_inning_headers, away_line_score, home_line_score, game_pk)

        # Append team totals to line scores
        scoreboard_inning_headers += scoreboard_totals_headers
        away_line_score += away_totals
        home_line_score += home_totals

        # Build bars according to lengths
        double_bar = '=' * ((len(scoreboard_inning_headers * 5) + len(scoreboard_inning_headers[0])) - 3)
        single_bar = '-' * len(double_bar)

        game_status_info = build_game_status_info(game_pk, len(double_bar)).strip('\n')

        # ---- Print the scoreboard ----

        # print game info line
        print('{} @ {}: {} (Game #{})'.format(TEAM_NAMES_BY_ABBREV[away_team], TEAM_NAMES_BY_ABBREV[home_team],
                                              get_game_date_time(game_pk), game_pk))

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
        if game_status.upper() == 'FINAL' or game_status.upper() == 'GAME OVER':
            if game_status.upper() == 'GAME OVER':
                end_loop = False
            else:
                end_loop = True

        # Game not started
        if game_status.upper() == 'SCHEDULED' or game_status.upper() == 'WARMUP':
            if game_status.upper() == 'SCHEDULED':
                end_loop = True

        # any other not 'in progress' state
        if game_status.upper() != 'IN PROGRESS':
            print(game_status_info)

        # Print game note if there is one
        if game_note:
            if len(game_note) > len(double_bar):
                print('Note: ' + game_note[:len(double_bar) - 5])
                print('      ' + game_note[len(double_bar) - 5 + 1:])
            else:
                print('Note: ' + game_note)

        if game_status.upper() == 'IN PROGRESS':
            print(game_status_info)

        print(double_bar)

        # Print banner
        print(COPYRIGHT)
        sys.stdout.flush()

        # Sleep for a while and continue with loop
        if not end_loop:
            if game_status[:7].upper() == 'DELAYED' or game_status.upper() == 'WARMUP' or game_status.upper() == ' PRE-GAME':
                time.sleep(delay_refresh_rate)
            else:
                time.sleep(refresh_rate)

    return


def print_help():
    """
    Print basic usage instructions.

    :return:
    """

    print(COPYRIGHT)
    print('Usage:')
    print('>python MLB-live-scoreboard.py [favorite_team] [away_team, home_team, game_date]')
    print('For example:')
    print('python MLB-live-scoreboard.py WSH')
    print('python MLB-live-scoreboard.py WSH PHI 04/10/2019')
    print('')
    print('No arguments reads data from config.py file.')
    print('Date format:  MM/DD/YYYY')
    print('Valid team names:')
    for key in sorted(TEAM_NAMES_BY_ABBREV.keys()):
        print('  {} - {}'.format(key, TEAM_NAMES_BY_ABBREV[key]))
    print()
    return


def validate_date(game_date):
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


##### MAIN #####

# Init some stuff
load_teams()
game_pk = 0
home_team = ''
away_team = ''

# Print banner
print(COPYRIGHT)

# no args -- use team in config.py
if len(sys.argv) == 1:
    # print('DEBUG: using favorite team')
    favorite_team = config.SB_CONFIG['team']
    if not validate_team_name(favorite_team):
        sys.exit('ERROR: Invalid team name found in config.py: {}'.format(favorite_team))
    else:
        game_pk = find_todays_gamepk(favorite_team)

# one arg = single team or --help
elif len(sys.argv) == 2:
    if sys.argv[1] == '--help':
        print_help()
        sys.exit(0)
    else:
        # print('DEBUG: single team on command line')
        away_team = sys.argv[1]
        if not validate_team_name(away_team):
            sys.exit('ERROR: Invalid team name on command line: {}'.format(away_team))
        else:
            game_pk = find_todays_gamepk(away_team)

# full command line specs = away_team home_team game_date
elif len(sys.argv) == 4:
    # print('DEBUG: full command line')
    away_team = sys.argv[1]
    if not validate_team_name(away_team):
        sys.exit('ERROR: Invalid away team name: {}'.format(away_team))

    home_team = sys.argv[2]
    if not validate_team_name(home_team):
        sys.exit('ERROR: Invalid home team name: {}'.format(home_team))

    game_date = sys.argv[3]
    if not validate_date(game_date):
        sys.exit('ERROR:  Invalid date: {}'.format(game_date))

    game_pk = find_gamepk(home_team, away_team, game_date)

# else gather data interactively from user
else:
    # home_team, away_team, game_date = get_user_inputs()
    # game_pk = find_gamepk(away_team, home_team, game_date)
    print_help()

# run scoreboard if gamepk found
if game_pk != 0:
    run_scoreboard(game_pk)

else:
    if home_team != '' and away_team != '':
        print('No game found for {} at {} on {}'.format(away_team, home_team, game_date))

    else:
        print('{} has no scheduled game today.'.format(config.SB_CONFIG['team']))

# <SDG><
