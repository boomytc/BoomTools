# GUI通用项目目录规范

本文件是通用 GUI 项目目录规范。标准模型产品、客户交付产品、需要 API 复用或远程访问的产品，可以采用 **PySide6 + FastAPI 混合架构**。  
`ffmpeg-gui` 当前阶段是纯本机工具基线：以 `AGENTS.md` 为最高优先级，采用 **PySide6 + Qt Widgets + QSS + services/runtime + contracts**，不默认创建 `backend/`、`clients/`、`processes/backend_process.py` 或 HTTP 上传目录。

## ffmpeg-gui 当前目录基线

```text
ffmpeg-gui/
├── desktop/app/
│   ├── main.py
│   ├── bootstrap.py
│   ├── core/
│   ├── ui/
│   │   ├── components/
│   │   ├── delegates/
│   │   ├── dialogs/
│   │   ├── layouts/
│   │   ├── panels/
│   │   ├── widgets/
│   │   └── main_window.py
│   ├── controllers/
│   ├── services/
│   ├── runtime/
│   ├── tasks/
│   └── utils/
├── shared/contracts/
├── resources/qss/app.qss
├── data/
├── docs/
├── tests/
├── requirements.txt
├── README.md
└── AGENTS.md
```

`desktop/app/ui/components/` 只放通用 GUI 结构件：`PanelFrame`、`SegmentedToggle`、`PanelActionBar`、`FixedScrollArea`、`FormSection`。产品级组合留在 `panels/` 和 `widgets/`，表格绘制留在 `delegates/`，主内容布局宿主留在 `layouts/`。

不默认增加 `deploy/` 目录。部署、依赖、工程配置、打包配置优先参考 `pyproject.toml`。  
如后续确实需要 Docker、Nginx、systemd、AppImage、安装包脚本，再按需新增。

标准 PySide6 + FastAPI 产品目录结构如下。仅在触发服务化/API 复用需求时使用，不作为 `ffmpeg-gui` 当前默认结构：

```text
project-name/
├── desktop/
│   └── app/
│       ├── main.py
│       ├── bootstrap.py
│       ├── core/
│       │   ├── config.py
│       │   ├── paths.py
│       │   ├── logging.py
│       │   └── constants.py
│       ├── ui/
│       │   ├── main_window.py
│       │   ├── pages/
│       │   ├── dialogs/
│       │   ├── widgets/
│       │   ├── delegates/
│       │   └── resources_rc.py
│       ├── controllers/
│       │   ├── main_controller.py
│       │   └── inference_controller.py
│       ├── viewmodels/
│       │   ├── app_state.py
│       │   ├── model_state.py
│       │   └── task_state.py
│       ├── clients/
│       │   ├── api_client.py
│       │   ├── websocket_client.py
│       │   └── sse_client.py
│       ├── processes/
│       │   └── backend_process.py
│       ├── tasks/
│       │   ├── worker.py
│       │   ├── task_manager.py
│       │   └── signals.py
│       └── utils/
│           ├── file_utils.py
│           └── qt_utils.py
│
├── backend/
│   └── app/
│       ├── main.py
│       ├── api/
│       │   ├── router.py
│       │   └── endpoints/
│       │       ├── health.py
│       │       ├── models.py
│       │       ├── inference.py
│       │       ├── tasks.py
│       │       └── files.py
│       ├── core/
│       │   ├── config.py
│       │   ├── paths.py
│       │   ├── logging.py
│       │   └── security.py
│       ├── schemas/
│       │   └── common.py
│       ├── services/
│       │   ├── inference_service.py
│       │   ├── task_service.py
│       │   ├── file_service.py
│       │   └── export_service.py
│       ├── runtime/
│       │   ├── catalog.py
│       │   ├── model_manager.py
│       │   └── adapters/
│       ├── workers/
│       │   └── task_worker.py
│       └── utils/
│           └── file_utils.py
│
├── shared/
│   └── contracts/
│       ├── errors.py
│       ├── response.py
│       ├── model.py
│       ├── inference.py
│       └── tasks.py
│
├── resources/
│   ├── icons/
│   ├── images/
│   ├── fonts/
│   ├── qss/
│   │   └── app.qss
│   └── app.qrc
│
├── data/
│   ├── uploads/
│   ├── outputs/
│   ├── temp/
│   ├── cache/
│   ├── debug/
│   ├── logs/
│   └── db/
│
├── docs/
│   ├── 使用说明.md
│   ├── 接口说明.md
│   ├── 开发说明.md
│   └── 打包说明.md
│
├── tests/
│   ├── backend/
│   │   └── test_health.py
│   ├── desktop/
│   │   └── test_api_client.py
│   └── integration/
│       └── test_desktop_backend_health.py
│
├── scripts/
│   ├── init_project.py
│   ├── start_backend.py
│   ├── check_env.py
│   ├── download_models.py
│   ├── clean_outputs.py
│   └── build_app.py
│
├── assets/
├── pyproject.toml
├── README.md
├── AGENTS.md
├── .env.example
└── .gitignore
```

