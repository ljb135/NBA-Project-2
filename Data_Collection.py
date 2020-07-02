import urllib.request
from urllib.error import HTTPError
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, select, and_, text
import datetime
import gzip
import json
import csv
import re
import pandas as pd

db = create_engine('sqlite:///NBAPlayers.db', echo=False)
meta = MetaData()
conn = db.connect()

players = Table('players', meta,
                Column('NAME', String),
                Column('PLAYER_ID', String, primary_key=True),
                Column('TEAM', String),
                Column('TEAM_ID', String),
                Column('YEAR', String, primary_key=True),
                Column('AGE', Integer),
                Column('HEIGHT', Integer),
                Column('WEIGHT', Integer),
                Column('MIN', Integer),
                Column('PTS', Integer),
                Column('FTM', Integer),
                Column('FTA', Integer),
                Column('FT_PCT', Integer),
                Column('FGM', Integer),
                Column('FGA', Integer),
                Column('FG_PCT', Integer),
                Column('FG3M', Integer),
                Column('FG3A', Integer),
                Column('FG3_PCT', Integer),
                Column('AST', Integer),
                Column('TOV', Integer),
                Column('STL', Integer),
                Column('BLK', Integer),
                Column('OREB', Integer),
                Column('DREB', Integer),
                Column('PF', Integer))


# converts a list of players stats into team stats
class Team:
    def __init__(self, players_stats):
        self.players_stats = players_stats

        self.age = None
        self.pts = None
        self.efg_pct = None
        self.fta = None
        self.ft_pct = None
        self.ftr = None
        self.fg2a = None
        self.fg2_pct = None
        self.fg3a = None
        self.fg3_pct = None
        self.ast = None
        self.tov = None
        self.ast_tov = None
        self.oreb = None
        self.dreb = None
        self.stl = None
        self.blk = None
        self.pf = None

        self.__calculate()

    # insert methods for calculating each stat
    def __calculate(self):
        total_age = 0
        total_pts = 0
        total_ftm = 0
        total_fta = 0
        total_fgm = 0
        total_fga = 0
        total_3pm = 0
        total_3pa = 0
        total_ast = 0
        total_tov = 0
        total_stl = 0
        total_blk = 0
        total_oreb = 0
        total_dreb = 0
        total_pf = 0
        for player in self.players_stats:
            total_age += player[0]
            total_pts += player[2]
            total_ftm += player[3]
            total_fta += player[4]
            total_fgm += player[6]
            total_fga += player[7]
            total_3pm += player[9]
            total_3pa += player[10]
            total_ast += player[12]
            total_tov += player[13]
            total_stl += player[14]
            total_blk += player[15]
            total_oreb += player[16]
            total_dreb += player[17]
            total_pf += player[18]

        # calculate average age
        self.age = round(total_age/len(self.players_stats), 1)

        # calculate total points
        self.pts = round(total_pts, 1)

        # calculate effective field goal percentage
        self.efg_pct = round((total_fgm + (0.5 * total_3pm))/total_fga, 1)

        # calculate total free throw attempts
        self.fta = round(total_fta, 1)

        # calculate free throw percentage
        self.ft_pct = round(total_ftm/total_fta, 1)

        # calculate free throw rate
        self.ftr = round(total_fta/total_fga, 1)

        # calculate total two point attempts
        self.fg2a = round(total_fga - total_3pa, 1)

        # calculate two point percentage
        self.fg2_pct = round((total_fgm - total_3pm)/(total_fga - total_3pa), 1)

        # calculate total three point attempts
        self.fg3a = round(total_3pa, 1)

        # calculate three point percentage
        self.fg3_pct = round(total_3pm/total_3pa, 1)

        # calculate total assists
        self.ast = round(total_ast, 1)

        # calculate total turnovers
        self.tov = round(total_tov, 1)

        # calculate assist to turnover ratio
        self.ast_tov = round(total_ast/total_tov, 1)

        # calculate total offensive rebounds
        self.oreb = round(total_oreb, 1)

        # calculate total defensive rebounds
        self.dreb = round(total_dreb, 1)

        # calculate total steals
        self.stl = round(total_stl, 1)

        # calculate total blocks
        self.blk = round(total_blk, 1)

        # calculate total personal fouls
        self.pf = round(total_pf, 1)

    def export(self):
        return [self.age, self.pts, self.efg_pct, self.fta, self.ft_pct, self.ftr, self.fg2a, self.fg2_pct, self.fg3a, self.fg3_pct, self.ast, self.tov, self.ast_tov, self.oreb, self.dreb, self.stl, self.blk, self.pf]


