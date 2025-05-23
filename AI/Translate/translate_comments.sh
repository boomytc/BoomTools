#!/bin/bash

# 设置密码
PASSWORD="1"

# 自动输入密码的函数
auto_sudo() {
    echo "$PASSWORD" | sudo -S "$@"
}

# 自动确认的函数
auto_confirm() {
    echo "y" | "$@"
}

# 显示使用帮助
show_help() {
    echo "用法: $0 <目录路径> [选项...]"
    echo ""
    echo "参数:"
    echo "  <目录路径>       要处理的源代码目录"
    echo ""
    echo "选项:"
    echo "  -t, --threads N  使用N个线程处理文件 (默认: 20)"
    echo "  -e, --exclude D  排除目录D (可指定多次)"
    echo "  -r, --report F   将处理报告保存到文件F"
    echo "  -h, --help       显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 /path/to/src --threads 16 --exclude terrsimPlugins --exclude thirdparty"
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

# 解析选项
while [ "$#" -gt 0 ]; do
    case "$1" in
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

# 检查zhipuai库
if ! python3 -c "import zhipuai" &> /dev/null; then
    echo "正在安装zhipuai库..."
    auto_confirm pip3 install zhipuai
fi

# 检查tqdm库
if ! python3 -c "import tqdm" &> /dev/null; then
    echo "正在安装tqdm库..."
    auto_confirm pip3 install tqdm
fi

# 检查python-magic库
if ! python3 -c "import magic" &> /dev/null; then
    echo "正在安装python-magic库..."
    auto_confirm pip3 install python-magic
    
    # 在Linux上，可能还需要安装系统依赖
    if [ "$(uname)" = "Linux" ]; then
        if command -v apt-get &> /dev/null; then
            echo "检测到Debian/Ubuntu系统，安装libmagic依赖..."
            auto_sudo apt-get update && auto_sudo apt-get install -y libmagic1
        elif command -v yum &> /dev/null; then
            echo "检测到CentOS/RHEL系统，安装file-devel依赖..."
            auto_sudo yum install -y file-devel
        fi
    fi
fi

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 构建报告参数
REPORT_ARGS="--output-report $REPORT_FILE"

echo "开始翻译C/C++文件注释 (使用 $THREADS 线程)..."
# 运行Python脚本，使用内置API密钥、指定的线程数和排除目录
time python3 "$SCRIPT_DIR/translate_comments.py" "$DIRECTORY" --threads "$THREADS" $EXCLUDE_ARGS $REPORT_ARGS

# 打印总结
echo "处理完成!"
echo "详细报告已保存至: $REPORT_FILE" 