## 一、总体原则

1. `desktop/` 和 `backend/` 必须分离。
2. 桌面端使用 PySide6，不使用 Web 前端作为默认 GUI。
3. 后端使用 FastAPI，只提供 JSON API / WebSocket / SSE。
4. 桌面端通过 API Client 调用 FastAPI，不直接耦合后端内部模块。
5. 标准产品默认采用本地内置 FastAPI；可按需切换为远程 FastAPI。
6. UI 层不直接加载模型、不直接推理、不直接解析 raw output。
7. 模型加载、缓存、释放、readiness、设备选择进入 backend runtime。
8. 标准输入输出、错误码、任务状态、模型状态进入 shared/contracts。
9. 所有路径统一通过 paths 模块解析，不允许硬编码个人机器路径。
10. 跨平台优先，目录和代码必须兼容 Windows / macOS / Linux。
11. 不默认增加 `deploy/` 目录；确实需要 Docker、systemd、Nginx、安装包脚本时再新增。
12. 以 `pyproject.toml` 作为依赖、测试、格式化、打包和启动命令的主要配置入口。
13. 不默认引入 Electron / Tauri / Vue / React / QML。

## 二、desktop/ 桌面端目录职责

### desktop/app/main.py

PySide6 桌面端入口。

负责：

```text
创建 QApplication
加载基础配置
加载 QSS
创建主窗口
初始化 bootstrap
进入 Qt 事件循环
```

不要在 `main.py` 中写：

```text
模型推理
复杂业务逻辑
大量 API 请求
后端启动细节
复杂状态管理
```

### desktop/app/bootstrap.py

桌面端启动编排。

负责：

```text
初始化配置
初始化日志
初始化 API Client
初始化 BackendProcess
检查后端健康状态
初始化 Controller
初始化 ViewModel
连接 UI 与 Controller
```

本地内置模式下，bootstrap 可以协调启动 FastAPI 子进程，但具体进程控制应放到 `processes/backend_process.py`。

### desktop/app/core/

桌面端基础能力目录。

默认包含：

```text
config.py
paths.py
logging.py
constants.py
```

职责：

```text
桌面端配置
GUI 资源路径
QSS 路径
图标路径
客户端 API 地址
本地用户配置路径
桌面端日志初始化
应用常量
```

注意：

- 桌面端路径主要处理 GUI 资源和客户端配置。
- 后端数据、模型、上传、输出路径由 backend/app/core/paths.py 负责。
- 跨平台路径统一使用 `pathlib.Path`。

### desktop/app/ui/

UI 层目录，只负责窗口、页面、控件和样式挂载。

默认包含：

```text
main_window.py
pages/
dialogs/
widgets/
delegates/
resources_rc.py
```

