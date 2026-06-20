# ffmpeg-gui

本机个人使用的 PySide6 桌面版 ffmpeg 工具。应用直接选择本机文件路径，调用本机 `ffmpeg` / `ffprobe` 处理媒体，不使用 FastAPI、WebView、Electron、Tauri、QML、ffmpeg.wasm 或 Whisper。

## 功能

- 查看 `ffprobe` 媒体信息
- 视频格式转换：MP4、WebM、MOV、MKV
- 视频压缩：CRF、preset、可选宽度
- 抽取音频：MP3、WAV、AAC、FLAC
- 生成 GIF：帧率和宽度可调
- 静音、旋转/翻转、数字裁剪、封面提取、速度调整
- 音量调整、响度标准化、移除元数据
- 软字幕嵌入：SRT、VTT、ASS、SSA
- Raw FFmpeg 高级参数模式，输入和输出路径仍由应用统一管理
- 单任务运行、进度、日志、取消、打开输出文件和打开输出目录

## 安装

需要 `uv`、Python 3.14、本机 `ffmpeg` 和 `ffprobe`。

```bash
cd /Users/boom/workspace/BoomTools/ffmpeg-gui
uv venv --python 3.14
uv pip install -r requirements.txt
```

确认本机 ffmpeg 可用：

```bash
ffmpeg -version
ffprobe -version
```

如需覆盖二进制路径，可以在 GUI 顶部输入框中设置，也可以使用环境变量：

```bash
FFMPEG_BIN=/opt/homebrew/bin/ffmpeg FFPROBE_BIN=/opt/homebrew/bin/ffprobe uv run python -m desktop.app.main
```

## 启动

```bash
cd /Users/boom/workspace/BoomTools/ffmpeg-gui
uv run python -m desktop.app.main
```

输出、临时文件和日志默认写入 `ffmpeg-gui/data/`，该目录不会提交到 git。

## 验证

```bash
cd /Users/boom/workspace/BoomTools/ffmpeg-gui
uv run python -m compileall desktop shared tests
uv run python -m pytest
```

集成 smoke 会真实调用本机 `ffmpeg`，默认跳过。如需运行：

```bash
RUN_FFMPEG_GUI_SMOKE=1 uv run python -m pytest tests/integration
```
