#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Tuple, Optional
import paramiko


def get_process_info(ssh_client: paramiko.SSHClient, pid: int) -> Tuple[bool, str, Optional[dict]]:
    """
    获取进程信息
    
    Args:
        ssh_client: SSH客户端
        pid: 进程ID
        
    Returns:
        Tuple[bool, str, Optional[dict]]: (是否成功, 错误信息, 进程信息)
    """
    if not ssh_client:
        return False, "SSH客户端未连接", None
        
    try:
        # 获取进程详细信息
        cmd = f"ps -p {pid} -o pid,ppid,user,stat,start,time,cmd --no-headers"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        if error:
            return False, f"获取进程信息错误: {error}", None
            
        if not output:
            return False, f"进程 {pid} 不存在", None
            
        # 解析输出
        parts = output.split(None, 6)
        if len(parts) < 7:
            return False, f"无法解析进程信息: {output}", None
            
        info = {
            "pid": int(parts[0]),
            "ppid": int(parts[1]),
            "user": parts[2],
            "state": parts[3],
            "start_time": parts[4],
            "cpu_time": parts[5],
            "command": parts[6]
        }
        
        return True, "", info
    except Exception as e:
        return False, f"获取进程信息异常: {str(e)}", None


def kill_process(ssh_client: paramiko.SSHClient, pid: int) -> Tuple[bool, str]:
    """
    终止进程
    
    Args:
        ssh_client: SSH客户端
        pid: 进程ID
        
    Returns:
        Tuple[bool, str]: (是否成功, 错误信息)
    """
    if not ssh_client:
        return False, "SSH客户端未连接"
        
    try:
        # 先尝试正常终止
        cmd = f"kill {pid}"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        error = stderr.read().decode().strip()
        
        if error:
            # 如果失败，尝试强制终止
            cmd = f"kill -9 {pid}"
            stdin, stdout, stderr = ssh_client.exec_command(cmd)
            error = stderr.read().decode().strip()
            
            if error:
                return False, f"终止进程错误: {error}"
        
        # 检查进程是否已终止
        cmd = f"ps -p {pid} -o pid --no-headers"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode().strip()
        
        if output:
            return False, f"进程 {pid} 仍在运行"
            
        return True, f"进程 {pid} 已终止"
    except Exception as e:
        return False, f"终止进程异常: {str(e)}"


def get_process_children(ssh_client: paramiko.SSHClient, pid: int) -> Tuple[bool, str, list]:
    """
    获取进程的子进程
    
    Args:
        ssh_client: SSH客户端
        pid: 进程ID
        
    Returns:
        Tuple[bool, str, list]: (是否成功, 错误信息, 子进程ID列表)
    """
    if not ssh_client:
        return False, "SSH客户端未连接", []
        
    try:
        # 获取子进程
        cmd = f"pgrep -P {pid}"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode().strip()
        
        if not output:
            return True, "", []
            
        # 解析输出
        child_pids = [int(p) for p in output.split()]
        return True, "", child_pids
    except Exception as e:
        return False, f"获取子进程异常: {str(e)}", []
