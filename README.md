# Solution to CloudCampus

**把 CloudCampus 当前界面上的所有任务，一次做完。**

打开你的课程页 / 某一周页面 / 成绩报告 / 作业列表，工具会先读出**当前界面上出现的全部任务**，然后按任务逐个完成、校验，最后告诉你还剩什么。它面向的是「这一屏里的任务」，不是只盯成绩单上的计分项。

[English](#english) · [技能文档](SKILL.md) · [浏览器矩阵](references/01-browser-bridge.md) · [实测记录](docs/verification.md)

---

## 这是什么

一个跑在真实浏览器里的 CloudCampus（Moodle 4）任务完成器：

- **输入**：你当前打开的 CloudCampus 界面（课程页、周页面、活动页、作业总表、成绩报告都可以）；
- **过程**：扫描出这一屏里所有要处理的东西，形成一个任务清单，逐个执行；
- **输出**：任务完成状态、成绩/提交记录、还剩哪些没做、为什么没做。

它不处理登录和验证码，直接复用你已登录的浏览器会话；只操作你自己的账号。

## 它把「当前界面」里的什么当作任务

| 界面上的任务 | 工具怎么处理 |
|---|---|
| H5P 互动练习（拖词、填空、找词、排序、题目集、单词卡、阅读电子书…） | 识别题型 → 用内容实例 API 作答 → 点 Check/Submit → 核对分数与作答记录 |
| 阅读类电子书（只有翻页，没有题） | 逐章翻完并记录「完成」；需要记成绩时写入完成状态 |
| 口语录音任务 | 生成 m4a 录音 → 上传到作业的文件提交区 |
| 写作类任务（reflection / paragraph / essay / summary / 句子练习） | 按题目和字数要求写稿 → 填在线文本或生成 docx |
| 图片类任务（思维导图 / 海报 / 批改照片） | 用 JSON spec 生成 PNG/JPG → 作为文件提交 |
| 文件类作业 | 通过页面内的 filemanager 上传（不走系统对话框） |
| 反馈 / 问卷 | 有题目时逐题填写并提交；没有题目时如实报告「该活动没有可填内容」 |
| 课程里的阅读材料、文件、页面 | 扫描出来列进任务清单，可按需下载/归档/打开 |
| 作业提交 | 在线文本或文件，保存后核对「Submitted for grading」 |
| 成绩与完成状态 | 重新读成绩报告 / 作业状态 / H5P review 页，确认真的完成了 |

> 计分只是任务的一种属性。**没有被计分的任务（阅读、反馈、资源）同样会被识别和完成**，这正是它和「刷分脚本」的区别。

## 工作方式（四步）

1. **扫描当前界面**：读课程索引 + 页面列表（可选叠加成绩报告），得到任务清单：任务 id、类型、所属周、题目、提交形式、当前状态。
2. **逐个执行**：按任务类型分派到对应执行器（H5P 解题器、写作/录音/图片生成器、作业提交器）。
3. **校验**：每完成一个就重新读页面/成绩/提交状态，不信任点击返回值。
4. **报告**：输出完成情况、失败原因、剩余任务；对无法自动完成的任务（比如没有题目的反馈、离线考试）明确说明。

## 浏览器支持（Edge 优先）

所有命令都支持 `--browser auto|edge|safari|cdp|webdriver`，默认 `auto`：挑当前已登录 CloudCampus 的浏览器。

| 后端 | 适用 | 前提 |
|---|---|---|
| `edge` | macOS Edge | Edge 菜单 **View → Developer → Allow JavaScript from Apple Events** 打开一次 |
| `cdp` | Edge / Chrome 系（macOS、Windows） | `bash scripts/launch_edge_cdp.sh` 启动独立 profile，登录一次 CloudCampus |
| `webdriver` | Windows Edge、Firefox（跨平台） | `msedgedriver --port 9515` / `geckodriver --port 4444` |
| `safari` | macOS Safari | Safari 设置 → 高级 → 允许 Apple 事件执行 JavaScript |

先跑浏览器医生，它会告诉你哪个后端现在能用：

```bash
python3 scripts/browser_doctor.py
```

## 快速开始

```bash
# 0) 放到 DSH 技能目录（也可以直接用 scripts/ 下的命令）
cp -R skill/ ~/.dsh/skills/solution-to-cloudcampus

# 1) 浏览器自检
python3 scripts/browser_doctor.py

# 2) 扫描当前界面的任务（course id 从课程 URL 的 id= 拿）
python3 scripts/scan_course.py --course-id 12345 --deep --out scan

# 3) 完成 H5P 类任务
python3 scripts/solve_h5p.py --course-id 12345 --from-scan scan/inventory.json

# 4) 完成作业类任务：先预览表单，再真提交
python3 scripts/submit_assignments.py --manifest manifest.json --inspect
python3 scripts/submit_assignments.py --manifest manifest.json

# 5) 核对任务是否真的完成
python3 scripts/verify_progress.py --course-id 12345 --manifest manifest.json
python3 scripts/audit_h5p_answers.py --course-id 12345
```

示例 manifest（把「任务」映射到本地内容）：

```json
{
  "course_id": 12345,
  "items": [
    {"id": 666001, "mode": "online", "text_path": "content/666001.md"},
    {"id": 668001, "mode": "file", "file_path": "artifacts/668001.docx"}
  ]
}
```

## 目录结构

```
SKILL.md                    技能主文档（触发词、能力边界、工作流、铁律）
references/                 浏览器接入、Moodle 页面地图、H5P 配方、作业提交、写作规范、媒体
scripts/
├─ cloudcampus.py           核心库：浏览器 + Moodle 页面读取
├─ browser.py               多浏览器后端（Safari / Chromium / CDP / WebDriver）
├─ cdp_bridge.mjs           CDP 桥（Node）
├─ browser_doctor.py        浏览器能力检查
├─ launch_edge_cdp.sh       启动 Edge（独立 profile）+ 调试端口
├─ scan_course.py           扫描当前界面的任务清单
├─ solve_h5p.py             H5P 类任务完成器（含作答核对、阅读书补分）
├─ submit_assignments.py    作业类任务提交（在线文本 / 文件）
├─ verify_progress.py       完成状态核对（成绩 + 提交）
├─ audit_h5p_answers.py     H5P review 页作答记录核对
├─ tts_gen.py               离线 TTS → m4a
├─ gen_docx.py              文本 → Word
├─ gen_visuals.py           思维导图 / 海报 / 批改照片
└─ js/                      页面操作片段（h5p/、assignment/、scan/）
assets/                     示例 manifest / spec / 稿件
docs/verification.md        真实课程实测记录（脱敏）
tests/smoke.sh              离线自检
```

## 实测记录（脱敏）

在一门真实的 EAP 课程上，用它把当前界面里出现的任务全部处理完（约 72 个计分项 + 阅读/反馈等非计分任务）：

- **48/48 H5P 练习满分**（含阅读类电子书补记完成）；
- **24/24 作业 Submitted for grading**（8 份口语录音 + 16 份写作/图文）；
- 课程总分 66.67% = 48/72 个计分项，其余 24 个作业项等老师评分；
- 6 份 H5P 练习一度只在成绩单有分、review 页没有作答记录，重做后全部补齐；
- 离线自检 `bash tests/smoke.sh`：**PASS=74 / FAIL=0**。

细节见 [docs/verification.md](docs/verification.md)。

## 适用边界与合规

- **只操作用户本人已登录的账号**；不处理登录、验证码，不换账号。
- 不修改老师评分、不延期 deadline；作业显示未评分是老师还没批，不代表没交。
- 口语录音是 **AI 合成音**（系统 TTS 近似），不是真人录音；使用前请确认课程对 AI 生成内容的规定。
- 阅读类 H5P 的「补分」是把完成记入成绩，不是做题得分；不需要可以跳过。
- 没有题目的反馈/问卷、离线考试等任务无法自动完成，工具会明确报告，不会假装完成。
- 引用只用课程材料里确实出现的来源，不伪造数据。

## English

**Solution to CloudCampus** is a browser-automation tool that finishes *every task on the CloudCampus page you are looking at* — H5P exercises, reading steps, speaking recordings, writing tasks, mind maps/posters, file submissions, feedback forms, and the rest of the current interface. It scans the page first, builds a task list, executes each task, and verifies completion, instead of only chasing graded items.
Supports Edge (primary), Safari, Chromium-family via CDP, and W3C WebDriver (Firefox / Edge on Windows).
It reuses the user's own logged-in browser session and never handles credentials.

## License

MIT
