# 使用 GitHub Actions 自动化同步班固米游戏收藏数据到 VNDB

本文将介绍如何使用 GitHub Actions 自动化任务来同步班固米（Bangumi）游戏收藏数据到 VNDB。这个自动化任务能够帮助你将班固米上的游戏收藏数据自动导出并更新到 VNDB，无需手动操作。以下是具体的操作步骤和解释。

## 前提条件

在开始之前，请确保你已经拥有以下内容：
1. 一个 GitHub 仓库，用于存放和运行 GitHub Actions 工作流。
2. 班固米（Bangumi）和 VNDB 的访问令牌，存储在 GitHub 仓库的 Secrets 中。
3. GitHub Actions 配置文件。

## 配置 GitHub Secrets

在 GitHub 仓库中，导航到 `Settings > Secrets and variables > Actions`，添加以下 Secrets：
- `BGM_ACCESS_TOKEN`: 你的班固米访问令牌。
- `VNDB_TOKEN`: 你的 VNDB 访问令牌。
- `HTTP_PROXY` 和 `HTTPS_PROXY`（可选）: 如果你需要通过代理服务器访问网络，配置这些代理服务器的地址。
-
## 运行工作流
配置完成后，可以在 GitHub Actions 页面手动触发该工作流。导航到你的 GitHub 仓库，点击 Actions 选项卡，找到你创建的工作流，点击 Run workflow 按钮手动触发任务。

## 结束语
通过上述步骤，你可以轻松地配置和运行 GitHub Actions 自动化任务，将班固米的游戏收藏数据同步到 VNDB。这不仅可以节省手动操作的时间，还能确保数据的及时更新。如果在配置过程中遇到问题，可以查阅 GitHub Actions 的官方文档或寻求社区帮助。
