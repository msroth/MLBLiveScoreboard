"""
=====================================================================
NAME:    MLBLiveScoreboard.py (C) 2018
PURPOSE: To produce a simple, live scoreboard to track MLB game play
         on your computer.

         EXAMPLE OUTPUT

         Retrieving game data from MLB (2018-06-22 10:38:04)...
         Mets @ Rockies: 2018/06/21 3:10PM
         =========================================================================
                     | 1  | 2  | 3  | 4  | 5  | 6  | 7  | 8  | 9  | R  | H  | E  |
         -------------------------------------------------------------------------
          NYM (31-41)  1    0    1    0    0    0    0    1    1  | 4    11   0
          COL (37-38)  3    2    0    0    0    0    0    1    x  | 6    9    0
         -------------------------------------------------------------------------
         Winner: Kyle Freeland (7-6), Loser: Steven Matz (3-5)
         Final
         =========================================================================
         MLBLiveScoreboard, v0.02

AUTHOR:  MSRoth
USAGE:   >python mlblivescoreboard <date of game> <away team> <home team> <game number>
COMMENTS:
    - this script makes use of the mlbgame package by panzarino
      (https://github.com/panzarino/mlbgame) to retrieve and parse
      MLB data.  Note there are a few places in this package that
      require patching to avoid race condition errors with the data.
    - this script has only been tested on Windows running Anaconda 4.1.1
      (Python 3.5.2).
    - the output for live games differs slightly than for completed games.  Live
      games include ball, strikes, outs, bases, and commentary.
    - this is the first Python program I have ever written, so I am sure
      there are a lot of style mistakes and use of brute force where
      finesse is available to a more experienced programmer.
    - the accuracy of the scoreboard is only as good as the MLB XML data
      published at gd2.mlb.com.  Often this data is late, incomplete, and just
      wrong.

TODO:
    - pass in a list of games and show multiple scoreboards at once


=====================================================================
"""

import sys
import datetime
import time
import os

# https://github.com/panzarino/mlbgame
import mlbgame.events
import mlbgame.data
import mlbgame.info
import mlbgame.stats

"""
Sample games for testing
2018-05-13 WAS ARI 1
2018-05-15 NYY WAS 1 -- suspended, resumed 2018-06-18
2018-05-19 LA WAS 1 and 2 -- double header
2018-05-20 DET SEA 1 -- 11 innings
2018-06-02 WAS ATL 1 -- 14 innings
2018-05-18 LA WAS 1 -- postponed

MLB Data URL
http://gd2.mlb.com/components/game/mlb/year_{0}/month_{1:02d}/day_{2:02d}
http://gd2.mlb.com/components/game/mlb/year_2018/month_07/day_11

"""

# Init global variables outside of loop
debug = False  # will only be set to true if command line is not used and will save XML files for debugging
MLB_TEAM_NAMES_DICT = {}
NAME = 'MLBLiveScoreboard, (c)2018 MSRoth'
VERSION = '0.02'
game_status = ''
game_date = ''
away_team = ''
home_team = ''
game_number = 1
now = datetime.datetime.now()
cl = False  # command line flag

"""
Helper functions for team names and abbreviations
"""


def validate_team_abbrev(team_abbrev):
    for key in MLB_TEAM_NAMES_DICT.keys():
        if key.upper() == team_abbrev.upper():
            return True
    print("Please use one of: ")
    for abbrev in sorted(MLB_TEAM_NAMES_DICT.keys()):
        print(abbrev.ljust(3) + ' = ' + MLB_TEAM_NAMES_DICT[abbrev])
    return False


def validate_team_name(team_name):
    for key in MLB_TEAM_NAMES_DICT.keys():
        if MLB_TEAM_NAMES_DICT[key].upper() == team_name.upper():
            return True
    return False


def get_team_name_from_abbrev(team_abbrev):
    for key in MLB_TEAM_NAMES_DICT.keys():
        if key.upper() == team_abbrev.upper():
            return MLB_TEAM_NAMES_DICT[key]
    return ''


def get_team_abbrev_from_name(team_name):
    for key in MLB_TEAM_NAMES_DICT.keys():
        if MLB_TEAM_NAMES_DICT[key].upper() == team_name.upper():
            return key
    return '   '


def build_team_name_dict():
    """
    Build dictionary to hold team names and abbreviations.
      key = abbreviation
      value = team common name
      note:  there seems to be a mismatch in the data for the Oakland Athletics (A's vs. Athletics)
    """

    teams = mlbgame.teams()
    for team in teams:
        # TODO: doesn't work for A's, seems to be mismatch between A's and Athletics
        MLB_TEAM_NAMES_DICT.update({team.club.upper(): team.club_common_name})
    return


