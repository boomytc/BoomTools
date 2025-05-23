# SSH脚本执行器

基于PySide6的SSH远程命令执行工具，可以连接远程服务器，执行命令并监控命令执行状态。

## 功能特点

- SSH连接管理：配置和保存SSH连接信息
- 命令执行：执行命令并获取PID
- 状态监控：实时监控命令执行状态
- 终端输出：显示命令执行的输出结果
- 日志记录：记录命令执行历史，支持恢复上次会话状态

## 技术栈

- PySide6：GUI界面
- Paramiko：SSH连接和命令执行

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行方式

```bash
python main.py
```

## 使用说明

1. 在连接配置区域输入SSH连接信息（主机地址、端口、用户名、密码）
2. 点击"连接"按钮连接到远程服务器
3. 在命令输入框中输入要执行的命令
4. 点击"执行"按钮执行命令
5. 在命令列表中查看命令执行状态
6. 在终端输出区域查看命令执行的输出结果

## 项目结构

```
cmd-runner/
├── main.py                 # 程序入口
├── requirements.txt        # 依赖库
├── README.md               # 项目说明
├── ui/                     # UI界面
│   ├── main_window.py      # 主窗口
│   ├── connection_widget.py # 连接配置组件
│   ├── command_widget.py   # 命令管理组件
│   └── terminal_widget.py  # 终端输出组件
├── core/                   # 核心功能
│   ├── ssh_manager.py      # SSH连接管理
│   ├── command_executor.py # 命令执行
│   └── status_monitor.py   # 状态监控
└── utils/                  # 工具类
    ├── config_manager.py   # 配置管理
    ├── log_manager.py      # 日志管理
    └── pid_utils.py        # PID相关工具
```
