

# 使用[bangumi collection export tool](https://greasyfork.org/zh-CN/scripts/408988-bangumi-collection-export-tool/feedback) 或[bangumi-takeout-py](https://github.com/jerrylususu/bangumi-takeout-py) 导出收藏记录同步到[VNDB](https://vndb.org/)。

## VNDB 数据同步脚本

本文介绍了一个用于从 VNDB API 获取和上传游戏数据的 Python 脚本。该脚本可以读取本地的游戏数据文件，并将其同步到 VNDB，同时支持从 VNDB 下载游戏列表并保存到本地。

## 脚本功能
1. 安全请求函数，用于处理 VNDB API 的请求。
2. 通过标题和中文标题获取 VNDB 中的游戏 ID。
3. 上传游戏数据到 VNDB。
4. 下载 VNDB 中的游戏列表。
5. 读取本地游戏数据文件（支持 `.xlsx`、`.csv`、`.json` 格式）。
6. 保存和加载同步进度，处理失败的上传记录。

## 环境要求
- Python 3
- 安装所需的库：
    ```bash
    pip install requests pandas openpyxl tqdm
    ```

## 配置
在运行脚本之前，需要进行以下配置：
1. 创建 `config.json` 文件，内容如下：
    ```json
    {
        "Token": "YOUR_API_TOKEN",
        "sync_local": true,
        "download_vndb": true
    }
    ```
2. 将本地的游戏数据文件（`.xlsx`、`.csv`、`.json` 格式）放置在脚本所在的目录。

## 使用步骤
1. 确保 Python 环境中安装了所需的库：
    ```bash
    pip install requests pandas openpyxl tqdm
    ```
2. 创建并配置 `config.json` 文件。
3. 将本地游戏数据文件放置在脚本目录中。
4. 运行脚本：
    ```bash
    python script_name.py
    ```
5. 脚本将自动读取本地游戏数据文件并同步到 VNDB，同时保存同步进度和失败的上传记录。

## 注意事项
- 确保 API 令牌有效且具有足够的权限访问用户数据。
- 本地游戏数据文件格式应符合脚本的读取要求，支持 `.xlsx`、`.csv` 和 `.json` 格式。
- 在同步过程中，脚本会处理 API 请求速率限制，并在必要时进行重试。

## 本地游戏数据文件格式
#### Excel 文件格式（.xlsx）
#### Excel 文件应包含以下列（顺序不重要）：

- 标题
- 中文标题（可选）
- 评分（可选）
- 完成日期（可选）
- 状态（如“想看”、“在看”、“看过”等）

## CSV 文件格式（.csv）
#### CSV 文件应包含以下列（顺序不重要）：

- 标题
- 中文标题（可选）
- 评分（可选）
- 完成日期（可选）
- 状态（如“想看”、“在看”、“看过”等）

## JSON 文件格式（.json）

JSON 文件应包含以下键：

- games: 包含游戏数据的列表
    - game_item: 每个游戏项
        - subject_type: 类型，应为 4（游戏）
        - subject: 游戏信息
            - name: 游戏标题
            - name_cn: 中文标题（可选）
            - rate: 评分（可选）
            - updated_at: 完成日期（可选）
            - type: 状态（如 1 表示“想看”，2 表示“在看”等）




_________________


 **通过以上配置和使用步骤，您可以轻松实现 VNDB 数据的同步和管理。确保配置正确，并按照步骤操作，即可成功同步和下载游戏数据。**
