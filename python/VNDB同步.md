

使用[bangumi collection export tool](https://greasyfork.org/zh-CN/scripts/408988-bangumi-collection-export-tool/feedback) 或[bangumi-takeout-py](https://github.com/jerrylususu/bangumi-takeout-py) 导出收藏记录同步到[VNDB](https://vndb.org/)。

默认优先使用第二列的游戏标题进行搜索，如果第二列为空，则使用第一列的游戏标题。
默认标记状态为【完成】，修改 "labels_set": [1], 可以标记为其他状态。
状态码

    <label id="1" label="Playing" private="true" />
    <label id="2" label="Finished" private="true" />
    <label id="3" label="Stalled" private="true" />
    <label id="4" label="Dropped" private="true" />
    <label id="5" label="Wishlist" private="true" />
    <label id="6" label="Blacklist" private="true" />
    <label id="7" label="Voted" private="true" />

