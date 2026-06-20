# AGENTS.md

本文件是 `ffmpeg-gui` 的 Agent 开发规范。开发前必须优先阅读并遵守本文，以及 `docs/GUI开发规范/` 下的三份规范文件。

## 产品定位

- `ffmpeg-gui` 是个人本机使用的 ffmpeg 桌面工具。
- 默认技术路线为 `PySide6 + Qt Widgets + QSS + services/runtime + contracts`。
- 本阶段不默认启动 FastAPI，不做本地 HTTP 文件上传；GUI 直接选择本机路径，任务层调用本机 `ffmpeg` / `ffprobe`。
- 需要后续 API 复用、WebUI、远程访问或客户交付服务化时，再升级为 `PySide6 + Local FastAPI + REST/SSE/WebSocket`。
- 不集成 `ffmpeg.wasm`、Whisper、PWA、Electron、Tauri、React、Vue、QML。

## 架构边界

- UI 层只负责窗口、页面、控件、布局、交互入口、状态展示、进度展示、日志展示和结果入口。
- Controller 层负责读取 UI 状态、校验输入、调用 service/task、更新 ViewModel。
- ViewModel 保存页面状态、任务状态、按钮启用状态、日志、输出文件、错误提示。
- Services/runtime 负责 ffmpeg 命令构建、参数校验、媒体探测、任务编排和输出文件管理。
- Contracts 负责稳定的 operation、options、task status、错误结构和结果结构。
- 任何耗时任务都不能运行在 Qt 主线程。

## 目录规范

默认采用以下最小骨架，按真实需求逐步扩展：

```text
ffmpeg-gui/
├── desktop/app/
│   ├── main.py
│   ├── bootstrap.py
│   ├── core/
│   ├── ui/
│   ├── controllers/
│   ├── viewmodels/
│   ├── services/
│   ├── runtime/
│   ├── tasks/
│   └── utils/
├── shared/contracts/
├── resources/
│   ├── icons/
│   ├── images/
│   ├── qss/app.qss
│   └── app.qrc
├── data/
│   ├── outputs/
│   ├── temp/
│   ├── cache/
│   ├── debug/
│   └── logs/
├── docs/
├── tests/
│   ├── desktop/
│   └── integration/
├── scripts/
├── requirements.txt
├── README.md
└── AGENTS.md
```

如果后续引入 FastAPI，再新增并遵守：

```text
backend/app/
desktop/app/clients/
desktop/app/processes/backend_process.py
tests/backend/
```

## PySide6 UI 规则

- 默认使用 Qt Widgets：`QMainWindow`、`QWidget`、`QDialog`、`QStackedWidget`、`QTableView`、`QPlainTextEdit`、`QProgressBar`、`QStatusBar`、`QFileDialog`。
- 主窗口只组织菜单、工具栏、页面容器、状态栏和全局区域，不塞入全部业务逻辑。
- 页面只负责布局和用户操作入口，不直接执行 ffmpeg。
- 文件选择、拖拽、任务列表、日志、输出下载/打开目录应拆成可复用 widget。
- 使用布局管理器，不使用绝对定位。
- QSS 统一放在 `resources/qss/app.qss`，不要在窗口代码中散落大量内联样式。
- 所有按钮、输入框、进度条、日志区域必须有明确的 disabled/loading/error/success 状态。

## ffmpeg 任务规则

- 默认从 `PATH` 查找 `ffmpeg` / `ffprobe`，支持配置覆盖。
- 任务执行必须用参数数组，禁止 `shell=True`。
- GUI 长任务优先使用 `QProcess` 或 `QThread + Worker`，通过 signal 回传：
  - `progress_changed`
  - `status_changed`
  - `log_received`
  - `result_ready`
  - `error_occurred`
  - `finished`
- 解析 `ffmpeg -progress pipe:1 -nostats` 获取进度；无 duration 时显示不确定进度和实时日志。
- 不复制大视频到上传目录；输入路径直接引用用户选择的本机文件。
- 输出默认写入用户选择目录或 `data/outputs/`，临时文件写入 `data/temp/`。
- 支持取消任务；取消时应终止进程并更新状态，不留下悬挂进程。

## 路径与配置

- 所有路径统一通过 `desktop/app/core/paths.py` 或 runtime/service 层解析。
- 使用 `pathlib.Path`，默认 UTF-8，必须兼容中文路径、空格路径和跨平台路径。
- 禁止硬编码 `/Users/...`、`/home/...`、`D:/...` 等个人机器路径。
- 不默认读取仓库父级或兄弟目录作为数据目录。
- 运行数据、日志、缓存、输出不提交 Git。
- 本地配置优先级建议：
  1. GUI 用户显式配置
  2. 本地覆盖配置
  3. 环境变量
  4. 项目默认配置

## Contracts 与状态

- Operation、options、task status、错误码、结果结构必须集中定义在 `shared/contracts/` 或等价的稳定模块中。
- GUI 只依赖产品级结构，不依赖 ffmpeg 原始日志格式作为业务判断来源。
- ffmpeg 原始日志可以显示和保存为 debug 产物，但不作为 UI 主流程合同。
- 错误必须转换为用户可理解的消息，同时保留 debug detail 供排查。

## 测试要求

至少覆盖：

- ffmpeg/ffprobe 路径解析
- 命令构建 allowlist 和参数数组
- 非法 operation、非法格式、非法参数
- 任务状态流转：pending/running/succeeded/failed/cancelled
- 进度解析和无 duration 场景
- API-less service/runtime 单元测试
- GUI Controller / ViewModel 状态测试
- 跨平台路径、中文路径、空格路径

GUI 视觉自动化可后置，但核心 service、runtime、contracts、task worker 必须优先测试。

## 常用命令

开发阶段使用 `uv` 创建 Python 3.14 环境，并用 `requirements.txt` 安装依赖：

```bash
uv venv --python 3.14
uv pip install -r requirements.txt
uv run python -m desktop.app.main
uv run python -m pytest
```

本项目是本机轻量 GUI 工具，不作为可安装 Python 包发布；当前不需要 `pyproject.toml`。如后续进入打包、发布或多依赖分组阶段，再重新引入工程配置文件。

## 禁止事项

- 不要在按钮回调里执行 ffmpeg 或阻塞等待。
- 不要在 Qt 主线程里做大文件读取、转码、轮询、日志读取。
- 不要把全部业务逻辑塞进 `main_window.py` 或 `main.py`。
- 不要在 UI 文件中直接拼复杂命令。
- 不要使用 `shell=True`。
- 不要关闭 GUI 后残留 ffmpeg 或后端进程。
- 不要无状态检查就启用主功能。
- 不要默认引入 FastAPI、Electron、Tauri、Vue、React、QML。
- 不要强求单文件 exe。
- 不要把运行输出、缓存、日志、大媒体文件提交到 Git。

## 后续升级到 FastAPI 的条件

只有出现以下需求时才升级为 `PySide6 + Local FastAPI`：

- 需要 GUI + Web/API 双入口。
- 需要远程调用或局域网共享。
- 需要复杂后台任务队列和可复用 API。
- 需要将 ffmpeg 服务独立测试、独立部署或被其他客户端调用。
- 需要与其他客户端共享统一 API 契约后再升级。

升级后必须新增 API Client、BackendProcess、健康检查、端口管理、优雅关闭和后端日志管理；后端默认只绑定 `127.0.0.1`。
