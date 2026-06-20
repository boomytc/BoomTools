# TODO 06: Stack 链式处理

## 目标

实现可组合的单输入滤镜链，多个兼容操作在一次 ffmpeg 执行中完成，避免重复转码造成质量损失。

## 支持范围

第一版 Stack 只支持单输入、同一输出视频的滤镜类 operation：

- `resize_compress`
- `crop`
- `rotate`
- `adjust`
- `denoise`
- `sharpen_blur`
- `pad`
- `volume`
- `speed`
- `fade`

不支持 Stack：

- `convert`
- `extract_audio`
- `gif`
- `thumbnail`
- `reverse`
- `boomerang`
- `loop`
- `strip_metadata`
- `normalize_audio`
- `subtitles`
- `raw`
- `media_info`
- 所有多输入 operation

## Runtime Checklist

- [ ] 新增 `filter_chain.py` 或等价模块：
  - [ ] 将可链式 operation 转成 `{vf: list[str], af: list[str]}`。
  - [ ] 明确不支持的 operation 返回结构化错误。
  - [ ] 不把所有命令构建迁移到链式架构；只处理 Stack 路径。
- [ ] 新增 `build_stack_command(...)`：
  - [ ] 输入路径仍由 GUI 管理。
  - [ ] trim 仍作为输入级 `-ss/-t`。
  - [ ] 输出 codec 统一由最终输出格式决定。
  - [ ] 单次 `-vf` / `-af` 合成。
- [ ] 处理 filter 顺序：
  - [ ] 用户添加顺序就是执行顺序。
  - [ ] 不做智能重排。
  - [ ] 需要 duration 的 fade 依赖媒体信息。

## UI Checklist

- [ ] 增加“单操作 / Stack”模式切换。
- [ ] 在 Stack 模式下：
  - [ ] 配置当前 operation 后可“添加到 Stack”。
  - [ ] Stack 列表支持上移、下移、删除、清空。
  - [ ] 不支持 Stack 的 operation 禁用并显示原因。
  - [ ] 显示组合命令预览。
- [ ] 批处理模式和 Stack 可以组合，但必须在 TODO 05 完成后再接入。

## 测试 Checklist

- [ ] `crop -> adjust -> pad` 组合命令构建通过。
- [ ] `speed -> fade` 保持用户顺序。
- [ ] 不支持 operation 加入 Stack 会失败。
- [ ] 集成 smoke 至少执行一个 3 步 Stack。

## 反目标

- 不做通用 ffmpeg 图形化节点编辑器。
- 不做自动优化排序。
- 不支持多输入 Stack。
- 不把 Stack 内部表达为用户可编辑 DSL。

## 验收

- Stack 模式下多个滤镜只执行一次 ffmpeg。
- 组合命令预览与实际执行参数一致。
- 单操作模式不受 Stack 改造影响。

