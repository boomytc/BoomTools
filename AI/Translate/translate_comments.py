#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C/C++文件注释翻译工具
版本: 1.3
修改时间: 2024-07-25
更新说明: 
1. 放宽翻译结果的验证条件，不再检查关键代码结构
2. 不再检查翻译后长度减少是否过多
3. 只在原文与译文完全相同时判定为翻译失败
4. 优化大文件处理逻辑
5. 扩大目标文件范围，增加.c、.cpp等源文件的处理
6. 添加文件类型分布统计功能
"""

import os
import re
import sys
import argparse
from zhipuai import ZhipuAI
import time
import tqdm
import concurrent.futures
import threading
from datetime import datetime, timedelta
import magic
import codecs

# 内置API密钥
DEFAULT_API_KEY = "429cb3d87bc5458387e77f763085ac35.lHKb36viMNufF43u"

# 默认线程数
DEFAULT_THREADS = 20

# 排除的目录
EXCLUDED_DIRS = ["terrsimPlugins", "terrsimWrappers"]

# 用于线程安全的计数器
class Counter:
    def __init__(self, initial=0):
        self.value = initial
        self.lock = threading.Lock()
    
    def increment(self):
        with self.lock:
            self.value += 1
            return self.value

# 全局进度条和计数器
global_pbar = None
processed_counter = Counter()
failed_files = []  # 修改为列表，存储元组 (file_path, reason)
failed_files_lock = threading.Lock()
error_messages = {}
error_messages_lock = threading.Lock()
backup_files = {}
backup_files_lock = threading.Lock()

# Helper function for ZhipuAI API call
def _call_zhipu_api(api_key, user_prompt, system_prompt_content):
    client = ZhipuAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="glm-4-plus",
            messages=[
                {"role": "system", "content": system_prompt_content},
                {"role": "user", "content": user_prompt}
            ],
        )
        translated_text = response.choices[0].message.content.strip()
        
        # 提取代码块内容
        code_match = re.search(r'```(?:cpp)?\n([\s\S]*?)\n```', translated_text)
        if code_match:
            return code_match.group(1), None
        # If no ```cpp block, return the raw response.
        return translated_text, None 
    except Exception as e:
        return None, f"API调用出错: {str(e)}"

def format_time_delta(td):
    """格式化时间差，显示时分秒毫秒"""
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

def is_in_excluded_dir(file_path):
    """检查文件是否在排除目录中"""
    normalized_path = os.path.normpath(file_path)
    for excluded_dir in EXCLUDED_DIRS:
        if f"/{excluded_dir}/" in normalized_path.replace("\\", "/"):
            return True
    return False

def is_target_file(file_path):
    """判断是否为目标文件类型（C/C++文件）"""
    if is_in_excluded_dir(file_path):
        return False
        
    target_extensions = {'.h', '.hpp', '.c', '.cpp', '.cc', '.cxx', ''}
    _, ext = os.path.splitext(file_path)
    return ext.lower() in target_extensions

def backup_file(file_path):
    """备份原始文件"""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        with backup_files_lock:
            backup_files[file_path] = content
        
        return True
    except Exception as e:
        with error_messages_lock:
            error_messages[file_path] = f"备份文件失败: {str(e)}"
        return False

def restore_file(file_path):
    """恢复原始文件"""
    try:
        with backup_files_lock:
            if file_path in backup_files:
                with open(file_path, 'wb') as f:
                    f.write(backup_files[file_path])
                return True
        return False
    except Exception as e:
        with error_messages_lock:
            error_messages[file_path] = f"恢复文件失败: {str(e)}"
        return False

def is_binary_file(file_path):
    """判断是否为二进制文件"""
    # 尝试读取文件前4KB检查是否为二进制
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(4096)
            # 检查是否包含空字节，这通常表示二进制文件
            if b'\x00' in chunk:
                return True
            # 检查非ASCII字符的比例
            non_ascii = sum(1 for b in chunk if b < 32 and b not in (9, 10, 13))  # 排除tab, LF, CR
            if non_ascii / len(chunk) > 0.1:  # 如果非ASCII字符超过10%，认为是二进制
                return True
    except Exception as e:
        with error_messages_lock:
            error_messages[file_path] = f"检查是否为二进制文件时出错: {str(e)}"
        return True  # 如果无法读取，保守地认为是二进制
    
    return False

def is_processable_file(file_path):
    """判断文件是否可以处理"""
    if not is_target_file(file_path):
        return False
    
    if is_binary_file(file_path):
        with error_messages_lock:
            error_messages[file_path] = "文件为二进制文件，不予处理"
        return False
    
    # 尝试以文本方式打开文件
    encoding = get_file_encoding(file_path)
    if not encoding:
        with error_messages_lock:
            error_messages[file_path] = "无法确定文件编码，可能存在乱码"
        return False
    
    return True

def get_file_encoding(file_path):
    """获取文件编码"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'ascii']
    
    # 首先尝试使用chardet检测编码
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(4096)  # 读取前4KB进行检测
            
            # 检查BOM标记
            if raw_data.startswith(codecs.BOM_UTF8):
                return 'utf-8-sig'
            elif raw_data.startswith(codecs.BOM_UTF16_LE) or raw_data.startswith(codecs.BOM_UTF16_BE):
                return 'utf-16'
            
            # 尝试使用magic库检测
            try:
                import magic
                mime = magic.Magic(mime_encoding=True)
                encoding = mime.from_buffer(raw_data)
                if encoding and encoding != 'binary':
                    try:
                        # 验证编码是否有效
                        raw_data.decode(encoding)
                        return encoding
                    except:
                        pass
            except:
                pass
    except:
        pass
    
    # 尝试常见编码
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)
                return encoding
        except:
            continue
    
    # 如果上述方法都失败，尝试使用latin-1（它可以读取任何8位文本）
    try:
        with open(file_path, 'r', encoding='latin-1') as f:
            f.read(1024)
        return 'latin-1'
    except:
        pass
    
    return None

