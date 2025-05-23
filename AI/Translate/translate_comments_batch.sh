#!/bin/bash

# 自动确认的函数
auto_confirm() {
    echo "y" | "$@"
}

# 提示用户输入密码的函数
prompt_sudo() {
    if [ "$EUID" -ne 0 ]; then
        echo "需要安装系统依赖，请输入sudo密码:"
        sudo "$@"
    else
        "$@"
    fi
}

# 显示使用帮助
show_help() {
    echo "用法: $0 <目录路径> [选项...]"
    echo ""
    echo "参数:"
    echo "  <目录路径>       要处理的源代码目录"
    echo ""
    echo "选项:"
    echo "  -a, --api-key KEY 使用指定的智谱AI API密钥 (如果未提供，则使用Python脚本中的默认密钥)"
    echo "  -t, --threads N  指定本地操作线程数量 (默认: 20)。Python脚本本身的默认是64。"
    echo "  -e, --exclude D  排除不需要处理的目录D (可指定多次)"
    echo "  -r, --report F   指定输出处理报告的文件路径 (默认: report.md)"
    echo "  -h, --help       显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 /path/to/src --api-key YOUR_API_KEY_HERE --threads 16 --exclude terrsimPlugins --exclude thirdparty"
    echo "  $0 /path/to/src -t 8 -e test -r report.md"
    exit 1
}

# 检查参数
if [ $# -lt 1 ]; then
    show_help
fi

# 处理参数
DIRECTORY=$1
shift

# 默认值
THREADS=20
EXCLUDE_ARGS=""
REPORT_FILE="report.md"
API_KEY_PASSTHROUGH_ARG="" # Added for API Key

# 解析选项
while [ "$#" -gt 0 ]; do
    case "$1" in
        -a|--api-key) # Added for API Key
            API_KEY_PASSTHROUGH_ARG="--api-key $2"
            shift 2
            ;;
        -t|--threads)
            THREADS="$2"
            shift 2
            ;;
        -e|--exclude)
            EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude $2"
            shift 2
            ;;
        -r|--report)
            REPORT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "错误: 未知选项 $1"
            show_help
            ;;
    esac
done

# 检查目录是否存在
if [ ! -d "$DIRECTORY" ]; then
    echo "错误: $DIRECTORY 不是一个有效的目录"
    exit 1
fi

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到python3，请先安装"
    exit 1
fi

# 检查必要的Python库是否安装
echo "检查必要的Python库..."

# 检查pip是否安装
if ! command -v pip3 &> /dev/null; then
    echo "错误: 未找到pip3，请先安装"
    if [ "$(uname)" = "Linux" ]; then
        echo "提示: 在大多数Linux发行版上，可以使用以下命令安装pip3:"
        echo "  - Debian/Ubuntu: sudo apt-get install python3-pip"
        echo "  - CentOS/RHEL: sudo yum install python3-pip"
        echo "  - Fedora: sudo dnf install python3-pip"
        echo "  - Arch Linux: sudo pacman -S python-pip"
    elif [ "$(uname)" = "Darwin" ]; then
        echo "提示: 在macOS上，可以使用以下命令安装pip3:"
        echo "  - 使用Homebrew: brew install python3"
        echo "  - 或者从python.org下载Python安装程序"
    fi
    exit 1
fi

# 创建依赖列表
REQUIRED_PACKAGES=("zhipuai" "tqdm" "python-magic")
MISSING_PACKAGES=()