职责：

```text
窗口布局
控件创建
页面切换
弹窗
表格代理
自定义组件
图标资源引用
基础信号绑定
```

禁止：

```text
直接调用模型
直接调用 backend service
直接执行耗时任务
直接写复杂 HTTP 请求
直接解析模型 raw output
直接保存大量业务数据
```

### desktop/app/ui/main_window.py

主窗口。

适合包含：

```text
菜单栏
工具栏
状态栏
主页面容器
日志区域
任务状态区域
模型状态区域
```

不要把所有页面逻辑、任务逻辑和 API 请求都写进 `main_window.py`。

### desktop/app/ui/pages/

页面目录。

根据产品可增加：

```text
home_page.py
inference_page.py
models_page.py
tasks_page.py
settings_page.py
result_page.py
logs_page.py
```

页面只负责当前页面布局和用户操作入口。

### desktop/app/ui/dialogs/

弹窗目录。

适合：

```text
settings_dialog.py
about_dialog.py
model_path_dialog.py
export_dialog.py
error_dialog.py
```

### desktop/app/ui/widgets/

自定义组件目录。

适合：

```text
file_drop_area.py
progress_card.py
model_status_badge.py
log_viewer.py
result_table.py
audio_player.py
image_preview.py
```

### desktop/app/ui/delegates/

Qt View Delegate 目录。

适合：

```text
table_button_delegate.py
progress_delegate.py
status_badge_delegate.py
```

### desktop/app/controllers/

Controller 层。

职责：

```text
接收 UI 事件
读取 ViewModel 状态
校验用户输入
调用 API Client
启动后台任务
处理回调
更新 ViewModel
触发 UI 刷新
```

默认包含：

```text
main_controller.py
inference_controller.py
```

根据需求可新增：

```text
model_controller.py
task_controller.py
settings_controller.py
file_controller.py
export_controller.py
```

禁止：

```text
在 Controller 中直接加载模型
在 Controller 中写大量后端业务逻辑
在 Controller 中硬编码后端地址
在 Controller 中直接拼接模型路径
```

### desktop/app/viewmodels/

页面状态和应用状态目录。

默认包含：

```text
app_state.py
model_state.py
task_state.py
```

适合放：

```text
当前 API 地址
当前后端状态
当前模型状态
当前任务状态
按钮启用状态
进度状态
日志状态
结果状态
错误状态
```

原则：

- UI 读写 ViewModel。
- Controller 更新 ViewModel。
- 不要让多个页面重复维护同一份状态。

### desktop/app/clients/

API 客户端目录。

默认包含：

```text
api_client.py
websocket_client.py
sse_client.py
```

职责：

```text
统一封装 REST API 请求
统一封装 WebSocket 连接
统一封装 SSE 事件流
处理超时
处理基础重试
处理响应结构
转换错误
```

禁止：

```text
在 UI 文件中直接写 requests/httpx
在多个页面里重复拼接 URL
在 API Client 中写复杂业务编排
```

推荐：

```text
api_client.py
- health()
- list_models()
- get_model_status(model_id)
- load_model(model_id)
- unload_model(model_id)
- create_task(payload)
- get_task(task_id)
- get_task_result(task_id)
- infer(payload)
- upload_file(path)
- download_file(file_id)
```

### desktop/app/processes/

本地后端进程管理目录。

默认包含：

```text
backend_process.py
```

职责：

```text
检查后端是否已启动
查找可用端口
启动 FastAPI 子进程
轮询 /api/health
捕获后端 stdout/stderr
写入日志
优雅关闭后端
异常退出检测
```

禁止：

```text
在 GUI 主线程中直接 uvicorn.run()
关闭 GUI 后残留后端进程
不处理端口占用
不做健康检查
```

### desktop/app/tasks/

桌面端后台任务目录。

默认包含：

```text
worker.py
task_manager.py
signals.py
```

