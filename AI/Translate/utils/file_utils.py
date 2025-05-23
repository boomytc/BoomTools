#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件操作相关工具，包括文件遍历、编码检测、读写操作等
"""
import os
import codecs
import threading

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    print("警告: python-magic 库未安装，将使用简单的文件类型检测方法")

# 文件备份存储
_backup_files = {}
_backup_files_lock = threading.Lock()

def get_file_encoding(file_path):
    """
    获取文件编码
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 检测到的编码，如果检测失败则返回 None
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(4096)  # 读取前4KB进行检测
            
            # 检查BOM标记
            if raw_data.startswith(codecs.BOM_UTF8):
                return 'utf-8-sig'
            elif raw_data.startswith(codecs.BOM_UTF16_LE):
                return 'utf-16-le'
            elif raw_data.startswith(codecs.BOM_UTF16_BE):
                return 'utf-16-be'
            elif raw_data.startswith(codecs.BOM_UTF32_LE):
                return 'utf-32-le'
            elif raw_data.startswith(codecs.BOM_UTF32_BE):
                return 'utf-32-be'
            
            # 尝试使用magic库检测
            if MAGIC_AVAILABLE:
                try:
                    m = magic.Magic(mime_encoding=True)
                    encoding = m.from_buffer(raw_data)
                    if encoding and encoding not in ['binary', 'unknown-8bit', 'application/octet-stream']:
                        try:
                            raw_data.decode(encoding)
                            return encoding
                        except:
                            pass
                except:
                    pass
            
            # 尝试常见编码
            for encoding in ['utf-8', 'gbk', 'gb2312', 'big5', 'shift-jis', 'latin-1']:
                try:
                    raw_data.decode(encoding)
                    return encoding
                except:
                    continue
            
            # 如果所有方法都失败，返回latin-1作为后备编码
            return 'latin-1'
    except Exception as e:
        print(f"编码检测失败: {e}")
        return None

def is_binary_file(file_path):
    """
    判断是否为二进制文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否为二进制文件
    """
    try:
        # 如果有magic库，优先使用
        if MAGIC_AVAILABLE:
            try:
                mime = magic.Magic(mime=True)
                file_type = mime.from_file(file_path)
                if file_type and not file_type.startswith(('text/', 'application/json', 'application/xml')):
                    return True
            except:
                pass
        
        # 读取文件前4KB检查是否为二进制
        with open(file_path, 'rb') as f:
            chunk = f.read(4096)
            # 检查是否包含空字节，这通常表示二进制文件
            if b'\x00' in chunk:
                return True
            # 检查非ASCII字符的比例
            non_ascii = sum(1 for b in chunk if b < 32 and b not in (9, 10, 13))  # 排除tab, LF, CR
            if len(chunk) > 0 and non_ascii / len(chunk) > 0.1:  # 如果非ASCII字符超过10%，认为是二进制
                return True
            return False
    except Exception as e:
        print(f"检查文件类型失败: {e}")
        return True  # 如果无法读取，保守地认为是二进制

def find_target_files(directory, extensions, excluded_dirs=None):
    """
    查找目标文件
    
    Args:
        directory: 要搜索的目录
        extensions: 目标文件扩展名列表
        excluded_dirs: 要排除的目录列表
        
    Returns:
        list: 符合条件的文件路径列表
    """
    if not os.path.isdir(directory):
        print(f"错误: {directory} 不是一个有效的目录")
        return []
        
    excluded_dirs = excluded_dirs or []
    target_files = []
    
    for root, dirs, files in os.walk(directory):
        # 跳过排除的目录
        dirs[:] = [d for d in dirs if d not in excluded_dirs and not any(
            os.path.join(os.sep, excl_dir, os.sep) in os.path.join(os.sep, root, d, os.sep)
            for excl_dir in excluded_dirs
        )]
        
        for file in files:
            file_path = os.path.join(root, file)
            _, ext = os.path.splitext(file_path)
            if ext.lower() in extensions and not is_binary_file(file_path):
                target_files.append(file_path)
                
    return target_files

def backup_file(file_path):
    """
    备份文件内容
    
    Args:
        file_path: 要备份的文件路径
        
    Returns:
        bool: 备份是否成功
    """
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        with _backup_files_lock:
            _backup_files[file_path] = content
        
        return True
    except Exception as e:
        print(f"备份文件失败: {e}")
        return False

def restore_file(file_path):
    """
    从备份恢复文件
    
    Args:
        file_path: 要恢复的文件路径
        
    Returns:
        bool: 恢复是否成功
    """
    try:
        with _backup_files_lock:
            if file_path in _backup_files:
                with open(file_path, 'wb') as f:
                    f.write(_backup_files[file_path])
                return True
        return False
    except Exception as e:
        print(f"恢复文件失败: {e}")
        return False

def safe_read_file(file_path, encoding=None):
    """
    安全读取文件内容
    
    Args:
        file_path: 文件路径
        encoding: 文件编码，如果为None则自动检测
        
    Returns:
        tuple: (文件内容, 编码) 或 (None, 错误信息)
    """
    if not encoding:
        encoding = get_file_encoding(file_path)
        if not encoding:
            return None, "无法确定文件编码"
    
    try:
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            content = f.read()
        return content, encoding
    except Exception as e:
        # 如果指定编码失败，尝试使用latin-1（它可以读取任何8位文本）
        try:
            with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
                content = f.read()
            return content, 'latin-1'
        except Exception as e2:
            return None, f"读取文件失败: {e2}"

def safe_write_file(file_path, content, encoding):
    """
    安全写入文件内容
    
    Args:
        file_path: 文件路径
        content: 要写入的内容
        encoding: 文件编码
        
    Returns:
        bool: 写入是否成功
    """
    try:
        # 尝试直接写入
        with open(file_path, 'w', encoding=encoding, errors='xmlcharrefreplace') as f:
            f.write(content)
        return True
    except UnicodeEncodeError:
        # 如果出现编码错误，尝试使用UTF-8编码
        try:
            with open(file_path, 'w', encoding='utf-8', errors='xmlcharrefreplace') as f:
                f.write(content)
            return True
        except Exception:
            # 如果还是失败，尝试使用二进制模式写入
            try:
                with open(file_path, 'wb') as f:
                    f.write(content.encode(encoding, errors='xmlcharrefreplace'))
                return True
            except Exception as e:
                print(f"写入文件失败: {e}")
                return False
    except Exception as e:
        print(f"写入文件失败: {e}")
        return False

def analyze_file_types(file_paths):
    """
    分析文件类型分布
    
    Args:
        file_paths: 文件路径列表
        
    Returns:
        dict: 文件类型统计 {扩展名: 数量}
    """
    file_types = {}
    for file_path in file_paths:
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        if ext in file_types:
            file_types[ext] += 1
        else:
            file_types[ext] = 1
    return file_types
