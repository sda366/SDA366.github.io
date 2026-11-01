# 小学有声图文课件 · 维护工具备份

这里放的是**生成与体检课件用的脚本副本**和**技能包备份**，方便换机器、换环境时随时取用。
站点页面本身不依赖本目录（页面只引用 `小学/js/read-assist.js`）。

来源：本地技能目录
- `C:\Users\hxszs\.workbuddy\skills\math-primary-courseware\assets\`
- `C:\Users\hxszs\.workbuddy\skills\chinese-primary-courseware\assets\`

**改动脚本请改技能目录里的那份**，这里只是备份；技能改完重新打包后把 `.skill` 覆盖到 `skills/` 即可。

## 最常用：一键加固 + 体检

```bash
python harden.py 小学/二年级/数学/有声图文学习中心 --check    # 只体检，不写文件
python harden.py <站点目录>                                    # 写入修补（幂等）
python harden.py --self-test                                   # 检查技能自身是否加固到位
```

六步流水线：引擎注入 → 声音提示条 → 单题点击链路 → watchdog → 换行符统一 → 全站体检。

## 单文件说明

| 文件 | 用途 |
|---|---|
| `harden.py` | 一键加固流水线（带 `--check` / `--sim` / `--self-test`） |
| `verify_all.py` | 全站体检 11 项（数学版；语文页加 `--no-think`） |
| `check_page_math.js` | 数学单页校验 16 项 |
| `check_page_chinese.js` | 语文单页校验 53 项 |
| `fix_askqa.py` | 修「点单题没声音/不展开」（abort 复位 + 延迟发声），幂等 |
| `sim_askqa.js` | Node 功能仿真：真跑一次单题点击，断言读题/想一想/展开/读答案 |
| `add_read_assist.py` | 把朗读引擎注入/迁移到 `<body>` 开标签后 |
| `add_sound_tip.py` | 顶部「手机没声音怎么办」提示条（可关闭、记住、宽屏隐藏） |
| `patch_watchdog.py` | 超时兜底改轮询，避免长文本被硬截断 |

## 技能包

`skills/math-primary-courseware.skill`、`skills/chinese-primary-courseware.skill`
—— 在 WorkBuddy 里可直接安装的技能压缩包（解压后根目录即技能名）。

当前版本：数学 v4.8 / 语文 v1.4（2026-11-01）。