职责：

```text
QThread Worker
QThreadPool 任务
后台 HTTP 请求
WebSocket/SSE 监听
文件上传下载
日志读取
进度回调
错误回调
任务取消
```

Signal 建议：

```text
progress_changed
status_changed
log_received
result_ready
error_occurred
finished
```

### desktop/app/utils/

桌面端通用工具。

适合放：

```text
文件选择辅助
Qt 辅助函数
图标加载
时间格式化
窗口居中
消息提示
```

不要把业务逻辑放进 `utils/`。

## 三、backend/ 后端目录职责

后端采用 FastAPI，职责与 Web 产品中的 backend 类似，但服务对象是桌面端和可能的远程客户端。

### backend/app/main.py

FastAPI 应用入口。

负责：

```text
创建 FastAPI app
注册 API router
注册中间件
注册异常处理
初始化日志
初始化 runtime
```

不要在 `main.py` 中写复杂业务逻辑。

### backend/app/api/

接口层，只负责请求入口。

职责：

```text
接收请求
参数校验
调用 service
返回标准响应
```

禁止：

```text
在 endpoint 中直接加载模型
在 endpoint 中直接推理
在 endpoint 中解析模型 raw output
在 endpoint 中硬编码模型路径
在 endpoint 中拼接大量业务结果
```

### backend/app/api/router.py

统一注册接口路由。

路径建议：

```text
/api/...
/ws/...
```

### backend/app/api/endpoints/

默认包含：

```text
health.py
models.py
inference.py
tasks.py
files.py
```

根据需求可新增：

```text
settings.py
auth.py
export.py
logs.py
devices.py
```

推荐接口：

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
POST /api/files/upload
GET  /api/files/{file_id}/download
WS   /ws/tasks/{task_id}
```

### backend/app/core/

后端基础能力目录。

默认包含：

```text
config.py
paths.py
logging.py
security.py
```

职责：

```text
配置读取
环境变量解析
路径解析
日志配置
异常配置
安全配置
应用常量
本地服务绑定地址
CORS / Token 配置
```

### backend/app/core/config.py

负责后端配置。

包括：

```text
应用名称
运行环境
API 前缀
绑定 host / port
CORS 配置
本地 token
模型默认配置
文件大小限制
任务参数
是否开启 debug
```

本地内置模式默认：

```text
host = 127.0.0.1
```

不要默认绑定：

```text
0.0.0.0
```

除非用户明确需要局域网或远程访问。

### backend/app/core/paths.py

统一路径解析。

必须管理：

```text
上传目录
输出目录
临时目录
缓存目录
debug 目录
日志目录
数据库目录
模型目录
配置目录
```

路径来源优先级建议：

```text
1. GUI 用户显式配置
2. 本地覆盖配置 .env.local / local_settings.json / runtime/local_models.json
3. 环境变量
4. .env
5. 项目默认配置
```

禁止：

```text
硬编码 /home/xxx/models
硬编码 D:/models
默认读取仓库父级目录
默认读取仓库兄弟目录
在 endpoint 中拼接模型路径
在 GUI 中把本机绝对模型路径作为默认方案写死
```

### backend/app/schemas/

Pydantic 请求和响应模型目录。

适合放：

```text
API 请求参数
API 响应结构
分页结构
表单结构
上传结构
设置结构
```

如果是桌面端和后端共享的稳定结构，应优先放到 `shared/contracts/`。

### backend/app/services/

业务逻辑层。

职责：

```text
业务编排
调用 runtime / model_manager
处理任务流程
处理文件流转
处理导出
组合标准化结果
返回产品级响应
```

禁止：

```text
在 service 中硬编码模型路径
在 service 中直接返回 raw output 给 API
在 service 中写大量具体模型框架细节
```

### backend/app/runtime/

运行时资源管理目录，尤其适合模型产品。

默认包含：

```text
catalog.py
model_manager.py
adapters/
```

职责：

```text
模型加载
模型卸载
模型缓存
模型 readiness
设备选择 CPU / CUDA / MPS
推理实例管理
模型目录管理
adapter 管理
raw output 调试产物保存
```

### backend/app/runtime/catalog.py

模型目录和模型配置注册。

职责：

```text
管理可用模型列表
暴露模型名称、版本、类型、能力、默认路径、运行设备、依赖要求
读取模型配置
```

不直接执行推理。

### backend/app/runtime/model_manager.py

模型生命周期管理。

职责：

```text
load_model
unload_model
get_model
is_ready
get_status
warmup
release
reload
```

模型加载、缓存、单例、显存释放、设备选择等逻辑必须放在这里，不要写进 API endpoint。

### backend/app/runtime/adapters/

具体模型适配器目录。

例如：

```text
runtime/adapters/ppocr/
runtime/adapters/sensevoice/
runtime/adapters/qwen/
runtime/adapters/faster_whisper/
runtime/adapters/custom_model/
```

每个 adapter 内部可包含：

```text
adapter.py
config.py
parser.py
```

职责：

```text
adapter.py
- 调用具体模型框架
- 执行推理
- 返回模型原始输出或中间结构

