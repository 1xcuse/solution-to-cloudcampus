# Solution to CloudCampus

**CloudCampus（Moodle 4）课程作业解决方式**：扫描课程 → 完成 H5P 互动练习 → 生成口语录音 / 写作 / 思维导图 / 海报 → 提交在线文本或文件作业 → 核验成绩与提交记录。

把「CloudCampus 上一门课的练习和作业全部做完、交齐、可核验」做成可复用的自动化流程。

[English](#english) · [技能文档](SKILL.md) · [浏览器矩阵](references/01-browser-bridge.md) · [实测记录](docs/verification.md)

---

## 这是给谁用的

给正在用 CloudCampus（Moodle 4）上课、需要完成大量重复练习和作业的人：

- 一门课几十个 H5P 互动练习，题型多、要一个个点；
- 每周的口语作业要录音、写作作业要交 Word/图片；
- 交完还要自己核对成绩：哪些做了、哪些 0 分、哪些作业还没提交。

这个项目把这些步骤做成命令行工具，用你已经登录的浏览器操作，不碰账号密码。

## 能做什么

| 能力 | 说明 |
|---|---|
| 课程扫描 | 读取成绩报告 + 课程索引，生成 72 项级别的清单：活动 id、类型、所属周、权重、当前成绩、作业题目与提交形式 |
| H5P 互动练习 | 支持 DragText、Blanks、FindTheWords、SortParagraphs、QuestionSet、Flashcards、InteractiveBook、mod_h5pactivity 等题型，自动完成并核对满分 |
| 阅读类电子书记分 | InteractiveBook 没有题，默认只显示未评分；用 `H5P.setFinished` 把「完成」记入成绩 |
| 在线文本作业 | 自动填入 Atto 编辑器并保存，自动识别服务端字数上限错误 |
| 文件作业 | docx / 图片 / 音频通过 DataTransfer 注入 Moodle filemanager 上传，不依赖系统文件对话框 |
| 口语录音 | macOS `say` + `afconvert` 生成 m4a（含低沉英音预设），自动提交到 File submissions |
| 写作生成 | 按题型写 reflection / paragraph / essay / summary，按去 AI 味规则润色（不堆模板句、不用破折号、写具体细节） |
| 图片作业 | 生成思维导图、学术海报、「批改过的手写作业照片」 |
| 成绩与作答审计 | 核对每个计分项、每份作业的提交状态、每个 H5P 的 review 页是否真的记录了作答 |
| 多浏览器 | Edge 优先，也支持 Safari、Chrome 系、CDP 模式、W3C WebDriver（Firefox / Windows Edge） |

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

# 2) 扫描课程（从课程 URL 的 id= 拿 course id）
python3 scripts/scan_course.py --course-id 12345 --deep --out scan

# 3) 做 H5P 练习
python3 scripts/solve_h5p.py --course-id 12345 --from-scan scan/inventory.json

# 4) 提交作业：先预览表单，再真提交
python3 scripts/submit_assignments.py --manifest manifest.json --inspect
python3 scripts/submit_assignments.py --manifest manifest.json

# 5) 审计成绩、提交状态、H5P 作答记录
python3 scripts/verify_progress.py --course-id 12345 --manifest manifest.json
python3 scripts/audit_h5p_answers.py --course-id 12345
```

示例 manifest：

```json
{
  "course_id": 12345,
  "items": [
    {"id": 666001, "mode": "online", "text_path": "content/666001.md"},
    {"id": 668001, "mode": "file", "file_path": "artifacts/668001.docx"}
  ]
}
```

## 工作原理（简版）

1. **复用已登录会话**：通过 AppleScript / CDP / WebDriver 在真实浏览器里执行 JS，不处理登录和验证码。
2. **导航竞态处理**：先轮询 URL 命中目标 id，再等页面就绪和业务标记（H5P 实例挂载），否则结果会写到上一个活动。
3. **H5P 用内容实例自己的 API**：`H5P.instances[0]` 的 droppables/draggables、cloze、grid、`getQuestions()` 等，按题型分派。
4. **Moodle 成绩来自 xAPI**：Check 后 collector 把 `result.score` 发到 `ajax.php?action=xapiresult`；`mod_hvp` 取最高分。
5. **文件上传**：用 `DataTransfer` 把 file 注入 `input[name=repo_upload_file]`，进 draft area 后保存，绕开系统文件对话框。
6. **字数上限**：解析错误页里的 `word limit N words / attempting M words`，改短后用同一条 manifest 重交。
7. **审计而不是相信点击返回值**：每次操作后重新读成绩报告 / 作业状态 / H5P review 页。

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
├─ scan_course.py           课程/作业/成绩扫描
├─ solve_h5p.py             H5P 完成器（含作答核对、阅读书补分）
├─ submit_assignments.py    作业提交（在线文本 / 文件）
├─ verify_progress.py       成绩 + 提交状态审计
├─ audit_h5p_answers.py     H5P review 页作答记录审计
├─ tts_gen.py               离线 TTS → m4a
├─ gen_docx.py              文本 → Word
├─ gen_visuals.py           思维导图 / 海报 / 批改照片
└─ js/                      页面操作片段（h5p/、assignment/、scan/）
assets/                     示例 manifest / spec / 稿件
docs/verification.md        真实课程实测记录（脱敏）
tests/smoke.sh              离线自检
```

## 实测记录（脱敏）

在一门真实的 EAP 课程上完整跑通（约 72 个计分项）：

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
- 引用只用课程材料里确实出现的来源，不伪造数据。

## English

**Solution to CloudCampus** is a browser-automation toolkit for Moodle 4 / CloudCampus coursework:
scan a course, solve its H5P exercises, generate speaking audio / writing / mind maps / posters,
submit online-text or file assignments, and verify grades plus submission records.
Supports Edge (primary), Safari, Chromium-family via CDP, and W3C WebDriver (Firefox / Edge on Windows).
It reuses the user's own logged-in browser session and never handles credentials.

## License

MIT
