import requests
import csv
import json
import time
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm  # 进度条

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
            # 400 搜索失败
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
        self.use_second_column = self.config.get("use_second_column", False)
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

    def upload_game(self, vid):
        saferequestvndb(
            self.proxy,
            "PATCH",
            f"ulist/v{vid}",
            json={
                "labels_set": [1],
            },
            headers=self.headers,
        )

    def download_game_list(self):
        collectresults = self.querylist(True)
        return collectresults

    def upload_game_list(self, game_titles):
        vids = [int(item["id"][1:]) for item in self.querylist(False)]
        failed_uploads = []
        
        for title in tqdm(game_titles, desc="Uploading games"):
            vid = getidbytitle_(self.proxy, title)
            if vid and int(vid[1:]) not in vids:
                try:
                    self.upload_game(int(vid[1:]))
                except Exception as e:
                    print(f"Failed to upload game '{title}': {e}")
                    failed_uploads.append(title)
        
        return failed_uploads

def read_local_game_data(file_path, use_second_column=False):
    game_titles = []
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header
        for row in reader:
            if use_second_column and row[1].strip():  # If the second column is not empty
                game_titles.append(row[1].strip())
            else:  # If the second column is empty, use the first column
                game_titles.append(row[0].strip())
    return game_titles

def save_failed_uploads(failed_uploads, file_path):
    with open(file_path, mode='w', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Failed Uploads"])
        for title in failed_uploads:
            writer.writerow([title])

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    local_game_data_path = os.path.join(script_dir, "local_game_data.csv")
    failed_uploads_path = os.path.join(script_dir, "failed_uploads.csv")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    if not os.path.exists(local_game_data_path):
        raise FileNotFoundError(f"Local game data file not found: {local_game_data_path}")

    sync = VNDBSync(config_path)
    
    game_titles = read_local_game_data(local_game_data_path, sync.use_second_column)

    if sync.sync_local:
        failed_uploads = sync.upload_game_list(game_titles)
        if failed_uploads:
            save_failed_uploads(failed_uploads, failed_uploads_path)
            print(f"Failed uploads saved to: {failed_uploads_path}")
    
    if sync.download_vndb:
        downloaded_list = sync.download_game_list()
        print("Downloaded List:")
        print(downloaded_list)