config.py
- 定义该模型运行配置
- 定义默认参数
- 定义设备和精度相关选项

parser.py
- 将模型原始输出转换成 shared/contracts 定义的标准化结果
```

### backend/app/workers/

后端任务执行目录。

适合：

```text
后台推理任务
批量任务
任务队列
长文件处理
可取消任务
任务状态更新
```

小项目可以先不用复杂队列；但任务状态和任务取消机制应预留。

### backend/app/utils/

后端通用工具。

适合放：

```text
文件工具
时间工具
字符串工具
哈希工具
格式转换
临时文件清理
```

不要把业务逻辑放进 `utils/`。

## 四、shared/contracts/ 合同目录职责

`shared/contracts/` 用于定义桌面端和后端共同认可的产品级输入输出结构。

默认包含：

```text
errors.py
response.py
model.py
inference.py
tasks.py
```

职责：

```text
标准错误码
标准响应结构
模型状态
readiness 结构
任务状态
推理输入结构
推理输出结构
调试产物结构
```

推荐职责：

```text
errors.py
- ErrorCode
- AppError
- ModelLoadError
- ModelPathError
- ModelNotReadyError
- InferenceError
- BackendUnavailableError

response.py
- ApiResponse
- ErrorResponse
- PageResponse

model.py
- ModelStatus
- ModelInfo
- ModelReadiness
- DeviceInfo
- RuntimeInfo

inference.py
- StandardInferenceInput
- StandardInferenceResult
- InferenceMeta
- DebugArtifact

