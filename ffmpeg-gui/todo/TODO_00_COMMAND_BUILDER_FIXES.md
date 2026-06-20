# TODO 00 - 命令构建与测试合同修复

## 目标

修复审查中暴露的 runtime 阻断问题，让命令构建合同和单元测试一致。只处理当前失败点，不扩大功能范围。

## 待处理

- [ ] 修复 `thumbnail` 输出扩展名：
  - `image_format=jpg` 输出 `.jpg`。
  - `image_format=png` 输出 `.png`。
  - `thumbnail` 不再走视频 `output_format` 分支。
  - 更新 `tests/desktop/test_command_builder.py`，移除 `image_format=jpg` 却期望 `.gif` 的错误断言。
- [ ] 修复字幕烧录命令构建：
  - `Operation.subtitles mode=burn` 不再引用未定义的 `extra_inputs`。
  - subtitle 路径只从 `TaskRequest.extra_inputs["subtitle"]` 获取。
  - 保持 `.srt/.vtt/.ass/.ssa` allowlist。
  - 保持 `FfmpegService` 对 ffmpeg `subtitles` filter 支持的前置检查。
- [ ] 统一 `media_info` 的 `CommandSpec` 合同：
  - 若 `CommandSpec.args` 表示完整 QProcess 参数数组，则必须包含 `ffmpeg_bin`。
  - 若 media info 不通过任务执行层运行，则不要复用普通 `build_command`。
  - 单测应使用真实存在的临时输入文件，避免用不存在文件测试命令构建。
- [ ] 修复 Stack 命令输出路径：
  - `build_stack_command(...)` 返回的 `spec.args` 必须把 `spec.output_path` append 到最后。
  - 保持参数数组执行，不使用 shell 拼接。
- [ ] 校准 `fade` 非法参数测试：
  - `fade_in_seconds` 单独使用应视为有效。
  - `fade_out_seconds` 仍必须有 `duration_seconds` 或可用媒体时长。
  - 测试只保留真实非法场景。

## 反目标

- 不新增 ffmpeg 参数 DSL。
- 不新增历史 operation alias。
- 不为了测试通过而放宽 raw/path allowlist。
- 不跳过失败测试或把失败转为 xfail。

## 验收

- [ ] `uv run python -m pytest tests/desktop/test_command_builder.py` 通过。
- [ ] `uv run python -m pytest tests/desktop/test_ffmpeg_service.py` 通过。
- [ ] `uv run python -m pytest tests/desktop/test_filter_chain.py` 通过。
- [ ] `uv run python -m pytest tests/desktop` 通过。
