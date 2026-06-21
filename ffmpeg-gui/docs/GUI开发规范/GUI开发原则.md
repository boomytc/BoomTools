# GUI开发原则

请基于以下原则进行 GUI 产品设计、代码实现和文档编写。  
本文件是通用 GUI 原则：标准模型产品、客户交付产品、需要 API 复用或远程访问的产品，可以采用 **PySide6 + FastAPI 混合架构**。  
`ffmpeg-gui` 当前阶段是例外基线：以 `AGENTS.md` 为最高优先级，采用 **PySide6 + Qt Widgets + QSS + services/runtime + contracts**，不默认启动 FastAPI，不做本地 HTTP 文件上传，不引入 WebUI、Electron、Tauri、React、Vue 或 QML。

## ffmpeg-gui 当前基线

1. GUI 直接选择本机路径，任务层调用本机 `ffmpeg` / `ffprobe`。
2. UI 组件层采用 `components/`、`panels/`、`widgets/`、`delegates/`、`layouts/` 分层。
3. `PanelFrame` 是产品主面板默认外壳；任务表继续使用 model/view/delegate。
4. QSS 只放在 `resources/qss/app.qss`，通过 `objectName` 和 dynamic property 接入样式。
5. 只有需要 GUI + Web/API 双入口、远程访问、复杂后台任务队列、服务化交付时，才升级为 PySide6 + Local FastAPI。
6. 本文件后续关于 FastAPI、API Client、BackendProcess、上传下载接口的条目，只在触发上述升级条件后适用。

## 一、总体架构原则

1. 标准 GUI 产品可采用桌面端与后端服务分离设计；小型本机工具可采用纯 PySide6 + services/runtime。
2. 桌面端使用 PySide6，主要负责：
   - 主窗口、页面、弹窗、菜单、托盘
   - 本地文件选择、拖拽、预览
   - 用户配置输入
   - 任务提交
   - 进度展示
   - 日志展示
   - 结果展示与导出入口
   - 调用本机 service/runtime，或在服务化产品中调用本地/远程 FastAPI
3. 后端使用 FastAPI 是标准产品和服务化产品的推荐方案，主要负责：
   - REST API
   - WebSocket / SSE
   - 文件上传与下载
   - 模型推理
   - 后台任务
   - 数据库访问
   - 权限认证
   - 配置管理
   - 日志与异常处理
   - 模型 runtime 管理
4. 桌面端不直接承担模型推理细节。
5. 桌面端不直接依赖模型 raw output。
6. 后端默认返回 JSON 数据，接口返回结构必须稳定。
7. 启用 FastAPI 时，PySide6 与 FastAPI 通过 API Client 通信。
8. 标准模型产品优先使用本地内置 FastAPI 服务，必要时支持远程 FastAPI。
9. 小型单机工具可以退化为纯 PySide6 + services/runtime，但应保留后续接入 FastAPI 的可能性。
10. 工程配置、依赖管理、测试和打包配置优先参考 `pyproject.toml`。

## 二、默认技术基线

标准模型/客户交付产品默认采用：

```text
PySide6
Qt Widgets
QSS
FastAPI
Pydantic
Uvicorn
HTTPX / requests
WebSocket / SSE Client
QThread / QThreadPool / Worker
Runtime Model Manager
Contracts
```

不要默认引入：

```text
Electron
Tauri
Vue
React
Angular
QML
DearPyGui
Tkinter
CustomTkinter
Kivy
```

除非产品需求已经明显需要。

## 三、架构模式选择原则

### 1. 小型本地工具

推荐：

```text
PySide6 + services + runtime + contracts
```

适合：

```text
简单文件处理
简单格式转换
小型模型 Demo
无 API 复用需求
无远程访问需求
无 WebUI 需求
```

特点：

- 结构简单。
- 启动快。
- 不需要端口管理。
- 不需要本地 HTTP 通信。
- 但后续扩展为 API 服务需要改造。

### 2. 标准桌面产品 / 客户交付产品

推荐：

```text
PySide6 + Local FastAPI + REST API + WebSocket / SSE + runtime + contracts
```

适合：

```text
ASR / TTS / OCR / LLM / 多模态模型工具
本地 AI 桌面产品
批量推理工具
需要进度展示
需要任务取消
需要日志流
需要模型加载状态
需要 GUI + API 复用
需要后续 Web 化
```