tasks.py
- TaskStatus
- TaskInfo
- TaskProgress
- TaskEvent
```

原则：

1. GUI 和 API 都只依赖标准化结果。
2. 模型 raw output 不进入 GUI 主流程。
3. 新增模型优先新增 adapter，不修改 GUI 主流程。
4. API 返回结构必须稳定。
5. 后续如增加 WebUI，也复用同一套 contracts。

## 五、resources/ GUI 资源目录

GUI 静态资源目录。

默认包含：

```text
icons/
images/
fonts/
qss/app.qss
app.qrc
```

职责：

```text
图标
图片
字体
QSS 样式
Qt Resource 文件
```

要求：

1. QSS 统一放在 `resources/qss/app.qss`。
2. 图标统一放在 `resources/icons/`。
3. 图片统一放在 `resources/images/`。
4. 不要在各窗口里散落大量内联样式。
5. 可使用 `pyside6-rcc` 将 `app.qrc` 编译为 `desktop/app/ui/resources_rc.py`。
6. 不要分享或外传系统字体文件。

## 六、data/ 运行数据目录

运行数据和代码目录必须分离。

默认包含：

```text
data/
├── uploads/
├── outputs/
├── temp/
├── cache/
├── debug/
├── logs/
└── db/
```

职责：

```text
uploads/   上传或导入文件
outputs/   输出结果
temp/      临时文件
cache/     缓存
debug/     raw output 调试产物
logs/      桌面端和后端日志
db/        本地数据库
```

注意：

- `backend/app/runtime/` 是代码层运行时管理。
- `data/` 是数据层运行产物。
- 二者不要混淆。
- `data/` 下运行产物通常不提交到 Git。
- 可提交必要示例文件，但必须明确放在 `assets/examples/` 或文档中说明。

## 七、docs/ 文档目录

默认至少保留：

```text
使用说明.md
接口说明.md
开发说明.md
打包说明.md
```

根据需要可增加：

```text
模型说明.md
安装说明.md
测试说明.md
常见问题.md
故障排查.md
客户交付说明.md
```

推荐职责：

```text
使用说明.md      给最终用户
接口说明.md      给 API 调用者和 GUI/API 联调
开发说明.md      给开发者和 Agent
打包说明.md      给交付人员
模型说明.md      说明模型路径、设备、能力、限制
故障排查.md      说明端口占用、模型加载失败、依赖缺失等问题
```

## 八、tests/ 测试目录

推荐结构：

```text
tests/
├── backend/
├── desktop/
└── integration/
```

至少覆盖：

```text
后端健康检查
配置加载
路径解析
API 响应结构
模型 readiness
模型未加载错误
raw output 不默认暴露
API Client 请求封装
后端进程启动与关闭
GUI 与后端健康检查联通
跨平台路径兼容
```

推荐文件：

```text
tests/backend/test_health.py
tests/backend/test_paths.py
tests/backend/test_model_readiness.py
tests/backend/test_inference_api.py
tests/backend/test_raw_output_policy.py
tests/desktop/test_api_client.py
tests/desktop/test_backend_process.py
tests/integration/test_desktop_backend_health.py
```

GUI 的视觉自动化测试可以后续补充，不要一开始为了自动化测试牺牲项目推进。  
但 contracts、API、路径、readiness 必须优先测试。

## 九、scripts/ 脚本目录

辅助脚本目录。

适合放：

```text
init_project.py
start_backend.py
check_env.py
download_models.py
prepare_data.py
clean_outputs.py
build_app.py
package_windows.py
package_macos.py
package_linux.py
```

职责：

```text
初始化项目
启动本地后端
检查环境
下载模型
准备数据
清理输出
桌面端打包
平台打包
```

不要把关键业务逻辑写进 scripts。  
scripts 应服务于开发、部署、测试和交付。

## 十、assets/ 示例素材目录

根目录 `assets/` 用于存放项目级示例素材、演示资源和说明素材。

例如：

```text
assets/examples/
assets/images/
assets/audio/
assets/docs/
assets/videos/
```

注意：

- GUI 运行资源放 `resources/`。
- 项目示例素材放 `assets/`。
- 前端 Web 资源不是默认项；只有同时提供 WebUI 时才新增 `frontend/`。
- 不要把运行输出误放进 assets。

## 十一、pyproject.toml

`pyproject.toml` 是 Python 项目的主要工程配置和部署参考。

可用于管理：

```text
项目信息
Python 版本
依赖
可选依赖
启动命令
测试配置
格式化配置
lint 配置
打包配置
PyInstaller / Nuitka 辅助配置
```

建议依赖分组：

```text
base        FastAPI / Pydantic / Uvicorn
desktop     PySide6
dev         pytest / ruff / mypy
packaging   pyinstaller / nuitka
model       torch / onnxruntime / transformers 等按需
```

小型项目不强制额外维护 `requirements.txt`。  
如果客户部署环境明确要求 `requirements.txt`，可由 `pyproject.toml` 导出生成。

## 十二、AGENTS.md

`AGENTS.md` 用于记录 Agent 开发规范。

应包含：

```text
GUI 技术架构原则
PySide6 / FastAPI 边界
目录结构规范
桌面端代码规则
后端 API 规则
模型产品合同
跨平台要求
打包要求
测试要求
禁止事项
常用命令
```

Agent 在开发前应优先阅读并遵守 `AGENTS.md`。

## 十三、可按需新增的目录

项目复杂度提升后，可增加：

```text
backend/app/models/
backend/app/repositories/
backend/app/db/
backend/app/migrations/
backend/app/security/
backend/app/tasks/
desktop/app/services/
desktop/app/plugins/
desktop/app/themes/
desktop/app/shortcuts/
installer/
```

使用场景：

```text
backend/app/models/          数据库 ORM 模型
backend/app/repositories/   数据库访问封装
backend/app/db/             数据库连接和会话管理
backend/app/migrations/     数据库迁移
backend/app/security/       认证、鉴权、权限
backend/app/tasks/          后端任务编排
desktop/app/services/       仅桌面端本地服务，不涉及后端业务
desktop/app/plugins/        插件体系
desktop/app/themes/         多主题
desktop/app/shortcuts/      快捷键管理
installer/                  安装包脚本，确实需要时再增加
```

不要在项目初期盲目增加大量目录，应根据真实需求逐步扩展。

## 十四、推荐本地运行命令

开发阶段：

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
python -m desktop.app.main
```

