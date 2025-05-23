# C/C++ 注释翻译工具

本工具用于将 C/C++ 代码文件中的英文注释自动翻译为中文，同时保持代码结构和格式不变。工具支持批量处理整个目录中的所有 C/C++ 文件，并提供详细的处理报告。

## 功能特点

- 支持翻译 `.h`, `.hpp`, `.c`, `.cpp`, `.cc`, `.cxx` 等 C/C++ 文件中的注释
- 智能识别并仅翻译注释部分，不修改代码逻辑和结构
- 支持多线程并行处理，提高翻译效率
- 提供详细的处理报告，包括成功率、失败原因等统计信息
- 自动备份原始文件，确保处理过程安全可靠
- 支持排除指定目录，避免处理不需要翻译的文件
- 提供两种实现方式：标准版和批处理版

## 工具说明

本目录包含以下主要文件：

1. `translate_comments.sh` - 标准版翻译工具的 Shell 脚本入口
2. `translate_comments.py` - 标准版翻译工具的 Python 实现
3. `translate_comments_batch.sh` - 批处理版翻译工具的 Shell 脚本入口
4. `translate_comments_batch.py` - 批处理版翻译工具的 Python 实现

### 标准版与批处理版的区别

- **标准版**：使用智谱 AI 的标准 API 接口，逐个文件进行翻译处理
- **批处理版**：使用智谱 AI 的批处理 API 接口，将多个翻译请求批量提交，提高处理效率

## 使用方法

### 标准版

```bash
./translate_comments.sh <目录路径> [选项...]
```

参数：
- `<目录路径>` - 要处理的源代码目录

选项：
- `-t, --threads N` - 使用 N 个线程处理文件（默认：20）
- `-e, --exclude D` - 排除目录 D（可指定多次）
- `-r, --report F` - 将处理报告保存到文件 F
- `-h, --help` - 显示帮助信息

示例：
```bash
./translate_comments.sh /path/to/src --threads 16 --exclude terrsimPlugins --exclude thirdparty
./translate_comments.sh /path/to/src -t 8 -e test -r report.md
```

### 批处理版

```bash
./translate_comments_batch.sh <目录路径> [选项...]
```

参数：
- `<目录路径>` - 要处理的源代码目录

选项：
- `-a, --api-key KEY` - 使用指定的智谱 AI API 密钥（如果未提供，则使用 Python 脚本中的默认密钥）
- `-t, --threads N` - 指定本地操作线程数量（默认：20）。Python 脚本本身的默认是 64。
- `-e, --exclude D` - 排除不需要处理的目录 D（可指定多次）
- `-r, --report F` - 指定输出处理报告的文件路径（默认：report.md）
- `-h, --help` - 显示帮助信息

示例：
```bash
./translate_comments_batch.sh /path/to/src --api-key YOUR_API_KEY_HERE --threads 16 --exclude terrsimPlugins --exclude thirdparty
./translate_comments_batch.sh /path/to/src -t 8 -e test -r report.md
```

## 依赖项

工具会自动检查并安装以下依赖：

- Python 3
- zhipuai（智谱 AI Python SDK）
- tqdm（进度条显示库）
- python-magic（文件类型检测库）

## 处理流程

1. 扫描指定目录中的所有 C/C++ 文件
2. 过滤掉二进制文件和不包含英文注释的文件
3. 备份原始文件内容
4. 使用智谱 AI 翻译文件中的英文注释
5. 验证翻译结果的完整性和正确性
6. 将翻译后的内容写回文件
7. 生成详细的处理报告

## 注意事项

- 工具默认使用内置的 API 密钥，建议通过 `--api-key` 参数提供您自己的 API 密钥
- 对于大型代码库，建议使用批处理版本以提高效率
- 处理报告默认保存在脚本所在目录的 `report.md` 文件中
- 如果翻译过程中出现错误，工具会自动恢复原始文件内容

## 版本信息

- 标准版：v1.3（2024-07-25）
- 批处理版：v2.0（2023-05-21）

## 更新日志

### 标准版 v1.3 更新内容
1. 放宽翻译结果的验证条件，不再检查关键代码结构
2. 不再检查翻译后长度减少是否过多
3. 只在原文与译文完全相同时判定为翻译失败
4. 优化大文件处理逻辑
5. 扩大目标文件范围，增加 .c、.cpp 等源文件的处理
6. 添加文件类型分布统计功能

### 批处理版 v2.0 更新内容
1. 重构为使用智谱 AI Batch API 进行翻译
2. 优化大文件处理和 API 调用效率
3. 调整进度报告和错误处理以适应批处理流程
4. 增强错误恢复和文件备份机制
5. 改进大文件分块处理逻辑
