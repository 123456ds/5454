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
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 锁用于控制API请求速率
rate_limit_lock = threading.Lock()
requests_per_interval = 200
interval_seconds = 300
requests_made = 10
interval_start_time = time.time()

# 安全请求函数，用于处理VNDB API的请求
def saferequestvndb(proxy, method, url, json=None, headers=None):
    global requests_made, interval_start_time

    with rate_limit_lock:
        current_time = time.time()
        if current_time - interval_start_time >= interval_seconds:
            interval_start_time = current_time
            requests_made = 0

        if requests_made >= requests_per_interval:
            time_to_wait = interval_seconds - (current_time - interval_start_time)
            if time_to_wait > 0:
                print(f"Rate limit reached, sleeping for {time_to_wait:.2f} seconds.")
                time.sleep(time_to_wait)
            interval_start_time = time.time()
            requests_made = 0

        requests_made += 1

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

# 安全获取VNDB JSON数据的函数
def safegetvndbjson(proxy, url, json):
    return saferequestvndb(proxy, "POST", url, json)

# 截断标题的函数，用于处理标题中的特殊字符
def truncate_title(title):
    symbol_regex = re.compile(r'[^\w\s]', re.UNICODE)
    
    match_start = symbol_regex.search(title)
    truncated_start = title[:match_start.start()] if match_start else title[:20]

    match_end = symbol_regex.search(title[::-1])
    truncated_end = title[len(title)-match_end.start():] if match_end else title[-20:]

    return truncated_start.strip(), truncated_end.strip()

# 通过标题获取VNDB中的游戏ID
def getvidbytitle_vn(proxy, title):
    js = safegetvndbjson(proxy, "vn", {"filters": ["search", "=", title], "fields": "id", "sort": "searchrank"})
    if js and js.get('results'):
        return js["results"][0]["id"]
    else:
        truncated_start, truncated_end = truncate_title(title)
        js_start = safegetvndbjson(proxy, "vn", {"filters": ["search", "=", truncated_start], "fields": "id", "sort": "searchrank"})
        if js_start and js_start.get('results'):
            return js_start["results"][0]["id"]
        
        js_end = safegetvndbjson(proxy, "vn", {"filters": ["search", "=", truncated_end], "fields": "id", "sort": "searchrank"})
        if js_end and js_end.get('results'):
            return js_end["results"][0]["id"]

    return None

# 通过标题获取VNDB中的发布ID
def getvidbytitle_release(proxy, title):
    js = safegetvndbjson(proxy, "release", {"filters": ["search", "=", title], "fields": "id,vns.id", "sort": "searchrank"})
    if js and js.get('results'):
        return js["results"][0]["vns"][0]["id"]
    else:
        truncated_start, truncated_end = truncate_title(title)
        
        js_start = safegetvndbjson(proxy, "release", {"filters": ["search", "=", truncated_start], "fields": "id,vns.id", "sort": "searchrank"})
        if js_start and js_start.get('results'):
            return js_start["results"][0]["vns"][0]["id"]
        
        js_end = safegetvndbjson(proxy, "release", {"filters": ["search", "=", truncated_end], "fields": "id,vns.id", "sort": "searchrank"})
        if js_end and js_end.get('results'):
            return js_end["results"][0]["vns"][0]["id"]

    return None

# 通过标题和中文标题获取VNDB中的ID
def getidbytitle_(proxy, title, title_cn):
    vid = getvidbytitle_vn(proxy, title)
    if not vid:
        vid = getvidbytitle_vn(proxy, title_cn)
    if not vid:
        vid = getvidbytitle_release(proxy, title)
    if not vid:
        vid = getvidbytitle_release(proxy, title_cn)
    return vid

