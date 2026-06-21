# TODO 06: 文档、验证与旧冗余清理

## 目标

在组件化和布局重构完成后，补齐文档、测试和视觉验证，删除所有开发期旧结构冗余。确保 `ffmpeg-gui` 不只是完成当前 UI，而是成为后续 PySide6 GUI 产品的可靠参考。

## 文档沉淀

更新：

- `AGENTS.md`
- `docs/GUI开发规范/` 下相关规范文件，如存在
- `README.md` 的开发说明，如需要

必须沉淀：

- UI components 分层说明。
- PanelFrame 使用规则。
- SegmentedToggle 使用规则。
- PanelActionBar 使用规则。
- FixedScrollArea 使用场景。
- FormSection 和参数表单规则。
- QSS objectName/dynamic property 约定。
- delegate-based table rendering 约定。

不沉淀：

- 已废弃旧结构。
- 已删除 helper。
- 过渡期命名。
- TODO 执行细节。

## 旧冗余清理清单

必须搜索并处理以下模式：

```text
Legacy
legacy
Old
old_
compat
deprecated
TODO compatibility
fallback
temporary
```

注意：正常业务 fallback 如错误处理 fallback 不在本清理范围；本阶段只清理重构兼容残留。

必须清理：

- [ ] 未使用 import。
- [ ] 未使用 helper。
- [ ] 旧 QSS selector。
- [ ] 旧 objectName。
- [ ] 旧测试断言。
- [ ] 旧文档中的过时 UI 描述。

## 验证范围

### 单元与布局测试

- [ ] UI components tests。
- [ ] operation selector tests。
- [ ] parameter form tests。
- [ ] task panel tests。
- [ ] task table model tests。
- [ ] main window layout tests。
- [ ] controller validation tests。

### 运行验证

至少覆盖：

- [ ] 空启动。
- [ ] 选择单个媒体文件。
- [ ] 添加多个文件。
- [ ] 切换 Stack 模式。
- [ ] 选择参数多的 operation。
- [ ] 开始任务、取消任务。
- [ ] 任务完成后输出列展示结果。
- [ ] 打开日志弹窗。
- [ ] 打开设置弹窗。

### 视觉验证

至少检查：

- [ ] 1440px 宽度。
- [ ] 1920px 宽度。
- [ ] 较矮窗口。
- [ ] 参数多时内滚动。
- [ ] 处理动作多时内滚动。
- [ ] 任务队列空态和多任务状态。
- [ ] 长中文文件名。
- [ ] 长输出路径。

## 最终命令

```bash
python3 -m compileall ffmpeg-gui/desktop ffmpeg-gui/shared ffmpeg-gui/tests
.venv/bin/python -m pytest
git diff --check
find ffmpeg-gui -name __pycache__ -type d -prune -exec rm -rf {} +
```

## 完成后的处理

全部阶段完成后：

- [ ] 将长期规则沉淀到 `AGENTS.md` 或 `docs/GUI开发规范/`。
- [ ] 确认 `TODO.md` 和 `todo/` 是否继续保留。
- [ ] 如果用户确认清理，则删除 `TODO.md` 和 `todo/`。
- [ ] 保留测试作为长期防回归资产。

## 验收标准

- 没有兼容性旧内容冗余。
- 没有过度实现的拖拽、布局保存或跨项目框架。
- GUI 结构可作为其他 PySide6 产品的参考。
- 所有验证命令通过。

## 完成状态

- [ ] 未开始
- [ ] 进行中
- [ ] 已完成
