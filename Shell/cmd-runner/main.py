#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any
import paramiko
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox,
    QSpinBox, QMessageBox, QSplitter, QFrame, QCompleter
)
from PySide6.QtCore import Qt, QThread, QObject, Signal, QEvent, QTimer, QStringListModel
from PySide6.QtGui import QFont, QShortcut, QKeySequence


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file=None):
        if config_file is None:
            # 获取脚本所在目录
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(script_dir, "config.json")
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置文件错误: {e}")
        
        # 默认配置
        return {
            "connections": [],
            "last_connection": None,
            "command_history": [],
            "ui_settings": {
                "font_size": 12,
                "max_history": 50
            }
        }
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件错误: {e}")
    
    def add_connection(self, host: str, port: int, username: str, password: str):
        """添加连接配置"""
        conn = {
            "host": host,
            "port": port,
            "username": username,
            "password": password
        }
        
        # 检查是否已存在
        for existing in self.config["connections"]:
            if (existing["host"] == host and existing["port"] == port 
                and existing["username"] == username):
                existing["password"] = password  # 更新密码
                self.save_config()
                return
        
        # 添加新连接
        self.config["connections"].append(conn)
        self.save_config()
    
    def set_last_connection(self, host: str, port: int, username: str, password: str):
        """设置最后使用的连接"""
        self.config["last_connection"] = {
            "host": host,
            "port": port,
            "username": username,
            "password": password
        }
        self.save_config()
    
    def add_command_history(self, command: str):
        """添加命令历史"""
        if not command.strip():
            return
        
        history = self.config.get("command_history", [])
        
        # 如果命令已存在，先移除旧的
        if command in history:
            history.remove(command)
        
        # 添加到开头
        history.insert(0, command)
        
        # 限制历史记录数量
        max_history = self.config.get("ui_settings", {}).get("max_history", 50)
        if len(history) > max_history:
            history = history[:max_history]
        
        self.config["command_history"] = history
        self.save_config()
    
    def get_command_history(self) -> list:
        """获取命令历史"""
        return self.config.get("command_history", [])


class SSHExecutor(QObject):
    """SSH执行器"""
    
    # 信号定义
    output_ready = Signal(str)
    error_ready = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self):
        super().__init__()
        self.client: Optional[paramiko.SSHClient] = None
        self.connected = False
        self.lock = threading.Lock()
    
    def connect(self, host: str, port: int, username: str, password: str) -> tuple[bool, str]:
        """连接SSH服务器"""
        with self.lock:
            if self.connected:
                return True, "已连接"
            
            try:
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                self.client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=10,
                    allow_agent=False,
                    look_for_keys=False
                )
                
                # 测试连接
                _, stdout, _ = self.client.exec_command("echo '连接测试'")
                result = stdout.read().decode('utf-8', errors='ignore').strip()
                
                if "连接测试" in result:
                    self.connected = True
                    return True, "连接成功"
                else:
                    self.client.close()
                    return False, "连接测试失败"
                    
            except paramiko.AuthenticationException:
                return False, "认证失败，请检查用户名和密码"
            except Exception as e:
                return False, f"连接错误: {str(e)}"
    
    def disconnect(self):
        """断开连接"""
        with self.lock:
            if self.client:
                self.client.close()
            self.connected = False
    
    def execute_command(self, command: str) -> tuple[bool, str, str]:
        """执行命令"""
        if not self.connected or not self.client:
            return False, "", "未连接到服务器"
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            
            # 读取输出
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
            
            return True, output, error
            
        except Exception as e:
            return False, "", f"执行命令错误: {str(e)}"


class ConnectionThread(QThread):
    """连接线程"""
    
    connect_finished = Signal(bool, str, str, int, str, str)
    
    def __init__(self, ssh_executor: SSHExecutor, host: str, port: int, username: str, password: str):
        super().__init__()
        self.ssh_executor = ssh_executor
        self.host = host
        self.port = port
        self.username = username
        self.password = password
    
    def run(self):
        """执行连接"""
        success, message = self.ssh_executor.connect(self.host, self.port, self.username, self.password)
        self.connect_finished.emit(success, message, self.host, self.port, self.username, self.password)


