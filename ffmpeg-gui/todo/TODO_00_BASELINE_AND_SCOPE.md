# TODO 00: 基线、范围与终态确认

## 目标

在开始结构重构前，明确当前 UI 基线、目标终态、非目标和删除策略。开发阶段允许大幅重构，因此本阶段的重点是防止后续产生兼容性旧内容冗余。

## 当前基线

需要确认并记录以下现状：

- `desktop/app/ui/main_window.py` 负责主窗口组织。
- `desktop/app/ui/panels/runtime_panel.py` 承载内容选择。
- `desktop/app/ui/widgets/operation_form.py` 承载处理动作、参数、Stack toggle。
- `desktop/app/ui/panels/task_panel.py` 承载任务队列、总进度、处理按钮。
- `desktop/app/ui/widgets/path_picker.py` 是路径选择复合控件。
- `desktop/app/ui/delegates/task_delegates.py` 是任务表绘制入口。
- `resources/qss/app.qss` 是唯一 QSS 入口。

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

- [ ] 审查 `ui/panels/`、`ui/widgets/`、`ui/delegates/` 的当前职责。
- [ ] 列出重复 UI 模式：标题区域、右侧 actions、toggle、固定滚动区域、表单小节。
- [ ] 确认哪些重复模式进入 `components/`。
- [ ] 确认哪些仍留在产品级 panel/widget。
- [ ] 确认所有阶段都直接替换旧实现。
- [ ] 确认测试文件的迁移范围。

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
- [ ] 已完成
