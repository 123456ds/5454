#修改自https://github.com/jerrylususu/bangumi-takeout-py/blob/master/fetch.py

import json
import time
import logging
import os
from pathlib import Path
import requests
from tqdm import tqdm

# 设置日志记录的级别为INFO
logging.basicConfig(level=logging.INFO)

API_SERVER = "https://api.bgm.tv"
LOAD_WAIT_MS = 5000  # 请求之间的等待时间，单位为毫秒
ACCESS_TOKEN = ""  # 存储访问令牌
USERNAME = ""  # 存储用户名

# 使用Bearer令牌进行API请求，返回JSON响应
def get_json_with_bearer_token(url):
    time.sleep(LOAD_WAIT_MS / 1000)  # 等待指定的毫秒数
    logging.debug(f"加载URL: {url}")
    headers = {
        'Authorization': 'Bearer ' + ACCESS_TOKEN,
        'accept': 'application/json',
        'User-Agent': 'bangumi-takeout-python/v1'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# 循环加载数据直到结束
def load_data_until_finish(endpoint, limit=30, name="", show_progress=False):
    items = []  # 存储所有加载的数据
    offset = 0  # 偏移量，用于分页
    while True:
        new_url = f"{endpoint}?limit={limit}&offset={offset}"
        resp = get_json_with_bearer_token(new_url)
        if 'data' in resp:
            new_items = resp['data']
            items.extend(new_items)
            if show_progress:
                tqdm.write(f"{name}: 加载了 {len(new_items)} 项, 目前总共: {len(items)} 项")
            if len(new_items) < limit:  # 如果加载的数据量小于每次请求的限制，说明已经加载完毕
                break
            offset += limit
        else:
            break
    return items

# 加载用户信息
def load_user():
    global USERNAME
    endpoint = f"{API_SERVER}/v0/me"
    user_data = get_json_with_bearer_token(endpoint)
    USERNAME = user_data["username"]
    return user_data

# 加载用户的收藏
def load_user_collections():
    endpoint = f"{API_SERVER}/v0/users/{USERNAME}/collections"
    collections = load_data_until_finish(endpoint, name="用户收藏", show_progress=True)
    logging.info(f"加载了 {len(collections)} 个收藏")
    with open("collections.json", "w", encoding="u8") as f:
        json.dump(collections, f, ensure_ascii=False, indent=4)
    return collections

# 触发认证
def trigger_auth():
    global ACCESS_TOKEN
    if Path("./.bgm_token").exists():
        with open("./.bgm_token", "r", encoding="u8") as f:
            tokens = json.load(f)
            ACCESS_TOKEN = tokens["access_token"]
            logging.info("访问令牌已加载")
    if not ACCESS_TOKEN:
        raise Exception("ACCESS_TOKEN 为空！")

# 主函数
def main():
    trigger_auth()
    logging.info("开始获取数据")
    user = load_user()
    collections = load_user_collections()
    takeout_data = {"meta": {"generated_at": time.time(), "user": user}, "data": collections}
    with open("takeout.json", "w", encoding="u8") as f:
        json.dump(takeout_data, f, ensure_ascii=False, indent=4)
    logging.info("完成")

if __name__ == "__main__":
    main()
