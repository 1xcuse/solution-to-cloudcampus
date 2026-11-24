# CloudCampus（Moodle 4）页面地图

平台：`https://www.cloudcampus.com.cn`，账号为学校统一登录后的学生账号。

## 关键 URL

| 用途 | URL |
|---|---|
| 课程首页 | `/course/view.php?id=<courseid>` |
| 成绩报告（学生视角） | `/grade/report/user/index.php?id=<courseid>` |
| H5P 互动练习 | `/mod/hvp/view.php?id=<cmid>` |
| H5P 评分分析/回看 | `/mod/hvp/grade.php?...` → 跳到 `/mod/hvp/review.php?id=<h5pid>&course=..&user=..` |
| H5P（核心插件） | `/mod/h5pactivity/view.php?id=<cmid>` |
| 作业 | `/mod/assign/view.php?id=<cmid>` |
| 作业总表 | `/mod/assign/index.php?id=<courseid>`（每行有 Submission status） |
| 反馈/问卷 | `/mod/feedback/view.php?id=<cmid>` |

课程 id、活动 id 都能从成绩报告行的链接里取，不要手抄。

## 课程结构

- 主题格式，页面默认只渲染一个 section（标题常见 `Topic: Week N`），**全部活动列在左侧 course index**（`.courseindex-section` / `.courseindex-item`）。
- course index 里的活动名要用 `textContent`（`innerText` 在抽屉隐藏时为空）。
- `js/scan/course_index.js` 输出 `{sections:[{title, items:[{cmid, mod, name, url}]}]}`，是判断「哪周有哪些活动」的权威来源。
- 活动类型按 URL `/mod/<type>/` 分类；本类课程常见：`resource`（74 个文件）、`hvp`（47 个 H5P）、`assign`（24 个作业）、`page`、`folder`、`forum`、`feedback`。

## 成绩报告（最可靠的进度证据）

`table tr` 中带 `/mod/.../view.php?id=` 链接的行就是计分项。列顺序：

| 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Calculated weight | Grade | Range | Percentage | Feedback | Contribution |

- Grade `-` = 未评分；`10.00` / `100.00` = 满分；`0.00` = 有提交但 0 分（要排查）。
- `Course total` 行在最后，用于交叉验算：满分项数 × 单项权重 ≈ total。
- `js/scan/grade_rows.js` 输出 `{rows:[{id, mod, weight, grade, range, pct, contribution, name}], total}`。
- 刷新成绩报告用重新导航即可；Moodle 的 grade_report_user 会即时反映 activity grade（本项目实测）。

## 作业页

- 页面正文里 `Opened: ...` 到 `Add submission` 之间是题目要求（可能有字数上限，见提交文档）。
- 按钮：`Add submission`（还没交）/ `Edit submission`（已交）/ `Remove submission`。
- 点开后 URL 变为 `&action=editsubmission`，此时才出现 **online text** 或 **filemanager**。
- 交过的作业 view 页显示 `Submission status: Submitted for grading` + 文件/在线文本摘要。
- 作业总表页（`/mod/assign/index.php`）适合一次性核对 24 个作业的提交状态。

## H5P 页面（mod_hvp）

- `view.php` 页面加载后：外层页有 `H5PIntegration`（含 `ajax.setFinished`、`ajax.xAPIResult`、`contents[].jsonContent` 题目答案），内容在 `iframe.h5p-iframe` 里，`iframe.contentWindow.H5P.instances[0]` 是当前内容实例。
- 外层还加载了 `mod/hvp/xapi-collector.js`：监听 xAPI 事件，把 `{contentId, xAPIResult}` POST 到 `H5PIntegration.ajax.xAPIResult`。评分由服务端根据 xAPI statement 的 `result.score` 计算（本项目实测：最高分保留）。
- 成绩报告里的 grade 就是这个分数换算到 0–10（或 0–100）。

## mod_h5pactivity（核心 H5P 插件）

- 内容在 **两层 iframe**：`iframe.h5p-player`（embed.php）→ 内层 iframe（about:blank 注入）。
- 访问实例：`document.querySelector('iframe.h5p-player').contentDocument.querySelector('iframe').contentWindow.H5P.instances[0]`。
- 这类活动带「尝试/attempt」机制：最后点 Summary 页的 `Submit Report` 才会生成 attempt 并写入成绩（0–100，满分 100）。

## 反馈（mod_feedback）

- 「Reflection questions」这类是问卷；页面会显示 `Answer the questions`。
- **但本项目那一个反馈活动里没有任何题目**（点进去提示 `No questions have been set up yet`），所以无法提交，也不算作业。遇到 feedback 先看有没有表单控件，没有就如实告诉用户。

## 登录与限流

- 脚本复用浏览器里已登录的会话（Edge/Safari/Chromium/CDP/WebDriver 均可），不处理登录、验证码。
- 频繁刷新成绩报告/页面没有触发限流（本项目 48 项实测），但仍建议每步 sleep 0.5–1.5 s。