def validate_date(date_str):
    """
    A simple way to validate the entered date
    """

    try:
        year, month, day = date_str.split('-')
        datetime.datetime(int(year), int(month), int(day))
    except ValueError:
        return False
    return True


def get_user_input():
    """
    If no command line values were found, prompt user for inputs
    """

    # get date of game
    input_game_date = input('Enter date of game [' + now.strftime('%Y-%m-%d') + ']: ')
    if input_game_date:
        if not validate_date(input_game_date):
            print('Invalid date entered [' + input_game_date + ']')
            sys.exit('Invalid date')
    else:
        input_game_date = now.strftime("%Y-%m-%d")

    # get visiting team
    input_away_team = input('Enter visiting team trigraph (e.g., STL): ')
    if not input_away_team:
        print('Away team cannot be blank')
        sys.exit('Invalid team name')
    if not validate_team_abbrev(input_away_team):
        sys.exit('Invalid team name')

    # get home team
    input_home_team = input('Enter home team tri-graph (e.g., WAS): ')
    if not input_home_team:
        print('Home team cannot be blank')
        sys.exit('Invalid team name')
    if not validate_team_abbrev(input_home_team):
        sys.exit('Invalid team name')

    # get game number (assume 1)
    input_game_number = input('Enter game number (usually 1, unless double-header): ')
    if not input_game_number:
        input_game_number = 1
    else:
        if int(input_game_number) not in range(1, 3):
            print("'" + input_game_number + "' is invalid.  Defaulting to '1'")
            input_game_number = 1

    return input_game_date, get_team_name_from_abbrev(input_away_team), \
           get_team_name_from_abbrev(input_home_team), input_game_number


def get_game_data(mlb_game_date, mlb_away_team, mlb_home_team, mlb_game_number):
    """
    Get game data from MLB using MLBGame package
    """

    print('Retrieving game data from MLB (' + now.strftime('%Y-%m-%d %X') + ')...')

    year, month, mlbgame_day = mlb_game_date.split('-')

    try:
        mlbgame_day = mlbgame.day(int(year), int(month), int(mlbgame_day), home=mlb_home_team, away=mlb_away_team)
        mlbgame_game = mlbgame_day[int(mlb_game_number) - 1]

        # Save XML for debugging and review
        if debug:
            print('[saving data to files for debugging]')
            # write files to examine for debugging
            f = open(mlbgame_game.game_id + "_boxscore.xml", "w", encoding='utf-8')
            box_xml = mlbgame.data.get_box_score(mlbgame_game.game_id).read()
            f.write(box_xml.decode('utf-8'))
            f.close()

            f = open(mlbgame_game.game_id + "_players.xml", "w", encoding='utf-8')
            player_xml = mlbgame.data.get_players(mlbgame_game.game_id).read()
            f.write(player_xml.decode('utf-8'))
            f.close()

            f = open(mlbgame_game.game_id + "_event.xml", "w", encoding='utf-8')
            event_xml = mlbgame.data.get_game_events(mlbgame_game.game_id).read()
            f.write(event_xml.decode('utf-8'))
            f.close()
    except:
        print('ERROR: No game data was found for date and teams')
        sys.exit("No game data found")

    return mlbgame_game


def load_team_totals(mlbgame_game):
    """
    Load team total lists with total runs, hits, errors for game
    """

    away_totals[0] = str(mlbgame_game.away_team_runs)
    away_totals[1] = str(mlbgame_game.away_team_hits)
    away_totals[2] = str(mlbgame_game.away_team_errors)

    home_totals[0] = str(mlbgame_game.home_team_runs)
    home_totals[1] = str(mlbgame_game.home_team_hits)
    home_totals[2] = str(mlbgame_game.home_team_errors)

    # TODO these don't seem right
    # stats = mlbgame.team_stats(mlbgame_game.game_id)
    # away_totals[3] = stats.away_batting.lob
    # home_totals[3] = stats.home_batting.lob

    return


def build_team_names_with_record(mlbgame_overview):
    """
    The first element of the line score is the teams' abbreviation and W-L record
    """

    away_line_score[0] = get_team_abbrev_from_name(mlbgame_overview.away_team_name) + \
        ' (' + str(mlbgame_overview.away_win) + '-' + str(mlbgame_overview.away_loss) + ')'
    away_len = len(away_line_score[0])
    home_line_score[0] = get_team_abbrev_from_name(mlbgame_overview.home_team_name) + \
        ' (' + str(mlbgame_overview.home_win) + '-' + str(mlbgame_overview.home_loss) + ')'
    home_len = len(home_line_score[0])
    if away_len > home_len:
        home_line_score[0] += ' '
    if home_len > away_len:
        away_line_score[0] += ' '
    return


