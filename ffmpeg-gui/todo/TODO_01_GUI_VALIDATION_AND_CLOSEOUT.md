# TODO 01 - GUI 输入校验与收尾验证

## 目标

修复 GUI slot 中用户输入错误未被友好处理的问题，并完成最终验证。验证通过后删除 `TODO.md` 和 `todo/`，不保留阶段规划冗余。

## 待处理

- [ ] 修复 `MainController.start_task()` 的输入校验错误处理：
  - 捕获 `_validate_operation_inputs(...)` 抛出的 `ValueError`。
  - 用 `window.show_error(...)` 或等价 GUI 错误状态展示。
  - 缺字幕、字幕不存在、字幕后缀非法时不能从 Qt slot 冒异常。
- [ ] 修复 Stack 添加流程的输入校验错误处理：
  - `_on_stack_add_requested()` 中缺字幕或非法输入不能冒异常。
  - 不支持 Stack 的操作继续显示用户可读错误。
- [ ] 复核 batch 与 Stack 组合：
  - 不支持批处理的 operation 仍明确禁用或提示。
  - Stack 批处理仍顺序执行，不引入并发队列或持久化队列。
- [ ] 复核反目标：
  - 没有 `pyproject.toml`、`pytest.ini` 回流。
  - 没有 Whisper、Transformers.js、ASR、模型下载、`ffmpeg.wasm`、PWA、WebView、FastAPI 代码。
  - 没有 `resizecompress`、`stripmeta`、`mixaudio`、`sxs`、`pip` 这类上游兼容 alias 进入 runtime contract。
- [ ] 清理验证产物：
  - 删除或忽略 `__pycache__`、日志、测试输出和临时媒体。
  - 不删除 `.venv`。
- [ ] 验证通过后删除规划产物：
  - 删除 `ffmpeg-gui/TODO.md`。
  - 删除 `ffmpeg-gui/todo/`。

## 反目标

- 不把业务逻辑塞进 `main_window.py`。
- 不新增复杂设置页、插件系统、数据库或远程服务。
- 不为了 GUI 错误处理改动 runtime command allowlist。

## 验收

- [ ] `uv run python -m compileall desktop shared tests` 通过。
- [ ] `uv run python -m pytest tests/desktop` 通过。
- [ ] `RUN_FFMPEG_GUI_SMOKE=1 uv run python -m pytest tests/integration` 通过。
- [ ] `git status --short --untracked-files=all` 不出现运行输出、日志、缓存或大媒体文件。
- [ ] 上述验证通过后，`TODO.md` 和 `todo/` 已移除。
