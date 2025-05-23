#!/usr/bin/env python
# -*- coding: utf-8 -*-

import paramiko
import threading
from typing import Optional, Tuple, Callable


class SSHManager:
    """SSH连接管理类，负责建立和管理SSH连接"""

    def __init__(self):
        self.client: Optional[paramiko.SSHClient] = None
        self.connected = False
        self.host = ""
        self.port = 22
        self.username = ""
        self.password = ""
        self.connection_lock = threading.Lock()
        self.on_connection_change: Optional[Callable[[bool], None]] = None

    def set_connection_callback(self, callback: Callable[[bool], None]):
        """设置连接状态变化的回调函数"""
        self.on_connection_change = callback

    def connect(self, host: str, port: int, username: str, password: str) -> Tuple[bool, str]:
        """
        建立SSH连接

        Args:
            host: 主机地址
            port: 端口
            username: 用户名
            password: 密码

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        with self.connection_lock:
            if self.connected:
                return True, "已连接"

            # 验证参数
            if not host:
                return False, "主机地址不能为空"

            if not username:
                return False, "用户名不能为空"

            # 保存连接信息
            self.host = host
            self.port = port
            self.username = username
            self.password = password

            try:
                print(f"正在连接到 {host}:{port}...")

                # 创建SSH客户端
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                # 尝试连接
                print(f"使用用户名 {username} 进行连接...")
                self.client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=10,
                    allow_agent=False,
                    look_for_keys=False
                )

                # 测试连接是否成功
                print("测试连接...")
                _, stdout, _ = self.client.exec_command("echo 连接测试")
                result = stdout.read().decode().strip()
                if result != "连接测试":
                    print(f"连接测试失败，返回: {result}")
                    self.client.close()
                    return False, "连接测试失败"

                print("连接成功")
                self.connected = True
                if self.on_connection_change:
                    self.on_connection_change(True)
                return True, "连接成功"

            except paramiko.AuthenticationException as e:
                print(f"认证失败: {str(e)}")
                return False, "认证失败，请检查用户名和密码"

            except paramiko.SSHException as e:
                print(f"SSH连接错误: {str(e)}")
                return False, f"SSH连接错误: {str(e)}"

            except Exception as e:
                import traceback
                error_msg = f"连接错误: {str(e)}\n{traceback.format_exc()}"
                print(error_msg)
                return False, f"连接错误: {str(e)}"

    def disconnect(self) -> Tuple[bool, str]:
        """
        断开SSH连接

        Returns:
            Tuple[bool, str]: (是否成功, 信息)
        """
        with self.connection_lock:
            if not self.connected:
                return True, "未连接"

            try:
                if self.client:
                    self.client.close()
                self.connected = False
                if self.on_connection_change:
                    self.on_connection_change(False)
                return True, "已断开连接"
            except Exception as e:
                return False, f"断开连接错误: {str(e)}"

    def execute_command(self, command: str) -> Tuple[str, int, str]:
        """
        执行命令并获取PID

        Args:
            command: 要执行的命令

        Returns:
            Tuple[str, int, str]: (命令ID, PID, 错误信息)
        """
        if not self.connected or not self.client:
            return "", -1, "未连接到服务器"

        try:
            # 使用特殊技巧获取命令的PID
            pid_command = f"{{ {command}; }} & pid=$!; echo $pid; wait $pid; echo $?"
            print(f"执行命令: {pid_command}")

            try:
                _, stdout, stderr = self.client.exec_command(pid_command)

                # 读取PID
                pid_str = stdout.readline().strip()
                print(f"获取到PID字符串: '{pid_str}'")

                try:
                    pid = int(pid_str)
                    print(f"成功转换PID: {pid}")
                    return command, pid, ""
                except ValueError as ve:
                    error_msg = f"无法将PID字符串转换为整数: '{pid_str}', 错误: {str(ve)}"
                    print(error_msg)

                    # 读取错误输出
                    stderr_output = stderr.read().decode('utf-8')
                    if stderr_output:
                        error_msg += f"\n错误输出: {stderr_output}"
                        print(f"错误输出: {stderr_output}")

                    return command, -1, error_msg

            except Exception as e:
                import traceback
                error_msg = f"执行SSH命令时出错: {str(e)}\n{traceback.format_exc()}"
                print(error_msg)
                return command, -1, error_msg

        except Exception as e:
            import traceback
            error_msg = f"执行命令错误: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return "", -1, error_msg

    def check_command_status(self, pid: int) -> Tuple[str, bool]:
        """
        检查命令执行状态

        Args:
            pid: 进程ID

        Returns:
            Tuple[str, bool]: (状态描述, 是否在运行)
        """
        if not self.connected or not self.client:
            return "未连接到服务器", False

        try:
            # 检查进程是否存在
            check_cmd = f"ps -p {pid} -o state= || echo 'X'"
            _, stdout, _ = self.client.exec_command(check_cmd)
            status = stdout.read().decode().strip()

            if status == 'X':
                return "已结束", False
            elif status == 'R':
                return "运行中", True
            elif status == 'S':
                return "休眠中", True
            elif status == 'D':
                return "不可中断", True
            elif status == 'Z':
                return "僵尸进程", False
            elif status == 'T':
                return "已停止", False
            else:
                return f"未知状态: {status}", False

        except Exception as e:
            return f"检查状态错误: {str(e)}", False

    def get_command_output(self, command: str) -> Tuple[str, str]:
        """
        获取命令的输出

        Args:
            command: 要执行的命令

        Returns:
            Tuple[str, str]: (标准输出, 标准错误)
        """
        if not self.connected or not self.client:
            return "", "未连接到服务器"

        try:
            _, stdout, stderr = self.client.exec_command(command)
            stdout_str = stdout.read().decode('utf-8')
            stderr_str = stderr.read().decode('utf-8')
            return stdout_str, stderr_str
        except Exception as e:
            return "", f"获取输出错误: {str(e)}"

    def is_connected(self) -> bool:
        """
        检查是否已连接

        Returns:
            bool: 是否已连接
        """
        return self.connected
