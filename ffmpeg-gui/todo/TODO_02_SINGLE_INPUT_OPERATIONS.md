# TODO 02: 单输入单输出功能补齐

## 目标

补齐不需要第二输入文件的上游业务功能。这一阶段优先完成可直接落地的 ffmpeg filter/参数组合，不引入批处理和 Stack。

## 范围

新增或增强：

- `resize_compress`
- `reverse`
- `fade`
- `adjust`
- `loop`
- `pad`
- `denoise`
- `boomerang`
- `sharpen_blur`
- `extract_audio` 增加 `ogg`
- `convert` 增加 `avi`
- `compress` 与 `resize_compress` 边界清晰化

## Operation 设计

### resize_compress

- 参数：
  - `output_format`: `mp4|webm|mov|mkv|avi`
  - `width`: 可选整数
  - `height`: 可选整数
  - `crf`: 默认 23
  - `preset`: 默认 `medium`
- 行为：
  - width/height 至少一个存在。
  - 单边为空时保持比例。
  - 两边都有时使用明确 scale。

### reverse

- 参数：
  - `output_format`: `mp4|webm|mov|mkv`
  - `include_audio`: 默认 true
- 行为：
  - 视频使用 `reverse`。
  - 音频存在且 `include_audio=true` 时使用 `areverse`。
  - 大文件风险只显示提示，不做复杂内存预测。

### fade

- 参数：
  - `fade_in_seconds`
  - `fade_out_seconds`
  - `output_format`
- 行为：
  - video filter 使用 `fade`。
  - audio filter 使用 `afade`。
  - fade-out 需要 duration；无 duration 时禁用 fade-out 或给出明确错误。

### adjust

- 参数：
  - `brightness`: `-1.0` 到 `1.0`
  - `contrast`: `0.0` 到 `2.0`
  - `saturation`: `0.0` 到 `3.0`
  - `grayscale`: bool
  - `output_format`
- 行为：
  - 使用 `eq`。
  - `grayscale=true` 时 saturation 固定为 0。

### loop

- 参数：
  - `plays`: `2` 到 `50`
  - `output_format`: 优先 `mp4|mkv|mov`
- 行为：
  - 使用 `-stream_loop plays-1`。
  - 默认 stream copy。
  - 不套用 trim；若 UI 有 trim 输入，loop 操作需禁用或忽略并提示。

### pad

- 参数：
  - `aspect_ratio`: `16:9|9:16|1:1|4:3|4:5|21:9`
  - `color`: `black|white|gray`
  - `output_format`
- 行为：
  - 使用 `scale` + `pad`，保持内容完整，不裁剪。

### denoise

- 参数：
  - `strength`: `light|medium|heavy`
  - `output_format`
- 行为：
  - `light`: `hqdn3d=2:2:3:3`
  - `medium`: `hqdn3d=4:4:6:6`
  - `heavy`: `hqdn3d=10:10:15:15`

### boomerang

- 参数：
  - `output_format`
- 行为：
  - 使用 `reverse` + `concat` filter_complex。
  - 默认移除音频。
  - 尊重 trim 的前向片段。

### sharpen_blur

- 参数：
  - `mode`: `sharpen|blur`
  - `strength`: `light|medium|heavy`
  - `output_format`
- 行为：
  - sharpen 使用 `unsharp`。
  - blur 使用 `boxblur`。

## UI Checklist

- [x] 在 `OperationFormWidget` 增加对应字段，不写内联业务逻辑。
- [x] 对需要 duration 的参数，在没有媒体信息时禁用或显示明确错误。
- [x] 单输入操作仍只需要一个输入文件和一个输出目录。
- [x] 运行中禁用表单，结束后恢复。

## 测试 Checklist

- [x] 每个 operation 有成功命令构建单测。
- [x] 每个 operation 至少一个非法参数单测。
- [x] 集成 smoke 增加短视频执行验证。
- [x] `loop` 验证输出文件存在且非空。
- [x] `thumbnail/gif/audio/video` 不互相污染输出扩展名。

## 反目标

- 不做可拖拽裁剪编辑器。
- 不做复杂内存预测或自动降级。
- 不做高级调色面板、LUT、曲线、预设库。
- 不做非必要的输出格式全排列；先按上游常用组合覆盖。

## 验收

- 当前阶段完成后，GUI 应比当前新增至少 9 个单输入 operation。
- `RUN_FFMPEG_GUI_SMOKE=1 uv run python -m pytest tests/integration` 覆盖本阶段新增 operation。
