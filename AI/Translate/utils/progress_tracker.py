#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进度跟踪和报告生成工具
"""
import os
import json
import threading
from datetime import datetime
from collections import defaultdict

from .file_utils import analyze_file_types

class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, total_files, output_report):
        """
        初始化进度跟踪器
        
        Args:
            total_files: 总文件数
            output_report: 输出报告文件路径
        """
        self.total_files = total_files
        self.output_report = output_report
        self.processed_files = []
        self.failed_files = {}  # {file_path: reason}
        self.skipped_files = {}  # {file_path: reason}
        self.start_time = datetime.now()
        self.lock = threading.Lock()
        
    def add_processed_file(self, file_path):
        """
        添加已处理文件
        
        Args:
            file_path: 文件路径
        """
        with self.lock:
            if file_path not in self.processed_files:
                self.processed_files.append(file_path)
            
    def add_failed_file(self, file_path, reason):
        """
        添加处理失败的文件
        
        Args:
            file_path: 文件路径
            reason: 失败原因
        """
        with self.lock:
            self.failed_files[file_path] = reason
            
    def add_skipped_file(self, file_path, reason):
        """
        添加跳过的文件
        
        Args:
            file_path: 文件路径
            reason: 跳过原因
        """
        with self.lock:
            self.skipped_files[file_path] = reason
            
    def get_progress(self):
        """
        获取当前进度
        
        Returns:
            dict: 进度信息
        """
        with self.lock:
            processed = len(self.processed_files)
            failed = len(self.failed_files)
            skipped = len(self.skipped_files)
            total_handled = processed + failed + skipped
            
            return {
                'total': self.total_files,
                'processed': processed,
                'failed': failed,
                'skipped': skipped,
                'total_handled': total_handled,
                'progress_percentage': total_handled / self.total_files * 100 if self.total_files > 0 else 0,
                'success_rate': processed / self.total_files * 100 if self.total_files > 0 else 0
            }
            
    def format_time_delta(self, end_time=None):
        """
        格式化时间差
        
        Args:
            end_time: 结束时间，如果为None则使用当前时间
            
        Returns:
            str: 格式化后的时间差
        """
        if end_time is None:
            end_time = datetime.now()
            
        td = end_time - self.start_time
        hours, remainder = divmod(td.total_seconds(), 3600)
        minutes, remainder = divmod(remainder, 60)
        seconds, milliseconds = divmod(remainder, 1)
        milliseconds *= 1000
        
        parts = []
        if hours > 0:
            parts.append(f"{int(hours)}小时")
        if minutes > 0 or hours > 0:
            parts.append(f"{int(minutes)}分")
        if seconds > 0 or minutes > 0 or hours > 0:
            parts.append(f"{int(seconds)}秒")
        parts.append(f"{int(milliseconds)}毫秒")
        
        return "".join(parts)
            
    def save_progress(self, save_path=None):
        """
        保存进度到文件
        
        Args:
            save_path: 保存路径，如果为None则使用默认路径
            
        Returns:
            bool: 是否保存成功
        """
        if save_path is None:
            save_dir = os.path.dirname(self.output_report)
            save_path = os.path.join(save_dir, '.translate_progress.json')
            
        with self.lock:
            progress = {
                'processed_files': self.processed_files,
                'failed_files': self.failed_files,
                'skipped_files': self.skipped_files,
                'total_files': self.total_files,
                'start_time': self.start_time.isoformat(),
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                # 确保目录存在
                save_dir = os.path.dirname(save_path)
                if save_dir and not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                    
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(progress, f, ensure_ascii=False, indent=2)
                return True
            except Exception as e:
                print(f"保存进度失败: {e}")
                return False
                
    def load_progress(self, save_path=None):
        """
        从文件加载进度
        
        Args:
            save_path: 保存路径，如果为None则使用默认路径
            
        Returns:
            bool: 是否加载成功
        """
        if save_path is None:
            save_dir = os.path.dirname(self.output_report)
            save_path = os.path.join(save_dir, '.translate_progress.json')
            
        if os.path.exists(save_path):
            try:
                with open(save_path, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                    
                with self.lock:
                    self.processed_files = progress.get('processed_files', [])
                    self.failed_files = progress.get('failed_files', {})
                    self.skipped_files = progress.get('skipped_files', {})
                    
                    # 尝试恢复开始时间
                    start_time_str = progress.get('start_time')
                    if start_time_str:
                        try:
                            self.start_time = datetime.fromisoformat(start_time_str)
                        except:
                            self.start_time = datetime.now()
                            
                return True
            except Exception as e:
                print(f"加载进度失败: {e}")
        return False
        
    def generate_report(self, all_files=None):
        """
        生成处理报告
        
        Args:
            all_files: 所有文件的路径列表，用于分析文件类型
            
        Returns:
            bool: 是否生成成功
        """
        try:
            # 确保输出目录存在
            report_dir = os.path.dirname(self.output_report)
            if report_dir and not os.path.exists(report_dir):
                os.makedirs(report_dir)
            
            end_time = datetime.now()
            elapsed_time = self.format_time_delta(end_time)
            
            with self.lock:
                processed = len(self.processed_files)
                failed = len(self.failed_files)
                skipped = len(self.skipped_files)
                
                # 按失败原因分类
                failure_reasons = defaultdict(list)
                for file_path, reason in self.failed_files.items():
                    failure_reasons[reason].append(file_path)
                
                # 按跳过原因分类
                skip_reasons = defaultdict(list)
                for file_path, reason in self.skipped_files.items():
                    skip_reasons[reason].append(file_path)
                
                # 分析文件类型
                file_types = {}
                if all_files:
                    file_types = analyze_file_types(all_files)
                
                with open(self.output_report, 'w', encoding='utf-8') as f:
                    f.write(f"# 注释翻译处理报告\n\n")
                    f.write(f"- 处理时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"- 总文件数: {self.total_files}\n")
                    f.write(f"- 成功处理: {processed} ({processed/self.total_files*100:.2f}% 如果总文件数不为0)\n")
                    f.write(f"- 处理失败: {failed}\n")
                    f.write(f"- 跳过文件: {skipped}\n")
                    f.write(f"- 处理耗时: {elapsed_time}\n\n")
                    
                    # 添加文件类型分布信息
                    if file_types:
                        f.write("## 文件类型分布\n\n")
                        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
                            f.write(f"- {ext}: {count} 个文件 ({count/self.total_files*100:.2f}% 如果总文件数不为0)\n")
                        f.write("\n")
                    
                    # 添加失败文件信息
                    if failure_reasons:
                        f.write(f"## 处理失败的文件 ({failed}个)\n\n")
                        for reason, files in sorted(failure_reasons.items(), key=lambda x: len(x[1]), reverse=True):
                            f.write(f"### {reason} ({len(files)}个)\n\n")
                            for file_path in sorted(files):
                                f.write(f"- {file_path}\n")
                            f.write("\n")
                    
                    # 添加跳过文件信息
                    if skip_reasons:
                        f.write(f"## 跳过的文件 ({skipped}个)\n\n")
                        for reason, files in sorted(skip_reasons.items(), key=lambda x: len(x[1]), reverse=True):
                            f.write(f"### {reason} ({len(files)}个)\n\n")
                            for file_path in sorted(files):
                                f.write(f"- {file_path}\n")
                            f.write("\n")
                
            return True
        except Exception as e:
            print(f"生成报告失败: {e}")
            return False