def safe_write_file(file_path, content, encoding):
    """安全地写入文件，处理编码问题"""
    try:
        # 尝试直接写入
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        return True
    except UnicodeEncodeError:
        # 如果出现编码错误，尝试使用UTF-8编码
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except:
            # 如果还是失败，尝试使用二进制模式写入
            try:
                with open(file_path, 'wb') as f:
                    f.write(content.encode(encoding, errors='xmlcharrefreplace'))
                return True
            except Exception as e:
                with error_messages_lock:
                    error_messages[file_path] = f"写入文件时出错: {str(e)}"
                return False

def process_file(file_path, api_key):
    """处理单个文件，翻译其中的英文注释"""
    global global_pbar, processed_counter, failed_files
    
    try:
        if not is_processable_file(file_path):
            with error_messages_lock:
                error_messages[file_path] = "文件不符合处理条件（可能是二进制文件或编码问题）"
            with failed_files_lock:
                failed_files.append((file_path, "文件不符合处理条件"))
            global_pbar.update(1)
            return False
        
        # 备份原始文件
        if not backup_file(file_path):
            with error_messages_lock:
                error_messages[file_path] = "备份文件失败"
            with failed_files_lock:
                failed_files.append((file_path, "备份文件失败"))
            global_pbar.update(1)
            return False
        
        encoding = get_file_encoding(file_path)
        if not encoding:
            with error_messages_lock:
                error_messages[file_path] = "无法确定文件编码"
            with failed_files_lock:
                failed_files.append((file_path, "无法确定文件编码"))
            global_pbar.update(1)
            return False
            
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
        except UnicodeDecodeError:
            # 如果指定编码失败，尝试使用latin-1（它可以读取任何8位文本）
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                encoding = 'latin-1'
            except Exception as e:
                with error_messages_lock:
                    error_messages[file_path] = f"读取文件时出错: {str(e)}"
                with failed_files_lock:
                    failed_files.append((file_path, f"读取文件时出错: {str(e)}"))
                global_pbar.update(1)
                return False
        
        # 直接翻译整个文件内容
        translated_content, error_msg = translate_file_content(api_key, content, file_path)
        
        # 检查是否有错误
        if error_msg:
            with error_messages_lock:
                error_messages[file_path] = error_msg
            # 如果是"文件不包含英文注释"的错误，也计入成功处理
            if error_msg == "文件不包含英文注释":
                processed_counter.increment()
                global_pbar.update(1)
                return True
            # 如果是"翻译后内容完全相同"的错误，也尝试写回（可能有少量变化）
            elif error_msg == "翻译后内容完全相同，可能翻译失败":
                # 仍然尝试写入，即使可能没有变化
                if not safe_write_file(file_path, translated_content, encoding):
                    # 写入失败
                    with error_messages_lock:
                        error_messages[file_path] = "写入文件失败"
                    with failed_files_lock:
                        failed_files.append((file_path, "写入文件失败"))
                else:
                    # 尝试写入成功，计算为成功处理
                    processed_counter.increment()
                global_pbar.update(1)
                return True
            with failed_files_lock:
                failed_files.append((file_path, error_msg))
            global_pbar.update(1)
            return False
        
        # 检查翻译后的内容是否与原内容相同
        if translated_content == content:
            with error_messages_lock:
                error_messages[file_path] = "翻译后内容未发生变化"
            with failed_files_lock:
                failed_files.append((file_path, "翻译后内容未发生变化"))
            global_pbar.update(1)
            return False
        
        # 安全写回文件
        if not safe_write_file(file_path, translated_content, encoding):
            # 写入失败，恢复原始文件
            restore_file(file_path)
            with error_messages_lock:
                error_messages[file_path] = "写入文件失败"
            with failed_files_lock:
                failed_files.append((file_path, "写入文件失败"))
            global_pbar.update(1)
            return False
        
        # 更新进度条
        global_pbar.update(1)
        processed_counter.increment()
        
        # 更新进度条描述
        file_name = os.path.basename(file_path)
        global_pbar.set_postfix_str(f"已处理: {processed_counter.value} | 当前: {file_name}")
        
        return True
    except Exception as e:
        error_msg = f"处理文件时出错: {str(e)}"
        with error_messages_lock:
            error_messages[file_path] = error_msg
        # 恢复原始文件
        restore_file(file_path)
        with failed_files_lock:
            failed_files.append((file_path, error_msg))
        global_pbar.update(1)
        return False

