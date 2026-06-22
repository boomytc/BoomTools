# ffmpeg-gui

本机个人使用的 PySide6 桌面版 ffmpeg 工具。应用直接选择本机文件路径，调用本机 `ffmpeg` / `ffprobe` 处理媒体，不使用 FastAPI、WebView、Electron、Tauri、QML、ffmpeg.wasm 或 Whisper。

当前稳定基线聚焦本机文件处理、批处理、Stack 链式处理、结果管理和长任务生命周期保护。功能覆盖和验收方式见：

- [功能矩阵](docs/功能矩阵.md)
- [手工验收清单](docs/手工验收清单.md)

## 功能

- 查看 `ffprobe` 媒体信息
- 内嵌媒体预览：任务表选中行可预览输入/输出，支持播放、暂停、seek，并可把当前时间写入处理范围或封面提取时间点
- 基础转换：`convert`、`resize_compress`、`compress`
- 主要视频处理：静音、旋转/翻转、裁剪、封面提取、速度调整、淡入淡出、亮度对比饱和度、循环、补边、去噪、锐化/模糊、倒放、倒放回放
- 音频处理：音量调整、响度标准化、混音
- 字幕：软字幕与字幕烧录（`.srt/.vtt/.ass/.ssa`）
- 多输入组合：叠加、拼接、并排、画中画
- Raw 参数：输入参数数组构建，支持可选第二输入
- 抽取音频支持 MP3/WAV/AAC/FLAC/OGG；视频输出支持 MP4/MKV/MOV/WebM/AVI；GIF 可通过 `gif` 操作或 Stack GIF 输出生成
- 单任务执行、批处理队列、任务进度、日志、取消、输出结果入口（打开文件、打开目录、复制路径、最近批次结果操作、打包当前批次成功结果）
- 长任务防睡眠：执行 ffmpeg 或打包 ZIP 时可临时阻止系统睡眠，macOS 下使用 `caffeinate -dimsu`，失败时降级但不阻塞任务

## 范围与反目标

- 按 `ffmpeg` 原生能力完成非模型功能复现，不接入 Whisper / 自动字幕模型 / Transformers.js / ffmpeg.wasm。
- 操作名使用本项目 `snake_case`：`resize_compress`、`side_by_side`、`picture_in_picture`、`media_info` 等，按本项目单一命名规范实现。
- 不引入 FastAPI、WebUI、数据库、远程服务或持久任务系统。
- 不做 Auto-Caption / Whisper 自动字幕、PWA、浏览器下载中心或内嵌 Web 播放器；当前预览是 PySide6/Qt Multimedia 本机控件。

## UI 结构

- `desktop/app/ui/components/`：通用 Qt Widgets 结构件，包含 `PanelFrame`、`SegmentedToggle`、`PanelActionBar`、`FixedScrollArea`、`FormSection`。
- `desktop/app/ui/panels/`：产品级区域组合，如内容选择、动作选择宿主、命令预览、媒体预览、任务队列。
- `desktop/app/ui/widgets/`：产品级复合控件、媒体播放器、字段工厂和表格模型。
- `desktop/app/ui/delegates/`：任务表 model/view 绘制委托，负责媒体摘要、文本列、进度和行操作渲染。
- `desktop/app/ui/layouts/`：主窗口内容布局宿主；当前使用 `DashboardLayout` 设置稳定 `panel_id`，不实现拖拽或布局持久化。
- `resources/qss/app.qss`：唯一视觉入口，通过 `objectName` 和 dynamic property 接入组件状态。

## 安装

需要 `uv`、Python 3.14、本机 `ffmpeg` 和 `ffprobe`。

```bash
cd ffmpeg-gui
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
cd ffmpeg-gui
uv run python -m desktop.app.main
```

输出、临时文件和日志默认写入 `ffmpeg-gui/data/`，该目录不会提交到 git。

## 内嵌媒体预览

右侧媒体预览面板跟随任务表当前行。输入文件可直接预览；任务成功后，如果输出文件仍存在，可切换到输出预览。预览面板使用 Qt Multimedia，不影响 ffmpeg 任务执行；如果本机 Qt 解码器无法播放某个文件，任务仍可继续运行。

预览面板提供轻量编辑辅助：

- “设为开始”“设为结束”“清空范围”会写回现有处理范围参数。
- 选择“提取封面”动作时，“设为封面时间”会写回 `timestamp_seconds`。
- 这些操作只更新当前参数表单和命令预览，不为批处理中每个文件单独保存独立编辑参数。

## GIF 质量

`gif` 操作支持两种质量模式：

- `fast`：默认模式，沿用单阶段 `fps,scale` 路径，启动快。
- `palette`：高质量模式，先在 `data/temp/` 生成临时 palette，再用 `paletteuse` 输出 GIF；任务结束、失败或取消后会清理临时 palette 文件。

两种模式都继续支持帧率、宽度和可选开始/结束时间范围。

Stack 模式额外提供 Stack 级输出设置：默认“跟随最后一步”，也可以直接输出 `gif`。选择 GIF 后可设置 `fast/palette`、帧率和宽度；palette 模式沿用同一套两阶段 palette 临时文件和清理流程。该能力只作用于 Stack 输出，不把 GIF 扩展为所有普通视频操作的常规输出格式。

## 批量结果打包

任务队列提供“打包成功结果”入口。它只收集最近一次批处理中状态为 `succeeded` 且文件仍存在的输出文件，失败、取消、无输出或已删除的结果会跳过。ZIP 写入当前输出目录，命名格式为 `ffmpeg-gui-batch-YYYYMMDD-HHMMSS.zip`。

任务队列也会显示最近批次统计，并支持复制最近批次所有成功输出路径、打开最近批次输出目录、在任务表中定位最近批次结果。

## 长任务防睡眠

设置中默认开启“长任务期间防止系统睡眠”。应用只会在 ffmpeg 任务或 ZIP 打包运行期间启用该保护，任务成功、失败、取消或关闭窗口后会停止。非 macOS 平台自动降级为空操作；macOS 下如果 `caffeinate` 不可用，会在状态栏提示但继续执行任务。

## 验证

```bash
cd ffmpeg-gui
uv run python -m compileall desktop shared tests
uv run python -m pytest
```

真实 ffmpeg smoke 会调用本机 `ffmpeg` / `ffprobe` 并生成临时媒体，默认跳过。如需执行稳定基线验证：

```bash
RUN_FFMPEG_GUI_SMOKE=1 uv run python -m pytest tests/integration
```
