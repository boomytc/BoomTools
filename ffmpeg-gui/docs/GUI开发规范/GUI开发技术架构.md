# GUI开发技术架构

本文件用于 GUI 产品设计、实现和文档编写的技术选型入口。  
通用标准产品可采用 **PySide6 + FastAPI 混合架构**，适合模型推理、客户交付、API 复用、Web 化或远程部署。  
`ffmpeg-gui` 当前阶段是纯本机工具基线：以 `AGENTS.md` 为最高优先级，采用 **PySide6 + Qt Widgets + QSS + services/runtime + contracts**；GUI 直接选择本机文件路径，任务层调用本机 `ffmpeg` / `ffprobe`，不默认启动 FastAPI，不做本地 HTTP 文件上传。

快速结论：

1. 默认桌面端采用 **PySide6 + Qt Widgets + QSS**。
2. 小型本机工具默认采用 **PySide6 + services/runtime + contracts**，不必启动后端服务。
3. 标准模型/客户交付产品可采用 **FastAPI + REST API + WebSocket / SSE**。
4. 桌面端不直接耦合模型推理细节；若启用后端，则通过 API Client 调用本地或远程 FastAPI。
5. 后端负责模型加载、模型推理、文件处理、后台任务、数据库、配置、日志和标准化返回。
6. GUI 与后端可以采用：
   - 本地内置模式：PySide6 启动本机 `127.0.0.1` FastAPI 服务。
   - 本地外置模式：用户手动启动 FastAPI，PySide6 作为客户端连接。
   - 远程服务模式：PySide6 连接局域网或服务器上的 FastAPI 服务。
7. 小型单机工具可以保持纯 PySide6 + services/runtime；`ffmpeg-gui` 当前就属于这一类。
8. 不默认使用 Electron / Tauri / Vue / React / QML，除非产品确实需要复杂前端交互、Web 复用或高度动画化界面。
9. 跨平台交付时，不追求强行单文件可执行程序。AI 产品更推荐目录式交付：程序、模型、配置、日志、输出目录分离。
10. 所有本机路径、模型路径、数据目录、日志目录必须统一管理，不允许硬编码个人机器路径。
11. 模型 raw output 不默认暴露给 GUI，GUI 只依赖后端返回的产品级标准结构。

## ffmpeg-gui 当前基线

```text
PySide6 + Qt Widgets + QSS
services/runtime
shared/contracts
QProcess / QThread Worker
PanelFrame / SegmentedToggle / PanelActionBar / FixedScrollArea / FormSection
QTableView + TaskTableModel + QStyledItemDelegate
```

当前不启用：

```text
FastAPI
HTTP 文件上传
API Client / BackendProcess
WebUI / 远程服务
Electron / Tauri / React / Vue / QML
```

只有出现 GUI + Web/API 双入口、远程访问、复杂后台任务队列、服务化交付或共享 API 契约需求时，再升级为 PySide6 + Local FastAPI。

## 一、标准产品技术组合

标准模型/客户交付产品推荐组合：

```text
PySide6 + Qt Widgets + QSS
FastAPI + Uvicorn
Pydantic
HTTPX / requests / websockets
QThread / QThreadPool / Worker
Runtime Model Manager
Contracts
pyproject.toml
PyInstaller / Nuitka / pyside6-deploy
```

桌面端职责：

```text
PySide6 Desktop
- 主窗口、页面、弹窗、托盘、菜单
- 文件选择、拖拽、预览
- 任务提交、进度展示、结果展示
- 本地配置界面
- 调用 FastAPI API
- 接收 WebSocket / SSE 进度
- 启动、检查、停止本地后端服务
```

后端职责：

```text
FastAPI Backend
- REST API
- WebSocket / SSE
- 文件上传与下载
- 模型加载、卸载、readiness 检查
- 模型推理
- 后台任务
- 数据库访问
- 权限认证
- 配置管理
- 日志与异常处理
- 标准化结果返回
```

共享合同职责：

```text
Shared Contracts
- 标准错误码
- 标准响应结构
- 模型状态
- readiness 结构
- 推理输入输出结构
- 任务状态结构
```

## 二、三种运行模式

### 1. 本地内置模式

适合客户交付、本地 AI 工具、离线部署。

