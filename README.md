# MLBLiveScoreboard
Python script to print live MLB game scoreboards to console

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
=====================================================================
