# TODO 08: 最终验证与清理

## 目标

确认除 Whisper / Auto-Caption 模型接入外，`ffmpeg-gui` 已达到本机功能复现终态，并清理实现过程中产生的冗余。

## 全量功能验收矩阵

- [ ] 基础：
  - [ ] `convert`
  - [ ] `resize_compress`
  - [ ] `compress`
  - [ ] `extract_audio`
  - [ ] `gif`
  - [ ] `mute`
- [ ] 视频编辑：
  - [ ] `speed`
  - [ ] `rotate`
  - [ ] `crop`
  - [ ] `thumbnail`
  - [ ] `reverse`
  - [ ] `fade`
  - [ ] `adjust`
  - [ ] `loop`
  - [ ] `pad`
  - [ ] `denoise`
  - [ ] `boomerang`
  - [ ] `sharpen_blur`
- [ ] 音频：
  - [ ] `volume`
  - [ ] `normalize_audio`
  - [ ] `mix_audio`
- [ ] 字幕和信息：
  - [ ] `subtitles` soft
  - [ ] `subtitles` burn
  - [ ] `media_info`
- [ ] 多输入：
  - [ ] `overlay`
  - [ ] `concat`
  - [ ] `side_by_side`
  - [ ] `picture_in_picture`
- [ ] 高级：
  - [ ] `raw`
  - [ ] Raw 第二输入
  - [ ] Raw 示例命令
- [ ] 工作流：
  - [ ] 批处理
  - [ ] Stack 链式处理
  - [ ] 命令预览
  - [ ] 输出估算

## 验证命令

```bash
cd /Users/boom/workspace/BoomTools/ffmpeg-gui
uv run python -m compileall desktop shared tests
uv run python -m pytest tests/desktop
RUN_FFMPEG_GUI_SMOKE=1 uv run python -m pytest tests/integration
QT_QPA_PLATFORM=offscreen uv run python -c 'from PySide6.QtWidgets import QApplication; from desktop.app.bootstrap import create_app; app = QApplication([]); boot = create_app(); boot.window.show(); app.processEvents(); boot.controller.close(); boot.window.close(); print("GUI_OFFSCREEN_OK")'
```

## 清理 Checklist

- [ ] 删除实现过程中临时创建但不再使用的 helper、TODO stub 或实验文件。
- [ ] 检查没有 `pyproject.toml`、`pytest.ini` 这类已确认冗余配置回流。
- [ ] 检查没有上游 operation id alias：
  - [ ] `resizecompress`
  - [ ] `stripmeta`
  - [ ] `mixaudio`
  - [ ] `sxs`
  - [ ] `pip`
  - [ ] `autocaption`
- [ ] 检查没有 Web/PWA/wasm 代码：
  - [ ] service worker
  - [ ] browser worker
  - [ ] ffmpeg.wasm
  - [ ] Transformers.js
- [ ] 清理生成物：
  - [ ] `__pycache__`
  - [ ] `.pytest_cache`
  - [ ] `data/config.json`
  - [ ] `data/logs/*.log`
  - [ ] smoke 测试临时媒体
- [ ] 更新 `README.md` 功能列表、安装命令、验证命令。
- [ ] 更新 `AGENTS.md`，只保留当前真实架构和 YAGNI 决策。

## 反目标

- 不为了“全量复现”引入模型字幕。
- 不为了“完整产品化”引入远程服务、账号、数据库、安装器。
- 不保留旧实现路径和新实现路径并行。
- 不保留已经确认冗余的配置文件。

## 最终判定

完成后应满足：

- `ffmpeg-gui` 是单一 PySide6 本机工具实现。
- 所有非模型功能都有 GUI 入口、runtime 命令构建、单元测试或集成 smoke。
- Whisper / Auto-Caption 不存在于运行时功能中。
- 没有兼容性历史冗余。
- 没有超出本机个人工具阶段的过度实现。

