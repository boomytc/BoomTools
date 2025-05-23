#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SSH脚本执行器演示脚本
展示新增功能和配置文件生成
"""

import json
import os
from main import ConfigManager

def demo_config_manager():
    """演示配置管理功能"""
    print("=== SSH脚本执行器功能演示 ===\n")
    
    # 创建配置管理器
    config_manager = ConfigManager()
    
    print("1. 测试配置文件路径:")
    print(f"   配置文件位置: {config_manager.config_file}")
    print(f"   文件是否存在: {os.path.exists(config_manager.config_file)}\n")
    
    # 添加示例连接
    print("2. 添加示例连接配置:")
    config_manager.add_connection("192.168.1.100", 22, "user1", "password1")
    config_manager.add_connection("example.com", 2222, "admin", "secret123")
    print("   已添加两个示例连接\n")
    
    # 设置最后连接
    print("3. 设置最后使用的连接:")
    config_manager.set_last_connection("192.168.1.100", 22, "user1", "password1")
    print("   已设置最后连接为: user1@192.168.1.100:22\n")
    
    # 添加命令历史
    print("4. 添加命令历史记录:")
    demo_commands = [
        "ls -la",
        "ps aux",
        "top",
        "df -h",
        "free -m",
        "uname -a",
        "whoami",
        "pwd",
        "cat /etc/os-release",
        "systemctl status nginx"
    ]
    
    for cmd in demo_commands:
        config_manager.add_command_history(cmd)
        print(f"   添加命令: {cmd}")
    
    print(f"\n   总共保存了 {len(config_manager.get_command_history())} 条命令历史\n")
    
    # 显示最终配置
    print("5. 生成的配置文件内容:")
    print("-" * 50)
    with open(config_manager.config_file, 'r', encoding='utf-8') as f:
        config_content = f.read()
        print(config_content)
    print("-" * 50)
    
    print("\n=== 演示完成 ===")
    print("现在可以运行 'python main.py' 启动SSH脚本执行器")
    print("演示功能:")
    print("- 连接下拉框会显示保存的连接")
    print("- 命令输入框支持历史记录自动完成")
    print("- 使用快捷键快速操作")
    print("- 命令输出带时间戳显示")

if __name__ == "__main__":
    demo_config_manager() 