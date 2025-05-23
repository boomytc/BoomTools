#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理工具
"""
import os
import json
import argparse

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file=None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config() if config_file else {}
        
    def _load_config(self):
        """
        从配置文件加载配置
        
        Returns:
            dict: 配置字典
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
        return {}
        
    def save_config(self):
        """
        保存配置到文件
        
        Returns:
            bool: 是否保存成功
        """
        if self.config_file:
            try:
                # 确保目录存在
                config_dir = os.path.dirname(self.config_file)
                if config_dir and not os.path.exists(config_dir):
                    os.makedirs(config_dir)
                    
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                return True
            except Exception as e:
                print(f"保存配置文件失败: {e}")
        return False
        
    def get(self, key, default=None):
        """
        获取配置项
        
        Args:
            key: 配置项键名
            default: 默认值
            
        Returns:
            配置项值
        """
        return self.config.get(key, default)
        
    def set(self, key, value):
        """
        设置配置项
        
        Args:
            key: 配置项键名
            value: 配置项值
        """
        self.config[key] = value
        
    def get_all(self):
        """
        获取所有配置
        
        Returns:
            dict: 配置字典
        """
        return self.config.copy()
    
    @staticmethod
    def parse_args():
        """
        解析命令行参数
        
        Returns:
            argparse.Namespace: 解析后的参数
        """
        parser = argparse.ArgumentParser(description='将C/C++文件中的英文注释翻译为中文')
        parser.add_argument('directory', help='要处理的目录路径')
        parser.add_argument('--api-key', help='智谱AI的API密钥')
        parser.add_argument('--model', default='glm-4-plus', help='使用的模型名称')
        parser.add_argument('--threads', type=int, default=20, help='线程数量 (默认: 20)')
        parser.add_argument('--exclude', nargs='+', help='要排除的目录列表')
        parser.add_argument('--output-report', help='输出处理报告的文件路径', default='report.md')
        parser.add_argument('--config', help='配置文件路径')
        parser.add_argument('--batch', action='store_true', help='使用批处理模式')
        parser.add_argument('--resume', action='store_true', help='恢复上次的处理进度')
        return parser.parse_args()
    
    @staticmethod
    def create_default_config(config_file):
        """
        创建默认配置文件
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            ConfigManager: 配置管理器实例
        """
        config = ConfigManager(config_file)
        config.set('api_key', os.environ.get('ZHIPUAI_API_KEY', ''))
        config.set('model', 'glm-4-plus')
        config.set('threads', 20)
        config.set('excluded_dirs', ['terrsimPlugins', 'terrsimWrappers'])
        config.set('output_report', 'report.md')
        config.set('batch_mode', False)
        config.save_config()
        return config
    
    @staticmethod
    def merge_args_with_config(args):
        """
        合并命令行参数和配置文件
        
        Args:
            args: 命令行参数
            
        Returns:
            dict: 合并后的配置
        """
        # 首先加载配置文件
        config = ConfigManager(args.config) if args.config else ConfigManager()
        
        # 合并配置
        merged_config = {
            'directory': args.directory,
            'api_key': args.api_key or config.get('api_key') or os.environ.get('ZHIPUAI_API_KEY', ''),
            'model': args.model or config.get('model', 'glm-4-plus'),
            'threads': args.threads or config.get('threads', 20),
            'exclude': args.exclude or config.get('excluded_dirs', []),
            'output_report': args.output_report or config.get('output_report', 'report.md'),
            'batch_mode': args.batch or config.get('batch_mode', False),
            'resume': args.resume or config.get('resume', False)
        }
        
        return merged_config