def count_target_files(directory):
    """计算目标文件数量"""
    count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if is_target_file(file_path) and not is_binary_file(file_path):
                count += 1
    return count

def translate_file_content(api_key, file_content, file_path):
    """直接将整个文件内容发送给智谱AI进行翻译"""
    try:
        # 检查文件内容是否包含英文注释
        cpp_comment_pattern = r'(\/\/.*?$|\/\*[\s\S]*?\*\/)' 
        all_comment_parts = re.findall(cpp_comment_pattern, file_content, re.MULTILINE)
        
        has_english_comments = False
        for comment_str in all_comment_parts:
            if re.search(r'[a-zA-Z]{3,}', comment_str):
                has_english_comments = True
                break
        
        if not has_english_comments:
            return file_content, "文件不包含英文注释"
        
        file_name = os.path.basename(file_path)
        file_size = len(file_content)
        
        if file_size > 15000:  # 假设15KB是API单次处理的合理大小
            return chunked_translate_file(api_key, file_content, file_path)
        
        system_prompt = "你是一个专业的代码注释翻译专家，能够精确识别C++头文件中的注释并将其从英文翻译为中文，同时完全不破坏代码结构和格式。"
        user_prompt = (
            f"请翻译以下C++头文件中的英文注释为中文，保持原有格式和注释符号。\n\n"
            f"规则：\n"
            f"1. 只翻译注释部分，不修改任何代码、变量名、字符串字面量等非注释内容\n"
            f"2. 保持所有注释符号（如//、/*、*/等）完全不变\n"
            f"3. 保持代码的缩进和换行格式\n"
            f"4. 翻译为专业且地道的中文，保持技术术语准确性\n"
            f"5. 不要添加、删除或修改任何非注释内容\n\n"
            f"文件名：{file_name}\n\n```cpp\n{file_content}\n```"
        )
        
        translated_content, api_error = _call_zhipu_api(api_key, user_prompt, system_prompt)
        
        if api_error:
            return file_content, api_error
        if translated_content is None:
             return file_content, "API调用返回空内容"

        # 验证翻译结果 - 只检查花括号匹配
        original_brackets = file_content.count('{') - file_content.count('}')
        translated_brackets = translated_content.count('{') - translated_content.count('}')
        
        if original_brackets != translated_brackets:
            return file_content, "翻译结果花括号不匹配，可能破坏了代码结构"
        
        # 如果翻译内容与原文完全相同，认为翻译失败
        if translated_content == file_content:
            return file_content, "翻译后内容完全相同，可能翻译失败"
        
        return translated_content, None
        
    except Exception as e:
        return file_content, f"翻译预处理或后处理出错: {str(e)}"

