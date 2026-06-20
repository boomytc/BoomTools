# ffmpeg-gui TODO 索引

## 终态目标

在 `ffmpeg-gui` 中复现 `/Users/boom/workspace/ffmpeg-webCLI-main` 除 Whisper / Auto-Caption 模型接入以外的核心功能，并保持本项目既定路线：

- 继续使用 `PySide6 + Qt Widgets + QSS + services/runtime + contracts`。
- 继续直接调用本机 `ffmpeg` / `ffprobe`，不引入 `ffmpeg.wasm`、PWA、WebView、FastAPI 或浏览器上传流程。
- 以本机个人使用为目标，优先稳定、清晰、可取消、可验证。
- 不复制上游 GPL 源码，只按功能形态重新实现。

## 反目标

- 不实现 Whisper、Transformers.js、自动字幕模型下载、模型缓存、模型释放或 ASR 转写流程。
- 不保留上游历史 operation id 兼容层，例如 `resizecompress`、`stripmeta`、`sxs`、`pip` 只作为需求来源，不在 GUI contract 中做兼容别名。
- 不做 `ffmpeg-web` / `ffmpeg-webCLI-main` 的 Web/PWA 复刻，不引入 service worker、浏览器虚拟文件系统或 wasm worker。
- 不把全部业务塞进 `main_window.py`；新增功能必须进入 contracts、runtime、services/tasks、UI widget/controller 的既有边界。
- 不做超出功能复现所需的插件系统、数据库、复杂持久队列、多用户、远程服务或打包发布体系。

## 阶段索引

| 状态 | 阶段 | 文件 | 目标 |
| --- | --- | --- | --- |
| [ ] | 00 | [TODO_00_SCOPE_BASELINE.md](todo/TODO_00_SCOPE_BASELINE.md) | 锁定功能清单、命名、验收边界 |
| [ ] | 01 | [TODO_01_CONTRACT_AND_RUNTIME_BASE.md](todo/TODO_01_CONTRACT_AND_RUNTIME_BASE.md) | 扩展 operation 合同、命令构建基础与测试矩阵 |
| [ ] | 02 | [TODO_02_SINGLE_INPUT_OPERATIONS.md](todo/TODO_02_SINGLE_INPUT_OPERATIONS.md) | 补齐单输入单输出业务功能 |
| [ ] | 03 | [TODO_03_SUBTITLE_RAW_AND_INFO.md](todo/TODO_03_SUBTITLE_RAW_AND_INFO.md) | 补齐非模型字幕、Raw 二输入、媒体信息能力 |
| [ ] | 04 | [TODO_04_MULTI_INPUT_OPERATIONS.md](todo/TODO_04_MULTI_INPUT_OPERATIONS.md) | 补齐 overlay、mix audio、concat、side-by-side、picture-in-picture |
| [ ] | 05 | [TODO_05_BATCH_QUEUE.md](todo/TODO_05_BATCH_QUEUE.md) | 增加本机批处理队列，顺序执行 |
| [ ] | 06 | [TODO_06_STACK_CHAINING.md](todo/TODO_06_STACK_CHAINING.md) | 增加可组合单输入滤镜链，单次编码 |
| [ ] | 07 | [TODO_07_GUI_PREVIEW_AND_POLISH.md](todo/TODO_07_GUI_PREVIEW_AND_POLISH.md) | 补齐本机 GUI 等价体验：预览、命令预览、估算、交互状态 |
| [ ] | 08 | [TODO_08_FINAL_VALIDATION_AND_CLEANUP.md](todo/TODO_08_FINAL_VALIDATION_AND_CLEANUP.md) | 全量验证、文档更新、冗余清理 |

## 当前功能差距摘要

当前 `ffmpeg-gui` 已有 14 个 operation：

`convert`、`compress`、`extract_audio`、`gif`、`mute`、`rotate`、`crop`、`thumbnail`、`speed`、`volume`、`strip_metadata`、`normalize_audio`、`subtitles`、`raw`。

需要补齐的非模型能力：

- 单输入处理：`resize_compress`、`reverse`、`fade`、`adjust`、`loop`、`pad`、`denoise`、`boomerang`、`sharpen_blur`。
- 多输入处理：`overlay`、`mix_audio`、`concat`、`side_by_side`、`picture_in_picture`。
- 字幕与 Raw 增强：硬字幕烧录、Raw 可选第二输入、Raw 示例命令。
- 工作流能力：批处理、Stack 链式处理、命令预览、输出大小估算、输入预览和更好的默认值。

## 总体验收

- 所有新增 operation 都通过参数数组执行，不使用 `shell=True`。
- 所有新增 operation 都有 runtime 单元测试，非法参数必须失败。
- 真实 ffmpeg smoke 覆盖每个新增 operation。
- GUI 仍可通过 `uv run python -m desktop.app.main` 启动。
- `uv run python -m compileall desktop shared tests` 通过。
- `uv run python -m pytest tests/desktop` 通过。
- `RUN_FFMPEG_GUI_SMOKE=1 uv run python -m pytest tests/integration` 通过。
- `git status --short --untracked-files=all` 不出现运行输出、日志、缓存或大媒体文件。

