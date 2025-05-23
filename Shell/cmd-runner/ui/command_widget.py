#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QAbstractItemView, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QDateTime
from PySide6.QtGui import QColor

from core.command_executor import CommandInfo


class CommandWidget(QWidget):
    """命令管理组件"""

    # 自定义信号
    execute_clicked = Signal(str)  # command
    stop_clicked = Signal(str)  # command_id
    view_details_clicked = Signal(str)  # command_id

    def __init__(self):
        super().__init__()

        # 初始化UI
        self._init_ui()

        # 连接信号
        self._connect_signals()

        # 禁用命令部分
        self.set_enabled(False)

    def _init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建分组框
        group_box = QGroupBox("命令管理")
        main_layout.addWidget(group_box)

        # 创建垂直布局
        v_layout = QVBoxLayout(group_box)

        # 创建命令输入布局
        cmd_layout = QHBoxLayout()
        cmd_layout.setSpacing(10)

        # 创建命令输入框
        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText("输入要执行的命令...")
        cmd_layout.addWidget(QLabel("命令:"))
        cmd_layout.addWidget(self.command_edit, 1)

        # 创建执行按钮
        self.execute_btn = QPushButton("执行")
        self.execute_btn.setFixedWidth(80)
        cmd_layout.addWidget(self.execute_btn)

        # 添加到垂直布局
        v_layout.addLayout(cmd_layout)

        # 创建命令表格
        self.command_table = QTableWidget()
        self.command_table.setColumnCount(6)
        self.command_table.setHorizontalHeaderLabels(["ID", "命令", "PID", "开始时间", "状态", "操作"])
        self.command_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.command_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.command_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.command_table.verticalHeader().setVisible(False)
        v_layout.addWidget(self.command_table)

    def _connect_signals(self):
        """连接信号"""
        # 执行按钮点击事件
        self.execute_btn.clicked.connect(self._on_execute)

        # 回车键执行命令
        self.command_edit.returnPressed.connect(self._on_execute)

        # 表格单元格点击事件
        self.command_table.cellClicked.connect(self._on_cell_clicked)

    def _on_execute(self):
        """执行按钮点击事件"""
        command = self.command_edit.text().strip()
        if command:
            self.execute_clicked.emit(command)
            self.command_edit.clear()

    def _on_cell_clicked(self, row, col):
        """
        表格单元格点击事件

        Args:
            row: 行索引
            col: 列索引
        """
        try:
            if col == 5:  # 操作列
                # 获取命令ID
                id_item = self.command_table.item(row, 0)
                if id_item:
                    cmd_id = id_item.data(Qt.UserRole)

                    # 获取状态
                    status_item = self.command_table.item(row, 4)
                    status = status_item.text() if status_item else ""

                    # 获取操作文本
                    action_item = self.command_table.item(row, 5)
                    action_text = action_item.text() if action_item else ""

                    # 根据操作文本执行不同操作
                    if action_text == "停止":
                        self.stop_clicked.emit(cmd_id)
                    elif action_text == "查看":
                        # 查看命令详情
                        self._show_command_details(cmd_id)
        except Exception as e:
            import traceback
            print(f"单元格点击错误: {str(e)}\n{traceback.format_exc()}")

    def add_command(self, cmd_info):
        """
        添加命令

        Args:
            cmd_info: 命令信息对象
        """
        # 查找是否已存在
        for row in range(self.command_table.rowCount()):
            id_item = self.command_table.item(row, 0)
            if id_item and id_item.data(Qt.UserRole) == cmd_info.id:
                # 更新现有行
                self._update_command_row(row, cmd_info)
                return

        # 添加新行
        row = self.command_table.rowCount()
        self.command_table.insertRow(row)
        self._update_command_row(row, cmd_info)

    def _update_command_row(self, row, cmd_info):
        """
        更新命令行

        Args:
            row: 行索引
            cmd_info: 命令信息对象
        """
        # ID列
        id_item = QTableWidgetItem(cmd_info.id[:8])
        id_item.setData(Qt.UserRole, cmd_info.id)
        self.command_table.setItem(row, 0, id_item)

        # 命令列
        cmd_item = QTableWidgetItem(cmd_info.command)
        self.command_table.setItem(row, 1, cmd_item)

        # PID列
        pid_item = QTableWidgetItem(str(cmd_info.pid) if cmd_info.pid > 0 else "")
        self.command_table.setItem(row, 2, pid_item)

        # 开始时间列
        start_time = QDateTime.fromString(
            cmd_info.start_time.isoformat(), Qt.ISODate
        ).toString("yyyy-MM-dd HH:mm:ss")
        time_item = QTableWidgetItem(start_time)
        self.command_table.setItem(row, 3, time_item)

        # 状态列
        status_item = QTableWidgetItem(cmd_info.status)
        if cmd_info.status == "运行中":
            status_item.setForeground(QColor(0, 128, 0))  # 绿色
        elif cmd_info.status == "已完成":
            status_item.setForeground(QColor(0, 0, 255))  # 蓝色
        elif cmd_info.status == "失败" or cmd_info.status == "已终止":
            status_item.setForeground(QColor(255, 0, 0))  # 红色
        self.command_table.setItem(row, 4, status_item)

        # 操作列
        action_text = "停止" if cmd_info.is_running else "查看"
        action_item = QTableWidgetItem(action_text)
        action_item.setForeground(QColor(0, 0, 255))  # 蓝色
        self.command_table.setItem(row, 5, action_item)

    def update_command_status(self, cmd_id, status):
        """
        更新命令状态

        Args:
            cmd_id: 命令ID
            status: 状态
        """
        for row in range(self.command_table.rowCount()):
            id_item = self.command_table.item(row, 0)
            if id_item and id_item.data(Qt.UserRole) == cmd_id:
                # 更新状态列
                status_item = QTableWidgetItem(status)
                if status == "运行中":
                    status_item.setForeground(QColor(0, 128, 0))  # 绿色
                elif status == "已完成":
                    status_item.setForeground(QColor(0, 0, 255))  # 蓝色
                elif status == "失败" or status == "已终止":
                    status_item.setForeground(QColor(255, 0, 0))  # 红色
                self.command_table.setItem(row, 4, status_item)

                # 更新操作列
                action_text = "停止" if status == "运行中" else "查看"
                action_item = QTableWidgetItem(action_text)
                action_item.setForeground(QColor(0, 0, 255))  # 蓝色
                self.command_table.setItem(row, 5, action_item)
                break

    def update_commands(self, commands):
        """
        更新命令列表

        Args:
            commands: 命令字典
        """
        for cmd_id, cmd_info in commands.items():
            self.add_command(cmd_info)

    def _show_command_details(self, cmd_id):
        """
        显示命令详情

        Args:
            cmd_id: 命令ID
        """
        try:
            # 查找命令
            for row in range(self.command_table.rowCount()):
                id_item = self.command_table.item(row, 0)
                if id_item and id_item.data(Qt.UserRole) == cmd_id:
                    # 获取命令信息
                    command = self.command_table.item(row, 1).text()
                    pid = self.command_table.item(row, 2).text()
                    start_time = self.command_table.item(row, 3).text()
                    status = self.command_table.item(row, 4).text()

                    # 构建详情文本
                    details = f"命令ID: {cmd_id}\n\n"
                    details += f"命令: {command}\n\n"
                    details += f"PID: {pid}\n\n"
                    details += f"开始时间: {start_time}\n\n"
                    details += f"状态: {status}\n\n"
                    details += "详细输出请查看终端窗口"

                    # 发送查看详情信号
                    self.view_details_clicked.emit(cmd_id)

                    # 显示消息框
                    QMessageBox.information(self, "命令详情", details)
                    return

            # 如果没有找到命令
            QMessageBox.warning(self, "查看详情", "找不到指定的命令")

        except Exception as e:
            import traceback
            error_msg = f"显示命令详情错误: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            QMessageBox.critical(self, "错误", f"显示命令详情错误: {str(e)}")

    def update_command_output(self, cmd_id, output):
        """
        更新命令输出

        Args:
            cmd_id: 命令ID
            output: 输出内容
        """
        # 由于我们使用消息框显示详情，这里不需要更新输出
        pass

    def set_enabled(self, enabled):
        """
        设置启用状态

        Args:
            enabled: 是否启用
        """
        self.command_edit.setEnabled(enabled)
        self.execute_btn.setEnabled(enabled)
