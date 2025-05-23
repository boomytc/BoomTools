#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import base64
from typing import Dict, Any, Optional


class ConfigManager:
    """配置管理类，负责保存和加载配置"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config: Dict[str, Any] = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        if not os.path.exists(self.config_file):
            return {
                "connections": [],
                "last_connection": None,
                "ui_settings": {
                    "theme": "light",
                    "font_size": 12,
                    "terminal_font_size": 10
                }
            }
            
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置错误: {str(e)}")
            return {
                "connections": [],
                "last_connection": None,
                "ui_settings": {
                    "theme": "light",
                    "font_size": 12,
                    "terminal_font_size": 10
                }
            }
    
    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置错误: {str(e)}")
    
    def get_connections(self) -> list:
        """
        获取保存的连接列表
        
        Returns:
            list: 连接列表
        """
        return self.config.get("connections", [])
    
    def add_connection(self, host: str, port: int, username: str, password: str):
        """
        添加连接
        
        Args:
            host: 主机地址
            port: 端口
            username: 用户名
            password: 密码
        """
        # 简单加密密码
        encoded_password = base64.b64encode(password.encode()).decode()
        
        # 检查是否已存在
        connections = self.get_connections()
        for i, conn in enumerate(connections):
            if conn["host"] == host and conn["port"] == port and conn["username"] == username:
                # 更新现有连接
                connections[i] = {
                    "host": host,
                    "port": port,
                    "username": username,
                    "password": encoded_password
                }
                self.config["connections"] = connections
                self.save_config()
                return
        
        # 添加新连接
        connections.append({
            "host": host,
            "port": port,
            "username": username,
            "password": encoded_password
        })
        self.config["connections"] = connections
        self.save_config()
    
    def remove_connection(self, host: str, port: int, username: str):
        """
        删除连接
        
        Args:
            host: 主机地址
            port: 端口
            username: 用户名
        """
        connections = self.get_connections()
        self.config["connections"] = [
            conn for conn in connections
            if not (conn["host"] == host and conn["port"] == port and conn["username"] == username)
        ]
        self.save_config()
    
    def get_last_connection(self) -> Optional[Dict[str, Any]]:
        """
        获取上次连接
        
        Returns:
            Optional[Dict[str, Any]]: 上次连接信息
        """
        last_conn = self.config.get("last_connection")
        if last_conn:
            # 解密密码
            if "password" in last_conn:
                try:
                    last_conn["password"] = base64.b64decode(last_conn["password"].encode()).decode()
                except:
                    last_conn["password"] = ""
        return last_conn
    
    def set_last_connection(self, host: str, port: int, username: str, password: str):
        """
        设置上次连接
        
        Args:
            host: 主机地址
            port: 端口
            username: 用户名
            password: 密码
        """
        # 简单加密密码
        encoded_password = base64.b64encode(password.encode()).decode()
        
        self.config["last_connection"] = {
            "host": host,
            "port": port,
            "username": username,
            "password": encoded_password
        }
        self.save_config()
    
    def get_ui_settings(self) -> Dict[str, Any]:
        """
        获取UI设置
        
        Returns:
            Dict[str, Any]: UI设置
        """
        return self.config.get("ui_settings", {
            "theme": "light",
            "font_size": 12,
            "terminal_font_size": 10
        })
    
    def set_ui_settings(self, settings: Dict[str, Any]):
        """
        设置UI设置
        
        Args:
            settings: UI设置
        """
        self.config["ui_settings"] = settings
        self.save_config()
