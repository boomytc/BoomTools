# TODO 04: 任务队列区域重建

## 目标

继续强化任务队列作为成熟 PySide6 model/view 示例的质量：模型只提供语义数据，delegate 负责展示，panel 负责布局和交互入口，controller 负责行为。

## 当前保留原则

- 继续使用 `QTableView + TaskTableModel + QStyledItemDelegate`。
- 不改为 table cell 内嵌 widget。
- 不把绘制逻辑写进 model。
- 不在 panel 中拼接业务状态文案之外的复杂数据。

## 结构目标

```text
desktop/app/ui/panels/task_panel.py          # 区域组合、按钮和表格事件
desktop/app/ui/widgets/task_table_model.py   # 任务表语义模型
desktop/app/ui/delegates/task_delegates.py   # 输入/输出摘要、进度、移除按钮、文本列绘制
```

如 delegate 继续变大，可拆分为：

```text
desktop/app/ui/delegates/task/
├── media_summary.py
├── progress.py
├── action.py
└── text_cell.py
```

但只有当文件继续膨胀到难以维护时才拆。

## 必做清单

### Header 与 actions

- [x] 使用 `PanelFrame` 和 `PanelActionBar`。
- [x] 任务统计和总进度保持标题下方。
- [x] 处理按钮保持右侧动作区。
- [x] 按钮启用状态仍由 panel 状态方法控制。

### 表格列结构

当前目标列顺序保持：

```text
输入 | 输出 | 行为 | 进度 | 操作
```

必做：

- [x] 输入/输出列同等 stretch 权重。
- [x] 行为列文本 delegate 选中状态统一。
- [x] 进度列使用 progress delegate。
- [x] 操作列使用 remove action delegate。
- [x] 长文本 tooltip 保留。

### 行内摘要

- [x] 输入媒体摘要继续在输入列第二行以标签呈现。
- [x] 输出摘要在任务完成后显示在输出列第二行。
- [x] 标签密度保持紧凑，不撑高行。
- [x] 行高稳定，不因标签数量少量变化抖动。

### 行操作

- [x] 移除按钮只对允许移除的任务启用。
- [x] 点击操作列只发出 `remove_task_requested(task_id)`。
- [x] 不在 delegate 中执行删除。

## 删除事项

- 删除旧状态列相关代码和测试。
- 删除消息列相关代码和测试。
- 删除任何兼容旧列顺序的分支。
- 删除旧 tooltip 文案中已不存在的列名。

## 测试要求

更新：

- `tests/desktop/test_task_table_model.py`
- `tests/desktop/test_task_panel.py`

覆盖：

- [x] 表头列顺序准确。
- [x] 输入/输出列宽模式一致。
- [x] 行为列使用文本 delegate。
- [x] 进度列使用进度 delegate。
- [x] 操作列点击发出移除信号。
- [x] 任务总进度 empty/running/done/indeterminate 都正确。

## 视觉验证

至少生成或人工检查：

- 空队列。
- 单个待处理任务。
- 多个任务，含 running/succeeded/failed/cancelled。
- 长文件名和中文路径。
- 窄窗口和宽窗口。

## 验收标准

- `TaskPanel` 不手写重复 header/actions 结构。
- 表格模型和 delegate 边界清楚。
- 旧列和旧状态显示逻辑彻底删除。
- 任务队列可以作为后续 GUI 产品表格模式参考。

## 验证命令

```bash
python3 -m compileall ffmpeg-gui/desktop ffmpeg-gui/shared ffmpeg-gui/tests
.venv/bin/python -m pytest tests/desktop/test_task_panel.py tests/desktop/test_task_table_model.py
.venv/bin/python -m pytest
git diff --check
```

## 完成状态

- [ ] 未开始
- [ ] 进行中
- [x] 已完成
