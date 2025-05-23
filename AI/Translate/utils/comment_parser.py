#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C/C++ 代码注释解析工具
"""
import re

# C/C++ 注释的正则表达式模式
CPP_COMMENT_PATTERN = r'(\/\/.*?$|\/\*[\s\S]*?\*\/)'

def extract_comments(code):
    """
    提取代码中的所有注释
    
    Args:
        code: 源代码字符串
        
    Returns:
        list: 提取的注释列表
    """
    return re.findall(CPP_COMMENT_PATTERN, code, re.MULTILINE)

def has_english_comments(code):
    """
    检查代码是否包含英文注释
    
    Args:
        code: 源代码字符串
        
    Returns:
        bool: 是否包含英文注释
    """
    comments = extract_comments(code)
    for comment in comments:
        # 检查是否包含至少3个连续英文字母的单词
        if re.search(r'[a-zA-Z]{3,}', comment):
            return True
    return False

def split_by_comment_blocks(content, max_chunk_size=5000):
    """
    将内容按注释块拆分
    
    Args:
        content: 源代码字符串
        max_chunk_size: 每个块的最大大小
        
    Returns:
        list: 拆分后的代码块列表
    """
    # 使用正则表达式匹配C++注释（行注释和块注释）
    parts = re.split(CPP_COMMENT_PATTERN, content, flags=re.MULTILINE)
    
    # 合并短块以减少API调用次数，同时确保注释块完整性
    chunks = []
    current_chunk = ""
    
    for part in parts:
        if not part:
            continue
            
        if len(current_chunk) + len(part) <= max_chunk_size:
            current_chunk += part
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = part
    
    if current_chunk:
        chunks.append(current_chunk)
    
    # 处理过大的块
    refined_chunks = []
    for chunk in chunks:
        if len(chunk) > max_chunk_size:
            # 如果块太大且不是一个完整的注释，进一步拆分
            if not re.fullmatch(CPP_COMMENT_PATTERN, chunk.strip()):
                # 尝试在语句边界拆分
                sub_chunks = split_at_statement_boundaries(chunk, max_chunk_size)
                refined_chunks.extend(sub_chunks)
            else:
                refined_chunks.append(chunk)
        else:
            refined_chunks.append(chunk)
    
    return refined_chunks

def split_at_statement_boundaries(text, max_size):
    """
    在语句边界拆分文本
    
    Args:
        text: 要拆分的文本
        max_size: 每个块的最大大小
        
    Returns:
        list: 拆分后的文本块列表
    """
    if len(text) <= max_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + max_size, len(text))
        
        # 如果不是文本末尾，尝试找到合适的分割点
        if end < len(text):
            # 尝试在分号、右花括号后的换行处分割
            candidates = [
                text.rfind(';\n', start, end),
                text.rfind('}\n', start, end),
                text.rfind('\n', start, end)
            ]
            
            # 选择最靠近 end 的有效分割点
            split_point = max([p for p in candidates if p != -1] or [start])
            
            if split_point > start:
                end = split_point + 1  # +1 to include the delimiter
            # 如果没有找到合适的分割点，就在 max_size 处强制分割
        
        chunks.append(text[start:end])
        start = end
    
    return chunks

def identify_comment_type(comment):
    """
    识别注释类型
    
    Args:
        comment: 注释字符串
        
    Returns:
        str: 'line' 表示行注释，'block' 表示块注释
    """
    if comment.startswith('//'):
        return 'line'
    elif comment.startswith('/*'):
        return 'block'
    return 'unknown'

def extract_comment_content(comment):
    """
    提取注释中的实际内容（去除注释符号）
    
    Args:
        comment: 注释字符串
        
    Returns:
        str: 注释内容
    """
    comment_type = identify_comment_type(comment)
    
    if comment_type == 'line':
        # 行注释: 去除 // 及其后的空格
        return re.sub(r'^\/\/\s*', '', comment)
    elif comment_type == 'block':
        # 块注释: 去除 /* 和 */ 及其间的空格
        content = re.sub(r'^\s*\/\*+\s*', '', comment)
        content = re.sub(r'\s*\*+\/\s*$', '', content)
        # 去除每行开头的 *
        content = re.sub(r'^\s*\*\s?', '', content, flags=re.MULTILINE)
        return content
    
    return comment  # 未知类型，返回原始内容
