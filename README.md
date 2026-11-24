# Solution to CloudCampus

**一个辅助你完成 CloudCampus 英语课程作业的学习工具。**

它不会替你「刷完就交」。它做的是学习里最费时间的那部分：帮你读懂当前界面上的任务、拆解题目、给出写作/口语示范、陪你练、在你做完后核对和复盘。最终交什么、怎么写，还是你决定。

[English](#english) · [技能文档](SKILL.md) · [浏览器矩阵](references/01-browser-bridge.md) · [实测记录](docs/verification.md)

---

## 这是什么

给在 CloudCampus 上学英语课（EAP / 学术英语）的人用的学习助手：

- 打开课程页、某一周页面或作业页，它先读出**当前界面上的任务**：这一周要做的练习、阅读、口语话题、写作题目、要交的文件；
- 然后按任务类型给你**学习支持**：题目解析、写作结构、示范录音、词汇和长难句、答案核对与错题复盘；
- 你完成后，它检查字数、格式、文件、提交状态，帮你确认「真的做完了」，而不是替你点提交。

它直接复用你已登录的浏览器会话，只操作你自己的账号，不处理登录和验证码。

## 它能帮你学什么

| 学习场景 | 工具提供的帮助 |
|---|---|
| 读题 / 任务理解 | 扫描当前界面任务清单；提取题干；把评分要求和关键词讲清楚（比如 "use your own words"、"cite two sources"） |
| 写作（reflection / paragraph / essay / summary） | 给结构骨架和段落示范；按你的草稿做语法、用词、衔接修改；提示字数上限；APA 7 文内引用格式 |
| 学术表达与去 AI 味 | 按「像学生自己写的」标准改：不用破折号、不堆排比、不写空话开头/总结腔，换具体细节 |
| 口语（Speaking Card / 话题陈述） | 生成示范录音（m4a，标注为 AI 合成音）；给口语稿、停顿位置、时长控制建议，供跟读和模仿 |
| H5P 互动练习 | 先自己做，再用工具核对答案与解析；错题整理出来复习；重复练到全对 |
| 阅读与词汇 | 从课程阅读里整理生词表、拆长难句、练 summary（用自己的话概括） |
| 作业提交前检查 | 检查字数、文件类型、附件数量、是否真的显示 Submitted；给出提交前 checklist |
| 学习计划 | 按周生成任务清单和完成度，标出还没做的任务，安排先后顺序 |

> 计分只是任务的一种属性。**没被计分的任务（阅读、反馈、资源）也会被识别**，因为它们同样占学习时间。

## 学习流程

1. **扫描当前界面** → 得到「这一屏有什么任务」的清单（任务 id、类型、所属周、题目、提交形式、当前状态）。
2. **分类处理** → H5P 练习核对、写作修改、口语示范、阅读词汇、文件提交检查。
3. **你自己完成** → 写、说、做，工具只给结构、示范和反馈。
4. **核对与复盘** → 重新读页面/成绩/提交状态，确认完成；把错的题和目标列出来。
5. **报告** → 还剩哪些任务、为什么没做（比如没有题目的反馈活动、离线考试）。

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

# 3) 练习类：做 H5P 并核对答案
python3 scripts/solve_h5p.py --course-id 12345 --from-scan scan/inventory.json

# 4) 写作/口语/图片类：生成示范与文件
python3 scripts/tts_gen.py speaking.txt --preset clarkson-ish --out artifacts/card.m4a
python3 scripts/gen_docx.py writing.txt --out artifacts/writing.docx

# 5) 提交前检查（--inspect 只看不交）
python3 scripts/submit_assignments.py --manifest manifest.json --inspect

# 6) 核对完成状态与作答记录
python3 scripts/verify_progress.py --course-id 12345
python3 scripts/audit_h5p_answers.py --course-id 12345
```

示例 manifest（把学习任务映射到本地内容）：

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
├─ solve_h5p.py             H5P 练习核对与解析
├─ submit_assignments.py    提交前检查 / 上传文件
├─ verify_progress.py       完成状态核对（成绩 + 提交）
├─ audit_h5p_answers.py     H5P review 页作答记录核对
├─ tts_gen.py               离线 TTS → m4a（口语示范）
├─ gen_docx.py              文本 → Word
├─ gen_visuals.py           思维导图 / 海报 / 批改照片
└─ js/                      页面操作片段（h5p/、assignment/、scan/）
assets/                     示例 manifest / spec / 稿件
docs/verification.md        真实课程实测记录（脱敏）
tests/smoke.sh              离线自检
```

## 实测记录（脱敏）

拿一门真实的 EAP 课程完整走了一遍（约 72 个计分项 + 阅读/反馈等非计分任务）：

- 48/48 H5P 练习做完并核对满分，其中 6 个阅读类电子书按「完成」记录；
- 24/24 作业按题目写好并提交（8 份口语录音 + 16 份写作/图文）；
- 6 份 H5P 练习一度只在成绩单有分、review 页没有作答记录，重做后补齐；
- 课程总分 66.67% = 48/72 个计分项，其余等老师评分；
- 离线自检 `bash tests/smoke.sh`：**PASS=74 / FAIL=0**。

这份记录是「学习流程能跑通」的证据，不是「代做保证」。细节见 [docs/verification.md](docs/verification.md)。

## 适用边界与学术诚信

- 工具给的是**讲解、示范和检查**；写和说的内容由你自己确认后再交。请遵守课程对 AI 辅助的规定。
- 不修改老师评分、不延期 deadline；作业显示未评分是老师还没批。
- 口语示范录音是 **AI 合成音**，不是真人录音；用于跟读练习，不要当作本人录音提交。
- 没有题目的反馈/问卷、离线考试等任务无法自动完成，工具会明确说明。
- 只操作用户本人已登录的账号；不处理登录、验证码，不换账号。

## English

**Solution to CloudCampus** is a learning assistant for English coursework on CloudCampus (Moodle 4). It reads the tasks on the page you are looking at — exercises, readings, speaking prompts, writing briefs, files — and helps you study them: breaking down instructions, showing writing structures and revisions, generating sample speaking audio, checking H5P answers with explanations, finding vocabulary and long sentences, and verifying completion before you submit. It is a study aid, not an autopilot: you stay in charge of what gets written and submitted.
Supports Edge (primary), Safari, Chromium-family via CDP, and W3C WebDriver (Firefox / Edge on Windows).
It reuses the user's own logged-in browser session and never handles credentials.

## License

MIT
