#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译结果验证工具
"""
import re

def validate_translation(original, translated):
    """
    验证翻译结果是否有效

    Args:
        original: 原始文本
        translated: 翻译后的文本

    Returns:
        tuple: (是否有效, 错误信息)
    """
    # 基本验证：检查是否为空
    if not translated:
        return False, "翻译结果为空"

    # 检查是否与原文完全相同
    if original == translated:
        return False, "翻译后内容与原文完全相同"

    # 结构验证
    validation_results = [
        validate_brackets(original, translated),
        validate_code_keywords(original, translated),
        validate_string_literals(original, translated),
        validate_code_structure(original, translated),
        validate_comment_translation_quality(original, translated)
    ]

    # 检查是否有任何验证失败
    for is_valid, error_msg in validation_results:
        if not is_valid:
            return False, error_msg

    return True, None

def validate_brackets(original, translated):
    """
    验证花括号、方括号和圆括号的匹配

    Args:
        original: 原始文本
        translated: 翻译后的文本

    Returns:
        tuple: (是否有效, 错误信息)
    """
    bracket_pairs = [
        ('{', '}', '花括号'),
        ('[', ']', '方括号'),
        ('(', ')', '圆括号')
    ]

    for open_char, close_char, name in bracket_pairs:
        original_open = original.count(open_char)
        original_close = original.count(close_char)
        translated_open = translated.count(open_char)
        translated_close = translated.count(close_char)

        if original_open != translated_open:
            return False, f"翻译结果中{name}开始符数量不匹配 (原文: {original_open}, 译文: {translated_open})"

        if original_close != translated_close:
            return False, f"翻译结果中{name}结束符数量不匹配 (原文: {original_close}, 译文: {translated_close})"

    return True, None

def validate_code_keywords(original, translated):
    """
    验证代码关键字是否保留

    Args:
        original: 原始文本
        translated: 翻译后的文本

    Returns:
        tuple: (是否有效, 错误信息)
    """
    # C/C++ 关键字列表
    keywords = [
        'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'break', 'continue',
        'return', 'goto', 'try', 'catch', 'throw', 'class', 'struct', 'enum',
        'union', 'typedef', 'namespace', 'using', 'template', 'virtual', 'static',
        'const', 'volatile', 'extern', 'inline', 'explicit', 'friend', 'private',
        'protected', 'public', 'operator', 'new', 'delete', 'this', 'sizeof'
    ]

    # 使用正则表达式匹配完整的关键字（确保它们是独立的单词）
    for keyword in keywords:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        original_count = len(re.findall(pattern, original))
        translated_count = len(re.findall(pattern, translated))

        if original_count != translated_count:
            return False, f"翻译结果中关键字 '{keyword}' 数量不匹配 (原文: {original_count}, 译文: {translated_count})"

    return True, None

def validate_string_literals(original, translated):
    """
    验证字符串字面量是否保留

    Args:
        original: 原始文本
        translated: 翻译后的文本

    Returns:
        tuple: (是否有效, 错误信息)
    """
    # 匹配双引号字符串（考虑转义）
    string_pattern = r'"(?:[^"\\]|\\.)*"'
    original_strings = re.findall(string_pattern, original)
    translated_strings = re.findall(string_pattern, translated)

    if len(original_strings) != len(translated_strings):
        return False, f"翻译结果中字符串字面量数量不匹配 (原文: {len(original_strings)}, 译文: {len(translated_strings)})"

    # 检查每个字符串是否保留
    for i, orig_str in enumerate(original_strings):
        if orig_str not in translated_strings:
            return False, f"翻译结果中缺少原始字符串: {orig_str}"

    return True, None

def validate_code_structure(original, translated):
    """
    验证代码结构是否保留

    Args:
        original: 原始文本
        translated: 翻译后的文本

    Returns:
        tuple: (是否有效, 错误信息)
    """
    # 检查分号数量
    original_semicolons = original.count(';')
    translated_semicolons = translated.count(';')
    if original_semicolons != translated_semicolons:
        return False, f"翻译结果中分号数量不匹配 (原文: {original_semicolons}, 译文: {translated_semicolons})"

    # 检查预处理指令
    preprocessor_pattern = r'#\s*\w+'
    original_preprocessors = re.findall(preprocessor_pattern, original)
    translated_preprocessors = re.findall(preprocessor_pattern, translated)
    if len(original_preprocessors) != len(translated_preprocessors):
        return False, f"翻译结果中预处理指令数量不匹配 (原文: {len(original_preprocessors)}, 译文: {len(translated_preprocessors)})"

    # 检查注释标记
    comment_markers = ['//', '/*', '*/']
    for marker in comment_markers:
        original_count = original.count(marker)
        translated_count = translated.count(marker)
        if original_count != translated_count:
            return False, f"翻译结果中注释标记 '{marker}' 数量不匹配 (原文: {original_count}, 译文: {translated_count})"

    # 检查行数是否匹配
    original_lines = original.splitlines()
    translated_lines = translated.splitlines()
    if len(original_lines) != len(translated_lines):
        return False, f"翻译结果中行数不匹配 (原文: {len(original_lines)}, 译文: {len(translated_lines)})"

    # 检查缩进是否保持一致
    for i, (orig_line, trans_line) in enumerate(zip(original_lines, translated_lines)):
        orig_indent = len(orig_line) - len(orig_line.lstrip())
        trans_indent = len(trans_line) - len(trans_line.lstrip())
        if orig_indent != trans_indent:
            return False, f"第 {i+1} 行缩进不匹配 (原文: {orig_indent}, 译文: {trans_indent})"

    # 检查函数和类定义是否保持一致
    function_pattern = r'(\w+\s+\w+\s*\([^)]*\)\s*(?:const|override|final|noexcept)?\s*(?:=\s*0)?\s*(?:{\s*)?)'
    class_pattern = r'(class|struct|enum|union)\s+\w+(?:\s*:\s*(?:public|protected|private)\s+\w+(?:\s*,\s*(?:public|protected|private)\s+\w+)*)?\s*{'

    for pattern in [function_pattern, class_pattern]:
        original_matches = re.findall(pattern, original)
        translated_matches = re.findall(pattern, translated)
        if len(original_matches) != len(translated_matches):
            return False, f"翻译结果中函数或类定义数量不匹配 (原文: {len(original_matches)}, 译文: {len(translated_matches)})"

    return True, None

def validate_comment_translation_quality(original, translated):
    """
    验证注释翻译质量

    Args:
        original: 原始文本
        translated: 翻译后的文本

    Returns:
        tuple: (是否有效, 错误信息)
    """
    # 提取原始文本中的注释
    comment_pattern = r'(\/\/.*?$|\/\*[\s\S]*?\*\/)'
    original_comments = re.findall(comment_pattern, original, re.MULTILINE)
    translated_comments = re.findall(comment_pattern, translated, re.MULTILINE)

    # 检查注释数量是否匹配
    if len(original_comments) != len(translated_comments):
        return False, f"翻译结果中注释数量不匹配 (原文: {len(original_comments)}, 译文: {len(translated_comments)})"

    # 检查每个注释是否有实质性变化
    unchanged_comments = 0
    for orig_comment, trans_comment in zip(original_comments, translated_comments):
        # 如果注释完全相同，可能没有被翻译
        if orig_comment == trans_comment:
            unchanged_comments += 1

    # 如果超过20%的注释没有变化，可能翻译质量有问题
    if len(original_comments) > 0 and unchanged_comments / len(original_comments) > 0.2:
        return False, f"有 {unchanged_comments} 个注释未被翻译，占比 {unchanged_comments / len(original_comments) * 100:.2f}%"

    return True, None
