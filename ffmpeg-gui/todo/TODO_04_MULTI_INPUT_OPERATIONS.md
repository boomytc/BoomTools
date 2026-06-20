# TODO 04: 多输入业务功能补齐

## 目标

补齐需要第二输入文件的业务功能，并保持本机 GUI 的路径直连优势。

## 范围

- `overlay`
- `mix_audio`
- `concat`
- `side_by_side`
- `picture_in_picture`

## 通用设计

- 扩展 `TaskRequest`：
  - [x] `extra_inputs: dict[str, Path]` 或等价结构。
  - [x] 不再继续滥用 `subtitle_path`。
  - [x] 保留当前单输入 operation 的简单调用方式。
- 扩展 `OperationFormWidget`：
  - [x] 支持 operation-specific 文件选择字段。
  - [x] 文件选择只通过 `QFileDialog` 或可键入本机路径。
  - [x] 文件后缀按 operation allowlist 校验。
- 输出默认：
  - [x] 多输入视频输出优先 `mp4`。
  - [x] 必要时允许 `mkv|mov|webm`。

## Operation 设计

### overlay

- 第二输入：图片文件 `.png/.jpg/.jpeg/.webp/.gif`。
- 参数：
  - `position`: `bottom_right|top_left|top_right|bottom_left|center`
  - `width_percent`: 默认 15，范围 1 到 100
  - `output_format`
- 行为：
  - 使用 `scale` + `overlay` filter_complex。
  - 音频 stream copy。

### mix_audio

- 第二输入：音频文件 `.mp3/.wav/.ogg/.aac/.flac/.m4a`。
- 参数：
  - `original_volume`: 0 到 2
  - `music_volume`: 0 到 2
  - `loop_music`: 默认 true
  - `output_format`
- 行为：
  - 使用 `amix=duration=first`。
  - 背景音乐短于视频时可用 `-stream_loop -1`。
  - 视频 stream copy。

### concat

- 第二输入：视频文件。
- 参数：
  - `output_format`
- 行为：
  - 使用 concat filter，允许不同分辨率/帧率/编码。
  - 第一段可应用 trim；第二段默认完整使用。
  - 输出 H.264/AAC。

### side_by_side

- 第二输入：视频文件。
- 参数：
  - `layout`: `horizontal|vertical`
  - `common_dimension`: 整数
  - `audio_source`: `first|second|none`
  - `output_format`
- 行为：
  - 横向使用 `hstack`，纵向使用 `vstack`。
  - 统一缩放到 common dimension。

### picture_in_picture

- 第二输入：视频文件。
- 参数：
  - `position`
  - `width_percent`: 默认 30
  - `loop_overlay`: 默认 true
  - `output_format`
- 行为：
  - overlay 视频短于主视频时 loop。
  - 主视频音频保留。
  - 输出 H.264/AAC。

## 测试 Checklist

- [x] 每个 operation 缺第二输入时失败。
- [x] 第二输入后缀不允许时失败。
- [x] 每个 operation 成功构建参数数组。
- [x] 集成 smoke 创建两个短视频、一个音频、一个图片，分别验证输出存在且非空。

## 反目标

- 不做任意多输入合成。
- 不做时间线编辑器。
- 不做音轨波形、关键帧动画、可视化拖拽定位。
- 不为多输入操作引入数据库或持久任务队列。

## 验收

- 五个多输入 operation 都能从 GUI 选择第二输入并成功执行。
- 关闭 GUI 或取消任务时不残留 ffmpeg 进程。
- 单输入 operation 不受 `extra_inputs` 改造影响。
