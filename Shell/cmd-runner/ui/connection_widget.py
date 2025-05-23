#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QComboBox, QGroupBox, QFormLayout
)
from PySide6.QtCore import Signal
import base64


class ConnectionWidget(QWidget):
    """连接配置组件"""

    # 自定义信号
    connect_clicked = Signal(str, int, str, str)  # host, port, username, password
    disconnect_clicked = Signal()

    def __init__(self):
        super().__init__()

        # 初始化UI
        self._init_ui()

        # 连接信号
        self._connect_signals()

    def _init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建分组框
        group_box = QGroupBox("SSH连接配置")
        main_layout.addWidget(group_box)

        # 创建表单布局
        form_layout = QFormLayout(group_box)

        # 创建水平布局
        h_layout = QHBoxLayout()
        h_layout.setSpacing(10)

        # 创建连接下拉框
        self.connection_combo = QComboBox()
        self.connection_combo.setMinimumWidth(200)
        h_layout.addWidget(QLabel("保存的连接:"))
        h_layout.addWidget(self.connection_combo, 1)

        # 创建删除按钮
        self.delete_btn = QPushButton("删除")
        self.delete_btn.setFixedWidth(80)
        h_layout.addWidget(self.delete_btn)

        # 添加到表单
        form_layout.addRow(h_layout)

        # 创建主机输入框
        self.host_edit = QLineEdit()
        form_layout.addRow("主机地址:", self.host_edit)

        # 创建端口输入框
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        form_layout.addRow("端口:", self.port_spin)

        # 创建用户名输入框
        self.username_edit = QLineEdit()
        form_layout.addRow("用户名:", self.username_edit)

        # 创建密码输入框
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("密码:", self.password_edit)

        # 创建按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        # 创建连接按钮
        self.connect_btn = QPushButton("连接")
        self.connect_btn.setFixedWidth(100)
        btn_layout.addWidget(self.connect_btn)

        # 创建断开按钮
        self.disconnect_btn = QPushButton("断开")
        self.disconnect_btn.setFixedWidth(100)
        self.disconnect_btn.setEnabled(False)
        btn_layout.addWidget(self.disconnect_btn)

        # 创建保存按钮
        self.save_btn = QPushButton("保存连接")
        self.save_btn.setFixedWidth(100)
        btn_layout.addWidget(self.save_btn)

        # 添加弹簧
        btn_layout.addStretch()

        # 创建状态标签
        self.status_label = QLabel("未连接")
        btn_layout.addWidget(self.status_label)

        # 添加到表单
        form_layout.addRow(btn_layout)

    def _connect_signals(self):
        """连接信号"""
        # 连接按钮点击事件
        self.connect_btn.clicked.connect(self._on_connect)

        # 断开按钮点击事件
        self.disconnect_btn.clicked.connect(self._on_disconnect)

        # 保存按钮点击事件
        self.save_btn.clicked.connect(self._on_save)

        # 删除按钮点击事件
        self.delete_btn.clicked.connect(self._on_delete)

        # 连接下拉框选择事件
        self.connection_combo.currentIndexChanged.connect(self._on_connection_selected)

    def _on_connect(self):
        """连接按钮点击事件"""
        host = self.host_edit.text().strip()
        port = self.port_spin.value()
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not host:
            self.status_label.setText("请输入主机地址")
            return

        if not username:
            self.status_label.setText("请输入用户名")
            return

        # 发送信号
        self.connect_clicked.emit(host, port, username, password)

    def _on_disconnect(self):
        """断开按钮点击事件"""
        self.disconnect_clicked.emit()

    def _on_save(self):
        """保存按钮点击事件"""
        host = self.host_edit.text().strip()
        port = self.port_spin.value()
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not host or not username:
            self.status_label.setText("请输入主机地址和用户名")
            return

        # 创建连接项
        connection = {
            "host": host,
            "port": port,
            "username": username,
            "password": base64.b64encode(password.encode()).decode()
        }

        # 检查是否已存在
        for i in range(self.connection_combo.count()):
            item_data = self.connection_combo.itemData(i)
            if (item_data["host"] == host and
                item_data["port"] == port and
                item_data["username"] == username):
                # 更新现有项
                self.connection_combo.setItemData(i, connection)
                self.status_label.setText("已更新连接")
                return

        # 添加新项
        display_text = f"{username}@{host}:{port}"
        self.connection_combo.addItem(display_text, connection)
        self.connection_combo.setCurrentIndex(self.connection_combo.count() - 1)
        self.status_label.setText("已保存连接")

    def _on_delete(self):
        """删除按钮点击事件"""
        current_index = self.connection_combo.currentIndex()
        if current_index >= 0:
            self.connection_combo.removeItem(current_index)
            self.status_label.setText("已删除连接")

    def _on_connection_selected(self, index):
        """
        连接下拉框选择事件

        Args:
            index: 选中项索引
        """
        if index < 0:
            return

        # 获取连接信息
        try:
            connection = self.connection_combo.itemData(index)
            if connection:
                self.host_edit.setText(connection.get("host", ""))
                self.port_spin.setValue(connection.get("port", 22))
                self.username_edit.setText(connection.get("username", ""))

                # 解密密码
                try:
                    if "password" in connection and connection["password"]:
                        password = base64.b64decode(connection["password"].encode()).decode()
                        self.password_edit.setText(password)
                    else:
                        self.password_edit.setText("")
                except Exception as e:
                    print(f"解密密码错误: {str(e)}")
                    self.password_edit.setText("")
        except Exception as e:
            import traceback
            print(f"获取连接信息错误: {str(e)}\n{traceback.format_exc()}")
            self.status_label.setText(f"获取连接信息错误: {str(e)}")

    def set_connections(self, connections):
        """
        设置连接列表

        Args:
            connections: 连接列表
        """
        self.connection_combo.clear()

        for conn in connections:
            host = conn.get("host", "")
            port = conn.get("port", 22)
            username = conn.get("username", "")

            if host and username:
                display_text = f"{username}@{host}:{port}"
                self.connection_combo.addItem(display_text, conn)

    def set_connection_info(self, host, port, username, password):
        """
        设置连接信息

        Args:
            host: 主机地址
            port: 端口
            username: 用户名
            password: 密码
        """
        self.host_edit.setText(host)
        self.port_spin.setValue(port)
        self.username_edit.setText(username)
        self.password_edit.setText(password)

    def set_connected(self, connected):
        """
        设置连接状态

        Args:
            connected: 是否已连接
        """
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        self.status_label.setText("已连接" if connected else "未连接")

    def set_connecting(self, connecting):
        """
        设置连接中状态

        Args:
            connecting: 是否连接中
        """
        self.connect_btn.setEnabled(not connecting)
        self.disconnect_btn.setEnabled(False)
        self.status_label.setText("连接中..." if connecting else "未连接")
