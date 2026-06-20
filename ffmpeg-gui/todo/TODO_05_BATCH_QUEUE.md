# TODO 05: 批处理队列

## 目标

增加本机批处理能力，顺序处理多个输入文件。保持简单队列，不引入后台服务、数据库或并发调度。

## 范围

- 多文件选择。
- 任务队列表格。
- 顺序执行。
- 批处理输出命名。
- 批处理日志和失败继续策略。

## 支持范围

第一版批处理支持：

- `convert`
- `compress`
- `resize_compress`
- `extract_audio`
- `gif`
- `mute`
- `speed`
- `rotate`
- `fade`
- `adjust`
- `strip_metadata`
- `volume`
- `loop`
- `pad`
- `normalize_audio`
- `denoise`
- `sharpen_blur`

第一版批处理不支持：

- `crop`：每个文件尺寸可能不同，先不做自动适配。
- `reverse`：大视频内存/耗时风险明显。
- `boomerang`：属于特殊全片效果。
- `thumbnail`：每个文件时间点不同，先不做批量默认。
- `subtitles`：需要逐文件字幕匹配。
- `overlay`、`mix_audio`、`concat`、`side_by_side`、`picture_in_picture`：多输入协调复杂。
- `media_info`：信息展示，不是输出处理。
- `raw`：用户参数不可预测。

## Checklist

- [x] 扩展输入区域：
  - [x] 保留单文件选择。
  - [x] 增加“添加多个文件到队列”。
  - [x] 队列只保存本机路径，不复制媒体文件。
- [x] 扩展 `TaskState`：
  - [x] 增加 queued/running/succeeded/failed/cancelled per item。
  - [x] 复用现有 `QTableView`。
  - [x] 支持移除未运行任务。
- [x] 扩展 `TaskManager`：
  - [x] 一次只运行一个 ffmpeg。
  - [x] 单个失败后继续下一个。
  - [x] 支持“取消当前”和“取消队列”。
- [x] 输出命名：
  - [x] 使用输入文件 stem + operation + 时间戳或序号。
  - [x] 不覆盖已有输出。
- [x] UI 状态：
  - [x] 批处理中禁用参数表单。
  - [x] 明确显示当前 item 和总进度。
  - [x] 不支持的 operation 在批处理模式下禁用并显示原因。

## 反目标

- 不做并发转码。
- 不做暂停/恢复持久队列。
- 不做数据库。
- 不做 ZIP 打包输出。
- 不做每个文件不同参数的复杂矩阵。

## 验收

- 三个短视频批量 convert 成功。
- 一个失败文件不会阻塞后续文件。
- 批量取消能终止当前 ffmpeg 并标记剩余任务 cancelled。
- `uv run python -m pytest tests/desktop` 覆盖状态流转。
