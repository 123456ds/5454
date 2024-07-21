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

def saferequestvndb(proxy, method, url, json=None, headers=None):
    """
    安全地向VNDB API发送请求，处理重试和错误情况。

    :param proxy: 代理设置
    :param method: HTTP方法（GET, POST, PATCH等）
    :param url: API的URL路径
    :param json: 请求的JSON数据
    :param headers: 请求头
    :return: 响应的JSON数据或None
    """
    # 创建一个会话对象
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        print(method, url, json)
        # 发送请求
        resp = session.request(
            method,
            "https://api.vndb.org/kana/" + url,
            headers=headers,
            json=json,
            proxies=proxy,
        )
        if resp.status_code == 429:
            # 如果状态码为429，等待3秒后重试
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
    """
    安全地发送POST请求到VNDB API并返回JSON响应。

    :param proxy: 代理设置
    :param url: API的URL路径
    :param json: 请求的JSON数据
    :return: 响应的JSON数据或None
    """
    return saferequestvndb(proxy, "POST", url, json)

def gettitlefromjs(js):
    """
    从VNDB的JSON响应中提取主标题。

    :param js: VNDB的JSON响应
    :return: 主标题
    """
    try:
        for _ in js["titles"]:
            main = _["main"]
            title = _["title"]
            if main:
                return title
        raise Exception()
    except:
        return js["title"]

def truncate_title(title):
    """
    截断标题，去除特殊符号。

    :param title: 原始标题
    :return: 截断后的标题（开始和结束部分）
    """
    # 定义匹配任意符号的正则表达式
    symbol_regex = re.compile(r'[^\w\s]', re.UNICODE)
    
    # 从头部截断
    match_start = symbol_regex.search(title)
    truncated_start = title[:match_start.start()] if match_start else title[:20]

    # 从尾部截断
    match_end = symbol_regex.search(title[::-1])
    truncated_end = title[len(title)-match_end.start():] if match_end else title[-20:]

    return truncated_start.strip(), truncated_end.strip()

def getvidbytitle_vn(proxy, title):
    """
    通过标题从VNDB的'vn'端点获取游戏ID。

    :param proxy: 代理设置
    :param title: 游戏标题
    :return: 游戏ID或None
    """
    js = safegetvndbjson(
        proxy,
        "vn",
        {"filters": ["search", "=", title], "fields": "id", "sort": "searchrank"},
    )
    if js and js.get('results'):
        return js["results"][0]["id"]
    else:
        # 尝试模糊搜索，截取标题
        truncated_start, truncated_end = truncate_title(title)
        
        js_start = safegetvndbjson(
            proxy,
            "vn",
            {"filters": ["search", "=", truncated_start], "fields": "id", "sort": "searchrank"},
        )
        if js_start and js_start.get('results'):
            return js_start["results"][0]["id"]
        
        js_end = safegetvndbjson(
            proxy,
            "vn",
            {"filters": ["search", "=", truncated_end], "fields": "id", "sort": "searchrank"},
        )
        if js_end and js_end.get('results'):
            return js_end["results"][0]["id"]

    return None

def getvidbytitle_release(proxy, title):
    """
    通过标题从VNDB的'release'端点获取游戏ID。

    :param proxy: 代理设置
    :param title: 游戏标题
    :return: 游戏ID或None
    """
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
    else:
        # 尝试模糊搜索，截取标题
        truncated_start, truncated_end = truncate_title(title)
        
        js_start = safegetvndbjson(
            proxy,
            "release",
            {
                "filters": ["search", "=", truncated_start],
                "fields": "id,vns.id",
                "sort": "searchrank",
            },
        )
        if js_start and js_start.get('results'):
            return js_start["results"][0]["vns"][0]["id"]
        
        js_end = safegetvndbjson(
            proxy,
            "release",
            {
                "filters": ["search", "=", truncated_end],
                "fields": "id,vns.id",
                "sort": "searchrank",
            },
        )
        if js_end and js_end.get('results'):
            return js_end["results"][0]["vns"][0]["id"]

    return None