def build_w_l_pitcher_line(mlbgame_game):
    """
    Return a string containing the winning and losing pitchers' names and records
    """

    output = ''
    output = 'Winner: ' + mlbgame_game.w_pitcher + ' (' + str(mlbgame_game.w_pitcher_wins) + \
             '-' + str(mlbgame_game.w_pitcher_losses) + ')'
    output += ', Loser: ' + mlbgame_game.l_pitcher + ' (' + str(mlbgame_game.l_pitcher_wins) + \
              '-' + str(mlbgame_game.l_pitcher_losses) + ')'
    return output


def build_pitcher_batter_line(mlbgame_game, i, s):
    """
    Return a string containing the current pitcher and batter for a live game.  Frequently,
    the batter's name will be incorrect while the B\S\O will be correct.  I believe this is
    the case when the inning event is not updated by MLB until after the event is completed.
    """

    batter_line = ''
    pitcher_line = ''
    output = ''
    innings = mlbgame.game_events(mlbgame_game.game_id)
    player_list = mlbgame.players(mlbgame_game.game_id)

    for inning in innings:
        if inning.num == int(i):
            # print('-inning: ' + inning.nice_output())
            if s.upper() == 'TOP':
                batters = inning.top
                players = player_list.away_players
                pitchers = player_list.home_players
            else:
                batters = inning.bottom
                players = player_list.home_players
                pitchers = player_list.away_players

            for batter in batters:
                # print('-batter: ' + batter.nice_output())
                for player in players:
                    if player.id == batter.batter:
                        # print('-found batter: ' + player.boxname)
                        batter_line = player.boxname + ' (' + player.current_position + ', ' + '{:.3}'.format(
                            player.avg) + ' AVG)'

                        for pitcher in pitchers:
                            # print('-pitcher: ' + str(pitcher.id))
                            if batter.pitcher == pitcher.id:
                                # print('-found pitcher: ' + pitcher.boxname)
                                pitcher_line = pitcher.boxname + ' (' + '{:.3}'.format(pitcher.era) + ' ERA)'
    output = 'Pitching: ' + pitcher_line + '  Batting: ' + batter_line
    return output


def print_help():
    """
    Print a simple help and usage message
    """

    print()
    print(NAME + ' v' + VERSION)
    print('Usage: >python  MLBLiveScoreboard.py <game_date> <away_team> <home_team> <game_number>')
    print('   game_date = YYY-MM-DD')
    print('   away_team and home_team = one of: ' + ','.join(MLB_TEAM_NAMES_DICT.keys()))
    print('   game_number = 1, unless double-header')
    print()
    return


def parse_args():
    """
    Parse and validate arguments passed on the command line.  Invalid arguments will result
    in the script exiting.
    """

    arg_game_date = ''
    arg_away_team = ''
    arg_home_team = ''
    arg_game_number = ''
    have_args = True

    # If no or incorrect number of args, force interactive mode to get inputs
    if len(sys.argv) != 5:
        print_help()
        have_args = False
    else:
        arg_game_date = sys.argv[1]
        arg_away_team = sys.argv[2]
        arg_home_team = sys.argv[3]
        arg_game_number = sys.argv[4]

        # Get game date
        if not validate_date(arg_game_date):
            print("Invalid date entered [" + arg_game_date + "]")
            # sys.exit("Invalid date")
            have_args = False

        # get visiting team
        if not arg_away_team:
            print("Away team cannot be blank")
            # sys.exit("Invalid team name")
            have_args = False
        if not validate_team_abbrev(arg_away_team):
            # sys.exit("Invalid team name")
            have_args = False

        # get home team
        if not arg_home_team:
            print("Home team cannot be blank")
            # sys.exit("Invalid team name")
            have_args = False
        if not validate_team_abbrev(arg_home_team):
            # sys.exit("Invalid team name")
            have_args = False

        # get game number (assume 1)
        if not arg_game_number:
            arg_game_number = 1
        else:
            if int(arg_game_number) not in range(1, 3):
                print("'" + arg_game_number + "' is invalid.  Defaulting to '1'")
            arg_game_number = 1

    # Return the boolean indicating whether valid args were found
    # If args are valid, return them
    return have_args, arg_game_date, get_team_name_from_abbrev(arg_away_team), get_team_name_from_abbrev(
        arg_home_team), arg_game_number


