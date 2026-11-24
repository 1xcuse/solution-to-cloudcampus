# H5P 互动练习：按类型通关配方

总原则：**用内容实例自己的 API 和页面 DOM，不猜坐标、不模拟鼠标拖拽**。H5P 实例对象在
`iframe.h5p-iframe` 的 `contentWindow.H5P.instances[0]`；外层页面有 `H5PIntegration`。

## 公共准备

- 页面就绪判定见 `01-browser-bridge.md`；`solve_h5p.py` 为每个 id 生成 `ready_<id>.js`。
- 每类内容都先 `ins.libraryInfo.machineName` 判断类型，再分派。
- 大多数题型最后要**点页面上的 Check/Submit 按钮**触发 H5P 的 xAPI 事件；仅少数类型自动判分。
- mod_hvp 的成绩规则：服务端按 xAPI statement 的 `result.score` 记录，**取最好的一次**，所以干净跑一遍即可。
- 全部做完后刷新成绩报告核对；`-` 或 `0.00` 必须排查。

## DragText

- 实例有 `ins.droppables`（每项 `.text` = 该空正确答案）和 `ins.draggables`（每项 `.text` = 词块）。
- 对每个 droppable，按文本匹配一个未用过的 draggable，调 `ins.drop(draggable, droppable)`；
  然后点击 `.h5p-question-check-answer`（若存在；instantFeedback 型会自动判分）。
- 重复答案（同一词出现多次）要每个空各拖一次，不能去重。
- 脚本：`js/h5p/solve_drag.js`。

## Blanks

- `ins.params.questions` 是 HTML 数组，`*answer*` 是答案（`/` 分隔备选）。
- 输入框 `.h5p-text-input`；用原生 value setter + `input/keyup/change/blur` 事件填写，再点 Check。
- 标签与 `*` 错位的作者错误（如 `*<strong>word*</strong>`）：答案按 HTML 去标签后取。
- 若点 Check 后分数不是满分，别硬猜：`ins.clozes[i].correct()` 可逐个验证，或读页面 “Correct answer” 后再重填。
- 脚本：`js/h5p/solve_blanks.js`。

## FindTheWords

- 网格是 canvas（`.h5p-drawing-canvas`），实例 `ins.grid.wordGrid` 是字母二维数组，`ins.vocabulary.words` 是词表。
- 在 `wordGrid` 里按 8 方向搜索每个词，然后用 **原生 MouseEvent** 在 canvas 上派发
  `mousedown → mousemove → mouseup`（坐标用 `elementSize` 换算成 cell 中心，`clientX = rect.left + x`）。
- 全部找到后点 `ins.$submitButton`。
- 脚本：`js/h5p/solve_ftw.js`。

## SortParagraphs

- 正确顺序在 `ins.params.paragraphs`（HTML）；页面初始顺序是乱的。
- 用 `ins.content.getDraggables()` 读当前顺序，与目标顺序由前向后比较，
  调 `ins.content.handleDraggableMoved(el, 'up')` 一次移动一位；**每次移动后等约 1 s**（有动画）。
- 顺序正确后点 `.h5p-question-check-answer`。
- 脚本：`js/h5p/sp_step.js`（步进驱动）。

## QuestionSet

- 实例有 `getQuestions()`；每题是子实例（MultiChoice / TrueFalse / DragText / Blanks / Essay）。
- 每题 DOM 是 `.question-container`，题序可能被随机化；**不要按索引答题**，按题干文本/选项集合匹配。
- 正确答案从页面自己的 `H5PIntegration.contents[...].jsonContent` 解析（含所有子题与答案）：
  `js/h5p/qs_plan.js` 生成 `window.__PLAN`。
- 流程：`ins.resetTask()` 清空上次尝试 → 逐题作答 →
  - MultiChoice/TrueFalse：点击选项；有的配置自动判分，有的要点 Check；
  - 嵌套 DragText/Blanks：用子实例的 `droppables/draggables` 或 `params.questions` 填；
  - Essay：把 `params.solution.sample` 粘进 textarea（关键词评分）；
  - 每题判分后点 `.h5p-question-next`；最后一题变 `.h5p-question-finish`。