def getidbytitle_(proxy, title, title_cn):
    """
    通过标题和中文标题获取游戏ID。

    :param proxy: 代理设置
    :param title: 游戏标题
    :param title_cn: 游戏中文标题
    :return: 游戏ID或None
    """
    vid = getvidbytitle_vn(proxy, title)
    if not vid:
        vid = getvidbytitle_vn(proxy, title_cn)
    if not vid:
        vid = getvidbytitle_release(proxy, title)
    if not vid:
        vid = getvidbytitle_release(proxy, title_cn)
    return vid

class VNDBSync:
    def __init__(self, config_path, proxy=None):
        """
        初始化VNDBSync类，读取配置文件并设置代理。

        :param config_path: 配置文件路径
        :param proxy: 代理设置
        """
        # 读取配置文件
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.proxy = proxy
        self.headers = {
            "Authorization": f"Token {self.config['Token']}",
        }
        self.sync_local = self.config.get("sync_local", False)
        self.download_vndb = self.config.get("download_vndb", False)
        self.progress_file = os.path.join(os.path.dirname(config_path), "progress.json")
        self.failed_uploads_path = os.path.join(os.path.dirname(config_path), "failed_uploads.json")
        self.current_index = self.load_progress()

    @property
    def userid(self):
        """
        获取用户ID。

        :return: 用户ID
        """
        return saferequestvndb(self.proxy, "GET", "authinfo", headers=self.headers)["id"]

    def querylist(self, title):
        """
        查询用户列表中的游戏数据。

        :param title: 是否包含标题字段
        :return: 游戏数据列表
        """
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
        """
        上传游戏数据到VNDB。

        :param vid: 游戏ID
        :param labels_set: 标签集合
        :param vote: 评分
        :param finished: 完成日期
        """
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
        """
        下载用户游戏列表。

        :return: 游戏数据列表
        """
        collectresults = self.querylist(True)
        return collectresults

    def upload_game_list(self, game_data):
        """
        上传游戏列表到VNDB。

        :param game_data: 游戏数据列表
        :return: 失败的上传列表
        """
        failed_uploads = []
        
        for i in tqdm(range(self.current_index, len(game_data)), desc="Uploading games"):
            game = game_data[i]
            title, title_cn, labels_set, vote, finished = game
            vid = getidbytitle_(self.proxy, title, title_cn)
            if vid:
                try:
                    self.upload_game(int(vid[1:]), labels_set, vote, finished)
                    self.current_index = i + 1
                    self.save_progress()
                except Exception as e:
                    print(f"Failed to upload game '{title}': {e}")
                    failed_uploads.append(game)
                    self.save_failed_uploads([game])  # 每次失败时保存
            else:
                print(f"Failed to find ID for game '{title}'")
                failed_uploads.append(game)
                self.save_failed_uploads([game])  # 每次失败时保存
        
        return failed_uploads

    def save_progress(self):
        """
        保存当前进度到文件。
        """
        with open(self.progress_file, 'w', encoding='utf-8') as file:
            json.dump({"current_index": self.current_index}, file)

    def load_progress(self):
        """
        从文件加载当前进度。

        :return: 当前进度索引
        """
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return data.get("current_index", 0)
        return 0

    def save_failed_uploads(self, failed_uploads):
        """
        保存失败的上传记录到文件。

        :param failed_uploads: 失败的上传记录列表
        """
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