def build_base_and_commentary_lines(game, w):
    """
    Build a list of strings containing the base status and the play commentary.  This is subject to the
    timeliness and content of the MLB data and occasionally lags actual play
    """

    # Init vars to blank
    out_lines = ['', '', '']
    commentary = ''

    # Get the raw base and commentary data
    bases, commentary = get_bases_and_commentary(game.game_id)

    # Build the base configuration
    out_lines[0] = '   [' + bases[1] + ']    | Commentary: '
    out_lines[1] = '[' + bases[2] + ']   [' + bases[0] + '] | '
    out_lines[2] = '   [ ]    | '

    # Add commentary, hard chopped not to extend past end of scoreboard (i.e., wrap)
    if commentary:
        # if len(commentary) > w-24:
        out_lines[0] += commentary[:w - 24]
        commentary = commentary[w - 24:]
        # else:
        #    out_lines[0] += commentary

        for i in range(1, 3):
            out_lines[i] += commentary[:w - 12]
            commentary = commentary[w - 12:]

    """
    # Experiment with bases on right side
    if commentary:
        if len(commentary) > w-24:
            out_lines[0] = 'Top of 1\nBalls: 0 Strikes: 0 Outs: 0\nCommentary: ' + commentary[:w - 24] + ' |    [' + bases[1] + ']'
            commentary = commentary[w-24:]
            out_lines[1] = commentary[:w-12] + ' | [' + bases[2] + ']   [' + bases[0] + ']'
            commentary = commentary[w - 12:]
            out_lines[2] = commentary[:w-12] + ' |    [ ]'
    """

    return out_lines


def get_bases_and_commentary(game_id):
    """
    Return list of strings and a string containing the raw base and commentary data from MLB
    """

    overview = mlbgame.overview(game_id)
    current_inning = overview.inning
    top_bottom = overview.inning_state.upper()
    inning_list = mlbgame.game_events(game_id)

    # Init vars to blank
    commentary = ''
    first = ' '
    second = ' '
    third = ' '

    # Find current inning half
    for inning in inning_list:
        if inning.num == current_inning:
            if top_bottom == 'TOP':
                inn = inning.top
            else:
                inn = inning.bottom

            # Loop through all events and just save data from the last one
            # Kind of a brute for approach
            for event in inn:
                if len(event.nice_output()) > 0 :
                    commentary = event.nice_output()
                else:
                    commentary = ' '
                # get each batters base status
                if len(str(event.b1)) > 0:
                    first = 'x'
                else:
                    first = ' '
                if len(str(event.b2)) > 0:
                    second = 'x'
                else:
                    second = ' '
                if len(str(event.b3)) > 0:
                    third = 'x'
                else:
                    third = ' '

    return [first, second, third], commentary


"""
########## MAIN PROGRAM ##########
"""

# Build the dictionary of team names and tri-graphs
build_team_name_dict()

# Get input args
cl, game_date, away_team, home_team, game_number = parse_args()
debug = False

# If no input args, get input from user interactively
if not cl:
    game_date, away_team, home_team, game_number = get_user_input()
    debug = True

