#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import time
from typing import Dict, List, Optional, Callable

from core.command_executor import CommandExecutor, CommandInfo


class StatusMonitor:
    """状态监控类，负责监控命令执行状态并更新UI"""
    
    def __init__(self, command_executor: CommandExecutor):
        self.command_executor = command_executor
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_monitor = threading.Event()
        self.on_status_update: Optional[Callable[[Dict[str, CommandInfo]], None]] = None
        
    def set_status_update_callback(self, callback: Callable[[Dict[str, CommandInfo]], None]):
        """设置状态更新的回调函数"""
        self.on_status_update = callback
        
    def start_monitoring(self):
        """启动监控线程"""
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.stop_monitor.clear()
            self.monitor_thread = threading.Thread(
                target=self._monitor_status,
                daemon=True
            )
            self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控线程"""
        self.stop_monitor.set()
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
            self.monitor_thread = None
    
    def _monitor_status(self):
        """监控状态的线程"""
        while not self.stop_monitor.is_set():
            try:
                # 获取所有命令的状态
                commands = {
                    cmd.id: cmd for cmd in self.command_executor.get_all_commands()
                }
                
                # 通知UI更新
                if self.on_status_update:
                    self.on_status_update(commands)
                    
            except Exception as e:
                print(f"监控状态错误: {str(e)}")
                
            # 每秒更新一次
            time.sleep(1)
    
    def check_running_commands(self) -> List[CommandInfo]:
        """
        检查正在运行的命令
        
        Returns:
            List[CommandInfo]: 正在运行的命令列表
        """
        return [
            cmd for cmd in self.command_executor.get_all_commands()
            if cmd.is_running
        ]
