# TODO 01: UI Components 基础层

## 目标

提取当前已经反复出现的 UI 模式，建立 `desktop/app/ui/components/`。这不是做通用 GUI 框架，而是把 `ffmpeg-gui` 中已经稳定的重复结构组件化。

## 新增目录

```text
desktop/app/ui/components/
├── __init__.py
├── panel.py
├── segmented_toggle.py
├── action_bar.py
├── scroll_area.py
└── form_section.py
```

## 组件边界

### PanelFrame

文件：`components/panel.py`

职责：

- 提供统一面板外壳。
- 支持标题、可选说明、可选右侧 actions。
- 提供内容 layout。
- 提供紧凑、标准两种 density。
- 设置稳定 objectName 和 dynamic property。

不做：

- 不承载业务状态。
- 不直接知道 ffmpeg operation。
- 不替代 `RuntimePanel`、`TaskPanel` 这类产品级 panel。
- 不内置拖拽布局。

建议 API：

```python
class PanelFrame(QFrame):
    def __init__(self, title: str, *, description: str = "", density: str = "compact") -> None: ...
    def add_action(self, widget: QWidget) -> None: ...
    def body_layout(self) -> QVBoxLayout: ...
```

### SegmentedToggle

文件：`components/segmented_toggle.py`

职责：

- 封装 `QButtonGroup + checkable QPushButton`。
- 对外暴露当前 value。
- 通过 signal 发出 value changed。
- 接入 `role="segmentButton"` QSS。

不做：

- 不关心 Stack 是否可用。
- 不关心 batch 模式。
- 不内置 operation 业务判断。

建议 API：

```python
class SegmentedToggle(QWidget):
    value_changed = Signal(str)
    def set_options(self, options: list[SegmentOption]) -> None: ...
    def value(self) -> str: ...
    def set_value(self, value: str) -> None: ...
```

### PanelActionBar

文件：`components/action_bar.py`

职责：

- 统一按钮组间距。
- 支持 primary、danger、quiet、compact 角色。
- 支持右对齐、左对齐。
- 返回按钮实例，调用方负责连接 signal。

不做：

- 不内置任务队列逻辑。
- 不判断 busy 状态。
- 不自动启停按钮。

### FixedScrollArea

文件：`components/scroll_area.py`

职责：

- 固定高度内滚动。
- 默认关闭水平滚动。
- 支持右侧 scrollbar gutter。
- 用于处理动作列表、参数内容等区域。

不做：

- 不自动生成内容。
- 不知道 operation 或参数字段。

### FormSection

文件：`components/form_section.py`

职责：

- 统一“小节标题 + QFormLayout”的结构。
- 统一 label alignment、field max width、spacing。
- 支持空态说明。

不做：

- 不负责解析参数。
- 不负责 ffmpeg options 合法性。

## QSS 要求

- 所有新组件通过 objectName 或 dynamic property 接入 `resources/qss/app.qss`。
- 不在组件 Python 代码中写颜色、边框、圆角样式。
- 可以在 Python 中设置 `setContentsMargins`、`setSpacing`、size policy。

## 测试要求

新增：

```text
tests/desktop/test_ui_components.py
```

覆盖：

- [ ] `PanelFrame` 标题、actions、body layout 可用。
- [ ] `SegmentedToggle` 单选、value changed、禁用态可用。
- [ ] `PanelActionBar` 能按 role 创建按钮。
- [ ] `FixedScrollArea` 无水平滚动、固定高度、gutter 生效。
- [ ] `FormSection` form layout 边距和 label 对齐稳定。

## 迁移限制

本阶段只创建组件和测试，不迁移产品 panel。这样可以先固定组件 API，避免边写边迁导致边界摇摆。

## 验收标准

- `desktop/app/ui/components/` 存在且有清晰导出。
- 组件没有引用 `shared.contracts.Operation`。
- 组件没有引用 ffmpeg runtime/service/controller。
- 组件测试通过。
- 无旧兼容层。

## 验证命令

```bash
python3 -m compileall ffmpeg-gui/desktop ffmpeg-gui/shared ffmpeg-gui/tests
.venv/bin/python -m pytest tests/desktop/test_ui_components.py
git diff --check
```

## 完成状态

- [ ] 未开始
- [ ] 进行中
- [ ] 已完成
