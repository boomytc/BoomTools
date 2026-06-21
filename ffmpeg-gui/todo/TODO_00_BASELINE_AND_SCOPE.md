# TODO 00: 基线、范围与终态确认

## 目标

在开始结构重构前，明确当前 UI 基线、目标终态、非目标和删除策略。开发阶段允许大幅重构，因此本阶段的重点是防止后续产生兼容性旧内容冗余。

## 当前基线

需要确认并记录以下现状：

- 已确认：`desktop/app/ui/main_window.py` 负责主窗口 masthead、运行时内容选择、操作区域、命令预览和任务队列的整体组织；后续需要将主内容布局收敛到单一 layout host。
- 已确认：`desktop/app/ui/panels/runtime_panel.py` 承载内容选择、拖拽入口、批量文件摘要和输出目录选择；其中标题行和面板边距仍为手写结构。
- 已确认：`desktop/app/ui/widgets/operation_form.py` 同时承载处理动作、参数表单、Stack toggle、字段控件创建和字段值收集；后续应拆为 selector、parameter form 和 field factory。
- 已确认：`desktop/app/ui/panels/task_panel.py` 承载任务队列、总进度、处理按钮和表格事件；表格已经使用 model/view/delegate，但 header/actions 仍为手写结构。
- 已确认：`desktop/app/ui/widgets/path_picker.py` 是路径选择复合控件；组件只发出 browse intent，不持有文件对话框策略。
- 已确认：`desktop/app/ui/delegates/task_delegates.py` 是任务表绘制入口；状态、进度、媒体摘要和移除按钮渲染都应继续停留在 delegate 层。
- 已确认：`resources/qss/app.qss` 是唯一 QSS 入口；当前仍存在 `QGroupBox#operationGroup`、`QGroupBox#parameterGroup` 等待迁移删除的旧 selector。

## 重复 UI 模式记录

进入 `components/` 的重复模式：

- 面板外壳：标题、说明、右侧 actions、统一 density、统一边距和动态属性。
- 分段切换：`QButtonGroup + checkable QPushButton`，用于单操作 / Stack 链式等互斥模式。
- 动作按钮条：主按钮、危险按钮、弱按钮、紧凑按钮的创建和间距。
- 固定滚动区域：关闭水平滚动、保留右侧 gutter、稳定高度。
- 表单小节：小节标题、`QFormLayout` 对齐、字段最大宽度和空态说明。

保留在产品级 panel/widget 的模式：

- `MediaDropArea` 的点击、键盘和拖拽行为。
- `OperationSelector` 的 operation 可用性、tooltip 和批处理禁用状态。
- `OperationParameterForm` 的字段 collect、媒体默认值应用和额外输入收集。
- `TaskPanel` 的任务按钮启用规则、总进度摘要、表格点击和右键菜单。
- `CommandPreviewPanel` 的命令复制和批量模板文案。
- `StackPanel` 的 Stack 项目管理信号和状态说明。

## 测试迁移范围

- 新增 `tests/desktop/test_ui_components.py` 覆盖基础组件。
- 新增或更新 `tests/desktop/test_runtime_panel.py`、`tests/desktop/test_operation_selector.py`、`tests/desktop/test_operation_parameter_form.py`、`tests/desktop/test_main_window_layout.py`。
- 更新 `tests/desktop/test_operation_panel_layout.py`、`tests/desktop/test_task_panel.py`、`tests/desktop/test_task_table_model.py` 中仍引用旧内部结构的断言。
- 保留 controller、service、runtime 测试作为行为回归，不为旧 UI 内部结构保留兼容断言。

## 唯一目标结构

采用以下唯一结构，不保留旧结构兼容：

```text
desktop/app/ui/components/
├── __init__.py
├── panel.py
├── segmented_toggle.py
├── action_bar.py
├── scroll_area.py
└── form_section.py
```

允许后续根据真实需求新增：

```text
desktop/app/ui/layouts/
desktop/app/ui/state/
```

但本阶段不创建空目录。

## 非目标

- 不实现拖拽布局。
- 不实现布局预设保存。
- 不引入 Qt Designer `.ui` 文件。
- 不引入 QML。
- 不做跨项目 Python 包发布。
- 不做 Web、FastAPI 或远程 UI。
- 不做兼容旧 panel 构造参数的 wrapper。

## 必做清单

- [x] 审查 `ui/panels/`、`ui/widgets/`、`ui/delegates/` 的当前职责。
- [x] 列出重复 UI 模式：标题区域、右侧 actions、toggle、固定滚动区域、表单小节。
- [x] 确认哪些重复模式进入 `components/`。
- [x] 确认哪些仍留在产品级 panel/widget。
- [x] 确认所有阶段都直接替换旧实现。
- [x] 确认测试文件的迁移范围。

## 删除策略

每次迁移完成后必须删除：

- 被新组件完全替代的 helper 函数。
- 旧 objectName 对应的 QSS selector。
- 只服务旧布局的测试断言。
- 临时属性、临时 wrapper、临时 compatibility branch。

不允许保留：

- `LegacyPanel`
- `OldOperationForm`
- `compat_*`
- `deprecated_*`
- “以后可能用”的空 helper

## 验收标准

- 根 `TODO.md` 和阶段文件完整。
- 阶段边界清晰，不包含实现期不需要的泛化目标。
- 每个阶段都有删除策略和验证命令。
- 无需运行完整测试；本阶段只需文档检查和 `git diff --check`。

## 验证命令

```bash
git diff --check
```

## 完成状态

- [ ] 未开始
- [ ] 进行中
- [x] 已完成
