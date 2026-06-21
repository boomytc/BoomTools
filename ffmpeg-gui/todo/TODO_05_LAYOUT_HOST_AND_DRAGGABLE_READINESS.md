# TODO 05: 布局宿主与拖拽布局准备

## 目标

为未来“区域拖拽布局”“布局预设”“面板重排”建立可承载边界，但本阶段不实现完整拖拽交互。先让 panel 都变成可被 layout host 管理的单元。

## 背景判断

当前 GUI 已经具备多个稳定区域：

- 内容选择
- 处理动作
- 参数
- Stack 队列
- 命令预览
- 任务队列

这些区域未来可能需要：

- 调整左右比例。
- 折叠/展开某些区域。
- 保存布局预设。
- 拖动区域顺序。
- 在其他 GUI 产品中复用布局模式。

但现在直接做拖拽会过早。因此本阶段只建立宿主结构。

## 目标结构

可考虑新增：

```text
desktop/app/ui/layouts/
├── __init__.py
├── dashboard_layout.py
└── layout_state.py
```

只有当组件迁移完成后再创建，不提前建空目录。

## DashboardLayout

职责：

- 统一组织主页面 panel。
- 管理 vertical/horizontal split。
- 管理 panel 间 spacing。
- 为未来可拖拽布局提供单一入口。

不做：

- 不实现拖拽。
- 不保存用户配置。
- 不知道 ffmpeg 业务状态。
- 不替代 `MainWindow` 的全局职责。

## LayoutState

只有当需要保存布局时再做。初始只定义简单结构：

```python
@dataclass
class PanelPlacement:
    panel_id: str
    area: str
    order: int
    visible: bool = True
```

但本阶段不接入配置保存。

## Panel ID 规则

所有可布局 panel 必须有稳定 id：

- `content`
- `operation`
- `parameters`
- `stack`
- `command_preview`
- `tasks`

这个 id 只用于布局，不用于业务逻辑。

## 必做清单

- [ ] 确认所有主要 panel 都有稳定 objectName。
- [ ] 确认 panel 构造不依赖父 layout 的具体位置。
- [ ] 确认 panel 对外 signal 不因迁移 layout host 改变。
- [ ] 将主窗口中的布局组织从散落 `root.addWidget(...)` 收敛到单一方法或 layout host。
- [ ] 评估是否使用 `QSplitter` 支持可调整比例。
- [ ] 若引入 `QSplitter`，测试默认尺寸和最小尺寸。

## 不做事项

- 不做拖拽排序 UI。
- 不做布局 JSON 持久化。
- 不做多窗口 dock。
- 不做 `QDockWidget`，除非后续明确需要桌面 IDE 式布局。
- 不做旧布局 fallback。

## 删除事项

- 删除主窗口中被 layout host 替代的重复 layout 组织代码。
- 删除只为固定旧位置存在的 size hack。
- 删除无用 stretch 或 spacer。

## 测试要求

新增或更新：

- `tests/desktop/test_main_window_layout.py`

覆盖：

- [ ] 主窗口能构建所有 panel。
- [ ] 关键 panel objectName 和 panel id 稳定。
- [ ] 默认布局中内容选择在顶部。
- [ ] 操作/参数区域同一行。
- [ ] 任务队列在下方。
- [ ] 窗口 resize 后没有 panel 高度异常膨胀。

## 验收标准

- 主窗口布局组织更清晰。
- panel 具备未来拖拽布局的边界。
- 没有实现过早的拖拽功能。
- 无兼容旧布局分支。

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
