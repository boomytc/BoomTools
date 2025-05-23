#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
from typing import Dict, List
from datetime import datetime

from core.command_executor import CommandInfo


class LogManager:
    """日志管理类，负责记录和恢复命令执行日志"""

    def __init__(self, log_file: str = "command_log.json"):
        self.log_file = log_file
        self.logs: List[Dict] = self._load_logs()

    def _load_logs(self) -> List[Dict]:
        """
        加载日志

        Returns:
            List[Dict]: 日志列表
        """
        if not os.path.exists(self.log_file):
            return []

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载日志错误: {str(e)}")
            return []

    def save_logs(self):
        """保存日志"""
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(self.logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存日志错误: {str(e)}")

    def add_command_log(self, cmd_info: CommandInfo):
        """
        添加命令日志

        Args:
            cmd_info: 命令信息对象
        """
        # 转换为字典
        log_entry = cmd_info.to_dict()

        # 检查是否已存在
        for i, log in enumerate(self.logs):
            if log["id"] == log_entry["id"]:
                # 更新现有日志
                self.logs[i] = log_entry
                self.save_logs()
                return

        # 添加新日志
        self.logs.append(log_entry)
        self.save_logs()

    def get_running_commands(self) -> List[CommandInfo]:
        """
        获取上次退出时仍在运行的命令

        Returns:
            List[CommandInfo]: 命令信息对象列表
        """
        running_commands = []
        for log in self.logs:
            if log.get("is_running", False):
                cmd_info = CommandInfo.from_dict(log)
                running_commands.append(cmd_info)
        return running_commands

    def update_command_status(self, cmd_id: str, status: str, is_running: bool):
        """
        更新命令状态

        Args:
            cmd_id: 命令ID
            status: 状态
            is_running: 是否在运行
        """
        for i, log in enumerate(self.logs):
            if log["id"] == cmd_id:
                log["status"] = status
                log["is_running"] = is_running
                if not is_running and not log.get("end_time"):
                    log["end_time"] = datetime.now().isoformat()
                self.logs[i] = log
                self.save_logs()
                return

    def clear_old_logs(self, days: int = 7):
        """
        清除旧日志

        Args:
            days: 保留天数
        """
        from datetime import timedelta

        now = datetime.now()
        filtered_logs = []

        for log in self.logs:
            try:
                # 检查是否是运行中的命令
                if log.get("is_running", False):
                    filtered_logs.append(log)
                    continue

                # 检查日期
                start_time = datetime.fromisoformat(log["start_time"])
                if start_time > (now - timedelta(days=days)):
                    filtered_logs.append(log)
            except Exception as e:
                print(f"处理日志时出错: {str(e)}")
                # 如果解析出错，保留该日志
                filtered_logs.append(log)

        self.logs = filtered_logs
        self.save_logs()
