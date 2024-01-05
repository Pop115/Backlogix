import time
import warnings
from datetime import datetime
warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
from howlongtobeatpy import HowLongToBeat
import requests
from bs4 import BeautifulSoup
import re

STEAM_API_KEY = ""
STEAM_ACCESS_TOKEN = ""
STEAM_USER_ID = ""
HOWLONGTOBEAT_API_KEY = "YOUR_HOWLONGTOBEAT_API_KEY"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}



def get_steam_games():
    api_url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/?access_token=" + STEAM_API_KEY
    response = requests.get(api_url)

    if response.status_code == 200:
        data = response.json()
        return data


def get_app_id_by_name(steam_games, game_name):
    patterns_to_exclude = ["soundtrack", "expansion", "OST", "Demo", "Playtest", "cosmetic", "pack", "dlc", "Beta", "artbook"]

    pattern = re.compile(re.escape(game_name), re.IGNORECASE)
    exclude_patterns = [re.compile(re.escape(exclude), re.IGNORECASE) for exclude in patterns_to_exclude]

    matches = [app for app in steam_games['applist']['apps'] if
               re.search(pattern, app['name']) and not any(
                   re.search(exclude, app['name']) for exclude in exclude_patterns)]

    if len(matches) > 1:
        print("Multiple matches found for the given game name:")
        for i, match in enumerate(matches, start=1):
            print(f"{i}. {match['name']} (AppID: {match['appid']})")

        while True:
            try:
                # Ask the user to choose a match
                choice = int(input("Enter the number corresponding to the correct match: "))
                if 1 <= choice <= len(matches):
                    game_app_id = matches[choice - 1]['appid']
                    clean_game_name = matches[choice - 1]['name']
                    print(f"{matches[choice - 1]['name']} selected (AppID: {game_app_id})")
                    return game_app_id, clean_game_name
                else:
                    print("Invalid choice. Please enter a valid number.")
            except ValueError:
                print("Invalid input. Please enter a number.")
    elif len(matches) == 1:
        return matches[0]['appid'], matches[0]['name']
    else:
        print(f"No matches found for the game name '{game_name}'.")
        return None, None


def get_steam_game_tags_date_price(app_id):
    # api_url = f"https://partner.steam-api.com/ISteamUser/GetAppPriceInfo/v1/?key={STEAM_API_KEY}&steamid={STEAM_USER_ID}&appids={app_id}"
    api_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&steamid={STEAM_USER_ID}"
    response = requests.get(api_url)
    data = response.json().get(str(app_id), {}).get("data", {})

    tags = []
    date = data.get("release_date", {}).get("date")
    price = data.get("price_overview", {}).get("final_formatted")

    return tags, date, price


def get_owned_games_steam():
    api_url = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?key={STEAM_API_KEY}&steamid={STEAM_USER_ID}"
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        owned_games = {}
        data = response.json().get("response", {}).get("games", [])
        for game in data:
            app_id = game["appid"]
            playtime_hours = game["playtime_forever"] / 60
            last_played_timestamp = game["rtime_last_played"]
            last_played_date = datetime.utcfromtimestamp(last_played_timestamp).strftime('%Y-%m-%d')
            owned_games[app_id] = {"playtime_hours": playtime_hours, "last_played": last_played_date}
        print(f"Retrieved {len(owned_games)} owned games")
        return owned_games


def get_metacritic_score(clean_game_name):
    joined_game_name = "%20".join(clean_game_name.split(" "))
    api_url = f"https://www.metacritic.com/search/{joined_game_name}"
    print(f"Searching for {clean_game_name} on metacritic")
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        metacritic_game_link = soup.find("a", class_="c-pageSiteSearch-results-item")
        if metacritic_game_link is None:
            print(f"{clean_game_name} not found on metacritic")
            return None, None
        print(f"Found link for game {metacritic_game_link.get('href')}")
        api_url_2 = f"https://www.metacritic.com{metacritic_game_link.get('href')}"
        game_pattern = re.compile(r'game', re.IGNORECASE)
        if game_pattern.search(api_url_2):
            response = requests.get(api_url_2, headers=headers)
            if response.status_code == 200:
                print(f"Retrieved game page")
                soup2 = BeautifulSoup(response.content, "html.parser")

                metascore_element = soup2.find("div", title=re.compile("Metascore.*"))
                user_score_element = soup2.find("div", title=re.compile("User score.*"))

                metascore = metascore_element.findChildren("span")[0].text.strip()
                user_score = user_score_element.findChildren("span")[0].text.strip()
                print(f"Metascore for {clean_game_name} is {metascore}, user score is {user_score}")
                return user_score, metascore
            else:
                print(f"Error: Unable to fetch data. Status code: {response.status_code}")
        else:
            print(f"{clean_game_name} not found on metacritic")
    else:
        print(f"Error: Unable to fetch data. Status code: {response.status_code}")
    return None, None


def get_achievements_game_steam(game_app_id):
    api_url = f"https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/?key={STEAM_API_KEY}&steamid={STEAM_USER_ID}&appid={game_app_id}"
    # TODO


