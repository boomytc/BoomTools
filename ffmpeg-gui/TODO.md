# ffmpeg-gui 收尾 TODO

## 目标

旧的 00-08 功能复现阶段已经实施，不继续保留完成项。当前 TODO 只跟踪审查发现的阻断问题，修复后再删除本文件和 `todo/` 目录。

## 继续遵守的边界

- 不引入 Whisper、Transformers.js、自动字幕模型、模型下载或 ASR 流程。
- 不引入 `ffmpeg.wasm`、PWA、WebView、FastAPI、Electron、Tauri、QML。
- 不新增上游历史 operation id 兼容层，例如 `resizecompress`、`stripmeta`、`sxs`、`pip`。
- 不新增插件系统、数据库、复杂持久队列、多用户、远程服务或打包发布体系。
- 修复范围只限当前阻断问题和必要测试合同校准，遵循 YAGNI。

## 阶段索引

| 状态 | 阶段 | 文件 | 目标 |
| --- | --- | --- | --- |
| [ ] | 00 | [TODO_00_COMMAND_BUILDER_FIXES.md](todo/TODO_00_COMMAND_BUILDER_FIXES.md) | 修复命令构建、输出扩展名、字幕烧录、media_info、Stack 输出与测试合同 |
| [ ] | 01 | [TODO_01_GUI_VALIDATION_AND_CLOSEOUT.md](todo/TODO_01_GUI_VALIDATION_AND_CLOSEOUT.md) | 修复 GUI 输入错误处理，跑完整验证，通过后删除 TODO 冗余 |

## 完成条件

- `uv run python -m compileall desktop shared tests` 通过。
- `uv run python -m pytest tests/desktop` 通过。
- `RUN_FFMPEG_GUI_SMOKE=1 uv run python -m pytest tests/integration` 通过。
- `git status --short --untracked-files=all` 不出现运行输出、日志、缓存或大媒体文件。
- 通过后删除 `TODO.md` 和 `todo/`，不保留规划文件冗余。