特点：

- GUI 与后端边界清晰。
- 后端接口可复用。
- 后续可以增加 WebUI。
- 模型服务可独立测试。
- 更适合正式交付。

### 3. 远程服务型产品

推荐：

```text
PySide6 Client + Remote FastAPI Backend
```

适合：

```text
企业内网部署
多人共享 GPU 服务
模型部署在服务器
客户端只负责操作界面
需要统一权限认证
需要集中日志与审计
```

特点：

- 客户端轻量。
- GPU 资源集中管理。
- 后端统一维护。
- 需要处理网络、安全、认证、超时和断线重连。

## 四、桌面端代码原则

### 1. UI 层原则

UI 层只负责界面和交互，不写复杂业务逻辑。

UI 层可以做：

```text
创建窗口
创建控件
布局
绑定按钮事件
展示状态
展示进度
展示结果
展示错误提示
打开文件选择框
打开配置弹窗
```

UI 层不要做：

```text
直接加载模型
直接执行模型推理
直接读写大量业务数据
直接拼接后端接口逻辑
直接解析模型 raw output
直接处理复杂任务编排
直接执行耗时操作
```

### 2. Controller 层原则

Controller 负责连接 UI、ViewModel、API Client 和 Task。

职责：

```text
接收 UI 事件
读取当前页面状态
校验用户输入
调用 API Client
启动后台任务
处理任务回调
更新 ViewModel
通知 UI 刷新
```

禁止：

```text
把模型推理代码写进 Controller
把大量 HTTP 请求散落到多个 Controller
在 Controller 中硬编码后端地址和模型路径
```

### 3. ViewModel / State 原则

ViewModel 负责页面状态。

适合放：

```text
当前模型状态
当前任务状态
按钮启用状态
进度百分比
日志文本
结果列表
错误提示
当前配置快照
```

不要让多个 UI 页面各自维护重复状态。

### 4. API Client 原则

API Client 统一封装 PySide6 调用 FastAPI 的逻辑。

要求：

```text
所有 REST 请求进入 api_client.py
所有 WebSocket 请求进入 websocket_client.py
所有 SSE 请求进入 sse_client.py
不要在 UI 文件中直接写 requests/httpx
不要在多个页面中重复拼接 URL
不要把业务判断全部塞进 API Client
```

API Client 只负责：

```text
请求参数转换
请求发送
响应解析
错误转换
超时处理
基础重试
```

业务编排仍由 Controller / Service / Backend 完成。

### 5. 后端进程管理原则

本地内置模式下，GUI 可以负责启动后端子进程。

要求：

```text
后端服务启动逻辑放在 desktop/app/processes/backend_process.py
GUI 启动时检查端口和健康状态
如未启动，则启动本地 FastAPI 子进程
后端 ready 后再启用主功能
关闭 GUI 时优雅关闭后端
后端日志写入 data/logs/
```

禁止：

```text
在 GUI 主线程中直接运行 uvicorn.run()
无健康检查就启用主界面
不处理端口占用
关闭 GUI 后残留多个后端进程
```

## 五、后端代码原则

后端 FastAPI 仍按 API 服务组织。

1. 使用 APIRouter 分模块组织接口。
2. 使用 Pydantic 定义请求和响应模型。
3. API 路径统一使用 `/api` 前缀。
4. WebSocket 路径统一使用 `/ws` 前缀。
5. 业务逻辑进入 services 层。
6. 模型加载、缓存、释放、设备选择进入 runtime/model_manager。
7. 具体模型框架调用进入 runtime/adapters。
8. 模型 raw output 通过 parser 转换成 contracts 标准结构。
9. 配置项进入 core/config.py。
10. 路径解析进入 core/paths.py。
11. 错误处理和日志要统一。
12. 接口返回格式要统一。

Endpoint 只负责：

```text
接收请求
参数校验
调用 service
返回标准响应
```

Endpoint 禁止：

```text
直接加载模型
直接推理
直接写复杂业务逻辑
直接拼接模型路径
直接返回 raw output
```

## 六、通信与任务原则

### 1. 普通请求

适合：

```text
健康检查
配置读取
模型列表
模型状态
任务创建
结果查询
简单推理
```

