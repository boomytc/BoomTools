# TODO 02: 现有 Panel 迁移到统一结构

## 目标

将当前产品级区域迁移到 `components.PanelFrame` 等组件上，删除重复的 header、actions、边距和布局样板。

## 迁移对象

- `desktop/app/ui/panels/runtime_panel.py`
- `desktop/app/ui/widgets/operation_form.py`
- `desktop/app/ui/panels/task_panel.py`
- `desktop/app/ui/panels/command_preview_panel.py`
- `desktop/app/ui/panels/stack_panel.py`

## 迁移顺序

### 1. RuntimePanel

目标：

- 使用 `PanelFrame(title="内容选择")`。
- 保留 `MediaDropArea` 为产品级拖拽控件。
- 输出目录行作为 body 内部内容。

删除：

- 手写 `header_row`。
- 重复 `sectionTitle` label 创建代码。
- 只服务旧 layout 的 spacing/margin 分支。

验收：

- 内容选择区域高度不回弹。
- 点击/拖入行为不变。
- 输出目录选择按钮仍在目标目录同一行。

### 2. OperationFormWidget 外层

目标：

- 处理动作区域使用 `PanelFrame`。
- 参数区域使用 `PanelFrame`。
- 面板标题不再靠 `QGroupBox` 或手写重复结构。

删除：

- `operation_group = QGroupBox()` 旧面板外壳。
- `parameters_group = QGroupBox()` 旧面板外壳。
- `QGroupBox#operationGroup`、`QGroupBox#parameterGroup` 特例 QSS。

验收：

- 处理动作和参数区域标题、边距一致。
- Stack 模式不导致区域高度跳动。
- 内滚动仍生效。

### 3. TaskPanel

目标：

- 使用 `PanelFrame(title="任务队列")`。
- header actions 使用 `PanelActionBar`。
- 总进度使用 `PanelFrame` 的 description 或 body header 子行。

删除：

- 手写 `title_block`。
- 手写 `button_row`。
- 重复按钮间距。

验收：

- 任务统计和进度在标题下方。
- 右侧按钮组独立。
- 任务表高度和列宽不受影响。

### 4. CommandPreviewPanel

目标：

- 使用 `PanelFrame(title="命令预览")`。
- 复制按钮作为 action。
- 输入框作为 body 内容。

删除：

- 重复外层 QFrame header 结构。

验收：

- 命令预览仍可复制。
- 空态 placeholder 不变。

### 5. StackPanel

目标：

- 使用 `PanelFrame(title="Stack 队列")`。
- Stack 操作按钮使用 `PanelActionBar`。

删除：

- 旧 QGroupBox 标题结构。

验收：

- Stack 模式切换后区域高度稳定。
- 不支持当前操作时说明明确。

## 不做事项

- 不改变 controller signal。
- 不改变 task model。
- 不改变 ffmpeg command builder。
- 不引入兼容旧构造函数。

## 测试要求

更新或新增：

- `tests/desktop/test_operation_panel_layout.py`
- `tests/desktop/test_task_panel.py`
- `tests/desktop/test_runtime_panel.py` 如不存在则创建。

覆盖：

- [ ] 每个 panel 使用新组件。
- [ ] 各区域标题和 actions 存在。
- [ ] 核心信号仍可触发。
- [ ] 旧 `QGroupBox` 特例不再存在。

## 验收标准

- 产品级 panel 代码明显变薄。
- 重复 header/actions 结构集中在 components。
- 删除旧 QSS 特例。
- 无 compatibility wrapper。

## 验证命令

```bash
python3 -m compileall ffmpeg-gui/desktop ffmpeg-gui/shared ffmpeg-gui/tests
.venv/bin/python -m pytest tests/desktop/test_operation_panel_layout.py tests/desktop/test_task_panel.py
.venv/bin/python -m pytest
git diff --check
```

## 完成状态

- [ ] 未开始
- [ ] 进行中
- [ ] 已完成
