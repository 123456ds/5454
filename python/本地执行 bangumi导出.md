## 本地执行 bangumi导出

这是一个用于从 Bangumi API 获取用户收藏数据并保存为 JSON 文件的脚本。该脚本修改自 [https://github.com/jerrylususu/bangumi-takeout-py/blob/master/fetch.py](https://github.com/jerrylususu/bangumi-takeout-py/blob/master/fetch.py)。以下是详细的使用说明和代码解析。

## 脚本功能
1. 使用 Bearer 令牌进行 API 请求，返回 JSON 响应。
2. 循环加载数据直到结束。
3. 加载用户信息。
4. 加载用户的收藏并保存为 `collections.json` 文件。
5. 将所有数据打包并保存为 `takeout.json` 文件。

## 环境要求
- Python 3
- 安装 `requests` 和 `tqdm` 库

## 配置
在运行脚本之前，需要配置访问令牌和用户名：
1. 将访问令牌保存在 `./.bgm_token` 文件中，格式如下：
    ```json
    {
        "access_token": "YOUR_ACCESS_TOKEN"
        "USERNAME ": "YOUR_USERNAME"    
    }
    ```
2. 确保脚本中的 `API_SERVER` 和 `LOAD_WAIT_MS` 配置正确。