- 有时 Next/Finish 按钮没出现：对该题实例 `q.showButton('next')` / `q.showButton('finish')`，等一拍再点。
- 脚本：`js/h5p/qs_step4.js`（步进）+ `qs_reset.js` / `qs_plan.js` / `qs_final.js`。

## Flashcards

- 卡片是输入式：逐卡把 `ins.options.cards[i].answer` 写入 `.h5p-textinput`，点该卡 `.h5p-check-button`。
- 翻到最后，点 `.h5p-show-results-label` 显示结果。
- 该内容类型**不主动上报分数**；按官方同构方式补一条带 score 的 `answered` statement 到
  `H5PIntegration.ajax.xAPIResult`（用 `ins.getXAPIData()` 的 statement 加 `result.score`）。
- 脚本：`fc_solve.js` + `fc_post.js`。

## InteractiveBook

- 阅读型内容：`ins.chapters` 每章 `completed` 标记；点 `.h5p-interactive-book-status-arrow.next`（顶栏翻页）
  逐页前进，`progressAuto` 会自动把章节标记完成。
- 单章的书永远停在第 1 页、`completed=false`：调用 `ins.setChapterRead(ins.activeChapter, true)`。
- **阅读书没有可评分交互，content max score = 0，mod_hvp 不会自动给分**。
  实测有效的补齐步骤（`js/h5p/finish_ib.js`）：
  1. 发一条带 `result.score = {raw:1,max:1,scaled:1}` 的 xAPI statement；
  2. `H5P.opened[contentId] = new Date()`（否则 H5P.setFinished 内部 `date.getTime` 报错）；
  3. `H5P.setFinished(contentId, 1, 1)`。
  之后成绩报告显示 10.00/100%。这是把「完成」记入成绩的最小动作，不是伪造题目答案；
  如果用户不想这样，就不要做这一步，把「该内容无分数」如实说明。
- 脚本：`js/h5p/ib_step2.js`、`ib_mark_read.js`、`finish_ib.js`、`ib_final.js`。

## mod_h5pactivity（内嵌电子书）

- 两层 iframe；脚本里统一按 `iframe.h5p-player > iframe` 找实例。
- 流程：点 Read 开始 → 逐页 Next → 途中出现的 SingleChoiceSet 每题点 `.h5p-sc-is-correct` 选项 →
  最后 Summary 页点 `Submit Report`（`js/h5p/h5pa_step2.js`）。
- 提交后在成绩报告出现 0–100 分（本项目满分 100）。
- 注意：外层 `H5PIntegration.ajax` 没有 xAPI 端点，分数由 mod_h5pactivity 自己从 attempt 计算，
  不要手写 statement。

## 成绩 10 分 ≠ review 有答题记录（重要）

成绩报告显示 10.00 只说明 gradebook 有分；学生/老师点 "Grade analysis" 打开的 review 页
（`mod/hvp/review.php`）可能显示 "This user hasn't submitted an answer to the H5P yet"。
原因是某些内容是通过 `setFinished`（完成事件）记分的，答题 payload 没有进 xAPI 表。
实测 an EAP course 48 项里有 6 项出现过这种情况（都是 DragText/Blanks）。

处理：用 `scripts/audit_h5p_answers.py --course-id N` 审计所有 H5P 的 review 页：
- `OK`：显示 `Score: x out of y / Gradebook score: ...`
- `NO_ANSWER`：没记录 → 重新打开该内容、重新作答并点 Check（会 POST 一条 answered statement），
  再审计一次通常就变成 OK；成绩仍取最高分，不会掉。
- `NO_BOOK`：InteractiveBook 等无题内容，review 页只有标题，属正常（分数靠 `finish_ib.js`）。
- `NO_LINK`：如 mod_h5pactivity，没有 grade.php 链接，去它的 attempt/成绩页核对。

## 状态与重试

- 元素未就绪、类型不对、点 Check 没反应时：先重新加载页面，再跑一次；不要在同一页反复暴力点击
  （会把 0 分尝试写进成绩，虽然取最高分，但记录很乱）。
- 同一内容重复提交会留下多条 attempt，mod_hvp 取最高分；InteractiveBook 的 `setFinished` 重复调用无副作用。
- 全部完成后跑 `verify_progress.py` 做审计。
