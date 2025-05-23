#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import time
import uuid
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime

from core.ssh_manager import SSHManager


class CommandInfo:
    """命令信息类，存储命令的详细信息"""

    def __init__(self, command: str, pid: int = -1):
        self.id = str(uuid.uuid4())
        self.command = command
        self.pid = pid
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.status = "准备中"  # 准备中, 运行中, 已完成, 失败
        self.is_running = False
        self.output = ""
        self.error = ""

    def to_dict(self) -> Dict:
        """转换为字典，用于日志记录"""
        return {
            "id": self.id,
            "command": self.command,
            "pid": self.pid,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "is_running": self.is_running
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'CommandInfo':
        """从字典创建命令信息对象，用于日志恢复"""
        cmd = cls(data["command"], data["pid"])
        cmd.id = data["id"]
        cmd.start_time = datetime.fromisoformat(data["start_time"])
        if data["end_time"]:
            cmd.end_time = datetime.fromisoformat(data["end_time"])
        cmd.status = data["status"]
        cmd.is_running = data["is_running"]
        return cmd


class CommandExecutor:
    """命令执行器，负责执行命令并管理命令状态"""

    def __init__(self, ssh_manager: SSHManager):
        self.ssh_manager = ssh_manager
        self.commands: Dict[str, CommandInfo] = {}  # 命令ID -> 命令信息
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_monitor = threading.Event()
        self.on_status_change: Optional[Callable[[str, str], None]] = None
        self.on_output_update: Optional[Callable[[str, str], None]] = None

    def set_status_callback(self, callback: Callable[[str, str], None]):
        """设置状态变化的回调函数"""
        self.on_status_change = callback

    def set_output_callback(self, callback: Callable[[str, str], None]):
        """设置输出更新的回调函数"""
        self.on_output_update = callback

    def execute_command(self, command: str) -> Tuple[bool, str, CommandInfo]:
        """
        执行命令

        Args:
            command: 要执行的命令

        Returns:
            Tuple[bool, str, CommandInfo]: (是否成功, 错误信息, 命令信息)
        """
        if not self.ssh_manager.is_connected():
            return False, "未连接到服务器", CommandInfo(command)

        # 创建命令信息对象
        cmd_info = CommandInfo(command)
        self.commands[cmd_info.id] = cmd_info

        # 启动执行线程
        thread = threading.Thread(
            target=self._execute_command_thread,
            args=(cmd_info,),
            daemon=True
        )
        thread.start()

        # 确保监控线程在运行
        self._ensure_monitor_running()

        return True, "", cmd_info

    def _execute_command_thread(self, cmd_info: CommandInfo):
        """
        在线程中执行命令

        Args:
            cmd_info: 命令信息对象
        """
        try:
            # 执行命令并获取PID
            _, pid, error = self.ssh_manager.execute_command(cmd_info.command)

            if pid == -1:
                cmd_info.status = "失败"
                cmd_info.error = error
                cmd_info.end_time = datetime.now()
                if self.on_status_change:
                    self.on_status_change(cmd_info.id, cmd_info.status)
                return

            cmd_info.pid = pid
            cmd_info.status = "运行中"
            cmd_info.is_running = True

            if self.on_status_change:
                self.on_status_change(cmd_info.id, cmd_info.status)

            # 获取命令输出
            try:
                self._update_command_output(cmd_info)
            except Exception as e:
                import traceback
                error_msg = f"获取命令输出错误: {str(e)}\n{traceback.format_exc()}"
                print(error_msg)
                cmd_info.error += f"\n{error_msg}"
                if self.on_output_update:
                    self.on_output_update(cmd_info.id, f"\n{error_msg}")

        except Exception as e:
            import traceback
            error_msg = f"执行命令错误: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            cmd_info.status = "失败"
            cmd_info.error = error_msg
            cmd_info.end_time = datetime.now()
            cmd_info.is_running = False
            if self.on_status_change:
                self.on_status_change(cmd_info.id, cmd_info.status)

    def _update_command_output(self, cmd_info: CommandInfo):
        """
        更新命令输出

        Args:
            cmd_info: 命令信息对象
        """
        if not cmd_info.is_running or cmd_info.pid <= 0:
            return

        try:
            # 使用ps命令检查进程是否存在
            check_cmd = f"ps -p {cmd_info.pid} -o pid= || echo ''"
            stdout, _ = self.ssh_manager.get_command_output(check_cmd)

            if not stdout.strip():
                # 进程已结束
                cmd_info.is_running = False
                cmd_info.status = "已完成"
                cmd_info.end_time = datetime.now()
                if self.on_status_change:
                    self.on_status_change(cmd_info.id, cmd_info.status)
                return

            # 获取命令输出
            output_cmd = f"cat /proc/{cmd_info.pid}/fd/1 2>/dev/null || echo ''"
            stdout, _ = self.ssh_manager.get_command_output(output_cmd)

            if stdout and stdout != "":
                # 添加新输出
                if cmd_info.output != stdout:
                    new_output = stdout[len(cmd_info.output):]
                    if new_output:
                        cmd_info.output = stdout
                        if self.on_output_update:
                            self.on_output_update(cmd_info.id, new_output)

            # 获取错误输出
            error_cmd = f"cat /proc/{cmd_info.pid}/fd/2 2>/dev/null || echo ''"
            _, stderr = self.ssh_manager.get_command_output(error_cmd)

            if stderr and stderr != "":
                # 添加新错误输出
                if cmd_info.error != stderr:
                    new_error = stderr[len(cmd_info.error):]
                    if new_error:
                        cmd_info.error = stderr
                        if self.on_output_update:
                            self.on_output_update(cmd_info.id, f"错误: {new_error}")

        except Exception as e:
            import traceback
            error_msg = f"\n获取输出错误: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)

            if cmd_info.error.find(str(e)) == -1:  # 避免重复添加相同的错误
                cmd_info.error += error_msg
                if self.on_output_update:
                    self.on_output_update(cmd_info.id, error_msg)

    def _ensure_monitor_running(self):
        """确保监控线程在运行"""
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.stop_monitor.clear()
            self.monitor_thread = threading.Thread(
                target=self._monitor_commands,
                daemon=True
            )
            self.monitor_thread.start()

    def _monitor_commands(self):
        """监控命令状态的线程"""
        while not self.stop_monitor.is_set():
            try:
                # 检查所有运行中的命令
                for cmd_id, cmd_info in list(self.commands.items()):
                    if cmd_info.is_running and cmd_info.pid > 0:
                        _, is_running = self.ssh_manager.check_command_status(cmd_info.pid)

                        # 更新状态
                        if cmd_info.is_running != is_running:
                            cmd_info.is_running = is_running
                            if not is_running:
                                cmd_info.status = "已完成"
                                cmd_info.end_time = datetime.now()

                            if self.on_status_change:
                                self.on_status_change(cmd_id, cmd_info.status)

                        # 更新输出
                        self._update_command_output(cmd_info)

            except Exception as e:
                print(f"监控命令错误: {str(e)}")

            # 每秒检查一次
            time.sleep(1)

    def stop_command(self, cmd_id: str) -> Tuple[bool, str]:
        """
        停止命令

        Args:
            cmd_id: 命令ID

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        if cmd_id not in self.commands:
            return False, "命令不存在"

        cmd_info = self.commands[cmd_id]
        if not cmd_info.is_running or cmd_info.pid <= 0:
            return False, "命令未在运行"

        try:
            # 发送终止信号
            kill_cmd = f"kill {cmd_info.pid}"
            self.ssh_manager.get_command_output(kill_cmd)

            # 更新状态
            cmd_info.is_running = False
            cmd_info.status = "已终止"
            cmd_info.end_time = datetime.now()

            if self.on_status_change:
                self.on_status_change(cmd_id, cmd_info.status)

            return True, "命令已终止"
        except Exception as e:
            return False, f"终止命令错误: {str(e)}"

    def get_command_info(self, cmd_id: str) -> Optional[CommandInfo]:
        """
        获取命令信息

        Args:
            cmd_id: 命令ID

        Returns:
            Optional[CommandInfo]: 命令信息对象
        """
        return self.commands.get(cmd_id)

    def get_all_commands(self) -> List[CommandInfo]:
        """
        获取所有命令

        Returns:
            List[CommandInfo]: 命令信息对象列表
        """
        return list(self.commands.values())

    def stop_monitoring(self):
        """停止监控线程"""
        self.stop_monitor.set()
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
            self.monitor_thread = None