# VNDB同步类
class VNDBSync:
    def __init__(self, config_path, proxy=None):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.proxy = proxy
        self.headers = {"Authorization": f"Token {self.config['Token']}"}
        self.sync_local = self.config.get("sync_local", False)
        self.download_vndb = self.config.get("download_vndb", False)
        self.progress_file = os.path.join(os.path.dirname(config_path), "progress.json")
        self.failed_uploads_path = os.path.join(os.path.dirname(config_path), "failed_uploads.json")
        self.current_index = self.load_progress()

    @property
    def userid(self):
        return saferequestvndb(self.proxy, "GET", "authinfo", headers=self.headers)["id"]

    # 查询用户列表
    def querylist(self, title):
        userid = self.userid
        pagei = 1
        collectresults = []
        while True:
            json_data = {"user": userid, "fields": ("id, vn.title,vn.titles.title,vn.titles.main" if title else "id"), "sort": "vote", "results": 100, "page": pagei}
            pagei += 1
            response = saferequestvndb(self.proxy, "POST", "ulist", json=json_data, headers=self.headers)
            collectresults += response["results"]
            if not response["more"]:
                break
        return collectresults

    # 上传游戏数据
    def upload_game(self, vid, labels_set, vote=None, finished=None):
        data = {"labels_set": labels_set}
        if vote:
            data["vote"] = vote
        if finished:
            data["finished"] = finished
        saferequestvndb(self.proxy, "PATCH", f"ulist/v{vid}", json=data, headers=self.headers)

    # 下载游戏列表
    def download_game_list(self):
        return self.querylist(True)

    # 上传游戏列表
    def upload_game_list(self, game_data):
        failed_uploads = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_game = {executor.submit(self.upload_single_game, game, i): game for i, game in enumerate(game_data[self.current_index:], start=self.current_index)}
            
            for future in tqdm(as_completed(future_to_game), total=len(future_to_game), desc="上传游戏数据"):
                game = future_to_game[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"记录失败的上传 '{game[0]}': {e}") 
                    failed_uploads.append(game)
                    self.save_failed_uploads([game])
        
        return failed_uploads

    def upload_single_game(self, game, index):
        title, title_cn, labels_set, vote, finished = game
        vid = getidbytitle_(self.proxy, title, title_cn)
        if vid:
            try:
                self.upload_game(int(vid[1:]), labels_set, vote, finished)
                self.current_index = index + 1
                self.save_progress()
            except Exception as e:
                print(f"记录失败的上传 '{title}': {e}") 
                self.save_failed_uploads([game])
        else:
            print(f"找不到ID '{title}'") 
            self.save_failed_uploads([game])

    # 保存进度
    def save_progress(self):
        with open(self.progress_file, 'w', encoding='utf-8') as file:
            json.dump({"current_index": self.current_index}, file)

    # 加载进度
    def load_progress(self):
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return data.get("current_index", 0)
        return 0

    # 保存失败的上传
    def save_failed_uploads(self, failed_uploads):
        if os.path.exists(self.failed_uploads_path):
            with open(self.failed_uploads_path, 'r', encoding='utf-8') as file:
                existing_data = json.load(file)
        else:
            existing_data = {"data": []}
        
        for game in failed_uploads:
            entry = {
                "title": game[0],
                "title_cn": game[1],
                "labels_set": game[2],
                "vote": game[3],
                "finished": game[4]
            }
            existing_data["data"].append(entry)
        
        with open(self.failed_uploads_path, 'w', encoding='utf-8') as file:
            json.dump(existing_data, file, ensure_ascii=False, indent=4)

# 读取本地游戏数据
def read_local_game_data(file_path):
    _, file_extension = os.path.splitext(file_path)
    game_data = []
    
    if file_extension == ".xlsx":
        df = pd.read_excel(file_path)
        for _, row in df.iterrows():
            title = row.iloc[1] if pd.notna(row.iloc[1]) else row.iloc[0]
            title_cn = row.iloc[0] if pd.notna(row.iloc[0]) else None
            finished = None
            if pd.notna(row.iloc[5]):
                try:
                    finished_date = pd.to_datetime(row.iloc[5])
                    finished = finished_date.strftime('%Y-%m-%d')
                except ValueError:
                    finished = row.iloc[5]
            vote = int(row.iloc[6] * 10) if pd.notna(row.iloc[6]) else None
            status_map = {"想看": [5], "在看": [1], "看过": [2], "搁置": [3], "抛弃": [4]}
            labels_set = status_map.get(row.iloc[10], [])
            game_data.append((title, title_cn, labels_set, vote, finished))

    elif file_extension == ".csv":
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                if row[2].strip() == "游戏":
                    title = row[0] if row[0].strip() else row[1]
                    title_cn = row[1] if row[1].strip() else None
                    finished = row[5].replace('/', '-') if row[5].strip() else None
                    vote = int(row[9].strip()) * 10 if row[9].strip() != "(无评分)" else None
                    status_map = {"想看": [5], "在看": [1], "看过": [2], "搁置": [3], "抛弃": [4]}
                    labels_set = status_map.get(row[4], [])
                    game_data.append((title, title_cn, labels_set, vote, finished))

    elif file_extension == ".json":
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if "data" not in data:
                print("JSON数据中没有'data'键")
                raise ValueError("期望的游戏数据格式错误.")
            for item in data["data"]:
                if item.get("subject_type") == 4:
                    title = item["subject"]["name"]
                    title_cn = item["subject"].get("name_cn", None)
                    finished = item["updated_at"].split('T')[0]
                    vote = int(item["rate"]) * 10 if item["rate"] != 0 else None
                    status_map = {1: [5], 2: [2], 3: [1], 4: [3], 5: [4]}
                    labels_set = status_map.get(item["type"], [])
                    game_data.append((title, title_cn, labels_set, vote, finished))
    
    print(f"Read {len(game_data)} 输出本地游戏数据信息 {file_path}") 
    return game_data

# 主函数
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    
    ignored_files = ["progress.json", "config.json", "failed_uploads.json"]
    local_game_data_path = None
    
    for extension in [".xlsx", ".csv", ".json"]:
        for file_name in os.listdir(script_dir):
            if file_name in ignored_files:
                continue
            if file_name.endswith(extension):
                local_game_data_path = os.path.join(script_dir, file_name)
                break
        if local_game_data_path:
            break

    if not local_game_data_path:
        raise FileNotFoundError("未找到本地游戏数据文件 (.xlsx, .csv, or .json format).")
    else:
        print(f"输出本地游戏数据文件路径: {local_game_data_path}") 
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    sync = VNDBSync(config_path)
    
    game_data = read_local_game_data(local_game_data_path)
    print(f"Read {len(game_data)}本地游戏数据")  

    if sync.sync_local:
        failed_uploads = sync.upload_game_list(game_data)
        if failed_uploads:
            sync.save_failed_uploads(failed_uploads)
            print(f"失败的上传保存到: {sync.failed_uploads_path}") 
    
    if sync.download_vndb:
        downloaded_list = sync.download_game_list()
        print("下载列表:")
        print(downloaded_list)
