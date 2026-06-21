# ffmpeg-gui

本机个人使用的 PySide6 桌面版 ffmpeg 工具。应用直接选择本机文件路径，调用本机 `ffmpeg` / `ffprobe` 处理媒体，不使用 FastAPI、WebView、Electron、Tauri、QML、ffmpeg.wasm 或 Whisper。

## 功能

- 查看 `ffprobe` 媒体信息
- 基础转换：`convert`、`resize_compress`、`compress`
- 主要视频处理：静音、旋转/翻转、裁剪、封面提取、速度调整、淡入淡出、亮度对比饱和度、循环、补边、去噪、锐化/模糊、倒放、倒放回放
- 音频处理：音量调整、响度标准化、混音
- 字幕：软字幕与字幕烧录（`.srt/.vtt/.ass/.ssa`）
- 多输入组合：叠加、拼接、并排、画中画
- Raw 参数：输入参数数组构建，支持可选第二输入
- 抽取音频（MP3/WAV/AAC/FLAC/OGG）与 GIF 输出（mp4/mkv/mov/webm/avi）
- 单任务执行、批处理队列、任务进度、日志、取消、输出结果入口（打开文件、打开目录、复制路径）

## 范围与反目标

- 按 `ffmpeg` 原生能力完成非模型功能复现，不接入 Whisper / 自动字幕模型 / Transformers.js / ffmpeg.wasm。
- 操作名使用本项目 `snake_case`：`resize_compress`、`side_by_side`、`picture_in_picture`、`media_info` 等，按本项目单一命名规范实现。
- 不引入 FastAPI、WebUI、数据库、远程服务或持久任务系统。

## UI 结构

- `desktop/app/ui/components/`：通用 Qt Widgets 结构件，包含 `PanelFrame`、`SegmentedToggle`、`PanelActionBar`、`FixedScrollArea`、`FormSection`。
- `desktop/app/ui/panels/`：产品级区域组合，如内容选择、动作选择宿主、命令预览、任务队列。
- `desktop/app/ui/widgets/`：产品级复合控件、字段工厂和表格模型。
- `desktop/app/ui/delegates/`：任务表 model/view 绘制委托，负责媒体摘要、文本列、进度和行操作渲染。
- `desktop/app/ui/layouts/`：主窗口内容布局宿主；当前使用 `DashboardLayout` 设置稳定 `panel_id`，不实现拖拽或布局持久化。
- `resources/qss/app.qss`：唯一视觉入口，通过 `objectName` 和 dynamic property 接入组件状态。

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
