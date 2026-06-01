import sys
sys.path.insert(0, 'G:/workbuddy/binaries/python/envs/default/Lib/site-packages')

import pandas as pd

# 读取xlsx
df = pd.read_excel('E:/GitHub/SDA366.github.io/高一9班10班历史成绩合并排名.xlsx')
print('COLUMNS:', df.columns.tolist())
print('SHAPE:', df.shape)
# 输出为HTML表格字符串
html_table = df.to_html(index=False, border=0, classes='score-table')
# 写入文件
with open('E:/GitHub/SDA366.github.io/高一/成绩表_显示.html', 'w', encoding='utf-8') as f:
    f.write('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>成绩表</title>
<link rel="stylesheet" href="../css/theme.css">
<link rel="stylesheet" href="../css/style.css">
<style>
  .table-wrap { max-width:900px; margin:2rem auto; overflow-x:auto; }
  .score-table { width:100%; border-collapse:collapse; font-size:13pt; }
  .score-table th { background:var(--red-deep); color:var(--gold-pale); padding:8px 12px; position:sticky; top:0; }
  .score-table td { padding:7px 12px; border-bottom:1px solid var(--gold-pale); }
  .score-table tr:nth-child(even) { background:var(--section-alt); }
  .score-table tr:hover { background:#f5efe6; }
</style>
</head>
<body class="theme-blue">
''' + html_table + '''
</body>
</html>''')
print('DONE')
