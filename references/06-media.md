# 媒体产物：TTS 录音、Word 文档、图片

## 语音合成（macOS 自带）

```bash
say -v Daniel -f script.txt -o out.aiff
afconvert -f m4af -d aac -b 64000 -s 3 out.aiff out.m4a
afinfo out.m4a | grep duration
```

- 声音：`Daniel`（en-GB 男声，最接近 BBC 主持人的可离线选项）；`Samantha`（en-US 女声）；
  `Karen`（en-AU 女声）。
- 内嵌指令（写在文本里）：`[[pbas N]]` 音高、`[[rate N]]` 语速、`[[slnc 300]]` 停顿 300 ms。
- 实测（本机 macOS 15 / M 系列）：Daniel 默认 pbas≈44，约 111 Hz；
  `pbas 42/40/38/36` 约 99/85/75/72 Hz；再低会触底不再降低。
- `rate` 有分档：60–70 ≈162 wpm；80–100 ≈175 wpm；110–140 ≈191 wpm；190+ 更快。
  `clarkson-ish` 预设用 pbas 40 + rate 60 + 标点停顿，听起来低沉、偏慢。
- 输出 m4a 单声道 22.05 kHz，约 60–80 秒对应 400–560 KB。
- **诚实边界**：这是合成语音，不是本人录音，更不是 Clarkson 的声音克隆；不要向用户声称是真人。
  若课程禁止 AI 生成音频，应先提醒用户。

批量：`python3 scripts/tts_gen.py script1.txt script2.txt --preset clarkson-ish --outdir audio/`

## Word 文档

- 用 `scripts/gen_docx.py`（需要 python-docx；DSH 内置运行时的 python 已带）。
- 输入 UTF-8 文本，空行分段；Calibri 12pt、1 英寸页边距即可。
- 作业文件只放正文，不需要封面/姓名页（除非题目要求）。

## 图片产物（Pillow）

`scripts/gen_visuals.py` 三个子命令，都由 JSON spec 驱动（示例在 `assets/`）：

| 类型 | 输出 | 用途 |
|---|---|---|
| `mindmap` | PNG 1600×1100 | 思维导图作业 |
| `poster` | PNG 1200×1697（A1 比例） | 学术海报作业 |
| `photo` | JPG ~1000px 宽 | “拍张批改过的作业照片”类提交 |

- 手写体：`/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf`；批注用 `MarkerFelt.ttc`。
- 海报文字用 Arial/Arial Bold，自动换行；生成后用 `read_image` 检查有没有出框。
- `photo` 会做纸张纹理、轻微旋转、阴影、暗角，看起来像手机拍的照片；批注 token 必须能在正文里找到。
- 上传前压到 200 KB 以内（JPG q≈82）可以放心用 base64 注入。
