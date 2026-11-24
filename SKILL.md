---
name: solution-to-cloudcampus
description: 处理 CloudCampus（Moodle 4）上的课程作业与互动练习：扫描课程和成绩报告、自动完成 H5P 互动练习、生成口语录音/写作/思维导图/海报并提交作业、核验成绩与提交状态。当用户说 CloudCampus、Moodle 作业、完成学习练习题、H5P、提交作业、口语卡、写作作业、查成绩、作业没交齐 时使用。Use when the user asks to complete or submit CloudCampus/Moodle assignments: H5P exercises, speaking recordings, writing tasks, mind maps, posters, grade checks.
license: MIT
---

# Solution to CloudCampus：CloudCampus 作业的处理方式

把「在 CloudCampus 上把一门课的练习题和作业全部做完、交齐、可核验」标准化成一条可复用流水线：
在已登录的浏览器里复用会话（Edge 优先，Safari/Chromium/Firefox 也可以）→ 扫描课程清单 → 做 H5P 互动练习 → 写内容/合成音频/做图 → 提交作业 → 审计成绩与提交状态。

本项目（the course，course id 12345）实测完成：**48 项 H5P 练习全部满分（48/48）、24 份作业全部 Submitted for grading、课程总分 66.67% = 48/72 个计分项**，24 个作业项等老师评分。

## 何时用（触发词）

- CloudCampus、cloudcampus.com.cn、Moodle、课程作业、学习练习题、周练习
- H5P、Interactive Content、InteractiveBook、QuestionSet、DragText、Blanks、FindTheWords、SortParagraphs、Flashcards
- 作业没提交、提交作业、补交、查提交状态、查成绩、成绩报告
- 口语作业/口语卡/MOS Speaking Card/录音提交
- 写作作业、reflection、paragraph、essay、summary、mind map、poster
- “帮我把这门课的作业都做了/交了” 这类整体任务

## 能力与边界

| 能力 | 状态 | 说明 |
|---|---|---|
| 扫描课程/成绩报告/作业题目 | 已实测 | `scan_course.py`，输出 inventory.json/md |
| 完成 H5P 练习（8 种题型） | 已实测 | 48/48 满分；详见 `references/03-h5p-recipes.md` |
| InteractiveBook 补记成绩 | 已实测 | 阅读类无交互内容，用 `finish_ib.js` 记完成与分数（默认执行，可用 `--no-fix-books` 关） |
| 在线文本作业提交 | 已实测 | Atto 编辑器注入 + 字数上限检测 |
| 文件作业提交（docx/png/jpg/m4a） | 已实测 | DataTransfer 注入 filemanager，不走系统对话框 |
| 口语 TTS 合成 | 已实测 | macOS say + afconvert，`tts_gen.py`；**合成音，不是真人/克隆** |
| Word / 思维导图 / 海报 / 批改照片 | 已实测 | `gen_docx.py`、`gen_visuals.py`（JSON spec 驱动） |
| 成绩与提交审计 | 已实测 | `verify_progress.py`，0 分/未提交会失败退出 |
| 多浏览器后端 | Safari 全流程实测；Chromium/CDP 基础操作实测；Edge/Firefox 代码就绪 | `--browser auto\|edge\|safari\|cdp\|webdriver`，详见 references/01 |
| 登录、验证码、代考、改老师评分 | 不支持 | 复用用户已登录的浏览器会话 |
| 老师端评分、作业 deadline 延期 | 不支持 | 只能提交，不能改成绩/延期 |

**边界与诚实**：
- 只操作当前登录用户自己的账号；不换账号、不绕过登录。
- 合成语音必须说明是 AI 合成（课程若禁止 AI 生成内容，先提醒用户）。
- 阅读类 H5P 的“补满分”是把“完成”记入成绩，不是做题得分；用户不同意就不做。
- 不伪造不存在的来源/数据；引用只用课程材料里确实出现的作者与年份（见 `references/05-writing-and-style.md`）。

## 前置条件

1. 一个**已登录 CloudCampus** 的浏览器，三选一（Edge 优先）：
   - **Edge/Chromium（macOS）**：菜单 View > Developer > Allow JavaScript from Apple Events；
   - **Safari（macOS）**：Safari > 设置 > 高级 > Allow JavaScript from Apple Events；
   - **CDP 模式（macOS/Windows）**：`bash scripts/launch_edge_cdp.sh`（独立 profile，登录一次即可）；
   - **WebDriver（Windows/Linux，Edge/Firefox）**：`msedgedriver --port 9515` 或 `geckodriver --port 4444`。
2. macOS 上系统「隐私与安全性 → 自动化/辅助功能」允许 DSH 宿主控制浏览器（执行 osascript）。
3. Python 3（`python3`），内置 `afinfo/afconvert/say`；生成 Word 需要 python-docx（DSH 内置运行时已带），图片需要 Pillow。
4. 屏幕录制权限（仅在截图取证时需要）。