使用 REST API。

### 2. 长任务

适合：

```text
模型加载
大文件处理
批量推理
长音频转写
视频处理
大模型推理
TTS 长文本合成
OCR 批量识别
```

推荐任务化：

```text
POST /api/tasks
GET /api/tasks/{task_id}
GET /api/tasks/{task_id}/result
WS /ws/tasks/{task_id}
```

或者：

```text
POST /api/inference
GET /api/inference/{task_id}
WS /ws/inference/{task_id}
```

### 3. 实时进度

推荐：

```text
WebSocket：双向通信、日志流、实时任务状态
SSE：单向事件推送、进度流
轮询：简单任务或兼容性优先场景
```

GUI 中监听 WebSocket / SSE 必须放到后台线程或专门的异步客户端中，不允许阻塞主线程。

## 七、线程与主线程原则

Qt 主线程只负责 UI。

必须后台化：

```text
HTTP 长请求
WebSocket 监听
SSE 监听
文件上传
文件下载
大文件读取
解压缩
转码
模型加载等待
推理结果等待
批量任务
日志读取
```

推荐方式：

```text
QThread + Worker QObject
QThreadPool + QRunnable
QProcess
```

Signal 用于线程间通信：

```text
progress_changed
status_changed
log_received
result_ready
error_occurred
finished
```

禁止：

```text
time.sleep() 阻塞 UI 主线程
while True 阻塞 UI 主线程
requests.post() 在按钮回调里长时间等待
在主线程里监听 WebSocket
在主线程里执行模型推理
```

## 八、跨平台原则

GUI 产品必须考虑 Windows / macOS / Linux。

### 1. 路径原则

1. 使用 `pathlib.Path`。
2. 所有路径由 paths 模块统一解析。
3. 不硬编码 `/home/xxx`。
4. 不硬编码 `D:/xxx`。
5. 不默认读取仓库父级或兄弟目录。
6. 不在 UI 中拼接模型路径。
7. 不在 API endpoint 中拼接模型路径。
8. 本地覆盖配置使用 `.env.local`、`local_settings.json`、`runtime/local_models.json` 等。

### 2. 配置原则

配置来源优先级建议：

```text
1. 用户界面显式配置
2. 本地覆盖配置 .env.local / local_settings.json
3. 环境变量
4. .env
5. 项目默认配置
```

### 3. 资源原则

GUI 资源统一放在：

```text
resources/icons/
resources/images/
resources/fonts/
resources/qss/
resources/app.qrc
```

样式统一放在：

```text
resources/qss/app.qss
```

不要在不同窗口中散落大量内联样式。

### 4. 设备原则

模型设备选择按平台处理：

```text
Windows：CPU / CUDA
Linux：CPU / CUDA
macOS：CPU / MPS，视模型框架支持情况而定
```

设备检测和选择逻辑进入 backend runtime，不进入 UI。

### 5. 编码原则

1. 默认 UTF-8。
2. 文件名显示要考虑中文路径。
3. 日志和导出文件要兼容中文。
4. 外部命令调用要处理路径空格和中文路径。

## 九、模型产品合同原则

当 GUI 产品涉及模型推理、OCR、ASR、TTS、LLM、多模态模型或其他运行时能力时，必须保留 contracts。

contracts 应定义：

```text
标准错误码
标准响应结构
模型状态
模型 readiness
任务状态
标准推理输入
标准推理输出
调试产物结构
```

推荐文件：

```text
shared/contracts/errors.py
shared/contracts/model.py
shared/contracts/inference.py
shared/contracts/tasks.py
shared/contracts/response.py
```

核心原则：

1. GUI 和 API 只依赖标准化结果，不依赖模型原始输出。
2. 模型配置、路径解析、readiness、运行时加载和推理结果必须有明确合同。
3. adapter / runtime 只处理模型事实、模型加载和推理。
4. service 负责业务编排。
5. raw output 只能作为调试、审计、问题排查产物，不默认暴露给 GUI 或外部 API。
6. 新增模型时，优先增加 adapter，而不是大改 GUI、API 或 service。
7. 模型未 ready 时，推理接口必须返回结构化错误。
8. GUI 根据错误码显示友好提示，不直接展示底层框架异常。

推荐 readiness 返回结构：

