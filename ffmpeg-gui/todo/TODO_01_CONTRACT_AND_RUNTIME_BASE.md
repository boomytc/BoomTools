# TODO 01: Operation 合同与 Runtime 基础扩展

## 目标

为全部非模型功能建立统一命令构建基础，先补合同、参数校验、输出格式和测试矩阵，再进入具体 UI。

## Checklist

- [ ] 扩展 `shared/contracts/operations.py`：
  - [ ] `resize_compress`
  - [ ] `reverse`
  - [ ] `fade`
  - [ ] `adjust`
  - [ ] `loop`
  - [ ] `media_info`
  - [ ] `pad`
  - [ ] `denoise`
  - [ ] `boomerang`
  - [ ] `sharpen_blur`
  - [ ] `overlay`
  - [ ] `mix_audio`
  - [ ] `concat`
  - [ ] `side_by_side`
  - [ ] `picture_in_picture`
- [ ] 扩展 `desktop/app/runtime/ffmpeg.py` 常量：
  - [ ] 视频输出增加 `avi`，但只在明确 operation 支持时开放。
  - [ ] 音频输出增加 `ogg`。
  - [ ] 图片输入允许 `.png/.jpg/.jpeg/.webp/.gif` 用于 overlay。
  - [ ] 第二音频输入允许 `.mp3/.wav/.ogg/.aac/.flac/.m4a`。
  - [ ] 第二视频输入允许常见视频扩展，不做 MIME 猜测系统。
- [ ] 新增多输入命令构建入口：
  - [ ] 保持当前 `build_command(...)` 支持单输入。
  - [ ] 增加明确的 `extra_inputs` 或等价结构，不复用 `subtitle_path` 承载所有二输入。
  - [ ] 多输入仍由后端/GUI 管理路径，Raw 不能任意访问未选择路径。
- [ ] 建立滤镜片段辅助函数：
  - [ ] 只放可复用的 ffmpeg filter 片段，不做通用 DSL。
  - [ ] 片段必须返回参数数组或结构化 filter，不返回 shell 字符串。
- [ ] 扩展 `tests/desktop/test_command_builder.py`：
  - [ ] 每个新增 operation 至少一个成功构建测试。
  - [ ] 每类非法参数至少一个失败测试。
  - [ ] 多输入缺失、后缀不允许、尺寸/倍率越界必须失败。

## 参数边界

- 所有数值范围按个人本机工具保守限制：
  - 宽高不超过 `7680x4320`。
  - 倍率、音量、循环次数、淡入淡出秒数必须有上限。
  - 多输入操作默认输出 `mp4`，后续再按真实需求扩展格式。
- Raw 第二输入只允许一个额外文件；不支持任意多输入 Raw。

## 反目标

- 不引入 Pydantic、FastAPI schema 或 Web API 兼容层。
- 不建立通用 ffmpeg AST / DSL。
- 不做上游 operation id alias。
- 不因为未来 Stack 需要而提前把所有 operation 重写成链式结构；只抽取当前阶段真正复用的 filter 片段。

## 验收

- `uv run python -m compileall desktop shared tests` 通过。
- `uv run python -m pytest tests/desktop/test_command_builder.py` 通过。
- 所有新增命令构建结果都满足：
  - `args` 是 list。
  - 不包含 `shell=True` 风格拼接。
  - 输入和输出路径由 runtime 统一放置。