# used to store information regarding a single NBA Game
class NBAGame:
    def __init__(self, game_id, daily_games_json, season):
        self.game_id = game_id
        self.daily_games_json = daily_games_json
        self.season = season

        self.home_id = None
        self.away_id = None
        self.home_points = None
        self.away_points = None
        self.home_players = []
        self.away_players = []
        self.home_win = None

        self.__set_team_ids()
        self.__set_points()
        self.__set_seasonal_stats()
        self.__set_result()

    # finds the match lineup in "Series Standings" and sets the appropriate values
    def __set_team_ids(self):
        for i in range(len(self.daily_games_json["resultSets"][2]["rowSet"])):  # increment through all games
            if self.daily_games_json["resultSets"][2]["rowSet"][i][0] == self.game_id:  # find matching game
                self.home_id = self.daily_games_json["resultSets"][2]["rowSet"][i][1]
                self.away_id = self.daily_games_json["resultSets"][2]["rowSet"][i][2]
                return

    # finds the points for each team in "Line Score" and sets the appropriate values
    def __set_points(self):
        for i in range(len(self.daily_games_json["resultSets"][1]["rowSet"])):  # increment through all teams
            if self.daily_games_json["resultSets"][1]["rowSet"][i][3] == self.home_id:  # match home id
                self.home_points = self.daily_games_json["resultSets"][1]["rowSet"][i][22]
            if self.daily_games_json["resultSets"][1]["rowSet"][i][3] == self.away_id:  # match away id
                self.away_points = self.daily_games_json["resultSets"][1]["rowSet"][i][22]
            if self.home_points is not None and self.away_points is not None:  # stops when both are filled
                return

    # finds player stats in "PlayerStats" and sets the appropriate values
    def __set_seasonal_stats(self):
        game_stats_json = stats_in_game(self.game_id)  # uses game-specific box score JSON
        player_ids = []
        for player in game_stats_json["resultSets"][0]["rowSet"]:  # increment through all players
            try:
                mins_played = player[8]
                if mins_played is not None:
                    player_ids.append(str(player[4]))

            except AttributeError:
                continue
            except Exception as e:
                print(e)

        # queries the stats for all of the players who played in the game
        query = select([players]).where(and_(players.c.YEAR == self.season, players.c.PLAYER_ID.in_(player_ids)))
        result = conn.execute(query).fetchall()
        print(result)

        for player in result:
            print(player)
            team_id = player[3]
            del player[6:8]
            del player[:5]

            if team_id == self.home_id:  # add player to respective team
                self.home_players.append(player)
            else:
                self.away_players.append(player)

        print(self.away_players)
        print(self.home_players)

    # compares scores and determines which team won
    def __set_result(self):
        if self.home_points > self.away_points:
            self.home_win = True
        else:
            self.home_win = False

    # prints all variables
    def print_vars(self):
        attrs = vars(self)
        print('\n'.join("%s: %s" % item for item in attrs.items()))

    # inserts seasonal data into an array
    def compile_data(self):
        game_data_array = []  # array that stores the stats --> corresponds to a single row in the CSV file
        edit_stat_indexes = [1, 2, 3, 4, 5, 6, 9, 10, 12, 13, 14, 15, 16, 17, 18]  # indexes of stats to be modified

        game_data_array.append(int(self.game_id))  # adds gameID to array
        game_data_array.append(int(self.home_win))  # adds win result to array

        home_total_min = 0
        away_total_min = 0

        for player in self.home_players:
            home_total_min += player[1]
        for player in self.away_players:
            away_total_min += player[1]

        if len(self.home_players) < 5:
            home_min_ratio = len(self.home_players)*48/home_total_min
        else:
            home_min_ratio = 5*48/home_total_min
        if len(self.away_players) < 5:
            away_min_ratio = len(self.away_players)*48/away_total_min
        else:
            away_min_ratio = 5*48/away_total_min

        # loops through all players on both teams and edits stats using minutes ratio
        for player_number in range(len(self.home_players)):
            for index in edit_stat_indexes:
                self.home_players[player_number][index] = self.home_players[player_number][index] * home_min_ratio
        for player_number in range(len(self.away_players)):
            for index in edit_stat_indexes:
                self.away_players[player_number][index] = self.away_players[player_number][index] * away_min_ratio

        game_data_array.extend(Team(self.home_players).export())
        game_data_array.extend(Team(self.away_players).export())

        return game_data_array


