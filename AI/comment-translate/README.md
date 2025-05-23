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

1. `translate_comments.sh` - 翻译工具的 Shell 脚本入口
2. `translate_comments.py` - 翻译工具的 Python 实现
3. `utils/` - 工具函数模块目录

### 工具特点

- **模块化设计**：代码结构清晰，便于维护和扩展
- **两种处理模式**：支持标准模式和批处理模式
  - **标准模式**：使用智谱 AI 的标准 API 接口，逐个文件进行翻译处理
  - **批处理模式**：使用智谱 AI 的批处理 API 接口，将多个翻译请求批量提交，提高处理效率
- **严格的验证**：确保翻译结果不破坏代码结构和格式
- **进度管理**：支持保存和恢复处理进度

## 使用方法

```bash
./translate_comments.sh <目录路径> [选项...]
```

参数：
- `<目录路径>` - 要处理的源代码目录

选项：
- `-a, --api-key KEY` - 使用指定的智谱 AI API 密钥
- `-t, --threads N` - 使用 N 个线程处理文件（默认：20）
- `-e, --exclude D` - 排除目录 D（可指定多次）
- `-r, --report F` - 将处理报告保存到文件 F
- `-m, --model M` - 使用指定的模型（默认：glm-4-plus）
- `-b, --batch` - 使用批处理模式
- `-c, --config F` - 使用指定的配置文件
- `--resume` - 恢复上次的处理进度
- `-h, --help` - 显示帮助信息

### 标准模式示例

```bash
# 基本用法
./translate_comments.sh /path/to/src

# 使用8个线程，排除test目录，将报告保存到custom_report.md
./translate_comments.sh /path/to/src -t 8 -e test -r custom_report.md

# 使用自定义API密钥
./translate_comments.sh /path/to/src --api-key YOUR_API_KEY_HERE
```

### 批处理模式示例

```bash
# 使用批处理模式
./translate_comments.sh /path/to/src --batch

# 使用批处理模式，自定义API密钥和线程数
./translate_comments.sh /path/to/src --batch --api-key YOUR_API_KEY_HERE --threads 16

# 使用批处理模式，排除多个目录
./translate_comments.sh /path/to/src --batch --exclude terrsimPlugins --exclude thirdparty
```

### 恢复处理进度

```bash
# 恢复上次的处理进度
./translate_comments.sh /path/to/src --resume

# 恢复上次的处理进度，使用批处理模式
./translate_comments.sh /path/to/src --resume --batch
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
- 对于大型代码库，建议使用批处理模式以提高效率
- 处理报告默认保存在脚本所在目录的 `report.md` 文件中
- 如果翻译过程中出现错误，工具会自动恢复原始文件内容
- 可以使用 `--resume` 参数恢复上次的处理进度
- 可以使用 `--config` 参数指定配置文件，保存常用设置

## 版本信息

- v3.0（2024-05-23）

## 更新日志

### v3.0 更新内容
1. 重构为模块化设计，提高代码可维护性和可扩展性
2. 合并标准版和批处理版为单一工具，通过参数选择处理模式
3. 增强翻译质量验证，确保翻译结果不破坏代码结构
4. 优化提示词，提高翻译质量，特别是对专业术语的处理
5. 添加进度保存和恢复功能，支持中断后继续处理
6. 支持配置文件，方便保存常用设置
7. 改进大文件分块处理逻辑，提高翻译效率和质量
8. 增强错误恢复和文件备份机制
