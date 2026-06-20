# TODO 00: 范围基线与命名边界

## 目标

建立功能复现的唯一边界，避免后续实现时混入 Whisper、Web/PWA、兼容别名或过度工程。

## 输入事实

- 上游 `ffmpeg-webCLI-main/docs/index.html` 暴露 29 个操作 tile：
  - `convert`
  - `resizecompress`
  - `audio`
  - `mute`
  - `gif`
  - `speed`
  - `rotate`
  - `crop`
  - `thumbnail`
  - `reverse`
  - `fade`
  - `adjust`
  - `stripmeta`
  - `autocaption`
  - `subtitles`
  - `volume`
  - `loop`
  - `overlay`
  - `mixaudio`
  - `concat`
  - `sxs`
  - `pip`
  - `info`
  - `pad`
  - `normalize`
  - `denoise`
  - `boomerang`
  - `sharpenblur`
  - `raw`
- 当前 `ffmpeg-gui` 已有 14 个 operation，缺口集中在单输入滤镜、多输入合成、批处理、链式处理和增强体验。

## 目标 operation 命名

采用本项目自己的 snake_case 命名，不保留上游历史 id 兼容层：

| 上游名称 | GUI 合同名称 |
| --- | --- |
| `resizecompress` | `resize_compress` |
| `audio` | 已有 `extract_audio` |
| `stripmeta` | 已有 `strip_metadata` |
| `normalize` | 已有 `normalize_audio` |
| `sharpenblur` | `sharpen_blur` |
| `mixaudio` | `mix_audio` |
| `sxs` | `side_by_side` |
| `pip` | `picture_in_picture` |
| `info` | `media_info` |

直接复用名称：

`reverse`、`fade`、`adjust`、`loop`、`overlay`、`concat`、`pad`、`denoise`、`boomerang`。

明确排除：

`autocaption`。

## Checklist

- [ ] 在 `shared/contracts/operations.py` 中只增加目标 snake_case operation，不加入上游 id alias。
- [ ] 更新 `OPERATION_LABELS`，按“基础 / 视频编辑 / 音频 / 字幕 / 多输入 / 高级 / 信息”分组展示。
- [ ] 明确 `autocaption` 不进入 `Operation`，也不做 disabled 占位入口。
- [ ] 更新测试中的目标 operation 清单，确保当前 14 个 operation 仍然保留。
- [ ] 在 `README.md` 中说明本项目复现的是本机 ffmpeg 功能，不复现 Whisper/PWA/wasm。

## 反目标

- 不创建 `LegacyOperation`、`operation_aliases`、`upstream_id` 这类兼容结构。
- 不为了对齐上游 UI 文案而污染 GUI 合同命名。
- 不在 root README 里承诺远程服务、浏览器端离线或模型字幕。

## 验收

- `rg -n "resizecompress|stripmeta|mixaudio|sxs|pip|autocaption" ffmpeg-gui/desktop ffmpeg-gui/shared ffmpeg-gui/tests` 只允许出现在 TODO 文档或注释解释中，不允许出现在运行时合同或业务分支中。
- `uv run python -m pytest tests/desktop` 通过。