# finds all games on a specific day and returns a JSON containing info of all games on that day
def games_on_date(month, day, year):
    day = f"{month}%2F{day}%2F{year}"
    game_id_url = f"https://stats.nba.com/stats/scoreboardV2?DayOffset=0&LeagueID=00&gameDate={day}"
    game_id_headers = {"Host": "stats.nba.com", "Connection": "keep-alive", "Accept": "application/json, text/plain, */*", "x-nba-stats-origin": "stats", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36", "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en;q=0.9"}

    req = urllib.request.Request(url=game_id_url, headers=game_id_headers)
    response = urllib.request.urlopen(req)
    data = response.read()
    data = str(gzip.decompress(data), 'utf-8')
    gameday_json = json.loads(data)
    return gameday_json


# returns all the games played on a specific day
def get_game_ids(gameday_json):
    game_list = gameday_json["resultSets"][0]["rowSet"]
    game_ids = []
    for game in game_list:
        game_ids.append(game[2])
    return game_ids


# finds box score information of a specific game and a JSON containing detailed stats of players in the game
def stats_in_game(game_id):
    game_stats_url = f"https://stats.nba.com/stats/boxscoretraditionalv2?EndPeriod=10&EndRange=28800&GameID={game_id}&RangeType=0&StartPeriod=1&StartRange=0"
    game_stats_headers = {"Host": "stats.nba.com", "Connection": "keep-alive", "Accept": "application/json, text/plain, */*", "x-nba-stats-origin": "stats", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36", "Referer": f"https://stats.nba.com/game/{game_id}/", "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en;q=0.9"}

    req = urllib.request.Request(url=game_stats_url, headers=game_stats_headers)
    response = urllib.request.urlopen(req)
    data = response.read()
    data = str(gzip.decompress(data), 'utf-8')
    json_file = json.loads(data)
    return json_file


# converts data into a csv file
def export_data(game_day_matrix, filename):
    with open(filename, 'a', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)  # creating a csv writer object
        csv_writer.writerows(game_day_matrix)  # writing the data rows


def collect_data(date_range, filename):
    try:
        start_month = date_range[0].month
        start_year = date_range[0].year
        changed_season = True

        if start_month > 4:
            season = start_year
        else:
            season = start_year - 1

        for date in date_range:
            year = date.year
            month = date.month
            day = date.day

            if month in range(5, 10):
                continue

            if month == 10 and changed_season is False:
                season += 1
                changed_season = True
            elif month != 10:
                changed_season = False

            try:
                games = games_on_date(str(month).zfill(2), str(day).zfill(2), year)
                game_id_list = get_game_ids(games)
                game_day_matrix = []
                games_skipped = 0

                for game_id in game_id_list:
                    if str(game_id)[2] != "2":
                        games_skipped += 1
                        continue
                    target_game = NBAGame(game_id, games, season)
                    game_data = target_game.compile_data()
                    game_day_matrix.append(game_data)

                time = datetime.datetime.now().strftime("%I:%M:%S %p")
                games_added = len(game_id_list) - games_skipped

                export_data(game_day_matrix, filename)
                print(str(month).zfill(2), str(day).zfill(2), year, f": {games_added} games added\t({time})")

            except HTTPError as ex:
                if ex.code == 400:
                    break
                else:
                    raise
    except KeyboardInterrupt:
        exit()


csv_filename = "Data/10-11_data.csv"
start_date = datetime.datetime(2010, 10, 26)
end_date = datetime.datetime(2011, 4, 20)
date_list = pd.date_range(start_date, end_date)
collect_data(date_list, csv_filename)