class CommandExecuteThread(QThread):
    """命令执行线程"""
    
    output_ready = Signal(str)
    error_ready = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, ssh_executor: SSHExecutor, command: str):
        super().__init__()
        self.ssh_executor = ssh_executor
        self.command = command
    
    def run(self):
        """执行命令"""
        success, output, error = self.ssh_executor.execute_command(self.command)
        
        if success:
            if output:
                self.output_ready.emit(output)
            if error:
                self.error_ready.emit(error)
            self.finished.emit(True, "命令执行完成")
        else:
            self.finished.emit(False, error)


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.ssh_executor = SSHExecutor()
        self.command_thread: Optional[CommandExecuteThread] = None
        self.connection_thread: Optional[ConnectionThread] = None
        
        self.init_ui()
        self.load_last_connection()
        self.setup_shortcuts()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("SSH脚本执行器 - 轻量版")
        self.setGeometry(100, 100, 900, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 连接配置区域
        self.create_connection_group(main_layout)
        
        # 命令执行区域
        self.create_command_group(main_layout)
        
        # 输出显示区域
        self.create_output_group(main_layout)
    
    def create_connection_group(self, parent_layout):
        """创建连接配置组"""
        group = QGroupBox("SSH连接配置")
        layout = QHBoxLayout(group)
        
        # 主机地址
        layout.addWidget(QLabel("主机:"))
        self.host_combo = QComboBox()
        self.host_combo.setEditable(True)
        self.host_combo.setMinimumWidth(150)
        layout.addWidget(self.host_combo)
        
        # 端口
        layout.addWidget(QLabel("端口:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        self.port_spin.setMinimumWidth(80)
        layout.addWidget(self.port_spin)
        
        # 用户名
        layout.addWidget(QLabel("用户名:"))
        self.username_edit = QLineEdit()
        self.username_edit.setMinimumWidth(100)
        layout.addWidget(self.username_edit)
        
        # 密码
        layout.addWidget(QLabel("密码:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setMinimumWidth(100)
        layout.addWidget(self.password_edit)
        
        # 连接按钮
        self.connect_btn = QPushButton("连接")
        self.connect_btn.setMinimumWidth(80)
        self.connect_btn.clicked.connect(self.on_connect)
        layout.addWidget(self.connect_btn)
        
        # 断开按钮
        self.disconnect_btn = QPushButton("断开")
        self.disconnect_btn.setMinimumWidth(80)
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.clicked.connect(self.on_disconnect)
        layout.addWidget(self.disconnect_btn)
        
        layout.addStretch()
        
        # 状态标签
        self.status_label = QLabel("未连接")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        parent_layout.addWidget(group)
        
        # 填充历史连接
        self.load_connection_history()
        
        # 连接信号
        self.host_combo.currentTextChanged.connect(self.on_connection_selected)
    
    def create_command_group(self, parent_layout):
        """创建命令执行组"""
        group = QGroupBox("命令执行")
        layout = QHBoxLayout(group)
        
        # 命令输入
        layout.addWidget(QLabel("命令:"))
        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText("请输入要执行的命令... (支持历史记录自动完成)")
        self.command_edit.returnPressed.connect(self.on_execute)
        
        # 设置命令历史自动完成
        self.setup_command_completer()
        
        layout.addWidget(self.command_edit)
        
        # 执行按钮
        self.execute_btn = QPushButton("执行")
        self.execute_btn.setMinimumWidth(80)
        self.execute_btn.setEnabled(False)
        self.execute_btn.clicked.connect(self.on_execute)
        layout.addWidget(self.execute_btn)
        
        # 清空输出按钮
        self.clear_btn = QPushButton("清空输出")
        self.clear_btn.setMinimumWidth(80)
        self.clear_btn.clicked.connect(self.on_clear_output)
        layout.addWidget(self.clear_btn)
        
        parent_layout.addWidget(group)
    
    def setup_command_completer(self):
        """设置命令自动完成"""
        history = self.config_manager.get_command_history()
        
        # 创建字符串列表模型
        self.completer_model = QStringListModel()
        self.completer_model.setStringList(history)
        
        # 创建自动完成器
        completer = QCompleter()
        completer.setModel(self.completer_model)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        
        self.command_edit.setCompleter(completer)
    
    def update_command_completer(self):
        """更新命令自动完成列表"""
        history = self.config_manager.get_command_history()
        self.completer_model.setStringList(history)
    
    def create_output_group(self, parent_layout):
        """创建输出显示组"""
        group = QGroupBox("命令输出")
        layout = QVBoxLayout(group)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 标准输出
        output_frame = QFrame()
        output_layout = QVBoxLayout(output_frame)
        output_layout.addWidget(QLabel("标准输出:"))
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        output_layout.addWidget(self.output_text)
        
        splitter.addWidget(output_frame)
        
        # 错误输出
        error_frame = QFrame()
        error_layout = QVBoxLayout(error_frame)
        error_layout.addWidget(QLabel("错误输出:"))
        
        self.error_text = QTextEdit()
        self.error_text.setReadOnly(True)
        self.error_text.setFont(QFont("Consolas", 10))
        self.error_text.setStyleSheet("QTextEdit { background-color: #fff5f5; }")
        error_layout.addWidget(self.error_text)
        
        splitter.addWidget(error_frame)
        
        # 设置分割器比例
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter)
        parent_layout.addWidget(group)
    
    def load_connection_history(self):
        """加载连接历史"""
        connections = self.config_manager.config.get("connections", [])
        self.host_combo.clear()
        
        for conn in connections:
            display_text = f"{conn['username']}@{conn['host']}:{conn['port']}"
            self.host_combo.addItem(display_text, conn)
    
    def load_last_connection(self):
        """加载最后使用的连接"""
        last_conn = self.config_manager.config.get("last_connection")
        if last_conn:
            self.host_combo.setCurrentText(f"{last_conn['username']}@{last_conn['host']}:{last_conn['port']}")
            self.username_edit.setText(last_conn["username"])
            self.password_edit.setText(last_conn["password"])
            self.port_spin.setValue(last_conn["port"])
    
    def on_connection_selected(self):
        """连接选择变化"""
        current_data = self.host_combo.currentData()
        if current_data:
            self.username_edit.setText(current_data["username"])
            self.password_edit.setText(current_data["password"])
            self.port_spin.setValue(current_data["port"])
    
    def on_connect(self):
        """连接按钮点击"""
        host = self.host_combo.currentText().split('@')[-1].split(':')[0] if '@' in self.host_combo.currentText() else self.host_combo.currentText()
        port = self.port_spin.value()
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        
        if not host or not username:
            QMessageBox.warning(self, "输入错误", "请输入主机地址和用户名")
            return
        
        # 禁用连接按钮
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("连接中...")
        
        # 创建连接线程
        self.connection_thread = ConnectionThread(self.ssh_executor, host, port, username, password)
        self.connection_thread.connect_finished.connect(self.on_connect_finished)
        self.connection_thread.start()
    
    def on_connect_finished(self, success: bool, message: str, host: str, port: int, username: str, password: str):
        """连接完成处理"""
        if success:
            # 保存连接配置
            self.config_manager.add_connection(host, port, username, password)
            self.config_manager.set_last_connection(host, port, username, password)
            self.load_connection_history()
        
        self.update_connection_status(success, message)
    
    def on_disconnect(self):
        """断开连接"""
        self.ssh_executor.disconnect()
        self.update_connection_status(False, "已断开连接")
    
    def on_execute(self):
        """执行命令"""
        if not self.ssh_executor.connected:
            QMessageBox.warning(self, "连接错误", "请先连接到SSH服务器")
            return
        
        command = self.command_edit.text().strip()
        if not command:
            QMessageBox.warning(self, "输入错误", "请输入要执行的命令")
            return
        
        # 保存命令到历史记录
        self.config_manager.add_command_history(command)
        self.update_command_completer()
        
        # 禁用执行按钮
        self.execute_btn.setEnabled(False)
        self.execute_btn.setText("执行中...")
        
        # 显示命令
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output_text.append(f"\n[{timestamp}] $ {command}")
        
        # 清空命令输入框
        self.command_edit.clear()
        
        # 创建执行线程
        self.command_thread = CommandExecuteThread(self.ssh_executor, command)
        self.command_thread.output_ready.connect(self.on_output_ready)
        self.command_thread.error_ready.connect(self.on_error_ready)
        self.command_thread.finished.connect(self.on_command_finished)
        self.command_thread.start()
    
    def on_output_ready(self, output: str):
        """处理标准输出"""
        self.output_text.append(output)
        self.output_text.ensureCursorVisible()
    
    def on_error_ready(self, error: str):
        """处理错误输出"""
        self.error_text.append(error)
        self.error_text.ensureCursorVisible()
    
    def on_command_finished(self, success: bool, message: str):
        """命令执行完成"""
        # 恢复执行按钮
        self.execute_btn.setEnabled(True)
        self.execute_btn.setText("执行")
        
        if not success:
            self.error_text.append(f"执行失败: {message}")
    
    def on_clear_output(self):
        """清空输出"""
        self.output_text.clear()
        self.error_text.clear()
    
    def update_connection_status(self, connected: bool, message: str):
        """更新连接状态"""
        if connected:
            self.status_label.setText("已连接")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.execute_btn.setEnabled(True)
        else:
            self.status_label.setText("未连接")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("连接")
            self.disconnect_btn.setEnabled(False)
            self.execute_btn.setEnabled(False)
        
        self.output_text.append(f"\n{message}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.ssh_executor.connected:
            self.ssh_executor.disconnect()
        event.accept()

    def setup_shortcuts(self):
        """设置快捷键"""
        # Ctrl+Enter: 执行命令
        execute_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        execute_shortcut.activated.connect(self.on_execute)
        
        # Ctrl+L: 清空输出
        clear_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_shortcut.activated.connect(self.on_clear_output)
        
        # Ctrl+D: 断开连接
        disconnect_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        disconnect_shortcut.activated.connect(self.on_disconnect)
        
        # F5: 连接
        connect_shortcut = QShortcut(QKeySequence("F5"), self)
        connect_shortcut.activated.connect(self.on_connect)
        
        # Escape: 停止当前操作或清空命令输入
        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self.on_escape)
        
        # 设置按钮快捷键提示
        self.connect_btn.setToolTip("连接到SSH服务器 (F5)")
        self.disconnect_btn.setToolTip("断开SSH连接 (Ctrl+D)")
        self.execute_btn.setToolTip("执行命令 (Ctrl+Enter)")
        self.clear_btn.setToolTip("清空输出 (Ctrl+L)")
        self.command_edit.setToolTip("输入命令后按Ctrl+Enter执行，支持历史记录自动完成")
    
    def on_escape(self):
        """Escape键处理"""
        # 如果命令输入框有内容，清空它
        if self.command_edit.text():
            self.command_edit.clear()
        # 如果命令正在执行，这里可以添加取消功能（未来扩展）


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("SSH脚本执行器")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 