# Loop until the game is over
end_loop = False
while not end_loop:

    # Try to clear the screen between each redraw of scoreboard
    if os.name.upper() == 'NT':
        os.system('cls')
    else:
        print('\n\n\n')

    # Init vars for redraw
    now = datetime.datetime.now()
    scoreboard_title = ''
    game_note = ''
    game_status = ''
    scoreboard_inning_headers = ['', '1', '2', '3', '4', '5', '6', '7', '8',
                                 '9', ]  # init with space for team name and 9 innings
    away_line_score = ['', '', '', '', '', '', '', '', '', '', ]  # init with space for team name and 9 innings
    home_line_score = ['', '', '', '', '', '', '', '', '', '', ]  # init with space for team name and 9 innings

    # Init team total lists
    # removed LOB until it can be corrected
    # away_totals = ['0', '0', '0', '0']
    # home_totals = ['0', '0', '0', '0']
    # scoreboard_totals_headers = ['R', 'H', 'E', 'LOB']
    away_totals = ['0', '0', '0']
    home_totals = ['0', '0', '0']
    scoreboard_totals_headers = ['R', 'H', 'E']

    # Get game data from MLB
    game = get_game_data(game_date, away_team, home_team, game_number)

    # Load team totals
    load_team_totals(game)

    # Get game status and notes
    ov = mlbgame.overview(game.game_id)
    game_status = ov.status
    game_note = ov.note

    # Sometimes boxscore chokes if middle of inning
    # https://github.com/panzarino/mlbgame/issues/62
    # See numerous fixes to game.py and boxscore.py denoted with MSR
    boxscore = mlbgame.box_score(game.game_id)

    # For each inning half, get score and build scoreboard line lists
    innings = boxscore.innings
    for x in innings:
        # If less than 10 innings update lists
        if int(x['inning']) < 10:
            away_line_score[x['inning']] = str(x['away'])
            home_line_score[x['inning']] = str(x['home'])

        # If in extra innings append data to lists
        else:
            scoreboard_inning_headers.append(str(x['inning']))
            away_line_score.append(str(x['away']))
            home_line_score.append(str(x['home']))

        # Special case for inning in progress with no score
        if int(x['inning']) == int(ov.inning) and \
                ov.inning_state.upper() == 'TOP' and \
                (str(x['away'])).strip() == '':
            away_line_score[x['inning']] = '-'

        # Prevent '0' from showing as home score at top and middle of inning
        # I believe this occurs depending upon how the MLB data is formatted
        if int(x['inning']) == int(ov.inning) and \
                (ov.inning_state.upper() == 'TOP' or ov.inning_state.upper() == 'MIDDLE'):
            home_line_score[x['inning']] = ' '

        # Special case for inning in progress with no score
        if int(x['inning']) == int(ov.inning) and \
                ov.inning_state.upper() == 'BOTTOM' and \
                (str(x['home'])).strip() == '':
            home_line_score[x['inning']] = '-'

    # Add team names and records to line scores
    build_team_names_with_record(ov)
    team_name_length = max(len(away_line_score[0]), len(home_line_score[0]))
    scoreboard_inning_headers[0] = ' ' * len(away_line_score[0])

    # Append team totals to line scores
    scoreboard_inning_headers += scoreboard_totals_headers
    away_line_score += away_totals
    home_line_score += home_totals

    # Build bars according to lengths
    double_bar = '=' * ((len(scoreboard_inning_headers * 5) + len(scoreboard_inning_headers[0])) - 3)
    single_bar = '-' * len(double_bar)

    # ---- Print the scoreboard ----
    print(ov.away_team_name + ' @ ' + ov.home_team_name + ': ' + ov.time_date + ov.home_ampm)
    print(double_bar)

    # Print inning headers
    output = ''
    for x in scoreboard_inning_headers:
        output += ' ' + str(x).ljust(3) + '|'
    print(output)
    print(single_bar)

    # Print away line score
    output = ''
    for i, x in enumerate(away_line_score):
        if scoreboard_inning_headers[i] == 'R':
            output = output[:-1] + '|'
        output += ' ' + str(x).ljust(3) + ' '
    print(output)

    # Print home line score
    output = ''
    for i, y in enumerate(home_line_score):
        if scoreboard_inning_headers[i] == 'R':
            output = output[:-1] + '|'
        output += ' ' + str(y).ljust(3) + ' '
    print(output)
    print(single_bar)

    # Print game status
    if game_status.upper() == 'IN PROGRESS':
        end_loop = False
        # print('Status: ' + ov.inning_state + ' of ' + str(ov.inning))

        if ov.inning_state.upper() != 'END' and ov.inning_state.upper() != 'MIDDLE':
            # TODO - batter is always one player behind
            # print(build_pitcher_batter_line(game, ov.inning, ov.inning_state))

            # Print status and B-S-O
            print('Status: ' + ov.inning_state + ' of ' + str(ov.inning) + ' - Balls: ' +
                  str(ov.balls) + '  Strikes: ' + str(ov.strikes) + '  Outs: ' + str(ov.outs))

            # Print commentary
            output = build_base_and_commentary_lines(game, len(double_bar))
            for l in output:
                print(l)

        else:
            print('Status: ' + ov.inning_state + ' of ' + str(ov.inning))

    # Game over
    if game_status.upper() == 'FINAL' or game_status.upper() == 'GAME OVER':
        print(build_w_l_pitcher_line(game))
        end_loop = True

    # Game over, final, delayed
    if game_status.upper() != 'IN PROGRESS':
        print(game_status)

    # Print game note if there is one
    if game_note:
        print('Note: ' + game_note)

    print(double_bar)

    # Print banner
    print(NAME + ', v' + VERSION)
    print()
    sys.stdout.flush()

    # Sleep for a while and continue with loop
    if not end_loop:
        if game_status.upper() == 'DELAYED':
            time.sleep(60)
        else:
            time.sleep(20)

### <SDG>< ###
