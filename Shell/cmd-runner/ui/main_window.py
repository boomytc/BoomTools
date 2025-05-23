#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QMessageBox
)

from ui.connection_widget import ConnectionWidget
from ui.command_widget import CommandWidget
from ui.terminal_widget import TerminalWidget

from core.ssh_manager import SSHManager
from core.command_executor import CommandExecutor
from core.status_monitor import StatusMonitor

from utils.config_manager import ConfigManager
from utils.log_manager import LogManager


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()

        # 初始化核心组件
        self.ssh_manager = SSHManager()
        self.command_executor = CommandExecutor(self.ssh_manager)
        self.status_monitor = StatusMonitor(self.command_executor)

        # 初始化工具组件
        self.config_manager = ConfigManager()
        self.log_manager = LogManager()

        # 设置窗口属性
        self.setWindowTitle("SSH脚本执行器")
        self.resize(1000, 800)

        # 初始化UI
        self._init_ui()

        # 连接信号
        self._connect_signals()

        # 加载配置
        self._load_config()

        # 启动状态监控
        self.status_monitor.start_monitoring()

    def _init_ui(self):
        """初始化UI"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 创建连接部件
        self.connection_widget = ConnectionWidget()
        main_layout.addWidget(self.connection_widget)

        # 创建命令部件
        self.command_widget = CommandWidget()
        main_layout.addWidget(self.command_widget)

        # 创建终端部件
        self.terminal_widget = TerminalWidget()
        main_layout.addWidget(self.terminal_widget)

    def _connect_signals(self):
        """连接信号"""
        # 连接部件信号
        self.connection_widget.connect_clicked.connect(self._on_connect)
        self.connection_widget.disconnect_clicked.connect(self._on_disconnect)

        # 命令部件信号
        self.command_widget.execute_clicked.connect(self._on_execute_command)
        self.command_widget.stop_clicked.connect(self._on_stop_command)
        self.command_widget.view_details_clicked.connect(self._on_view_command_details)

        # SSH管理器信号
        self.ssh_manager.set_connection_callback(self._on_connection_change)

        # 命令执行器信号
        self.command_executor.set_status_callback(self._on_command_status_change)
        self.command_executor.set_output_callback(self._on_command_output_update)

        # 状态监控信号
        self.status_monitor.set_status_update_callback(self._on_status_update)

    def _load_config(self):
        """加载配置"""
        # 加载连接配置
        connections = self.config_manager.get_connections()
        self.connection_widget.set_connections(connections)

        # 加载上次连接
        last_conn = self.config_manager.get_last_connection()
        if last_conn:
            self.connection_widget.set_connection_info(
                last_conn.get("host", ""),
                last_conn.get("port", 22),
                last_conn.get("username", ""),
                last_conn.get("password", "")
            )

        # 加载运行中的命令
        running_commands = self.log_manager.get_running_commands()
        for cmd in running_commands:
            self.command_widget.add_command(cmd)

    def _on_connect(self, host, port, username, password):
        """
        连接按钮点击事件

        Args:
            host: 主机地址
            port: 端口
            username: 用户名
            password: 密码
        """
        # 禁用连接按钮
        self.connection_widget.set_connecting(True)

        # 在主线程中直接连接，避免多线程问题
        try:
            success, message = self.ssh_manager.connect(host, port, username, password)

            # 更新UI
            self.connection_widget.set_connecting(False)
            if success:
                self.connection_widget.set_connected(True)
                self.config_manager.add_connection(host, port, username, password)
                self.config_manager.set_last_connection(host, port, username, password)
                self.terminal_widget.append_output(f"已连接到 {host}:{port}")
            else:
                self.connection_widget.set_connected(False)
                QMessageBox.warning(self, "连接失败", message)
                self.terminal_widget.append_output(f"连接失败: {message}")
        except Exception as e:
            import traceback
            error_msg = f"连接过程中发生错误: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.connection_widget.set_connecting(False)
            self.connection_widget.set_connected(False)
            QMessageBox.critical(self, "连接错误", f"连接过程中发生错误: {str(e)}")
            self.terminal_widget.append_output(error_msg)

    def _on_disconnect(self):
        """断开连接按钮点击事件"""
        success, message = self.ssh_manager.disconnect()
        if success:
            self.connection_widget.set_connected(False)
            self.terminal_widget.append_output("已断开连接")
        else:
            QMessageBox.warning(self, "断开连接失败", message)
            self.terminal_widget.append_output(f"断开连接失败: {message}")

    def _on_connection_change(self, connected):
        """
        连接状态变化事件

        Args:
            connected: 是否已连接
        """
        self.connection_widget.set_connected(connected)
        self.command_widget.set_enabled(connected)

    def _on_execute_command(self, command):
        """
        执行命令按钮点击事件

        Args:
            command: 要执行的命令
        """
        success, error, cmd_info = self.command_executor.execute_command(command)
        if success:
            self.command_widget.add_command(cmd_info)
            self.terminal_widget.append_output(f"执行命令: {command}")
            self.log_manager.add_command_log(cmd_info)
        else:
            QMessageBox.warning(self, "执行命令失败", error)
            self.terminal_widget.append_output(f"执行命令失败: {error}")

    def _on_stop_command(self, cmd_id):
        """
        停止命令按钮点击事件

        Args:
            cmd_id: 命令ID
        """
        success, message = self.command_executor.stop_command(cmd_id)
        if success:
            self.terminal_widget.append_output(f"已停止命令: {cmd_id}")
            cmd_info = self.command_executor.get_command_info(cmd_id)
            if cmd_info:
                self.log_manager.add_command_log(cmd_info)
        else:
            QMessageBox.warning(self, "停止命令失败", message)
            self.terminal_widget.append_output(f"停止命令失败: {message}")

    def _on_command_status_change(self, cmd_id, status):
        """
        命令状态变化事件

        Args:
            cmd_id: 命令ID
            status: 状态
        """
        self.command_widget.update_command_status(cmd_id, status)
        self.terminal_widget.append_output(f"命令 {cmd_id} 状态变为: {status}")

        # 更新日志
        cmd_info = self.command_executor.get_command_info(cmd_id)
        if cmd_info:
            self.log_manager.add_command_log(cmd_info)

    def _on_command_output_update(self, cmd_id, output):
        """
        命令输出更新事件

        Args:
            cmd_id: 命令ID
            output: 输出内容
        """
        # 更新终端输出
        self.terminal_widget.append_output(output)

        # 更新命令详情对话框中的输出
        self.command_widget.update_command_output(cmd_id, output)

    def _on_status_update(self, commands):
        """
        状态更新事件

        Args:
            commands: 命令字典
        """
        self.command_widget.update_commands(commands)

    def _on_view_command_details(self, cmd_id):
        """
        查看命令详情事件

        Args:
            cmd_id: 命令ID
        """
        cmd_info = self.command_executor.get_command_info(cmd_id)
        if cmd_info:
            # 这里可以添加更多的处理，例如显示命令的详细输出
            self.terminal_widget.append_output(f"查看命令详情: {cmd_id}")
            self.terminal_widget.append_output(f"命令: {cmd_info.command}")
            self.terminal_widget.append_output(f"PID: {cmd_info.pid}")
            self.terminal_widget.append_output(f"状态: {cmd_info.status}")
            self.terminal_widget.append_output(f"输出: {cmd_info.output}")
            self.terminal_widget.append_output(f"错误: {cmd_info.error}")

    def closeEvent(self, event):
        """
        窗口关闭事件

        Args:
            event: 事件对象
        """
        # 停止监控
        self.status_monitor.stop_monitoring()
        self.command_executor.stop_monitoring()

        # 断开连接
        if self.ssh_manager.is_connected():
            self.ssh_manager.disconnect()

        # 保存运行中的命令
        for cmd in self.command_executor.get_all_commands():
            self.log_manager.add_command_log(cmd)

        # 接受关闭事件
        event.accept()
