# MLBLiveScoreboard
Python script to print live MLB game scoreboards to console

NAME:    MLB-live-scoreboard3.py (C) 2019 - 2021

PURPOSE: To produce a simple, live scoreboard to track MLB game play
         on your computer.


         Retrieving game data from MLB (07/17/2019 21:06:37)...
         Washington Nationals @ Baltimore Orioles: 2019/07/17 7:05PM (Game #564977)
         ===========================================================================
          Top 3rd      | 1  | 2  | 3  | 4  | 5  | 6  | 7  | 8  | 9  | R  | H  | E  |
         ---------------------------------------------------------------------------
          WSH ( 50-43 )  0    0    -                                | 0    1    0
          BAL ( 28-66 )  0    0                                     | 0    1    0
         ---------------------------------------------------------------------------
         B:0 S:0 O:1| Pitcher: Brooks (4.55 ERA) - Batter: Gomes (0-0, .204 AVG)
            [ ]     | Last play: Single - Victor Robles singles on a line drive to l
         [ ]   [X]  | eft fielder Anthony Santander.
            [o]     |
         ===========================================================================
         (C) 2018-2023 MSRoth, MLB Live Scoreboard v0.8

AUTHOR:  MSRoth

USAGE:   >python MLB-live-scoreboard3.py [favorite_team] [away_team, home_team, game_date]

         For example:
         
         python MLB-live-scoreboard.py WSH
         
         python MLB-live-scoreboard.py WSH PHI 04/10/2019

         No arguments reads data from config.py file.
         
         Date format:  MM/DD/YYYY   

         Valid team names:
           ARI - Arizona Diamondbacks
           ATL - Atlanta Braves
           BAL - Baltimore Orioles
           BOS - Boston Red Sox
           CHC - Chicago Cubs
           CIN - Cincinnati Reds
           CLE - Cleveland Indians
           COL - Colorado Rockies
           CWS - Chicago White Sox
           DET - Detroit Tigers
           HOU - Houston Astros
           KC - Kansas City Royals
           LAA - Los Angeles Angels
           LAD - Los Angeles Dodgers
           MIA - Miami Marlins
           MIL - Milwaukee Brewers
           MIN - Minnesota Twins
           NYM - New York Mets
           NYY - New York Yankees
           OAK - Oakland Athletics
           PHI - Philadelphia Phillies
           PIT - Pittsburgh Pirates
           SD - San Diego Padres
           SEA - Seattle Mariners
           SF - San Francisco Giants
           STL - St. Louis Cardinals
           TB - Tampa Bay Rays
           TEX - Texas Rangers
           TOR - Toronto Blue Jays
           WSH - Washington Nationals
   
COMMENTS:

    - this script uses the MLB REST API.
    
    - this script is very inefficient and chatty -- somethings I hope to clear up in the near future.
      
    - this script does not have a lot of error detection and sometimes encounters a race condition with data from MLB.  
      If that happens, just restart it and it usually clears up.
    
    - this is the first Python program I have ever written, so I am sure there are a lot of style mistakes and use of brute 
      force where finesse is available to a more experienced programmer.
     
