# TODO 03: 处理动作与参数区域重建

## 目标

在组件层稳定后，重建 `OperationFormWidget` 的内部结构。核心目标是让“处理动作”和“参数”成为可组合、可测试、可扩展的产品级组件，而不是一个不断膨胀的大 widget。

## 目标拆分

将 `OperationFormWidget` 拆为：

```text
desktop/app/ui/widgets/
├── operation_form.py              # 组合入口，保留对外 signal/API
├── operation_selector.py          # 处理动作列表和 Stack toggle
├── operation_parameter_form.py    # 参数表单渲染和 collect
└── operation_field_factory.py     # 字段控件创建
```

是否采用这些文件名可在实施时调整，但职责必须拆开。

## OperationSelector

职责：

- 展示处理动作按钮网格。
- 内部使用 `FixedScrollArea`。
- 使用 `SegmentedToggle` 显示“单操作 / Stack 链式”。
- 根据 batch 支持状态禁用不可用操作。
- 对外发出 selected operation 和 stack mode changed。

不做：

- 不创建参数控件。
- 不解析字段值。
- 不构建 ffmpeg 命令。

必做：

- [ ] 将 operation card 创建逻辑从 `OperationFormWidget` 移出。
- [ ] 将 `_sync_operation_button_states` 移到 selector 或专门 presenter。
- [ ] 保留 tooltip 逻辑，但不泄漏到参数表单。
- [ ] 操作按钮支持统一最小高度和滚动区域。

## OperationParameterForm

职责：

- 展示当前 operation 的参数。
- 使用 `FixedScrollArea` 和 `FormSection`。
- 管理 start/end 通用处理范围。
- 管理动态字段。
- 对外提供 `collect()`。

不做：

- 不展示 operation 按钮。
- 不关心 Stack 是否启用。
- 不处理 batch operation 支持。

必做：

- [ ] 将 `_render_fields`、`_clear_fields`、`_create_widget`、`_connect_change_signal` 拆出。
- [ ] 保留 `PathPicker` 用于 file 字段。
- [ ] 将 spinbox no-wheel 和 combo popup 样式相关类移到 field factory 或专用 widgets。
- [ ] 保留字段宽度和 scrollbar gutter。
- [ ] 参数区域高度固定，不因字段数量跳动。

## OperationFieldFactory

职责：

- 根据 `FIELD_SPECS` 的 field spec 创建控件。
- 只返回控件，不参与布局。
- 为控件设置 tooltip、placeholder、range、default。

不做：

- 不读取 UI 全局状态。
- 不调用 service/runtime。

## 对外 API 保持唯一

`OperationFormWidget` 对外仍保留当前产品 API：

- `file_browse_requested`
- `spec_changed`
- `stack_mode_toggled`
- `selected_operation()`
- `collect()`
- `set_batch_operation_support(...)`
- `set_stack_mode(...)`
- `stack_mode()`
- `apply_media_defaults(...)`
- `set_file_path(...)`
- `set_subtitle_path(...)`

注意：这是产品级 API 的唯一方案，不是为了兼容旧内部实现。内部旧实现迁移完成后必须删除。

## 删除事项

- 删除 `OperationFormWidget` 中已经拆出的私有方法。
- 删除旧的 `_operation_buttons` 直接维护方式，改由 selector 内部维护。
- 删除只为旧 layout 存在的测试。
- 删除未使用的 import。

## 测试要求

新增或更新：

- `tests/desktop/test_operation_selector.py`
- `tests/desktop/test_operation_parameter_form.py`
- `tests/desktop/test_operation_panel_layout.py`

覆盖：

- [ ] selector 单独可选择 operation。
- [ ] selector 的 batch 禁用状态正确。
- [ ] segmented toggle 发出 Stack 切换。
- [ ] 参数表单在 raw、多字段、无字段 operation 下高度稳定。
- [ ] collect 正确产出 options 和 extra_inputs。
- [ ] spinbox wheel 禁用仍有效。
- [ ] combo popup 使用 styled view。

## 验收标准

- `operation_form.py` 成为组合入口，不再超过合理复杂度。
- operation selector 和 parameter form 可单独测试。
- 参数控件 factory 不包含布局代码。
- 旧内部方法删除，不保留兼容路径。

## 验证命令

```bash
python3 -m compileall ffmpeg-gui/desktop ffmpeg-gui/shared ffmpeg-gui/tests
.venv/bin/python -m pytest tests/desktop/test_operation_panel_layout.py
.venv/bin/python -m pytest tests/desktop/test_main_controller_validation.py
.venv/bin/python -m pytest
git diff --check
```

## 完成状态

- [ ] 未开始
- [ ] 进行中
- [ ] 已完成