def chunked_translate_file(api_key, file_content, file_path):
    """分块翻译大文件"""
    try:
        # 将文件按注释块分割
        chunks = split_by_comment_blocks(file_content)
        translated_chunks = []
        
        system_prompt_chunk = "你是一个专业的代码注释翻译专家，能够精确识别C++代码中的注释并将其从英文翻译为中文，同时完全不破坏代码结构和格式。"

        for i, chunk in enumerate(chunks):
            # 如果chunk不包含注释或英文，直接保留
            if not re.search(r'(\/\/|\/\*|\*\/)', chunk) or not re.search(r'[a-zA-Z]{3,}', chunk):
                translated_chunks.append(chunk)
                continue
                
            user_prompt_chunk = (
                f"请翻译以下C++代码片段中的英文注释为中文，保持原有格式和注释符号。\n\n"
                f"规则：\n"
                f"1. 只翻译注释部分，不修改任何代码\n"
                f"2. 保持所有注释符号（如//、/*、*/等）完全不变\n"
                f"3. 保持代码的缩进和换行格式\n"
                f"4. 不要添加或删除任何非注释内容\n\n"
                f"代码片段 {i+1}:\n\n```cpp\n{chunk}\n```"
            )
            
            translated_chunk, api_error = _call_zhipu_api(api_key, user_prompt_chunk, system_prompt_chunk)

            if api_error:
                return file_content, f"分块翻译中API调用出错 (块 {i+1}): {api_error}"
            if translated_chunk is None:
                return file_content, f"分块翻译中API调用返回空内容 (块 {i+1})"
            
            translated_chunks.append(translated_chunk)
            
            # 避免API限流
            time.sleep(0.5)
        
        # 合并所有翻译后的块
        final_content = ''.join(translated_chunks)
        
        # 如果最终内容与原文完全相同，可能是翻译失败
        if final_content == file_content:
            return file_content, "翻译后内容完全相同，可能翻译失败"
        
        return final_content, None
        
    except Exception as e:
        return file_content, f"分块翻译出错: {str(e)}"

def split_by_comment_blocks(content):
    """将内容按注释块拆分"""
    # 使用正则表达式匹配C++注释（行注释和块注释）
    comment_pattern = r'(\/\/.*?$|\/\*[\s\S]*?\*\/)'
    
    # 将内容拆分为注释和非注释部分
    parts = re.split(comment_pattern, content, flags=re.MULTILINE)
    
    # 合并短块以减少API调用次数，同时确保注释块完整性
    chunks = []
    current_chunk = ""
    max_chunk_size = 5000  # 设置合理的块大小
    
    for part in parts:
        if len(current_chunk) + len(part) <= max_chunk_size:
            current_chunk += part
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = part
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def analyze_file_types(file_paths):
    """分析文件类型分布"""
    file_types = {}
    for file_path in file_paths:
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        if ext in file_types:
            file_types[ext] += 1
        else:
            file_types[ext] = 1
    return file_types

