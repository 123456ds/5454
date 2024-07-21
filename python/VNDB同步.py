import requests
import csv
import json
import time
import os
import pandas as pd
from openpyxl import load_workbook
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

def saferequestvndb(proxy, method, url, json=None, headers=None):
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        print(method, url, json)
        resp = session.request(
            method,
            "https://api.vndb.org/kana/" + url,
            headers=headers,
            json=json,
            proxies=proxy,
        )
        if resp.status_code == 429:
            time.sleep(3)
            print("retry 429")
            return saferequestvndb(proxy, method, url, json, headers)
        elif resp.status_code == 400:
            print(resp.text)
        else:
            if method.upper() in ["GET", "POST"]:
                try:
                    return resp.json()
                except:
                    print(resp.status_code)
                    print(resp.text)
                    return None
    except requests.exceptions.SSLError as e:
        print(f"SSL Error: {e}")
        time.sleep(5)
        return saferequestvndb(proxy, method, url, json, headers)

def safegetvndbjson(proxy, url, json):
    return saferequestvndb(proxy, "POST", url, json)

def gettitlefromjs(js):
    try:
        for _ in js["titles"]:
            main = _["main"]
            title = _["title"]
            if main:
                return title
        raise Exception()
    except:
        return js["title"]

def getvidbytitle_vn(proxy, title):
    js = safegetvndbjson(
        proxy,
        "vn",
        {"filters": ["search", "=", title], "fields": "id", "sort": "searchrank"},
    )
    if js and js.get('results'):
        return js["results"][0]["id"]

def getvidbytitle_release(proxy, title):
    js = safegetvndbjson(
        proxy,
        "release",
        {
            "filters": ["search", "=", title],
            "fields": "id,vns.id",
            "sort": "searchrank",
        },
    )
    if js and js.get('results'):
        return js["results"][0]["vns"][0]["id"]

def getidbytitle_(proxy, title):
    vid = getvidbytitle_vn(proxy, title)
    if vid:
        return vid
    return getvidbytitle_release(proxy, title)

class VNDBSync:
    def __init__(self, config_path, proxy=None):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.proxy = proxy
        self.headers = {
            "Authorization": f"Token {self.config['Token']}",
        }
        self.sync_local = self.config.get("sync_local", False)
        self.download_vndb = self.config.get("download_vndb", False)

    @property
    def userid(self):
        return saferequestvndb(self.proxy, "GET", "authinfo", headers=self.headers)["id"]

    def querylist(self, title):
        userid = self.userid
        pagei = 1
        collectresults = []
        while True:
            json_data = {
                "user": userid,
                "fields": (
                    "id, vn.title,vn.titles.title,vn.titles.main" if title else "id"
                ),
                "sort": "vote",
                "results": 100,
                "page": pagei,
            }
            pagei += 1
            response = saferequestvndb(
                self.proxy, "POST", "ulist", json=json_data, headers=self.headers
            )
            collectresults += response["results"]
            if not response["more"]:
                break
        return collectresults

    def upload_game(self, vid, labels_set, vote=None, finished=None):
        data = {"labels_set": labels_set}
        if vote:
            data["vote"] = vote
        if finished:
            data["finished"] = finished
        saferequestvndb(
            self.proxy,
            "PATCH",
            f"ulist/v{vid}",
            json=data,
            headers=self.headers,
        )

    def download_game_list(self):
        collectresults = self.querylist(True)
        return collectresults

    def upload_game_list(self, game_data):
        vids = [int(item["id"][1:]) for item in self.querylist(False)]
        failed_uploads = []
        
        for game in tqdm(game_data, desc="Uploading games"):
            title, labels_set, vote, finished = game
            vid = getidbytitle_(self.proxy, title)
            if vid:
                try:
                    self.upload_game(int(vid[1:]), labels_set, vote, finished)
                except Exception as e:
                    print(f"Failed to upload game '{title}': {e}")
                    failed_uploads.append(game)
            else:
                print(f"Failed to find ID for game '{title}'")
                failed_uploads.append(game)
        
        return failed_uploads

def read_local_game_data(file_path):
    _, file_extension = os.path.splitext(file_path)
    game_data = []
    
    if file_extension == ".xlsx":
        df = pd.read_excel(file_path)
        for _, row in df.iterrows():
            title = row.iloc[1] if pd.notna(row.iloc[1]) else row.iloc[0]
            finished = None
            if pd.notna(row.iloc[5]):
                try:
                    finished_date = pd.to_datetime(row.iloc[5])
                    finished = finished_date.strftime('%Y-%m-%d')
                except ValueError:
                    finished = row.iloc[5]
            vote = int(row.iloc[6] * 10) if pd.notna(row.iloc[6]) else None
            status_map = {
                "想看": [5],
                "在看": [1],
                "看过": [2],
                "搁置": [3],
                "抛弃": [4]
            }
            labels_set = status_map.get(row.iloc[10], [])
            game_data.append((title, labels_set, vote, finished))

    elif file_extension == ".csv":
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                if row[2].strip() == "游戏":
                    title = row[0]
                    finished = row[5].replace('/', '-') if row[5].strip() else None
                    vote = int(row[9].strip()) * 10 if row[9].strip() != "(无评分)" else None
                    status_map = {
                        "想看": [5],
                        "在看": [1],
                        "看过": [2],
                        "搁置": [3],
                        "抛弃": [4]
                    }
                    labels_set = status_map.get(row[4], [])
                    game_data.append((title, labels_set, vote, finished))

    elif file_extension == ".json":
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if "data" not in data:
                print("Error: JSON data does not contain 'data' key.")
                raise ValueError("Expected list of game data, but got an invalid structure.")
            for item in data["data"]:
                if item.get("subject_type") == 4:
                    title = item["subject"]["name"]
                    finished = item["updated_at"].split('T')[0]
                    vote = int(item["rate"]) * 10 if item["rate"] != 0 else None
                    status_map = {
                        1: [5],
                        2: [2],
                        3: [1],
                        4: [3],
                        5: [4]
                    }
                    labels_set = status_map.get(item["type"], [])
                    game_data.append((title, labels_set, vote, finished))
    
    print(f"Read {len(game_data)} game entries from local data file: {file_path}")
    return game_data

def save_failed_uploads(failed_uploads, file_path):
    with open(file_path, mode='w', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Title", "Labels Set", "Vote", "Finished"])
        for game in failed_uploads:
            writer.writerow(game)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    
    local_game_data_path = None
    for extension in [".xlsx", ".csv", ".json"]:
        for file_name in os.listdir(script_dir):
            if file_name == "config.json":
                continue
            if file_name.endswith(extension):
                local_game_data_path = os.path.join(script_dir, file_name)
                break
        if local_game_data_path:
            break

    if not local_game_data_path:
        raise FileNotFoundError("No game data file found in .xlsx, .csv, or .json format.")
    else:
        print(f"Found local game data file: {local_game_data_path}")
    
    failed_uploads_path = os.path.join(script_dir, "failed_uploads.csv")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    sync = VNDBSync(config_path)
    
    game_data = read_local_game_data(local_game_data_path)
    print(f"Read {len(game_data)} game entries from local data.")

    if sync.sync_local:
        failed_uploads = sync.upload_game_list(game_data)
        if failed_uploads:
            save_failed_uploads(failed_uploads, failed_uploads_path)
            print(f"Failed uploads saved to: {failed_uploads_path}")
    
    if sync.download_vndb:
        downloaded_list = sync.download_game_list()
        print("Downloaded List:")
        print(downloaded_list)
