from datetime import datetime
import pandas as pd
import requests
import random
import html
import json
import time
import tqdm
import os
import re


def steamSearchResults(params: dict) -> dict:
    """
    Fetches search results from the Steam store based on the provided parameters.

    Args:
        - params (dict): A dictionary of parameters to be sent with the search request.

    Returns:
        - dict: A dictionary containing the search results from the Steam store.
    """
    response = requests.get(
        "https://store.steampowered.com/search/results/", params=params
    )

    if response.status_code != 200:
        print(f"Failed to get search results: {response.status_code}")
        return {}

    try:
        results = response.json()

    except Exception as e:
        print(f"Failed to parse search results: {e}")
        return {}

    return results


def updateVideogames() -> None:
    """
    Fetches the top 100 video games from the Steam store and updates
    the "topSellers.json" file with their names and app IDs.

    Args:
        - None

    Returns:
        - None
    """
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    videogamesFile = os.path.join(currentDirectory, "topSellers.json")
    topSellersFile = os.path.join(currentDirectory, "topSellers.csv")

    with open(videogamesFile, "r", encoding="utf-8") as f:
        videogames = json.load(f)

    if os.path.exists(topSellersFile):
        df = pd.read_csv(topSellersFile)
    else:
        df = pd.DataFrame(columns=["date"] + [str(i) for i in range(1, 101)])

    defaultParameters = {
        "filter": "globaltopsellers",
        "hidef2p": 1,
        "page": None,  # Page is used to go through different parts of the ranking. Each page contains 25 results
        "json": 1,
    }

    dailyTopSellers = []

    for pageNum in range(1, 5):

        defaultParameters["page"] = pageNum
        searchResults = steamSearchResults(defaultParameters)

        if not searchResults.get("items"):
            continue

        # Processing search results to retrieve the appid of the game
        for item in searchResults["items"]:

            try:
                name = html.unescape(item["name"])

                # The URL can be steam/bundles/{appid} or steam/apps/{appid}
                appid = re.search(r"steam/\w+/(\d+)", item["logo"]).group(1)

                # Save the appid in the videogame json for later use
                videogames[name] = int(appid)
                dailyTopSellers.append(appid)

            except Exception as e:
                print(f"Failed to extract appid: {e}")
                item["appid"] = None

    # Sort by name
    videogames = dict(sorted(videogames.items(), key=lambda x: x[0].lower()))

    # Save the search results
    with open(videogamesFile, "w", encoding="utf-8") as f:
        json.dump(videogames, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Save the daily top sellers
    today = datetime.now().date()
    newRow = {"date": today}
    for i, appid in enumerate(dailyTopSellers, start=1):
        newRow[str(i)] = appid

    df.loc[len(df)] = newRow
    df.to_csv(topSellersFile, index=False)


def divideCategories() -> None:
    """
    Divides the video games in "topSellers.json" into different categories
    based on their type (game, dlc, music, hardware) and saves them in
    separate JSON files.

    Args:
        - None

    Returns:
        - None
    """
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    topSellersJsonPath = os.path.join(currentDirectory, "topSellers.json")

    # Ensure the folders exist
    rawDataDirectory = os.path.join(currentDirectory, "rawData")
    os.makedirs(rawDataDirectory, exist_ok=True)

    # Different type of products
    with open(
        os.path.join(currentDirectory, "videogames.json"), "r", encoding="utf-8"
    ) as f:
        videogames = json.load(f)
    with open(os.path.join(currentDirectory, "dlcs.json"), "r", encoding="utf-8") as f:
        dlcs = json.load(f)
    with open(os.path.join(currentDirectory, "music.json"), "r", encoding="utf-8") as f:
        music = json.load(f)
    with open(
        os.path.join(currentDirectory, "hardware.json"), "r", encoding="utf-8"
    ) as f:
        hardware = json.load(f)

    with open(topSellersJsonPath, "r", encoding="utf-8") as f:
        allItems = json.load(f)

    # Filter out items that are already classified
    classifiedIDs = (
        set(videogames.values())
        | set(dlcs.values())
        | set(music.values())
        | set(hardware.values())
    )
    allItems = {k: v for k, v in allItems.items() if v not in classifiedIDs}

    for videogame, id in tqdm.tqdm(allItems.items(), desc="Fetching basic info"):

        filePath = os.path.join(
            rawDataDirectory, f"{videogame.replace('/', '_')}Info.json"
        )

        # Ensure that the game info is fetched if the file does not exist
        if not os.path.exists(filePath):
            fetchGameInfo(id, videogame, False)

        with open(filePath, "r", encoding="utf-8") as f:
            gameInfo = json.load(f)

        # Add to the correct category
        if gameInfo["type"] == "game":
            videogames[videogame] = id
        elif gameInfo["type"] == "dlc":
            dlcs[videogame] = id
        elif gameInfo["type"] == "music":
            music[videogame] = id
        elif gameInfo["type"] == "hardware":
            hardware[videogame] = id
        else:
            raise ValueError(f"Unknown type for {videogame}: {gameInfo['type']}")

    # Sort the categories
    videogames = dict(sorted(videogames.items(), key=lambda x: x[0].lower()))
    dlcs = dict(sorted(dlcs.items(), key=lambda x: x[0].lower()))
    music = dict(sorted(music.items(), key=lambda x: x[0].lower()))
    hardware = dict(sorted(hardware.items(), key=lambda x: x[0].lower()))

    # Save the categories
    with open(
        os.path.join(currentDirectory, "videogames.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(videogames, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(os.path.join(currentDirectory, "dlcs.json"), "w", encoding="utf-8") as f:
        json.dump(dlcs, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(os.path.join(currentDirectory, "music.json"), "w", encoding="utf-8") as f:
        json.dump(music, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(
        os.path.join(currentDirectory, "hardware.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(hardware, f, indent=2, ensure_ascii=False)
        f.write("\n")


def fetchReviews(id: int, videogame: str, forceRefresh: bool = False) -> None:
    """
    Fetches reviews for a given video game from the Steam store
    and saves them as JSONL files.

    https://partner.steamgames.com/doc/store/getreviews

    Args:
        - id (int): The Steam app ID of the video game.
        - videogame (str): The name of the video game, used for naming the output files.
        - forceRefresh (bool): Whether to fetch reviews even if the output file already exists.

    Returns:
        - None
    """
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    dataDirectory = os.path.join(currentDirectory, "rawData")

    url = f"https://store.steampowered.com/appreviews/{id}?json=1"
    parameters = {"filter": "all", "language": "english", "num_per_page": 100}

    for reviewType in ["positive", "negative"]:

        outputPath = os.path.join(
            dataDirectory,
            f"{videogame.replace('/', '_')}{reviewType.capitalize()}.jsonl",
        )

        if not os.path.exists(outputPath) or forceRefresh:

            parameters["review_type"] = reviewType
            response = requests.get(url, params=parameters)
            time.sleep(random.random())

            if response.status_code == 200:
                data = response.json()

                if data["success"] == 1:

                    with open(outputPath, "w", encoding="utf-8") as file:

                        for review in data["reviews"]:
                            important = {
                                "score": float(review["weighted_vote_score"]),
                                "review": review["review"],
                            }
                            json.dump(important, file, ensure_ascii=False)
                            file.write("\n")


def fetchGameInfo(id: int, videogame: str, forceRefresh: bool = False) -> None:
    """
    Fetches detailed information for a given video game from the Steam store
    and saves it in a JSON file.

    Args:
        - id (int): The Steam app ID of the video game.
        - videogame (str): The name of the video game, used for naming the output file.
        - forceRefresh (bool): Whether to fetch game info even if the output file already exists.

    Returns:
        - None
    """
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    dataDirectory = os.path.join(currentDirectory, "rawData")
    gameInfoPath = os.path.join(
        dataDirectory, f"{videogame.replace('/', '_')}Info.json"
    )

    if not os.path.exists(gameInfoPath) or forceRefresh:
        url = f"https://store.steampowered.com/api/appdetails?appids={id}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data[str(id)]["success"]:
                with open(gameInfoPath, "w", encoding="utf-8") as file:
                    json.dump(data[str(id)]["data"], file, indent=2, ensure_ascii=False)
                    file.write("\n")


def getAllGames(forceRefresh: bool = False) -> None:
    """
    Fetches reviews for all video games listed in the "videogames.json" file.

    Args:
        - None

    Returns:
        - None
    """
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    videogamesPath = os.path.join(currentDirectory, "videogames.json")

    os.makedirs(os.path.join(currentDirectory, "rawData"), exist_ok=True)

    with open(videogamesPath, "r", encoding="utf-8") as file:
        videogames = json.load(file)

    for videogame, id in tqdm.tqdm(
        videogames.items(), desc="Fetching reviews and info"
    ):
        fetchReviews(id, videogame, forceRefresh=forceRefresh)
        fetchGameInfo(id, videogame, forceRefresh=forceRefresh)


if __name__ == "__main__":
    updateVideogames()
    divideCategories()