def main():
    parser = argparse.ArgumentParser(description='将C/C++文件中的英文注释翻译为中文')
    parser.add_argument('directory', help='要处理的目录路径')
    parser.add_argument('--api-key', default=DEFAULT_API_KEY, help='智谱AI的API密钥')
    parser.add_argument('--threads', type=int, default=DEFAULT_THREADS, help=f'线程数量 (默认: {DEFAULT_THREADS})')
    parser.add_argument('--exclude', nargs='+', help='要排除的目录列表')
    parser.add_argument('--output-report', help='输出处理报告的文件路径', default='report.md')
    args = parser.parse_args()
    
    directory = args.directory
    api_key = args.api_key
    threads = args.threads
    output_report = args.output_report
    
    # 如果输出报告路径不是绝对路径，则使用脚本所在目录
    if not os.path.isabs(output_report):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_report = os.path.join(script_dir, output_report)
    
    # 添加用户指定的排除目录
    if args.exclude:
        global EXCLUDED_DIRS
        EXCLUDED_DIRS.extend(args.exclude)
    
    print(f"排除目录: {', '.join(EXCLUDED_DIRS)}")
    
    if not os.path.isdir(directory):
        print(f"错误: {directory} 不是一个有效的目录")
        sys.exit(1)
    
    # 计算目标文件总数
    print("正在统计目标文件数量...")
    total_files = count_target_files(directory)
    print(f"找到 {total_files} 个C/C++文件 (.h, .hpp, .c, .cpp, .cc, .cxx)")
    
    if total_files == 0:
        print("未找到可处理的C/C++文件，退出程序")
        sys.exit(0)
    
    # 获取所有目标文件路径
    target_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if is_target_file(file_path) and not is_binary_file(file_path):
                target_files.append(file_path)
    
    # 分析文件类型分布
    file_types = analyze_file_types(target_files)
    
    # 初始化全局进度条
    global global_pbar
    global_pbar = tqdm.tqdm(total=total_files, desc=f"处理进度 (使用 {threads} 线程)", unit="文件")
    
    # 记录开始时间
    start_time = datetime.now()
    
    # 使用线程池执行文件处理
    # 多线程并行处理多个文件，每个线程负责一个文件的完整处理流程：
    # 1. 读取文件内容
    # 2. 调用智谱AI API翻译文件中的英文注释
    # 3. 将翻译后的内容写回文件
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        # 提交所有文件处理任务
        futures = [executor.submit(process_file, file_path, api_key) for file_path in target_files]
        
        # 等待所有任务完成
        concurrent.futures.wait(futures)
    
    # 计算耗时
    end_time = datetime.now()
    elapsed_time = end_time - start_time
    formatted_time = format_time_delta(elapsed_time)
    
    # 关闭进度条
    global_pbar.close()
    
    # 按失败原因分类统计
    failure_reasons = {}
    for file_path, reason in failed_files:
        if reason not in failure_reasons:
            failure_reasons[reason] = []
        failure_reasons[reason].append(file_path)
    
    # 输出结果
    print(f"\n处理完成! 共处理 {processed_counter.value} 个文件，成功率: {processed_counter.value/total_files*100:.2f}%")
    print(f"总耗时: {formatted_time}")
    
    if failed_files:
        print(f"\n以下 {len(failed_files)} 个文件无法处理:")
        for file_path, reason in failed_files:
            error = error_messages.get(file_path, reason)
            print(f"  - {file_path}: {error}")
        
        # 按原因分类展示
        print("\n按失败原因统计:")
        for reason, files in failure_reasons.items():
            print(f"\n原因: {reason} (共 {len(files)} 个文件)")
            for file_path in files[:5]:  # 只显示前5个文件
                print(f"  - {file_path}")
            if len(files) > 5:
                print(f"  - ... 等 {len(files)} 个文件")
    
    # 输出报告到文件
    try:
        # 确保输出目录存在
        report_dir = os.path.dirname(output_report)
        if report_dir and not os.path.exists(report_dir):
            os.makedirs(report_dir)
        
        with open(output_report, 'w', encoding='utf-8') as f:
            f.write(f"# 注释翻译处理报告\n\n")
            f.write(f"- 处理时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- 处理目录: {directory}\n")
            f.write(f"- 总文件数: {total_files} (包括.h, .hpp, .c, .cpp, .cc, .cxx)\n")
            
            # 添加文件类型分布信息
            f.write("- 文件类型分布:\n")
            for ext, count in file_types.items():
                f.write(f"  - {ext}: {count} 个文件 ({count/total_files*100:.2f}%)\n")
            
            f.write(f"- 成功处理: {processed_counter.value} ({processed_counter.value/total_files*100:.2f}%)\n")
            f.write(f"- 处理耗时: {formatted_time}\n")
            f.write(f"- 处理方式: 使用智谱AI直接翻译文件内容\n")
            f.write(f"- 翻译检验: 仅检查花括号匹配，不再检查结构完整性和内容长度\n\n")
            
            if failed_files:
                f.write(f"## 未处理文件列表 ({len(failed_files)}个)\n\n")
                # 按原因分组输出
                for reason, files in failure_reasons.items():
                    f.write(f"### {reason} ({len(files)}个)\n\n")
                    for file_path in files:
                        f.write(f"- {file_path}\n")
                    f.write("\n")
        
        print(f"\n处理报告已保存至: {output_report}")
    except Exception as e:
        print(f"\n保存处理报告时出错: {str(e)}")

if __name__ == "__main__":
    main()