def get_steam_user_info(steam_user_id):
    steamdb_user_url = f"https://steamdb.info/calculator/{steam_user_id}/json"
    response = requests.get(steamdb_user_url)
    data = response.json()

    hours_played = data.get("total_playtime", 0)
    achievement_count = data.get("achievements", 0)

    return hours_played, achievement_count


def get_howlongtobeat_info(clean_game_name):
    # howlongtobeat refresh after the query, every query will land on home page with beautifulsoup, nik
    # joined_game_name = "%2520".join(clean_game_name.split(" "))
    # hltb_api_url = f"https://howlongtobeat.com/?q={joined_game_name}"
    # print(f"Request to HowLongToBeat {hltb_api_url}")
    # hltb_response = requests.get(hltb_api_url, headers=headers)
    # if hltb_response.status_code == 200:
    #     print(hltb_response)
    #     hltb_soup = BeautifulSoup(hltb_response.content, "html.parser")
    #     print(hltb_response.content)
    #     howlongtobeat_times = hltb_soup.findAll("div", class_=re.compile("GameCard_search_list_tidbit.*"))
    #     howlongtobeat_main = howlongtobeat_times[1].text
    #     howlongtobeat_complete = howlongtobeat_times[5].text
    #     print(f"HowLongToBeat for {clean_game_name} : Main Story ({howlongtobeat_main}), Complete ({howlongtobeat_complete})")
    #     return howlongtobeat_main, howlongtobeat_complete
    # else:
    #     print("HowLongToBeat request failed")
    #     return None

    results = HowLongToBeat().search(clean_game_name)
    if results is not None and len(results) > 0:
        best_element = max(results, key=lambda element: element.similarity)
        print(
            f"HowLongToBeat for {clean_game_name} : Main Story ({best_element.main_story}), Complete ({best_element.completionist})")
        return best_element.main_story, best_element.completionist
    return None, None


def get_scorix(clean_game_name, user_score, metascore, main_time, complete_time):
    # average of all the ways to do "rating / time to beat"
    # literally magic

    nb_scores = 0
    user_main = 0
    user_complete = 0
    meta_main = 0
    meta_complete = 0

    try:
        user_score = float(user_score)
    except (ValueError, TypeError):
        print("User score NaN")
    try:
        metascore = float(metascore)
    except (ValueError, TypeError):
        print("Meta score NaN")
    try:
        main_time = float(main_time)
    except (ValueError, TypeError):
        print("Main time NaN")
    try:
        complete_time = float(complete_time)
    except (ValueError, TypeError):
        print("Complete time NaN")

    if type(user_score) is float:
        user_score_100 = user_score * 10
        if type(main_time) is float and main_time > 0:
            user_main = float(user_score_100) / float(main_time)
            nb_scores += 1
        if type(complete_time) is float and complete_time > 0:
            user_complete = float(user_score_100) / float(complete_time)
            nb_scores += 1

    if type(metascore) is float:
        if type(main_time) is float and main_time > 0:
            meta_main = float(metascore) / float(main_time)
            nb_scores += 1
        if type(complete_time) is float and complete_time > 0:
            meta_complete = float(metascore) / float(complete_time)
            nb_scores += 1

    if nb_scores > 0:
        scorix = (user_main + user_complete + meta_main + meta_complete) / nb_scores
        scorix_str = "%.2f" % round(scorix, 2)
        print(f"Scorix for {clean_game_name} is {scorix_str}")
        return scorix_str
    return None


csv_games = pd.read_csv("TODOGames2.csv")
steam_games = get_steam_games()  # Due to steam api, need to get all games on steam to retrieve their appid
owned_games_steam = get_owned_games_steam()

for index, row in csv_games.iterrows():
    game_name = row["Name"]
    if "steam_app_id" in row:
        game_app_id = row["steam_app_id"]

    game_app_id, clean_game_name = get_app_id_by_name(steam_games, game_name)
    if clean_game_name is None:
        clean_game_name = game_name
    if game_app_id is not None:
        tags, date, price = get_steam_game_tags_date_price(game_app_id)
        platform = "Steam"
        csv_games.at[index, "Release Date"] = date
        csv_games.at[index, "Price"] = price

    user_score, metascore = get_metacritic_score(clean_game_name)
    main_time, complete_time = get_howlongtobeat_info(clean_game_name)
    scorix = get_scorix(clean_game_name, user_score, metascore, main_time, complete_time)

    if user_score is not None:
        csv_games.at[index, "MetaCritic User Score"] = user_score
    if metascore is not None:
        csv_games.at[index, "MetaCritic Score"] = metascore
    csv_games.at[index, "Owned"] = game_app_id in owned_games_steam
    if main_time is not None:
        csv_games.at[index, "HowLongToBeat Main"] = main_time
    if complete_time is not None:
        csv_games.at[index, "HowLongToBeat Complete"] = complete_time
    if scorix is not None:
        csv_games.at[index, "Scorix"] = scorix
    time.sleep(1)
    print("\n")

csv_games.to_csv("updated_dataset.csv", index=False)
