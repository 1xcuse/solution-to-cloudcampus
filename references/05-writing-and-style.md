# 作业内容写作规范（去 AI 味 + 学术要求）

目标：写出来像这个学生自己写的，同时满足课程评分点。素材来自本会话实际提交的 16 篇写作 + 8 份口语稿。

## 去 AI 味的硬规则（来自 humanizer）

1. **不用破折号**（—, –, --）。改用句号、逗号、冒号或括号。
2. **不用 “not X but Y / not just X, but Y / it's not X, it's Y”** 这类否定对比；
   要对比就两边都带信息（“The plan is cheap, but it is slow.”）。
3. **不要三连排比**（A, B, and C）为了好听而凑三项；有几项写几项。
4. **删掉空话开场**：Let's dive in / Here's what you need to know / Honestly? / The real question is。
5. **删掉总结腔收尾**：That is the real win. / This shows the importance of... / 一行一段的“金句”。
6. **不用 AI 高频词**：crucial, pivotal, delve, landscape, tapestry, testament, underscore, showcase, vibrant, nestled, meticulous, robust（比喻义）, foster, leverage。
7. **不要加粗当装饰**，不要每个列表项都加粗标签。
8. 句子长短交替；写具体细节（哪个网站、哪节课、哪次错误）；允许一点犹豫和自我修正。

## 按作业类型的结构

- **Reflection（反思）**：第一人称；一个具体事件 + 学到什么 + 下一步怎么做。不写“套话总结”。
  150–220 词（先查字数上限，本项目有 200 词上限的）。
- **Your Paragraph（段落）**：1 个主题句 → 解释 → 一个具体例子/引用 → 解释证据如何支持主题 → 收束句。
  约 110–170 词；按课程 checklist 至少 1 处 APA 7 文内引用。
- **Essay submission**：审题后按题面要求的段落数写（本项目要求 “three connected body paragraphs”）：
  每段一个子问题（问题 → 影响 → 个人能做什么），段首衔接词，段内 2 处引用。
- **Summary（摘要）**：只保留主旨，删例子和细节，全部改写成自己的话；通常 90–150 词，不出现个人观点。
- **Paraphrase（改写）**：逐句改写，保留原意，换结构 + 换词；不要加自己的评论；注意字数上限可能很紧（70 词）。
- **句子练习**：simple / compound / complex / compound-complex 各写一句，明确标注类型。
- **Mind map（思维导图）**：中心问题 + 3–4 个分支（立场、理由、例子、反方/条件）+ 结论计划；用 `gen_visuals.py mindmap`。
- **Poster（海报）**：标题 + 一句 issue + 3 栏（原因/影响/对策）+ 个人行动清单 + 结论 + references；用 `gen_visuals.py poster`。
- **“贴批改照片”**：用 `gen_visuals.py photo` 生成手写纸面 + 红笔批注的图片；批注内容要与正文真实对应。

## 引用与来源

- 课程使用 **APA 7 文内引用**：`(Author, year)` 或 `Author (year)`；尽量用课程阅读材料里出现的作者，
  例如本项目 Climate 阅读是 `(Shaw, n.d.)` 和 `(Vocal Media, 2025)`，critical thinking 用 `(Cottrell, 2005)`。
- **没有原文就不要编具体数据/引语**。可以引用作者+年份支持一般性论断；宁可写得概括，也不要伪造页码或统计。
- 英式拼写（organise, behaviour, analyse, practise 作动词），与课程一致；同一篇内保持一致。

## 字数上限的处理

- 每篇先写到目标上限的 90% 左右，再提交；系统报 `word limit N words / attempting M words` 时按 N 改短。
- 压缩顺序：删重复解释 → 合并例子 → 去掉空泛的结论句 → 只留一个例子。
- 改完重跑同一条 manifest；不要新建作业或删提交。

## 语音稿（口语卡）

IELTS Part 2 结构：点题 → 按 bullet 展开 → 一个具体例子 → 收束（可带个人立场）。
约 170–220 词（本项目录音 69–82 秒，对应 MOS 1 分钟准备、1–1.5 分钟作答）。
口语化：缩写、Well/Right/Now 开头可以少量使用，但不要每句都是套话；英式表达优先。
