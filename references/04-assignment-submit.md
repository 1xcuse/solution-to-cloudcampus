# 作业提交（mod_assign）：在线文本与文件上传

## 先看清楚提交形式

打开 `/mod/assign/view.php?id=<id>`：

1. 页面正文找 `Opened:` 之后、`Add submission` / `Edit submission` 之前的题目要求。
2. 点 `Add submission`（或 `Edit submission`）进入 `&action=editsubmission`。
3. 检查表单：
   - 在线文本：`#id_onlinetext_editoreditable`（Atto 富文本）或 `textarea[name="onlinetext_editor[text]"]`
   - 文件：`.filemanager`（可能同时允许两种）
4. 两种都允许时，优先在线文本（内联、无需文件）；要求“拍照/文档”时走文件。

`js/assignment/form_info.js` 会返回 `{online_editor, online_textarea, filemanager, file_inputs, save_buttons}`。

## 在线文本

- 直接给 `#id_onlinetext_editable` 设 `innerHTML`（段落包 `<p>`）并派发 `input/blur`；
  同时给隐藏 textarea 设纯文本值，防止 Atto 未同步。
- 点 `Save changes`（有的作业最后是 `Submit assignment`，见 `js/assignment/save.js` 的匹配顺序）。
- 之后刷新页面看 `Submission status: Submitted for grading`。

## 文件上传（核心技巧）

不要用系统文件对话框（见 `01-browser-bridge.md`）。用页面上传控件 + DataTransfer：

1. 点 `.fp-btn-add a` 打开 File picker；点仓库列表里文字含 `Upload a file` 的 `.fp-repo`。
2. 页面出现 `input[name=repo_upload_file]`（在 `repo-form_*` 里）。
3. Python 读本地文件转 base64，写一段 JS 注入：
   ```js
   var file = new File([bytes], "name.ext", {type: mime});
   var dt = new DataTransfer(); dt.items.add(file);
   fi.files = dt.files;
   fi.dispatchEvent(new Event('change', {bubbles:true}));
   ```
4. 点 `Upload this file`；文件会进入该表单的 **draft area**（不是直接进作业）。
5. 用表单里的 `input[name=itemid]`（draft id）请求
   `/repository/draftfiles_ajax.php?action=list&itemid=..&sesskey=..&filepath=%2F`
   确认文件名出现（上传成功）。
6. 关掉 picker（header 的 close 按钮），点 `Save changes`；刷新看 `Submitted for grading` + 文件名。
7. 刷新后 view 页 File submissions 里应只出现你这次要交的文件。

**重要**：文件在 draft area 里就够了，点不点 `Select this file` 不影响保存（Moodle 的作业保存读取的是 itemid 的 draft area）。所以 picker 界面卡住时，确认 draft 列表有文件后直接关掉保存即可。

### 清理多余附件

如果之前重试把 A 作业的音频传进了 B 作业的 draft，保存后 view 页会多出附件。修正：
1. 打开该作业 → `Edit submission`，读 `input[name=files_filemanager]` 的 itemid。
2. 对每个多余文件请求
   `/repository/draftfiles_ajax.php?action=delete&itemid=..&filepath=%2F&sesskey=..&filename=<urlencoded 文件名>`
   （一次一个文件，用 query 参数；`filename[]` 数组形式会报 `clean() can not process arrays`）。
3. 再点 `Save changes`，刷新确认只剩正确文件。

## 字数上限（必须先问、后改）

Moodle 的在线文本有 word limit，超限时保存失败并显示：

> The word limit for this assignment is 200 words and you are attempting to submit 220 words.

保存失败时页面 URL 会变成不带 `id=` 的 `view.php`，`status.js` 读不到提交状态。流程：
- 解析页面文本里的 `word limit … N words … attempting M words`
- 把记录标为 `WORD_LIMIT`（exit code 3），**不要自动删字**；让写稿环节按上限改短后重跑
- 本项目实测上限：Reflection (p.27)=200、Paraphrase=70、Reflection on paragraph writing=120；
  其余常见 150–500，Essay 类通常更宽（本项目 293/285 词都通过）。

## 提交后的验证

- `Submitted for grading` + `Grading status: Not graded` 是正常状态（老师还没批）。
- 作业总表 `/mod/assign/index.php?id=<courseid>` 可以一次核对全部作业的 Submission status。
- 全部作业交完后，成绩报告里作业项仍然是 `-`（未评分），这不代表没交。

## manifest 约定

```json
{
  "course_id": 12345,
  "items": [
    {"id": 666033, "mode": "online", "text_path": "content/666033.md"},
    {"id": 668591, "mode": "file", "file_path": "artifacts/668591.docx"}
  ]
}
```

`submit_assignments.py` 支持 `--inspect` 只看表单不提交、`--only` 重跑个别项。
