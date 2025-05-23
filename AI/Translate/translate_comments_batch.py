#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C/C++文件注释翻译工具 (Batch API Version)
版本: 2.0
修改时间: 2023-05-21
更新说明:
1. 重构为使用智谱AI Batch API进行翻译。
2. 优化大文件处理和API调用效率。
3. 调整进度报告和错误处理以适应批处理流程。
4. 增强错误恢复和文件备份机制。
5. 改进大文件分块处理逻辑。
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
import magic # type: ignore
import codecs
import json
import tempfile
from collections import defaultdict

# 内置API密钥 (建议通过命令行参数传入，而不是硬编码)
# 如果需要在此处设置默认密钥，请替换下面的值
DEFAULT_API_KEY = os.environ.get("ZHIPUAI_API_KEY", "429cb3d87bc5458387e77f763085ac35.lHKb36viMNufF43u")

# 默认线程数 (主要用于本地文件操作，API并发由Batch服务处理)
DEFAULT_THREADS = 64 # 调整为64核

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

    def get_value(self):
        with self.lock:
            return self.value

# 全局进度条和计数器
global_pbar = None
processed_counter = Counter()
failed_files_info = {}  # 存储失败文件路径和原因 {file_path: reason}
failed_files_lock = threading.Lock()
error_messages = {}
error_messages_lock = threading.Lock()
backup_files = {} # {file_path: binary_content}
backup_files_lock = threading.Lock()

# ZhipuAI Client instance
zhipu_client = None

def extract_code_from_api_response(api_response_content: str) -> str:
    """从API返回内容中提取代码块（如果存在）"""
    code_match = re.search(r'```(?:[a-zA-Z]+)?\n([\s\S]*?)\n```', api_response_content)
    if code_match:
        return code_match.group(1)
    return api_response_content

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
    normalized_path = os.path.normpath(file_path)
    for excluded_dir in EXCLUDED_DIRS:
        if os.path.join(os.sep, excluded_dir, os.sep) in os.path.join(os.sep, normalized_path, os.sep):
            return True
    return False

def is_target_file(file_path):
    if is_in_excluded_dir(file_path):
        return False
    target_extensions = {'.h', '.hpp', '.c', '.cpp', '.cc', '.cxx'}
    _, ext = os.path.splitext(file_path)
    return ext.lower() in target_extensions

def backup_file_content(file_path, content):
    """备份文件内容到内存"""
    try:
        with backup_files_lock:
            backup_files[file_path] = content
        return True
    except Exception as e:
        with error_messages_lock:
            error_messages[file_path] = f"备份文件内容失败: {str(e)}"
        return False

def restore_file_from_memory(file_path):
    """从内存恢复原始文件"""
    try:
        with backup_files_lock:
            if file_path in backup_files:
                original_content = backup_files[file_path]
                try:
                    with open(file_path, 'wb') as f:
                        f.write(original_content)
                    return True
                except Exception as write_e:
                    with error_messages_lock:
                         error_messages[file_path] = f"恢复文件时写入失败: {str(write_e)}"
                    return False
        return False
    except Exception as e:
        with error_messages_lock:
            error_messages[file_path] = f"恢复文件失败: {str(e)}"
        return False

def is_binary_file(file_path):
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(4096)
            if b'\x00' in chunk:
                return True
            text_chars = sum(1 for byte in chunk if 32 <= byte <= 126 or byte in (9, 10, 13))
            if len(chunk) > 0 and text_chars / len(chunk) < 0.7:
                return True
    except Exception:
        return True
    return False