def read_local_game_data(file_path): # 读取本地游戏数据文件
    """
    从本地文件读取游戏数据。

    :param file_path: 文件路径
    :return: 游戏数据列表
    """
    _, file_extension = os.path.splitext(file_path)
    game_data = []
    
    if file_extension == ".xlsx": # 导入Excel数据
        df = pd.read_excel(file_path) # 读取Excel文件
        for _, row in df.iterrows(): # 遍历Excel数据
            title = row.iloc[1] if pd.notna(row.iloc[1]) else row.iloc[0] # 优先使用中文标题
            title_cn = row.iloc[0] if pd.notna(row.iloc[0]) else None # 其次使用英文标题
            finished = None # 完成日期
            if pd.notna(row.iloc[5]): # 格式化完成日期
                try:
                    finished_date = pd.to_datetime(row.iloc[5])
                    finished = finished_date.strftime('%Y-%m-%d')
                except ValueError:
                    finished = row.iloc[5]
            vote = int(row.iloc[6] * 10) if pd.notna(row.iloc[6]) else None # 格式化评分
            status_map = { # 状态映射
                "想看": [5],
                "在看": [1],
                "看过": [2],
                "搁置": [3],
                "抛弃": [4]
            }
            labels_set = status_map.get(row.iloc[10], []) # 格式化标签集
            game_data.append((title, title_cn, labels_set, vote, finished)) # 添加游戏数据

    elif file_extension == ".csv": # 导入CSV数据
        with open(file_path, mode='r', encoding='utf-8') as file: # 打开CSV文件
            reader = csv.reader(file) # 读取CSV文件
            next(reader) # 跳过标题行
            for row in reader:
                if row[2].strip() == "游戏": # 跳过非游戏数据
                    title = row[0] if row[0].strip() else row[1] # 优先使用中文标题
                    title_cn = row[1] if row[1].strip() else None # 其次使用英文标题
                    finished = row[5].replace('/', '-') if row[5].strip() else None # 格式化完成日期
                    vote = int(row[9].strip()) * 10 if row[9].strip() != "(无评分)" else None # 格式化评分
                    status_map = { # 状态映射
                        "想看": [5],
                        "在看": [1],
                        "看过": [2],
                        "搁置": [3],
                        "抛弃": [4]
                    }
                    labels_set = status_map.get(row[4], []) # 格式化标签集
                    game_data.append((title, title_cn, labels_set, vote, finished)) # 添加游戏数据

    elif file_extension == ".json": # 导入JSON数据
        with open(file_path, 'r', encoding='utf-8') as file: # 打开JSON文件
            data = json.load(file) # 读取JSON文件
            if "data" not in data: # 期望的游戏数据格式错误
                print(" JSON数据中没有'data'键") 
                raise ValueError("期望的游戏数据格式错误.") 
            for item in data["data"]: # 遍历游戏数据
                if item.get("subject_type") == 4: # 跳过非游戏数据
                    title = item["subject"]["name"] # 优先使用中文标题
                    title_cn = item["subject"].get("name_cn", None) # 其次使用英文标题
                    finished = item["updated_at"].split('T')[0] # 格式化完成日期
                    vote = int(item["rate"]) * 10 if item["rate"] != 0 else None # 格式化评分
                    status_map = { # 状态映射
                         1: [5],
                         2: [2],
                         3: [1],
                         4: [3],
                         5: [4]
                    }
                    labels_set = status_map.get(item["type"], []) # 格式化标签集
                    game_data.append((title, title_cn, labels_set, vote, finished)) # 添加游戏数据
    
    print(f"Read {len(game_data)} 读取本地游戏数据文件: {file_path}") # 读取本地游戏数据文件
    return game_data # 返回游戏数据列表

if __name__ == "__main__": # 主程序入口
    script_dir = os.path.dirname(os.path.abspath(__file__)) # 脚本所在目录
    config_path = os.path.join(script_dir, "config.json") # 配置文件路径
    
    ignored_files = ["progress.json", "config.json", "failed_uploads.json"] # 忽略的文件
    local_game_data_path = None # 本地游戏数据文件路径
    
    for extension in [".xlsx", ".csv", ".json"]: # 本地游戏数据文件扩展名
        for file_name in os.listdir(script_dir): 
            if file_name in ignored_files:
                continue
            if file_name.endswith(extension): 
                local_game_data_path = os.path.join(script_dir, file_name)
                break
        if local_game_data_path: 
            break

    if not local_game_data_path: # 未找到本地游戏数据文件
        raise FileNotFoundError("未找到本地游戏数据文件 .xlsx, .csv, or .json format.") 
    else:
        print(f"Found local game data file: {local_game_data_path}")
    
    if not os.path.exists(config_path): # 配置文件不存在
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    sync = VNDBSync(config_path) # 创建VNDB同步对象
    
    game_data = read_local_game_data(local_game_data_path) # 读取本地游戏数据文件
    print(f"Read {len(game_data)} 读取本地游戏数据文件.") 

    if sync.sync_local: # 同步本地游戏数据到VNDB
        failed_uploads = sync.upload_game_list(game_data)
        if failed_uploads:
            sync.save_failed_uploads(failed_uploads)
            print(f"Failed uploads saved to: {sync.failed_uploads_path}")
    
    if sync.download_vndb: # 下载VNDB游戏数据
        downloaded_list = sync.download_game_list()
        print("Downloaded List:")
        print(downloaded_list)
