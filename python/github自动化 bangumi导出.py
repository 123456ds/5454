#适用与增量更新，每天自动拉起最新修改的50条游戏收藏数据。

import requests
import json
import os

# 配置 Bangumi API 端点和访问令牌
BGM_API_URL = "https://api.bgm.tv/v0"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def get_headers(access_token):
    headers = HEADERS.copy()
    headers["Authorization"] = f"Bearer {access_token}"
    return headers

def fetch_username(headers):
    response = requests.get(f"{BGM_API_URL}/me", headers=headers)
    response.raise_for_status()
    return response.json()["username"]

def fetch_collections(username, headers):
    params = {
        "subject_type": "4",
        "limit": "50",
        "offset": "0",
    }
    response = requests.get(f"{BGM_API_URL}/users/{username}/collections", params=params, headers=headers)
    response.raise_for_status()
    return response.json()["data"]

def fetch_detailed_info(subject_id, headers):
    response = requests.get(f"{BGM_API_URL}/subjects/{subject_id}", headers=headers)
    response.raise_for_status()
    return response.json()

def main():
    access_token = os.getenv("BGM_ACCESS_TOKEN")
    if not access_token:
        raise ValueError("No access token provided. Set the BGM_ACCESS_TOKEN environment variable.")
    
    headers = get_headers(access_token)
    username = fetch_username(headers)
    collections = fetch_collections(username, headers)
    detailed_collections = []

    for item in collections:
        subject_id = item["subject_id"]
        detailed_info = fetch_detailed_info(subject_id, headers)
        detailed_collections.append({
            "updated_at": item["updated_at"],
            "comment": item["comment"],
            "tags": item["tags"],
            "subject": detailed_info,
            "subject_id": item["subject_id"],
            "vol_status": item["vol_status"],
            "ep_status": item["ep_status"],
            "subject_type": item["subject_type"],
            "type": item["type"],
            "rate": item["rate"],
            "private": item["private"]
        })

    output = {"data": detailed_collections}
    
    with open("collection_list.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