```json
{
  "model_id": "default",
  "available": true,
  "loaded": true,
  "ready": true,
  "device": "cuda",
  "path_valid": true,
  "last_error": null
}
```

推荐标准响应结构：

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

错误结构：

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "MODEL_NOT_READY",
    "message": "模型尚未加载",
    "detail": {}
  }
}
```

## 十、打包部署原则

### 1. 开发阶段

推荐：

```text
python -m backend.app.main
python -m desktop.app.main
```

或：

```text
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
python -m desktop.app.main
```

### 2. 内部测试阶段

推荐：

```text
PyInstaller
Nuitka
pyside6-deploy
```

### 3. 正式交付阶段

推荐目录式交付：

```text
MyApp/
├── MyApp.exe / MyApp.app / myapp
├── backend/
├── config/
├── models/
├── data/
├── resources/
└── README.md
```

不要强求：

```text
所有模型塞进单 exe
所有配置写死进程序
所有日志写入程序目录
不同平台使用同一套打包脚本
```

### 4. 平台差异

Windows：

```text
优先 PyInstaller / Nuitka
注意 VC++ Runtime、CUDA DLL、杀毒误报、路径空格
```

macOS：

```text
注意 .app、签名、公证、权限、MPS 支持、Gatekeeper
```

Linux：

```text
可用 venv + 启动脚本
必要时 AppImage / Nuitka
注意系统依赖、GL、音频、字体
```

## 十一、测试原则

至少覆盖：

```text
配置加载
路径解析
后端健康检查
API 响应结构
GUI API Client
后端进程启动与关闭
模型 readiness
模型未加载错误
任务创建与状态流转
raw output 不默认暴露
跨平台路径兼容
```

推荐测试目录：

```text
tests/backend/
tests/desktop/
tests/integration/
```

GUI 测试不一定一开始追求复杂自动化，但核心业务、API Client、路径和 contracts 必须测试。

## 十二、Agent 决策要求

在开始实现 GUI 项目前，请先判断：

1. 当前项目属于：
   - 小型本地工具
   - 本地 AI GUI
   - 标准客户交付桌面产品
   - 远程服务型桌面客户端
   - 复杂桌面平台
2. 是否需要 FastAPI。
3. 是否使用本地内置 FastAPI。
4. 是否需要远程 FastAPI。
5. 是否需要 WebSocket / SSE。
6. 是否需要后台任务和任务队列。
7. 是否需要模型 runtime 和 readiness。
8. 是否需要跨平台打包。
9. 是否需要模型外置。
10. 是否需要 GUI + Web 双入口。
11. 当前阶段最小可行、最稳妥的技术组合是什么。

默认判断：

```text
简单工具：PySide6 + services/runtime
标准产品：PySide6 + Local FastAPI
企业共享：PySide6 Client + Remote FastAPI
```

## 十三、禁止事项

1. 不要把模型推理写进按钮回调。
2. 不要在 UI 主线程执行长任务。
3. 不要在 UI 文件中直接写大量 HTTP 请求。
4. 不要让 GUI 直接依赖模型 raw output。
5. 不要让 API 默认返回 raw output。
6. 不要硬编码本机模型路径。
7. 不要默认读取仓库父级或兄弟目录作为模型目录。
8. 不要把业务逻辑全部塞进 `main_window.py`。
9. 不要把所有窗口、状态、请求都写进 `main.py`。
10. 不要无健康检查就启动主功能。
11. 不要不处理端口占用。
12. 不要关闭 GUI 后残留后端进程。
13. 不要强求单文件 exe。
14. 不要把模型大文件、日志、缓存、输出默认提交到 Git。
15. 不要为了“现代感”盲目引入 Electron / Tauri / Vue / React。
16. 不要默认使用 QML，除非确实需要高度动画化或触摸式界面。

## 十四、最终原则

GUI 产品优先选择：

```text
PySide6 + FastAPI + Contracts + Runtime + QSS
```

其中：

```text
PySide6 负责桌面界面
FastAPI 负责后端服务
Contracts 负责稳定输入输出
Runtime 负责模型生命周期
Services 负责业务编排
QSS 负责桌面样式
```

目标是：

```text
跨平台
易交付
可维护
可扩展
可服务化
可从桌面产品扩展到 Web/API 产品
```
