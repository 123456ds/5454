

使用[bangumi collection export tool](https://greasyfork.org/zh-CN/scripts/408988-bangumi-collection-export-tool/feedback) 或[bangumi-takeout-py](https://github.com/jerrylususu/bangumi-takeout-py) 导出收藏记录同步到[VNDB](https://vndb.org/)。

默认Token保存在config.json；默认数据文件与脚本在同一目录。

默认读取.xlsx文件。

默认标记状态为【完成】，修改 "labels_set": [1], 可以标记为其他状态。

状态码
```
    <label id="1" label="Playing" private="true" />  在玩
    <label id="2" label="Finished" private="true" /> 完成
    <label id="3" label="Stalled" private="true" />  搁置
    <label id="4" label="Dropped" private="true" />  抛弃
    <label id="5" label="Wishlist" private="true" /> 
    <label id="6" label="Blacklist" private="true" />
    <label id="7" label="Voted" private="true" />
```

config.json
```sh
{
    "Token": "your_token_here",  
    "sync_local": true,         #同步本地记录到 VNDB。
    "download_vndb": true       #从 VNDB 下载记录。
}
```


同步记录时可以额外添加的参数：

```
Add or update a visual novel in the user’s list. Requires the listwrite permission. The JSON body accepts the following members:

vote
Integer between 10 and 100.

notes
String.

started
Date.

finished
Date.

labels
Array of integers, label ids. Setting this will overwrite any existing labels assigned to the VN with the given array.

labels_set
Array of label ids to add to the VN, any already existing labels will be unaffected.

labels_unset
Array of label ids to remove from the VN.
```