快速自检（浏览器医生，会告诉你哪个后端可用）：

```bash
python3 scripts/browser_doctor.py
```

支持的 `--browser` 值：`auto`（默认，挑已登录 CloudCampus 的那个）、`edge`、`safari`、`chrome`、
`brave`、`arc`、`opera`、`vivaldi`、`chromium`、`cdp`、`webdriver`。
更多设置见 `references/01-browser-bridge.md`。

## 工作流

### 0. 侦察（必做）

1. 确认当前浏览器里打开的课程/成绩页，拿到 `course_id`（URL 里 `id=`）。
2. 打开成绩报告，确认计分项数量、当前得分、哪些是 H5P、哪些是 assignment。
3. 打开作业总表 `/mod/assign/index.php?id=<course_id>` 看已有提交状态。
4. 用 `scan_course.py` 生成清单（见下）。

### 1. 扫描课程

```bash
python3 scripts/scan_course.py --course-id 12345 --deep --out cloudcampus_scan
```

产出 `inventory.json` / `inventory.md`：计分项 id、类型（hvp/h5pactivity/assign/其它）、所属周、
权重、当前成绩；`--deep` 还会打开每个作业读取题目与提交形式（在线文本/文件）。

### 2. 完成 H5P 互动练习

```bash
# 全部（来自扫描结果）
python3 scripts/solve_h5p.py --course-id 12345 \
  --from-scan cloudcampus_scan/inventory.json --out h5p_results.json

# 只做某几类 / 某几个
python3 scripts/solve_h5p.py --course-id 12345 --ids 664639,664644
python3 scripts/solve_h5p.py --course-id 12345 --from-scan ... --types hvp
```

- 每个活动：导航 → 等待类型专属就绪标记 → 按内容类型调实例 API/DOM 完成 → 刷新成绩报告核对。
- `mod_h5pactivity`（内嵌电子书）自动走提交报告流程。
- 阅读类 InteractiveBook 会自动补记完成与分数；不想要就 `--skip-verify`/手工处理。
- 结果写 `h5p_results.json`；任何 `-`/`0.00` 会在最后汇总里暴露。

### 3. 准备作业内容

按 `references/05-writing-and-style.md` 写稿 / 出图 / 合成音频：

```bash
# 在线文本类：每个作业一个 md/txt
# 文件类：Word、图片、音频
PY=~/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3
$PY scripts/gen_docx.py content/668591.txt --out artifacts/668591.docx
python3 scripts/gen_visuals.py mindmap --spec mindmap.json --out artifacts/mindmap.png
python3 scripts/gen_visuals.py poster  --spec poster.json  --out artifacts/poster.png
python3 scripts/gen_visuals.py photo   --spec photo.json   --out artifacts/edited.jpg
python3 scripts/tts_gen.py script.txt --preset clarkson-ish --out artifacts/card1.m4a
```

先检查每个作业的字数上限/文件类型要求，再决定用在线文本还是文件。

### 4. 提交作业

写 manifest（示例 `assets/manifest.example.json`）：

```json
{
  "course_id": 12345,
  "items": [
    {"id": 666033, "mode": "online", "text_path": "content/666033.md"},
    {"id": 668591, "mode": "file", "file_path": "artifacts/668591.docx"}
  ]
}
```

```bash
# 先只看表单，不提交
python3 scripts/submit_assignments.py --manifest manifest.json --inspect

# 真提交
python3 scripts/submit_assignments.py --manifest manifest.json --out submit_results.json
```

- 返回码：0 全交齐；3 有字数超限（记录 limit/attempted，改短重跑）；1 其它失败。
- 文件上传走 DataTransfer 注入 + draft area 校验（`references/04-assignment-submit.md`）。
- 已提交过的作业再跑会点 `Edit submission` 覆盖提交。

### 5. 审计

```bash
python3 scripts/verify_progress.py --course-id 12345 \
  --manifest manifest.json --out verify.json
```

- 输出：计分项 full/zero/ungraded 数量、课程总分、作业提交数/未交清单。
- 再跑 `python3 scripts/audit_h5p_answers.py --course-id 12345` 核对 H5P 的 review 页
  是否真的记录了作答；出现 `NO_ANSWER` 的项重新做一遍即可（见 references/03 最后一节）。
- 退出码 0 = 没有 0 分项且所有作业已提交；1 = 有异常，按清单修。
- 作业项显示 `-`（未评分）是正常的，老师还没批；只要 `Submitted for grading` 就算交齐。

### 6. 收尾

- 关闭自己开的工作窗口/标签，不动用户其它标签。
- 把音频/文档/图片/稿件归档到一个文件夹，附一份提交清单（作业 id、题目、形式、字数/时长、状态）。
- 向用户报告：满分项、未评分项及原因、仍然未提交的东西（如果有）、合成音的诚实说明。

## 命令速查