```text
PySide6 GUI
  ↓ 启动子进程
Local FastAPI Backend 127.0.0.1:port
  ↓
services / runtime / model_manager
  ↓
models / adapters
```

特点：

- 用户只启动桌面程序。
- GUI 自动启动 FastAPI 子进程。
- GUI 轮询 `/api/health` 等待后端 ready。
- 关闭 GUI 时自动关闭本地后端。
- 后端只绑定 `127.0.0.1`，不默认暴露到公网。
- 适合打包成桌面产品交付。

### 2. 本地外置模式

适合开发调试、模型较重、需要单独排查后端日志的场景。

```text
用户手动启动 FastAPI
PySide6 GUI 连接 http://127.0.0.1:port
```

特点：

- 后端和 GUI 可独立启动。
- 更容易调试 API、模型加载、日志和异常。
- 适合开发阶段或内部测试阶段。
- GUI 启动时只做健康检查，不负责启动后端。

### 3. 远程服务模式

适合企业内网、多用户共享 GPU、服务器集中部署。

```text
PySide6 Client
  ↓ HTTPS / WebSocket
Remote FastAPI Backend
  ↓
GPU Runtime / Database / Storage
```

特点：

- 客户端轻量。
- 模型部署在服务器。
- 多个桌面客户端共享后端服务。
- 需要认证、权限、安全、日志和网络异常处理。
- 适合企业内网、GPU 服务器集中推理、多人使用。

## 三、默认适用场景

优先采用 PySide6 + FastAPI 的场景：

```text
ASR / TTS / OCR / LLM / 多模态模型桌面工具
本地文件处理工具
批量推理工具
客户离线交付产品
需要模型加载与释放控制的产品
需要进度展示、取消任务、任务队列的产品
需要 GUI + API 双入口的产品
未来可能扩展 WebUI 的产品
需要局域网或远程服务器推理的产品
```

可以不引入 FastAPI 的场景：

```text
非常小的单机工具
只有几个按钮和简单文件处理
不需要 API 复用
不需要 WebSocket / SSE
不需要远程调用
不需要后续 Web 化
```

此时可采用：

```text
PySide6 → controller → service → runtime
```

但标准产品仍建议预留 contracts、services、runtime 的结构，避免以后返工。

## 四、桌面 UI 技术选择

默认使用 Qt Widgets：

```text
QMainWindow
QWidget
QDialog
QStackedWidget
QTableView / QTableWidget
QTreeView
QPlainTextEdit
QTextEdit
QLabel
QPushButton
QProgressBar
QStatusBar
QSystemTrayIcon
QFileDialog
```

样式使用：

```text
QSS
统一 spacing / margin / radius / font-size
统一图标资源
统一颜色变量约定
```

默认不优先使用 QML / Qt Quick。

只有以下情况才考虑 QML：

```text
高度动画化
触摸屏
大屏展示
移动端风格界面
强视觉定制
类智能座舱/嵌入式 UI
```

对于普通 AI 工具、桌面软件、客户交付程序，Qt Widgets 更稳、更直接、更容易维护。

## 五、通信方式

PySide6 与 FastAPI 之间通过 API 通信：

```text
REST API       普通请求、配置读取、任务创建、结果查询
WebSocket      实时日志、实时进度、流式结果
SSE            单向进度推送、模型推理事件流
文件下载接口   导出结果、下载报告、下载处理产物
```

推荐接口形态：

```text
GET  /api/health
GET  /api/models
GET  /api/models/{model_id}/status
POST /api/models/{model_id}/load
POST /api/models/{model_id}/unload
POST /api/tasks
GET  /api/tasks/{task_id}
GET  /api/tasks/{task_id}/result
POST /api/inference
WS   /ws/tasks/{task_id}
```

GUI 中不要到处散落 HTTP 请求。  
所有 API 调用应统一封装在：

```text
desktop/app/clients/api_client.py
desktop/app/clients/websocket_client.py
desktop/app/clients/sse_client.py
```

## 六、线程与后台任务

GUI 主线程只负责界面响应，不执行耗时任务。

必须后台化的任务：

```text
启动后端
健康检查轮询
文件上传
大文件读取
模型加载等待
推理任务等待
WebSocket / SSE 监听
批量文件处理
结果导出
日志读取
外部命令执行
```

推荐方式：