如果使用内置后端启动：

```bash
python -m desktop.app.main
```

环境检查：

```bash
python scripts/check_env.py
```

模型下载：

```bash
python scripts/download_models.py
```

清理输出：

```bash
python scripts/clean_outputs.py
```

打包：

```bash
python scripts/build_app.py
```

## 十五、模型产品推荐接口

推荐 API：

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
POST /api/files/upload
GET  /api/files/{file_id}/download
WS   /ws/tasks/{task_id}
```

readiness 返回结构建议：

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

API 标准返回结构：

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

错误返回结构：

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

## 十六、禁止事项

1. 不要把复杂业务逻辑写进 PySide6 UI 文件。
2. 不要把模型推理写进按钮回调。
3. 不要在 GUI 主线程执行长任务。
4. 不要在 UI 文件中到处写 HTTP 请求。
5. 不要让 GUI 直接依赖模型 raw output。
6. 不要让 API 默认返回 raw output。
7. 不要把复杂业务逻辑写进 FastAPI endpoint。
8. 不要硬编码本机模型路径。
9. 不要默认读取仓库父级或兄弟目录作为模型目录。
10. 不要关闭 GUI 后残留后端进程。
11. 不要无健康检查就启用主功能。
12. 不要不处理端口占用。
13. 不要默认绑定 `0.0.0.0`。
14. 不要强求单文件 exe。
15. 不要默认引入 Electron / Tauri / Vue / React / QML。
16. 不要把运行数据、缓存、日志、模型大文件默认提交到 Git。
17. 不要把 GUI 资源、示例素材、运行输出混在同一个目录。
18. 不要在项目初期盲目增加大量目录。

## 十七、核心固定骨架

无论项目大小，建议至少固定以下骨架：

```text
desktop/app/main.py
desktop/app/bootstrap.py
desktop/app/ui/
desktop/app/controllers/
desktop/app/viewmodels/
desktop/app/clients/api_client.py
desktop/app/processes/backend_process.py
desktop/app/tasks/
backend/app/main.py
backend/app/api/
backend/app/core/config.py
backend/app/core/paths.py
backend/app/schemas/
backend/app/services/
backend/app/runtime/
shared/contracts/
resources/qss/app.qss
resources/app.qrc
data/
docs/
tests/
scripts/
pyproject.toml
README.md
AGENTS.md
.env.example
.gitignore
```

其他目录根据真实需求再增加。