def get_file_encoding(file_path):
    """
    获取文件编码，使用多种方法尝试检测

    Args:
        file_path: 文件路径

    Returns:
        str: 检测到的编码，如果检测失败则返回'latin-1'作为后备编码
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(4096)  # 读取前4KB进行检测

            # 首先检查BOM标记
            if raw_data.startswith(codecs.BOM_UTF8):
                return 'utf-8-sig'
            if raw_data.startswith(codecs.BOM_UTF16_LE):
                return 'utf-16-le'
            if raw_data.startswith(codecs.BOM_UTF16_BE):
                return 'utf-16-be'
            if raw_data.startswith(codecs.BOM_UTF32_LE):
                return 'utf-32-le'
            if raw_data.startswith(codecs.BOM_UTF32_BE):
                return 'utf-32-be'

            # 尝试使用magic库检测
            try:
                m = magic.Magic(mime_encoding=True)
                encoding = m.from_buffer(raw_data)
                if encoding and encoding not in ['binary', 'unknown-8bit', 'application/octet-stream']:
                    try:
                        raw_data.decode(encoding)
                        return encoding
                    except Exception as e:
                        print(f"警告: magic检测到编码 {encoding}，但解码失败: {e}")
            except Exception as e:
                print(f"警告: magic库检测编码失败: {e}")

            # 尝试常见编码
            common_encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'shift-jis', 'euc-jp', 'euc-kr', 'latin-1']
            for enc in common_encodings:
                try:
                    raw_data.decode(enc)
                    return enc
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    print(f"警告: 尝试使用 {enc} 解码时出错: {e}")
    except Exception as e:
        print(f"警告: 读取文件 {file_path} 进行编码检测时出错: {e}")

    # 如果所有方法都失败，返回latin-1作为后备编码
    print(f"警告: 无法确定文件 {file_path} 的编码，将使用latin-1作为后备编码")
    return 'latin-1'

def safe_write_file(file_path, content, encoding):
    """
    安全地写入文件，处理各种编码问题

    Args:
        file_path: 文件路径
        content: 要写入的内容
        encoding: 首选编码

    Returns:
        bool: 写入是否成功
    """
    # 首先尝试使用指定的编码
    try:
        with open(file_path, 'w', encoding=encoding, errors='xmlcharrefreplace') as f:
            f.write(content)
        print(f"成功: 文件 {file_path} 已使用 {encoding} 编码写入")
        return True
    except Exception as e:
        print(f"警告: 使用 {encoding} 编码写入文件 {file_path} 失败: {e}")
        with error_messages_lock:
            error_messages[file_path] = f"写入文件时出错 ({encoding}): {str(e)}"

        # 尝试使用UTF-8编码
        try:
            with open(file_path, 'w', encoding='utf-8', errors='xmlcharrefreplace') as f:
                f.write(content)
            print(f"警告: 文件 {file_path} 使用UTF-8编码回写，原编码 {encoding} 失败")
            return True
        except Exception as e_utf8:
            print(f"警告: 使用UTF-8编码写入文件 {file_path} 也失败: {e_utf8}")
            with error_messages_lock:
                error_messages[file_path] = f"写入文件时出错 (UTF-8 fallback): {str(e_utf8)}"

            # 最后尝试使用二进制模式写入
            try:
                with open(file_path, 'wb') as f:
                    # 尝试使用原始编码
                    try:
                        binary_content = content.encode(encoding, errors='xmlcharrefreplace')
                    except Exception:
                        # 如果原始编码失败，使用UTF-8
                        binary_content = content.encode('utf-8', errors='xmlcharrefreplace')
                    f.write(binary_content)
                print(f"警告: 文件 {file_path} 使用二进制模式写入成功")
                return True
            except Exception as e_bin:
                print(f"错误: 所有写入方法都失败，无法保存文件 {file_path}: {e_bin}")
                with error_messages_lock:
                    error_messages[file_path] = f"所有写入方法都失败: {str(e_bin)}"
                return False

def count_target_files_for_processing(directory):
    count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if is_target_file(file_path) and not is_binary_file(file_path):
                count += 1
    return count

def split_by_comment_blocks(content):
    comment_pattern = r'(\/\/.*?$|\/\*[\s\S]*?\*\/)'
    parts = re.split(comment_pattern, content, flags=re.MULTILINE)
    chunks = []
    current_chunk = ""
    max_chunk_size = 10000

    for i, part in enumerate(parts):
        if not part: continue

        if re.match(comment_pattern, part) or not current_chunk or \
           len(current_chunk) + len(part) <= max_chunk_size:
            current_chunk += part
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = part

    if current_chunk:
        chunks.append(current_chunk)

    refined_chunks = []
    for chunk in chunks:
        if len(chunk) > max_chunk_size and not re.fullmatch(comment_pattern, chunk.strip()):
            sub_chunks = [chunk[i:i+max_chunk_size] for i in range(0, len(chunk), max_chunk_size)]
            refined_chunks.extend(sub_chunks)
        else:
            refined_chunks.append(chunk)

    return refined_chunks

def prepare_translation_tasks_for_file(file_content, file_path, encoding):
    batch_api_requests = []
    task_metadata_list = []

    cpp_comment_pattern = r'(\/\/.*?$|\/\*[\s\S]*?\*\/)'
    all_comment_parts = re.findall(cpp_comment_pattern, file_content, re.MULTILINE)

    has_english_comments = False
    if not all_comment_parts:
        return [], [], "文件不包含注释"

    for comment_str in all_comment_parts:
        if re.search(r'[a-zA-Z]{3,}', comment_str):
            has_english_comments = True
            break

    if not has_english_comments:
        return [], [], "文件不包含英文注释"

    file_name = os.path.basename(file_path)

    if len(file_content) > 15000:
        chunks = split_by_comment_blocks(file_content)
        system_prompt_chunk = "你是一个专业的代码注释翻译专家，能够精确识别C++代码中的注释并将其从英文翻译为中文，同时完全不破坏代码结构和格式。"
        for i, chunk_content in enumerate(chunks):
            user_prompt_chunk = (
                f"请翻译以下C++代码片段中的英文注释为中文，保持原有格式和注释符号。\n\n"
                f"规则：\n"
                f"1. 只翻译注释部分，不修改任何代码、变量名、字符串字面量等非注释内容。\n"
                f"2. 保持所有注释符号（如//、/*、*/等）完全不变。\n"
                f"3. 保持代码的缩进和换行格式。\n"
                f"4. 翻译为专业且地道的中文，保持技术术语准确性。\n"
                f"5. 不要添加、删除或修改任何非注释内容。\n\n"
                f"代码片段 {i+1} (来自文件: {file_name}):\n\n```cpp\n{chunk_content}\n```"
            )
            custom_id = f"{file_path}::chunk::{i}"
            api_request_body = {
                "model": "glm-4-plus",
                "messages": [
                    {"role": "system", "content": system_prompt_chunk},
                    {"role": "user", "content": user_prompt_chunk}
                ]
            }
            batch_api_requests.append({
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v4/chat/completions",
                "body": api_request_body
            })
            task_metadata_list.append({
                "custom_id": custom_id,
                "file_path": file_path,
                "encoding": encoding,
                "original_content": chunk_content,
                "is_chunk": True,
                "chunk_index": i
            })
    else:
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
        custom_id = f"{file_path}::fullfile"
        api_request_body = {
            "model": "glm-4-plus",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        batch_api_requests.append({
            "custom_id": custom_id,
            "method": "POST",
            "url": "/v4/chat/completions",
            "body": api_request_body
        })
        task_metadata_list.append({
            "custom_id": custom_id,
            "file_path": file_path,
            "encoding": encoding,
            "original_content": file_content,
            "is_chunk": False,
            "chunk_index": None
        })

    return batch_api_requests, task_metadata_list, None

def analyze_file_types(file_paths):
    file_types = {}
    total_count = len(file_paths)
    if total_count == 0: return {}
    for file_path in file_paths:
        _, ext = os.path.splitext(file_path)
        ext = ext.lower() if ext else "no_extension"
        file_types[ext] = file_types.get(ext, 0) + 1
    return file_types

def _process_and_prepare_file(file_path_tuple):
    file_path, pbar_instance = file_path_tuple
    requests_list = []
    metadata_list_for_file = []
    error_msg = None
    skipped_no_eng = False

    try:
        encoding = get_file_encoding(file_path)
        try:
            with open(file_path, 'rb') as f_rb:
                original_binary_content = f_rb.read()
            with open(file_path, 'r', encoding=encoding, errors='replace') as f_r:
                file_content = f_r.read()
        except Exception as e:
            error_msg = f"读取文件失败: {e}"
            return file_path, [], [], error_msg, skipped_no_eng

        if not backup_file_content(file_path, original_binary_content):
            error_msg = error_messages.get(file_path, "备份失败")
            return file_path, [], [], error_msg, skipped_no_eng

        requests, metadata_list_for_task, prep_error = prepare_translation_tasks_for_file(file_content, file_path, encoding)

        if prep_error == "文件不包含英文注释" or prep_error == "文件不包含注释":
            skipped_no_eng = True
        elif prep_error:
            error_msg = prep_error
            restore_file_from_memory(file_path)

        if requests:
            requests_list.extend(requests)
            metadata_list_for_file.extend(metadata_list_for_task)

    except Exception as e:
        error_msg = f"预处理文件时出错: {e}"
        restore_file_from_memory(file_path)
    finally:
        if pbar_instance:
            pbar_instance.update(1)

    return file_path, requests_list, metadata_list_for_file, error_msg, skipped_no_eng

def _apply_and_write_results(args_tuple):
    file_path, parts, all_task_metadata_ref, backup_files_ref, pbar_instance = args_tuple
    success = False
    message = None

    try:
        parts.sort(key=lambda x: x[0] if x[0] is not None else -1)

        final_translated_content = "".join(p[1] for p in parts)
        file_had_errors = any(p[2] for p in parts)
        first_error_detail = next((p[2] for p in parts if p[2]), None)

        original_binary_content = backup_files_ref.get(file_path)
        if original_binary_content is None:
            message = "找不到原始备份内容"
            return file_path, success, message

        first_part_custom_id = None
        if parts:
            if parts[0][0] is not None:
                 first_part_custom_id = f"{file_path}::chunk::{parts[0][0]}"
            else:
                 first_part_custom_id = f"{file_path}::fullfile"

        current_encoding = "utf-8"
        if first_part_custom_id and first_part_custom_id in all_task_metadata_ref:
             current_encoding = all_task_metadata_ref[first_part_custom_id]["encoding"]
        else:
            found_meta_for_encoding = False
            for p_idx, _, _ in parts:
                temp_custom_id = f"{file_path}::chunk::{p_idx}" if p_idx is not None else f"{file_path}::fullfile"
                if temp_custom_id in all_task_metadata_ref:
                    current_encoding = all_task_metadata_ref[temp_custom_id]["encoding"]
                    found_meta_for_encoding = True
                    break
            if not found_meta_for_encoding:
                 print(f"警告: 无法从元数据中确定文件 {file_path} 的原始编码，将尝试使用utf-8。")

        try:
            original_full_content = original_binary_content.decode(current_encoding, errors='replace')
        except Exception as dec_err:
            message = f"解码原始备份内容失败: {dec_err}"
            return file_path, success, message

        if file_had_errors:
            message = f"部分翻译失败: {first_error_detail}"
            restore_file_from_memory(file_path)
        elif final_translated_content == original_full_content:
            message = "翻译后内容未发生变化"
            success = True
        else:
            original_brackets = original_full_content.count('{') - original_full_content.count('}')
            translated_brackets = final_translated_content.count('{') - final_translated_content.count('}')
            if original_brackets != translated_brackets:
                message = "翻译结果花括号不匹配"
                restore_file_from_memory(file_path)
            elif safe_write_file(file_path, final_translated_content, current_encoding):
                success = True
                message = "翻译成功并写回"
            else:
                message = error_messages.get(file_path, "写入翻译文件失败")
                restore_file_from_memory(file_path)
    except Exception as e:
        message = f"应用结果时出错: {str(e)}"
        restore_file_from_memory(file_path)
    finally:
        if pbar_instance:
            pbar_instance.update(1)

    return file_path, success, message

def check_dependencies():
    """
    检查必要的依赖是否已安装

    Returns:
        bool: 所有依赖是否都已正确安装
    """
    required_modules = {
        "zhipuai": "智谱AI Python SDK",
        "tqdm": "进度条显示库",
        "magic": "文件类型检测库"
    }

    missing_modules = []

    for module_name, description in required_modules.items():
        try:
            __import__(module_name)
        except ImportError:
            missing_modules.append(f"{module_name} ({description})")

    if missing_modules:
        print("错误: 缺少以下必要的Python库:")
        for module in missing_modules:
            print(f"  - {module}")
        print("\n请使用pip安装这些库:")
        print(f"  pip install {' '.join(m.split()[0] for m in missing_modules)}")
        return False

    # 特别检查zhipuai版本
    try:
        import zhipuai
        if not hasattr(zhipuai, 'batches'):
            print("错误: 当前安装的zhipuai库版本过低，不支持批处理API")
            print("请更新zhipuai库:")
            print("  pip install --upgrade zhipuai")
            return False
    except Exception as e:
        print(f"错误: 检查zhipuai版本时出错: {e}")
        return False

    return True

def main():
    parser = argparse.ArgumentParser(description='使用智谱AI Batch API将C/C++文件中的英文注释翻译为中文')
    parser.add_argument('directory', help='要处理的目录路径')
    parser.add_argument('--api-key', default=DEFAULT_API_KEY, help='智谱AI的API密钥')
    parser.add_argument('--threads', type=int, default=DEFAULT_THREADS, help=f'本地操作线程数量 (默认: {DEFAULT_THREADS})')
    parser.add_argument('--exclude', nargs='+', default=[], help='要排除的目录列表')
    parser.add_argument('--output-report', help='输出处理报告的文件路径', default='report.md')
    parser.add_argument('--version', action='version', version='%(prog)s 2.0 (2023-05-21)')
    args = parser.parse_args()

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 检查API密钥
    if args.api_key == DEFAULT_API_KEY and "429cb3d87bc5458387e77f763085ac35" in DEFAULT_API_KEY:
        print("警告: 使用默认API密钥。建议通过--api-key参数提供您自己的API密钥。")
        print("      或者设置环境变量ZHIPUAI_API_KEY")
        print("      如果继续使用默认密钥，可能会导致API调用失败或受到限制。")
        print("")

    global zhipu_client
    try:
        zhipu_client = ZhipuAI(api_key=args.api_key)
    except Exception as e:
        print(f"错误: 初始化智谱AI客户端失败: {e}")
        sys.exit(1)

    directory = args.directory
    output_report = args.output_report

    # 检查目录是否存在
    if not os.path.isdir(directory):
        print(f"错误: {directory} 不是一个有效的目录")
        sys.exit(1)

    EXCLUDED_DIRS.extend(args.exclude)
    print(f"排除目录: {', '.join(EXCLUDED_DIRS)}")

    if not os.path.isabs(output_report):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_report = os.path.join(script_dir, output_report)

    print("正在统计和准备目标文件...")
    all_target_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if is_target_file(file_path) and not is_binary_file(file_path):
                all_target_files.append(file_path)

    total_files_to_consider = len(all_target_files)
    print(f"找到 {total_files_to_consider} 个潜在的C/C++文件进行初步检查。")

    if total_files_to_consider == 0:
        print("未找到可处理的C/C++文件，退出程序。")
        sys.exit(0)

    global global_pbar
    global_pbar = tqdm.tqdm(total=total_files_to_consider, desc="准备文件和请求", unit="文件")

    start_time = datetime.now()

    all_batch_requests = []
    all_task_metadata = {}
    files_for_processing_count = 0
    skipped_files_no_eng_comments = 0

    preparation_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = [executor.submit(_process_and_prepare_file, (fp, global_pbar)) for fp in all_target_files]
        for future in concurrent.futures.as_completed(futures):
            preparation_results.append(future.result())

    for file_path, req_list, meta_list, err_msg, skipped_eng in preparation_results:
        if err_msg:
            with failed_files_lock:
                failed_files_info[file_path] = err_msg
        elif skipped_eng:
            processed_counter.increment()
            skipped_files_no_eng_comments += 1
        elif req_list:
            files_for_processing_count +=1
            all_batch_requests.extend(req_list)
            for meta_item in meta_list:
                all_task_metadata[meta_item['custom_id']] = meta_item
        else:
            processed_counter.increment()

    global_pbar.close()
    print(f"文件准备完成。总共 {files_for_processing_count} 个文件中的 {len(all_batch_requests)} 个部分将被翻译。")
    print(f"{skipped_files_no_eng_comments} 个文件因不含英文注释而被跳过。")

    if not all_batch_requests:
        print("没有需要通过Batch API处理的翻译任务。")
    else:
        batch_input_file_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl", encoding='utf-8') as tmp_file:
                for item in all_batch_requests:
                    tmp_file.write(json.dumps(item, ensure_ascii=False) + "\n")
                batch_input_file_path = tmp_file.name

            print(f"批处理输入文件已创建: {batch_input_file_path}")
            uploaded_file = zhipu_client.files.create(
                file=open(batch_input_file_path, "rb"),
                purpose="batch"
            )
            print(f"输入文件已上传: File ID {uploaded_file.id}")

            batch_job = zhipu_client.batches.create(
                input_file_id=uploaded_file.id,
                endpoint="/v4/chat/completions",
                completion_window="24h"
            )
            print(f"批处理任务已创建: Batch ID {batch_job.id}, 状态: {batch_job.status}")

            batch_pbar = tqdm.tqdm(total=batch_job.request_counts.total if batch_job.request_counts else len(all_batch_requests),
                                   desc="批处理进度", unit="请求")

            while batch_job.status not in ["completed", "failed", "cancelled"]:
                time.sleep(10)
                batch_job = zhipu_client.batches.retrieve(batch_job.id)
                if batch_job.request_counts:
                    processed_count = batch_job.request_counts.completed + batch_job.request_counts.failed
                    batch_pbar.n = processed_count
                    batch_pbar.set_postfix_str(f"状态: {batch_job.status}, 完成: {batch_job.request_counts.completed}, 失败: {batch_job.request_counts.failed}")
                else:
                    batch_pbar.set_postfix_str(f"状态: {batch_job.status}")
                batch_pbar.refresh()

            batch_pbar.close()
            print(f"批处理任务结束，最终状态: {batch_job.status}")

            if batch_job.status == "completed":
                output_file_id = batch_job.output_file_id
                error_file_id = batch_job.error_file_id

                if error_file_id:
                    print(f"批处理任务出现错误，错误文件ID: {error_file_id}")

                if output_file_id:
                    print(f"正在下载并处理结果文件: {output_file_id}")
                    results_content_response = zhipu_client.files.content(output_file_id)

                    results_raw_text = results_content_response.text

                    translations_by_file = defaultdict(list)

                    for line in results_raw_text.strip().split('\n'):
                        if not line: continue
                        try:
                            result_item = json.loads(line)
                            custom_id = result_item.get("custom_id")
                            metadata = all_task_metadata.get(custom_id)
                            if not metadata:
                                print(f"警告: 找不到custom_id {custom_id} 的元数据，跳过此结果。")
                                continue

                            file_path = metadata["file_path"]
                            chunk_idx = metadata["chunk_index"]
                            original_part_content = metadata["original_content"]

                            if result_item.get("error") or (result_item.get("response") and result_item["response"].get("status_code") != 200):
                                err_obj = result_item.get("error", {})
                                err_msg = err_obj.get("message", "批处理中单个请求失败")
                                if result_item.get("response"):
                                     err_msg += f" (状态码: {result_item['response'].get('status_code')})"
                                translations_by_file[file_path].append((chunk_idx, original_part_content, err_msg))
                            else:
                                response_body = result_item.get("response", {}).get("body", {})
                                translated_raw = response_body.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                                translated_processed = extract_code_from_api_response(translated_raw)
                                translations_by_file[file_path].append((chunk_idx, translated_processed, None))
                        except json.JSONDecodeError as json_e:
                            print(f"警告: 解析结果行失败: {json_e}. 行内容: '{line[:100]}...'")
                        except Exception as e:
                            print(f"警告: 处理结果项时发生未知错误: {e}. 行内容: '{line[:100]}...'")

                    if translations_by_file:
                        apply_pbar = tqdm.tqdm(total=len(translations_by_file), desc="应用翻译结果", unit="文件")

                        apply_args_list = []
                        for file_path, parts in translations_by_file.items():
                            apply_args_list.append((file_path, parts, all_task_metadata, backup_files, apply_pbar))

                        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
                            apply_futures = [executor.submit(_apply_and_write_results, arg_tuple) for arg_tuple in apply_args_list]
                            for future in concurrent.futures.as_completed(apply_futures):
                                fp, success_status, msg = future.result()
                                if success_status:
                                    processed_counter.increment()
                                    if msg == "翻译后内容未发生变化":
                                         with failed_files_lock: failed_files_info[fp] = msg
                                else:
                                    with failed_files_lock:
                                        failed_files_info[fp] = msg if msg else "应用结果时未知失败"
                        apply_pbar.close()

                else:
                    print("错误: 批处理任务完成但没有输出文件ID。")
                    for custom_id in all_batch_requests:
                         meta = all_task_metadata.get(custom_id['custom_id'])
                         if meta:
                            with failed_files_lock: failed_files_info[meta['file_path']] = "批处理无输出文件"
                            restore_file_from_memory(meta['file_path'])

            else:
                print(f"错误: 批处理任务未能成功完成 (状态: {batch_job.status})。正在尝试恢复所有已备份文件...")
                for fp_to_restore in backup_files.keys():
                    if fp_to_restore not in failed_files_info:
                         with failed_files_lock: failed_files_info[fp_to_restore] = f"批处理任务失败 (状态: {batch_job.status})"
                    restore_file_from_memory(fp_to_restore)

        except Exception as e:
            print(f"处理批处理任务时发生严重错误: {e}")
            for fp_to_restore in backup_files.keys():
                if fp_to_restore not in failed_files_info:
                    with failed_files_lock: failed_files_info[fp_to_restore] = f"批处理执行中发生严重错误"
                restore_file_from_memory(fp_to_restore)
        finally:
            if batch_input_file_path and os.path.exists(batch_input_file_path):
                os.remove(batch_input_file_path)
                print(f"临时批处理输入文件已删除: {batch_input_file_path}")

    end_time = datetime.now()
    elapsed_time = end_time - start_time
    formatted_time = format_time_delta(elapsed_time)

    actual_processed_count = processed_counter.get_value()
    total_considered_for_report = files_for_processing_count + skipped_files_no_eng_comments

    print(f"\n处理完成! 共考虑 {total_considered_for_report} 个文件进行翻译（或跳过）。")
    print(f"成功翻译（或确认无需翻译）: {actual_processed_count} 个文件。")
    if total_considered_for_report > 0 :
        success_rate = (actual_processed_count / total_considered_for_report) * 100
        print(f"成功率: {success_rate:.2f}%")
    else:
        print("没有文件符合翻译条件。")

    print(f"总耗时: {formatted_time}")

    if failed_files_info:
        print(f"\n以下 {len(failed_files_info)} 个文件处理失败或部分失败:")
        for file_path, reason in failed_files_info.items():
            full_reason = error_messages.get(file_path, reason)
            print(f"  - {file_path}: {full_reason}")

    try:
        report_dir = os.path.dirname(output_report)
        if report_dir and not os.path.exists(report_dir): os.makedirs(report_dir)

        with open(output_report, 'w', encoding='utf-8') as f:
            f.write(f"# 注释翻译处理报告 (Batch API)\n\n")
            f.write(f"- 处理时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- 处理目录: {directory}\n")
            f.write(f"- 初步检查文件总数: {total_files_to_consider}\n")
            f.write(f"- 实际进入翻译流程或因无英文注释跳过的文件数: {total_considered_for_report}\n")
            f.write(f"  - 其中，因不含英文注释跳过: {skipped_files_no_eng_comments} 个\n")
            f.write(f"  - 提交到批处理进行翻译的文件数: {files_for_processing_count} 个 (可能包含多个翻译单元)\n")

            file_type_stats = analyze_file_types(all_target_files)
            if file_type_stats:
                f.write("- 文件类型分布 (基于初步检查的文件):\n")
                for ext, count in sorted(file_type_stats.items()):
                    f.write(f"  - {ext}: {count} 个文件\n")

            f.write(f"- 成功处理 (翻译或确认无需翻译): {actual_processed_count} 个\n")
            if total_considered_for_report > 0:
                 f.write(f"- 成功率 (基于进入流程的文件): {success_rate:.2f}%\n")
            f.write(f"- 处理耗时: {formatted_time}\n")
            f.write(f"- 处理方式: 使用智谱AI Batch API\n\n")

            if failed_files_info:
                f.write(f"## 处理失败或部分失败的文件列表 ({len(failed_files_info)}个)\n\n")
                failure_reasons_summary = defaultdict(list)
                for fp, reason in failed_files_info.items():
                    failure_reasons_summary[reason].append(fp)

                for reason, files_list in sorted(failure_reasons_summary.items()):
                    f.write(f"### 原因: {reason} ({len(files_list)}个文件)\n")
                    for fp_item in files_list:
                        f.write(f"- {fp_item}\n")
                    f.write("\n")
        print(f"\n处理报告已保存至: {output_report}")
    except Exception as e:
        print(f"\n保存处理报告时出错: {str(e)}")

if __name__ == "__main__":
    main()