# 检查所有依赖
for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import ${package//-/_}" &> /dev/null; then
        MISSING_PACKAGES+=("$package")
    fi
done

# 安装缺失的依赖
if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo "需要安装以下Python库: ${MISSING_PACKAGES[*]}"
    read -p "是否自动安装这些依赖? [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        for package in "${MISSING_PACKAGES[@]}"; do
            echo "正在安装 $package..."
            pip3 install "$package"
            if [ $? -ne 0 ]; then
                echo "警告: 安装 $package 失败，请手动安装"
            fi
        done
    else
        echo "请手动安装缺失的依赖后再运行此脚本"
        exit 1
    fi
fi

# 检查python-magic是否需要系统依赖
if [[ " ${MISSING_PACKAGES[*]} " =~ " python-magic " ]] || ! python3 -c "import magic; magic.Magic()" &> /dev/null; then
    echo "检测到python-magic可能需要系统依赖..."

    # 在Linux上，可能还需要安装系统依赖
    if [ "$(uname)" = "Linux" ]; then
        if command -v apt-get &> /dev/null; then
            echo "检测到Debian/Ubuntu系统，安装libmagic依赖..."
            prompt_sudo apt-get update && prompt_sudo apt-get install -y libmagic1
        elif command -v yum &> /dev/null; then
            echo "检测到CentOS/RHEL系统，安装file-devel依赖..."
            prompt_sudo yum install -y file-devel
        elif command -v dnf &> /dev/null; then
            echo "检测到Fedora系统，安装file-devel依赖..."
            prompt_sudo dnf install -y file-devel
        elif command -v pacman &> /dev/null; then
            echo "检测到Arch Linux系统，安装file依赖..."
            prompt_sudo pacman -S --noconfirm file
        fi
    elif [ "$(uname)" = "Darwin" ]; then
        if command -v brew &> /dev/null; then
            echo "检测到macOS系统，使用Homebrew安装libmagic依赖..."
            brew install libmagic
        else
            echo "警告: 在macOS上未找到Homebrew，请手动安装libmagic"
        fi
    fi
fi

# 验证所有依赖是否已正确安装
echo "验证依赖安装..."
VALIDATION_FAILED=false
for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import ${package//-/_}" &> /dev/null; then
        echo "错误: $package 安装失败或无法导入"
        VALIDATION_FAILED=true
    fi
done

if [ "$VALIDATION_FAILED" = true ]; then
    echo "依赖验证失败，请解决上述问题后再运行此脚本"
    exit 1
fi

echo "所有依赖已成功安装"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 构建报告参数
REPORT_ARGS="--output-report $REPORT_FILE"

# 检查Python脚本是否存在
if [ ! -f "$SCRIPT_DIR/translate_comments_batch.py" ]; then
    echo "错误: 找不到翻译脚本 $SCRIPT_DIR/translate_comments_batch.py"
    exit 1
fi

# 检查Python脚本是否可执行
if [ ! -x "$SCRIPT_DIR/translate_comments_batch.py" ]; then
    echo "警告: 翻译脚本不可执行，正在添加执行权限..."
    chmod +x "$SCRIPT_DIR/translate_comments_batch.py"
fi

echo "==============================================="
echo "开始翻译C/C++文件注释"
echo "==============================================="
echo "目录: $DIRECTORY"
echo "线程数: $THREADS"
if [ -n "$API_KEY_PASSTHROUGH_ARG" ]; then
    echo "使用: 自定义API密钥"
else
    echo "使用: 脚本内置API密钥"
fi
if [ -n "$EXCLUDE_ARGS" ]; then
    echo "排除目录: $EXCLUDE_ARGS"
fi
echo "报告文件: $REPORT_FILE"
echo "==============================================="

# 运行Python脚本，使用内置API密钥、指定的线程数和排除目录
time python3 "$SCRIPT_DIR/translate_comments_batch.py" "$DIRECTORY" $API_KEY_PASSTHROUGH_ARG --threads "$THREADS" $EXCLUDE_ARGS $REPORT_ARGS

# 检查脚本执行状态
SCRIPT_EXIT_CODE=$?
if [ $SCRIPT_EXIT_CODE -ne 0 ]; then
    echo "==============================================="
    echo "错误: 翻译脚本执行失败，退出代码: $SCRIPT_EXIT_CODE"
    echo "请检查上面的错误信息"
    echo "==============================================="
    exit $SCRIPT_EXIT_CODE
fi

# 检查报告文件是否生成
if [ -f "$REPORT_FILE" ]; then
    REPORT_SIZE=$(wc -l < "$REPORT_FILE")
    echo "==============================================="
    echo "处理完成!"
    echo "详细报告已保存至: $REPORT_FILE (共 $REPORT_SIZE 行)"
    echo "==============================================="

    # 如果报告文件存在且不为空，询问是否打开
    if [ $REPORT_SIZE -gt 0 ] && command -v xdg-open &> /dev/null; then
        read -p "是否打开报告文件? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            xdg-open "$REPORT_FILE" &> /dev/null &
        fi
    elif [ $REPORT_SIZE -gt 0 ] && command -v open &> /dev/null; then
        read -p "是否打开报告文件? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            open "$REPORT_FILE" &> /dev/null &
        fi
    fi
else
    echo "==============================================="
    echo "处理完成，但未找到报告文件: $REPORT_FILE"
    echo "==============================================="
fi