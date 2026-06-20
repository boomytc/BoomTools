# TODO 03: 非模型字幕、Raw 增强与媒体信息

## 目标

补齐不涉及模型接入的字幕、Raw 和媒体信息能力。自动字幕/Whisper 明确不进入本阶段或后续阶段。

## 范围

- `subtitles` 增强：
  - 保留 soft subtitle embed。
  - 增加 hard-burn subtitle。
- `raw` 增强：
  - 增加可选第二输入文件。
  - 增加示例命令库。
  - 增加完整命令预览。
- `media_info`：
  - 独立 operation 或独立信息动作。
  - 深度扫描 ffmpeg log。

## 字幕 Checklist

- [x] `subtitles` 参数增加：
  - [x] `mode`: `soft|burn`
  - [x] `output_format`: soft 支持 `mp4|mkv`，burn 支持 `mp4|webm|mov|mkv`
  - [x] `font_size`: `small|medium|large`，仅 burn 使用
- [x] soft 模式保持当前行为：
  - [x] MP4 使用 `mov_text`。
  - [x] MKV 复制字幕流。
- [x] burn 模式：
  - [x] 使用本机 ffmpeg `subtitles` filter。
  - [x] 如果 ffmpeg 缺少相关 filter 或 libass 支持，显示明确错误。
  - [x] 不实现浏览器 canvas 字幕渲染 fallback。
- [x] 继续只允许 `.srt/.vtt/.ass/.ssa`。

## Raw Checklist

- [x] Raw 参数仍使用 `shlex.split` 解析成参数数组。
- [x] Raw 禁止用户自带主输入路径、主输出路径、`-i` 主输入替换、`-progress`、`pipe:`、`file:`。
  - [x] 新增可选第二输入：
  - [x] 用户通过 GUI 选择文件。
  - [x] runtime 将该路径作为受管 extra input。
  - [x] Raw 参数可引用受管第二输入，但不能引用任意文件路径。
  - [x] 新增示例命令库：
  - [x] drawbox watermark
  - [x] cap framerate
  - [x] grayscale
  - [x] loudnorm
  - [x] lossless remux
  - [x] letterbox
  - [x] denoise
  - [x] sharpen
  - [x] deshake
  - [x] vignette
  - [x] extract wav
  - [x] first frame
  - [x] replace audio with second input
  - [x] 示例命令只填充文本，不自动执行。

## Media Info Checklist

- [x] 将当前文件加载时的 `ffprobe` 信息保留为快速信息。
- [x] 增加深度扫描动作：
  - [x] 执行 `ffmpeg -hide_banner -i input`。
  - [x] 捕获 stderr 到日志区域。
  - [x] 不生成输出文件。
- [x] `media_info` 不进入批处理。

## 反目标

- 不实现 Whisper、ASR、Transformers.js、模型选择、模型缓存、自动字幕编辑流程。
- 不实现浏览器 canvas hard-burn 字幕渲染。
- 不允许 Raw 任意读写文件系统路径。
- 不做 Raw 多输入任意数量扩展；只支持一个受管第二输入。

## 验收

- 字幕 soft 和 burn 都有命令构建单测。
- Raw 第二输入有成功测试和非法路径测试。
- Media Info 深度扫描不会创建输出文件。
- `RUN_FFMPEG_GUI_SMOKE=1 uv run python -m pytest tests/integration` 覆盖 soft/burn 字幕、Raw 第二输入和 media info。
