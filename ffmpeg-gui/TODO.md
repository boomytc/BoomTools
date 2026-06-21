# ffmpeg-gui UI 结构长期演进 TODO

本 TODO 是 `ffmpeg-gui` 在开发阶段的结构演进索引。目标不是保守维护现状，而是把当前 GUI 打磨成一个可持续扩展、可被其他 PySide6 GUI 产品参考的成熟结构。

## 核心原则

- 开发阶段确定唯一方案即可，不做兼容性保留。
- 重构时直接迁移到新结构，删除旧结构、旧 helper、旧 QSS selector 和无效测试。
- 不保留“新旧两套 API 并行”的过渡层。
- 不为了未来未知项目做泛化框架，但要把已经重复出现的 UI 模式沉淀为组件。
- UI 组件只承载布局、交互入口和视觉状态，不承载 ffmpeg 业务规则。
- QSS 仍然是唯一视觉入口，组件通过 `objectName` 和 dynamic property 接入样式系统。
- 任务表继续遵循 model/view/delegate；模型暴露语义数据，delegate 负责绘制。
- 每个阶段完成后都要有明确终态和验证命令。

## 目标终态

完成后，`desktop/app/ui/` 应形成清晰的分层：

```text
desktop/app/ui/
├── components/        # 通用 GUI 组件：PanelFrame、SegmentedToggle、ActionBar、FixedScrollArea、FormSection
├── delegates/         # QTableView/QListView 绘制委托
├── dialogs/           # 设置、日志等弹窗
├── panels/            # 产品级区域组合：内容选择、处理动作、参数、任务队列
├── widgets/           # 产品级复合控件和模型
└── main_window.py     # 只组织主窗口和全局区域
```

`ffmpeg-gui` 应同时满足两类目标：

- 作为本机 ffmpeg 工具，界面紧凑、清晰、稳定。
- 作为 PySide6 GUI 项目参考，具备可复用组件、稳定面板边界、集中 QSS、可测试布局。

## 阶段索引

| 阶段 | 文件 | 状态 | 目标 |
| --- | --- | --- | --- |
| 00 | `todo/TODO_00_BASELINE_AND_SCOPE.md` | 已完成 | 固化当前基线、定义唯一终态和删除策略 |
| 01 | `todo/TODO_01_COMPONENT_SYSTEM.md` | 已完成 | 提取基础 UI 组件层 |
| 02 | `todo/TODO_02_PANEL_MIGRATION.md` | 待开始 | 将现有区域迁移到统一 PanelFrame 结构 |
| 03 | `todo/TODO_03_OPERATION_AND_PARAMETER_REBUILD.md` | 待开始 | 重建处理动作、参数区域的组件组合 |
| 04 | `todo/TODO_04_TASK_QUEUE_REBUILD.md` | 待开始 | 收敛任务队列表格、header、actions、delegate 边界 |
| 05 | `todo/TODO_05_LAYOUT_HOST_AND_DRAGGABLE_READINESS.md` | 待开始 | 为未来拖拽布局、布局预设建立可承载边界 |
| 06 | `todo/TODO_06_DOCS_VALIDATION_AND_CLEANUP.md` | 待开始 | 补齐文档、测试、视觉验证并删除旧冗余 |

## 全局验收标准

- `desktop/app/ui/components/` 中的组件能覆盖当前重复的区域、toggle、action bar、scroll area、form section。
- `RuntimePanel`、`OperationFormWidget`、`TaskPanel` 不再手写重复的标题行、右侧 actions、紧凑边距和滚动容器样板。
- 旧的临时 objectName、仅为旧布局存在的 QSS selector、重复 helper 必须删除。
- 不存在兼容旧 API 的 alias、wrapper、fallback、deprecated 分支。
- 所有新增组件有 focused tests。
- 现有功能行为保持通过测试验证，不靠旧结构兼容。
- 最终运行：
  - `python3 -m compileall ffmpeg-gui/desktop ffmpeg-gui/shared ffmpeg-gui/tests`
  - `.venv/bin/python -m pytest`
  - `git diff --check`
  - 清理 `__pycache__`

## 执行顺序要求

必须按阶段顺序推进。后一阶段不得提前引入大范围实现，除非当前阶段已经完成并通过验证。

如果某阶段发现前一阶段边界不对，直接修正前一阶段产物，不新增兼容层。

## 完成后的 TODO 处理

本目录是开发期执行索引。全部阶段完成并通过验证后，应将长期规则沉淀到 `AGENTS.md` 或 `docs/GUI开发规范/`，再由用户确认是否删除 `TODO.md` 和 `todo/`。
