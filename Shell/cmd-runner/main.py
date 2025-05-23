#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import signal
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    """主函数"""
    try:
        # 创建应用
        app = QApplication(sys.argv)
        app.setApplicationName("SSH脚本执行器")

        # 设置当前目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)

        # 创建主窗口
        window = MainWindow()
        window.show()

        # 运行应用
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        error_msg = f"程序启动错误: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)

        # 尝试显示错误对话框
        try:
            from PySide6.QtWidgets import QMessageBox
            app = QApplication.instance()
            if not app:
                app = QApplication(sys.argv)
            QMessageBox.critical(None, "程序错误", error_msg)
        except:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
