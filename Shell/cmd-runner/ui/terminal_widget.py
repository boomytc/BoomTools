#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QGroupBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QTextCursor, QFont


class TerminalWidget(QWidget):
    """终端输出组件"""
    
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
        group_box = QGroupBox("终端输出")
        main_layout.addWidget(group_box)
        
        # 创建垂直布局
        v_layout = QVBoxLayout(group_box)
        
        # 创建终端输出框
        self.terminal_edit = QTextEdit()
        self.terminal_edit.setReadOnly(True)
        self.terminal_edit.setLineWrapMode(QTextEdit.NoWrap)
        
        # 设置等宽字体
        font = QFont("Courier New", 10)
        self.terminal_edit.setFont(font)
        
        # 设置样式
        self.terminal_edit.setStyleSheet("""
            QTextEdit {
                background-color: #000000;
                color: #FFFFFF;
                border: 1px solid #444444;
            }
        """)
        
        v_layout.addWidget(self.terminal_edit)
        
        # 创建按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        # 创建清空按钮
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setFixedWidth(80)
        btn_layout.addWidget(self.clear_btn)
        
        # 创建自动滚动复选框
        self.auto_scroll_check = QCheckBox("自动滚动")
        self.auto_scroll_check.setChecked(True)
        btn_layout.addWidget(self.auto_scroll_check)
        
        # 添加弹簧
        btn_layout.addStretch()
        
        # 添加到垂直布局
        v_layout.addLayout(btn_layout)
    
    def _connect_signals(self):
        """连接信号"""
        # 清空按钮点击事件
        self.clear_btn.clicked.connect(self._on_clear)
    
    def _on_clear(self):
        """清空按钮点击事件"""
        self.terminal_edit.clear()
    
    def append_output(self, text):
        """
        添加输出
        
        Args:
            text: 输出文本
        """
        if not text:
            return
            
        # 获取当前光标
        cursor = self.terminal_edit.textCursor()
        
        # 移动到末尾
        cursor.movePosition(QTextCursor.End)
        
        # 插入文本
        cursor.insertText(text)
        
        # 如果不是以换行符结尾，添加换行符
        if not text.endswith("\n"):
            cursor.insertText("\n")
        
        # 如果启用自动滚动，滚动到底部
        if self.auto_scroll_check.isChecked():
            self.terminal_edit.setTextCursor(cursor)
            self.terminal_edit.ensureCursorVisible()
    
    def set_text_color(self, color):
        """
        设置文本颜色
        
        Args:
            color: 颜色
        """
        self.terminal_edit.setTextColor(color)
    
    def clear(self):
        """清空终端"""
        self.terminal_edit.clear()