```text
QThread              长生命周期任务
QThreadPool          短任务、可复用任务
QRunnable            可丢给线程池的任务
Worker QObject       有 signal 的后台任务
QProcess             启动后端、外部命令、转码工具
```

禁止：

```text
在按钮回调里直接请求长耗时 API
在 GUI 主线程里执行模型推理
在 GUI 主线程里等待大文件处理
在 GUI 主线程里阻塞读取 WebSocket
```

## 七、模型类产品标准原则

模型产品必须遵守：

1. GUI 不直接依赖模型 raw output。
2. GUI 不直接加载模型。
3. GUI 不直接判断模型底层框架细节。
4. FastAPI 不在 endpoint 中写复杂推理逻辑。
5. 模型加载、缓存、释放、设备选择进入 runtime/model_manager。
6. 模型差异通过 adapter 隔离。
7. adapter raw output 通过 parser 转成 contracts 定义的标准结果。
8. raw output 只能作为 debug 产物保存，不默认进入 GUI 主流程。
9. 模型未 ready 时，后端必须返回结构化错误，GUI 展示用户可理解的提示。
10. 模型路径必须通过配置和 paths 模块解析，不允许硬编码。

推荐返回结构：

```json
{
  "success": true,
  "data": {
    "task_id": "xxx",
    "model": {
      "name": "model_name",
      "version": "model_version",
      "device": "cuda"
    },
    "result": {},
    "meta": {
      "elapsed_ms": 1234,
      "input_file": "xxx"
    }
  },
  "error": null
}
```

GUI 只展示 `data.result`、`data.meta` 和标准化状态，不直接适配模型原始字段。

## 八、跨平台要求

目标平台：

```text
Windows 10/11
macOS
Linux Ubuntu / Debian 系
```

跨平台要求：

1. 路径统一使用 `pathlib.Path`。
2. 不硬编码 Windows 或 Linux 绝对路径。
3. 不默认读取仓库父级、兄弟目录作为模型目录。
4. 不把模型路径写死在 GUI 代码中。
5. 配置文件、日志目录、缓存目录、输出目录统一由 paths 模块管理。
6. 外部命令调用必须区分 Windows / macOS / Linux。
7. 打包脚本按平台分开处理。
8. 模型运行设备根据平台自动判断：
   - Windows / Linux：CPU / CUDA
   - macOS：CPU / MPS，具体取决于模型框架支持
9. GUI 样式不要依赖某个平台私有字体或控件行为。
10. 文件编码默认使用 UTF-8。

## 九、打包与交付原则

推荐交付形态：

```text
MyApp/
├── MyApp.exe / MyApp.app / myapp
├── backend/
├── models/
├── config/
├── data/
│   ├── uploads/
│   ├── outputs/
│   ├── cache/
│   └── logs/
├── resources/
└── README.md
```

不建议把所有模型和运行数据强行塞进单文件 exe。

推荐工具：

```text
开发运行：python -m desktop.app.main
后端运行：uvicorn backend.app.main:app
Windows 打包：PyInstaller / Nuitka
macOS 打包：PyInstaller / Nuitka / pyside6-deploy，需额外关注签名、公证、权限
Linux 打包：venv + 启动脚本 / AppImage / Nuitka
```

AI 产品推荐目录式交付，原因：

```text
模型文件大
配置需要客户现场调整
日志需要排查
输出目录需要保留
后端服务可能需要独立升级
不同平台依赖差异明显
```

## 十、Agent 默认决策规则

开始 GUI 项目前，必须先判断：

1. 是否是本地单机工具？
2. 是否需要跨平台？
3. 是否需要模型推理？
4. 是否需要 GUI + API 双入口？
5. 是否需要后续 Web 化？
6. 是否需要远程后端？
7. 是否需要任务进度、取消、日志流？
8. 是否需要模型热加载、设备选择、路径配置？
9. 是否需要客户离线交付？
10. 是否需要打包成 Windows / macOS / Linux 可执行程序？

默认结论：

```text
标准 GUI 产品：
PySide6 + FastAPI + Contracts + Runtime + QSS

小型单机工具：
PySide6 + services + runtime，可不启动 FastAPI

企业共享推理：
PySide6 Client + Remote FastAPI Backend
```

除非需求明确，否则不要盲目引入 Electron、Tauri、Vue、React、QML。