| 命令 | 作用 |
|---|---|
| `scan_course.py --course-id N --deep` | 扫描课程清单、作业题目、提交形式 |
| `solve_h5p.py --course-id N --from-scan ...` | 完成 H5P 练习并核对分数 |
| `submit_assignments.py --manifest m.json` | 提交在线文本/文件作业 |
| `browser_doctor.py` | 检查 Edge/Safari/CDP/WebDriver 哪个后端可用 |
| `launch_edge_cdp.sh` | 用独立 profile 启动 Edge 并开 CDP 端口（登录一次保留会话） |
| `verify_progress.py --course-id N --manifest m.json` | 成绩 + 提交状态审计 |
| `audit_h5p_answers.py --course-id N` | 逐个打开 H5P review 页，核对是否真的记录了作答 |
| `tts_gen.py script.txt --preset clarkson-ish` | 生成口语录音 m4a |
| `gen_docx.py text.txt --out x.docx` | 文本转 Word |
| `gen_visuals.py mindmap/poster/photo --spec s.json` | 生成思维导图/海报/批改照片 |

## 铁律（踩过的坑）

1. **导航后必须轮询到目标 id + 就绪标记再操作**。只 sleep 会把结果写到上一个活动（本项目曾把两个作业的 0 分尝试写错）。
2. **tab 编号要固定并核对**。用 `<tabindex>` 导航的脚本和用另一个 tab 执行 JS 会导致“假成功”（所有操作落在旧页面）。
3. **H5P 点 Check 前确认分数**：如 `getScore()==getMaxScore()` 再提交；失败先重载重试，不要连续点击。
4. **不要用系统文件对话框**；用 DataTransfer 注入。上传后一定查 draft area 列表再保存。
5. **在线文本有字数上限**；报错页 URL 会丢 `id=`，用页面文字解析 `word limit`。
6. **作业显示 `-` 不等于没交**；看 `Submission status`。
7. **InteractiveBook 阅读类不产生分数**；需要补记时用 `finish_ib.js`（含 `H5P.opened` 预处理）。
8. **mod_hvp 取最高分**；重复尝试不会把分数改低，但会在成绩分析里留下多条记录，尽量一次做对。
9. **浏览器被关掉/窗口为 0**：重新 `ensure_window`，不要假设 tab 还在；`--browser cdp` 时用 `launch_edge_cdp.sh` 重开。
10. **老师评分、deadline、账号问题**：不能自动化，如实告诉用户。
11. **成绩满分不代表 review 页有答题记录**：用 `audit_h5p_answers.py` 复核，`NO_ANSWER` 的项重做一次。
12. **Edge 的 JS 桥默认关闭**：没开菜单开关就换 `--browser cdp`（`launch_edge_cdp.sh`），两条路都走 Chromium 协议。

## 文件索引

```
SKILL.md                       本文件
references/01-browser-bridge.md 浏览器矩阵（Edge/Safari/Chromium/CDP/WebDriver）、等待与坑
references/02-moodle-map.md     CloudCampus 页面地图、成绩报告列含义
references/03-h5p-recipes.md    8 种 H5P 题型的通关 API 与脚本
references/04-assignment-submit.md  在线文本/文件上传/字数上限/清理附件
references/05-writing-and-style.md 去 AI 味写作规则、作业结构、引用与字数
references/06-media.md          TTS 参数、Word、图片生成
scripts/browser.py             浏览器后端：Safari / Chromium AppleScript / CDP / WebDriver
scripts/cdp_bridge.mjs         CDP 桥（Node，Runtime.evaluate / Page.navigate / 截图）
scripts/browser_doctor.py      检查各浏览器后端是否就绪
scripts/launch_edge_cdp.sh     启动 Edge（独立 profile）+ 调试端口
scripts/cloudcampus.py         核心库：浏览器 + Moodle 页面读取
scripts/scan_course.py         课程/作业扫描
scripts/solve_h5p.py           H5P 完成器（含成绩核对与阅读书补分）
scripts/submit_assignments.py  作业提交器（online/file）
scripts/verify_progress.py     成绩与提交审计
scripts/audit_h5p_answers.py   核对每个 H5P 的 review 页有没有真实作答记录
scripts/tts_gen.py             离线 TTS -> m4a
scripts/gen_docx.py            文本 -> docx
scripts/gen_visuals.py         mindmap / poster / 批改照片
scripts/js/                    页面操作片段（h5p/、assignment/、scan/）
assets/                        示例 manifest / spec / 稿子
tests/smoke.sh                 离线自检
```

## 已知限制与待扩展

- 目前题型覆盖 an EAP course 出现过的 8 种；若遇到 Quiz（mod_quiz）、Workshop、Choice 等需要新增配方。
- 文件上传依赖 Moodle 4 的 filemanager DOM（`.fp-btn-add`、`repo_upload_file`、`draftfiles_ajax.php`），Moodle 大版本升级后需回归。
- 字数上限/文件类型限制由站点配置决定，脚本只检测不猜测。
- 语音只能是系统 TTS 近似；没有本地声音克隆模型。
