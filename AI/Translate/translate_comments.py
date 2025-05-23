#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C/C++文件注释翻译工具 (模块化版本)
版本: 2.0
修改时间: 2024-05-23
"""

import os
import re
import concurrent.futures
import tqdm
import threading

from utils.api_client import APIClient
from utils.file_utils import find_target_files, safe_read_file, safe_write_file, backup_file, restore_file
from utils.comment_parser import has_english_comments, split_by_comment_blocks
from utils.validators import validate_translation
from utils.config_manager import ConfigManager
from utils.progress_tracker import ProgressTracker

# 全局进度条
global_pbar = None

def process_file_standard(file_path, api_client, progress_tracker, config):
    """
    使用标准模式处理单个文件

    Args:
        file_path: 文件路径
        api_client: API客户端
        progress_tracker: 进度跟踪器
        config: 配置信息

    Returns:
        bool: 处理是否成功
    """
    try:
        # 读取文件
        content, encoding = safe_read_file(file_path)
        if not content:
            progress_tracker.add_failed_file(file_path, f"读取文件失败: {encoding}")
            return False

        # 检查是否包含英文注释
        if not has_english_comments(content):
            progress_tracker.add_skipped_file(file_path, "文件不包含英文注释")
            progress_tracker.add_processed_file(file_path)
            return True

        # 备份原始内容
        if not backup_file(file_path):
            progress_tracker.add_failed_file(file_path, "备份文件失败")
            return False

        # 翻译文件内容
        file_name = os.path.basename(file_path)
        file_size = len(content)

        translated_content = None
        error_msg = None

        if file_size > 15000:  # 大文件分块处理
            chunks = split_by_comment_blocks(content)
            translated_chunks = []

            system_prompt = "你是一个专业的代码注释翻译专家，能够精确识别C++代码中的注释并将其从英文翻译为中文，同时完全不破坏代码结构和格式。请确保翻译准确、专业，保留所有代码结构和格式。"

            for i, chunk in enumerate(chunks):
                user_prompt_template = (
                    "请翻译以下C++代码片段中的英文注释为中文，保持原有格式和注释符号。\n\n"
                    "规则：\n"
                    "1. 只翻译注释部分，不修改任何代码、变量名、字符串字面量等非注释内容\n"
                    "2. 保持所有注释符号（如//、/*、*/等）完全不变\n"
                    "3. 保持代码的缩进和换行格式\n"
                    "4. 翻译为专业且地道的中文，保持技术术语准确性\n"
                    "5. 不要添加、删除或修改任何非注释内容\n"
                    "6. 对于专业术语，保留英文原文并在后面添加中文翻译\n"
                    "7. 确保翻译后的注释清晰易懂，符合中文表达习惯\n\n"
                    f"代码片段 {i+1} (来自文件: {file_name}):\n\n```cpp\n{chunk}\n```"
                )

                chunk_translated, chunk_error = api_client.translate_text(chunk, system_prompt, user_prompt_template)

                if chunk_error:
                    error_msg = f"翻译文件块 {i+1} 失败: {chunk_error}"
                    break

                translated_chunks.append(chunk_translated or chunk)

            if not error_msg:
                translated_content = ''.join(translated_chunks)
        else:
            # 小文件整体翻译
            system_prompt = "你是一个专业的代码注释翻译专家，能够精确识别C++文件中的注释并将其从英文翻译为中文，同时完全不破坏代码结构和格式。请确保翻译准确、专业，保留所有代码结构和格式。"
            user_prompt_template = (
                "请翻译以下C++文件中的英文注释为中文，保持原有格式和注释符号。\n\n"
                "规则：\n"
                "1. 只翻译注释部分，不修改任何代码、变量名、字符串字面量等非注释内容\n"
                "2. 保持所有注释符号（如//、/*、*/等）完全不变\n"
                "3. 保持代码的缩进和换行格式\n"
                "4. 翻译为专业且地道的中文，保持技术术语准确性\n"
                "5. 不要添加、删除或修改任何非注释内容\n"
                "6. 对于专业术语，保留英文原文并在后面添加中文翻译\n"
                "7. 确保翻译后的注释清晰易懂，符合中文表达习惯\n\n"
                f"文件名：{file_name}\n\n```cpp\n{content}\n```"
            )

            translated_content, error_msg = api_client.translate_text(content, system_prompt, user_prompt_template)

        # 检查是否有错误
        if error_msg:
            progress_tracker.add_failed_file(file_path, error_msg)
            restore_file(file_path)
            return False

        # 验证翻译结果
        is_valid, validation_error = validate_translation(content, translated_content)
        if not is_valid:
            progress_tracker.add_failed_file(file_path, f"翻译验证失败: {validation_error}")
            restore_file(file_path)
            return False

        # 写入翻译后的内容
        if not safe_write_file(file_path, translated_content, encoding):
            progress_tracker.add_failed_file(file_path, "写入文件失败")
            restore_file(file_path)
            return False

        # 标记为处理成功
        progress_tracker.add_processed_file(file_path)
        return True

    except Exception as e:
        progress_tracker.add_failed_file(file_path, f"处理文件时出错: {str(e)}")
        restore_file(file_path)
        return False
    finally:
        # 更新进度条
        if global_pbar:
            global_pbar.update(1)
            file_name = os.path.basename(file_path)
            global_pbar.set_postfix_str(f"当前: {file_name}")

def prepare_batch_chunks(target_files, progress_tracker):
    """
    准备批处理文件块

    Args:
        target_files: 目标文件列表
        progress_tracker: 进度跟踪器

    Returns:
        tuple: (文件块列表, 文件元数据字典, 处理的文件数)
    """
    file_chunks = []  # [(file_path, chunk_index, chunk_content), ...]
    file_metadata = {}  # {file_path: (file_name, encoding), ...}
    processed_count = 0

    # 创建临时进度条
    prep_pbar = tqdm.tqdm(total=len(target_files), desc="准备批处理文件", unit="文件")

    for file_path in target_files:
        try:
            # 读取文件
            content, encoding = safe_read_file(file_path)
            if not content:
                progress_tracker.add_failed_file(file_path, f"读取文件失败: {encoding}")
                prep_pbar.update(1)
                continue

            # 检查是否包含英文注释
            if not has_english_comments(content):
                progress_tracker.add_skipped_file(file_path, "文件不包含英文注释")
                progress_tracker.add_processed_file(file_path)
                prep_pbar.update(1)
                continue

            # 备份原始内容
            if not backup_file(file_path):
                progress_tracker.add_failed_file(file_path, "备份文件失败")
                prep_pbar.update(1)
                continue

            # 文件元数据
            file_name = os.path.basename(file_path)
            file_metadata[file_path] = (file_name, encoding)

            # 分块处理
            if len(content) > 15000:
                chunks = split_by_comment_blocks(content)
                for i, chunk in enumerate(chunks):
                    file_chunks.append((file_path, i, chunk))
            else:
                file_chunks.append((file_path, 0, content))

            processed_count += 1

        except Exception as e:
            progress_tracker.add_failed_file(file_path, f"准备批处理时出错: {str(e)}")
        finally:
            prep_pbar.update(1)

    prep_pbar.close()
    return file_chunks, file_metadata, processed_count

def process_batch_results(batch_results, file_chunks, file_metadata, progress_tracker):
    """
    处理批处理结果

    Args:
        batch_results: 批处理结果字典
        file_chunks: 文件块列表
        file_metadata: 文件元数据字典
        progress_tracker: 进度跟踪器

    Returns:
        int: 成功处理的文件数
    """
    # 按文件分组结果
    file_results = {}  # {file_path: [(chunk_index, translated_content), ...], ...}

    for file_path, chunk_index, _ in file_chunks:
        custom_id = f"{file_path}::{chunk_index}"
        if custom_id in batch_results:
            result = batch_results[custom_id]

            # 检查是否有错误
            if "error" in result or (result.get("response") and result["response"].get("status_code") != 200):
                error_msg = "批处理API调用失败"
                if "error" in result:
                    error_msg = result["error"].get("message", error_msg)
                progress_tracker.add_failed_file(file_path, f"块 {chunk_index} 处理失败: {error_msg}")
                continue

            # 提取翻译结果
            translated_content = ""
            if "response" in result and "body" in result["response"]:
                body = result["response"]["body"]
                if "choices" in body and len(body["choices"]) > 0:
                    content = body["choices"][0].get("message", {}).get("content", "")
                    # 提取代码块
                    code_match = re.search(r'```(?:cpp)?\n([\s\S]*?)\n```', content)
                    if code_match:
                        translated_content = code_match.group(1)
                    else:
                        translated_content = content

            if not translated_content:
                progress_tracker.add_failed_file(file_path, f"块 {chunk_index} 翻译结果为空")
                continue

            # 添加到文件结果
            if file_path not in file_results:
                file_results[file_path] = []
            file_results[file_path].append((chunk_index, translated_content))

    # 处理每个文件的结果
    success_count = 0
    results_pbar = tqdm.tqdm(total=len(file_results), desc="应用翻译结果", unit="文件")

    for file_path, chunks in file_results.items():
        try:
            # 读取原始文件
            original_content, encoding = safe_read_file(file_path)
            if not original_content:
                progress_tracker.add_failed_file(file_path, "读取原始文件失败")
                results_pbar.update(1)
                continue

            # 如果只有一个块，直接使用翻译结果
            if len(chunks) == 1 and chunks[0][0] == 0:
                translated_content = chunks[0][1]
            else:
                # 按块索引排序
                chunks.sort(key=lambda x: x[0])
                translated_content = ''.join(chunk[1] for chunk in chunks)

            # 验证翻译结果
            is_valid, validation_error = validate_translation(original_content, translated_content)
            if not is_valid:
                progress_tracker.add_failed_file(file_path, f"翻译验证失败: {validation_error}")
                restore_file(file_path)
                results_pbar.update(1)
                continue

            # 写入翻译后的内容
            _, encoding = file_metadata.get(file_path, (None, 'utf-8'))
            if not safe_write_file(file_path, translated_content, encoding):
                progress_tracker.add_failed_file(file_path, "写入文件失败")
                restore_file(file_path)
                results_pbar.update(1)
                continue

            # 标记为处理成功
            progress_tracker.add_processed_file(file_path)
            success_count += 1

        except Exception as e:
            progress_tracker.add_failed_file(file_path, f"应用翻译结果时出错: {str(e)}")
            restore_file(file_path)
        finally:
            results_pbar.update(1)

    results_pbar.close()
    return success_count

def process_file(file_path, api_client, progress_tracker, config):
    """
    处理单个文件（根据配置选择标准模式或批处理模式）

    Args:
        file_path: 文件路径
        api_client: API客户端
        progress_tracker: 进度跟踪器
        config: 配置信息

    Returns:
        bool: 处理是否成功
    """
    # 在单文件处理中，始终使用标准模式
    return process_file_standard(file_path, api_client, progress_tracker, config)

def batch_progress_callback(current, total, status):
    """批处理进度回调函数"""
    print(f"批处理进度: {current}/{total} ({current/total*100:.2f}%) - 状态: {status}")

def main():
    """主函数"""
    # 解析配置
    args = ConfigManager.parse_args()
    config = ConfigManager.merge_args_with_config(args)

    # 检查目录是否存在
    if not os.path.isdir(config['directory']):
        print(f"错误: {config['directory']} 不是一个有效的目录")
        return

    # 初始化API客户端
    api_client = APIClient(api_key=config['api_key'], model=config['model'])
    if not api_client.is_ready():
        print("错误: 初始化API客户端失败，请检查API密钥")
        return

    # 查找目标文件
    print("正在查找目标文件...")
    target_files = find_target_files(
        config['directory'],
        extensions=['.h', '.hpp', '.c', '.cpp', '.cc', '.cxx'],
        excluded_dirs=config['exclude']
    )

    total_files = len(target_files)
    print(f"找到 {total_files} 个C/C++文件")

    if total_files == 0:
        print("未找到可处理的C/C++文件，退出程序")
        return

    # 初始化进度跟踪器
    progress_tracker = ProgressTracker(total_files, config['output_report'])

    # 如果需要恢复进度
    if config['resume']:
        if progress_tracker.load_progress():
            print("已恢复上次处理进度")
            # 过滤掉已处理的文件
            already_processed = set(progress_tracker.processed_files)
            already_failed = set(progress_tracker.failed_files.keys())
            already_skipped = set(progress_tracker.skipped_files.keys())
            already_handled = already_processed | already_failed | already_skipped

            target_files = [f for f in target_files if f not in already_handled]
            print(f"跳过 {len(already_handled)} 个已处理的文件，剩余 {len(target_files)} 个文件待处理")

    # 根据模式选择处理方法
    if config['batch_mode']:
        print("使用批处理模式处理文件...")

        # 准备批处理文件块
        file_chunks, file_metadata, processed_count = prepare_batch_chunks(target_files, progress_tracker)

        if not file_chunks:
            print("没有需要处理的文件块，退出程序")
            return

        print(f"准备了 {len(file_chunks)} 个文件块，来自 {processed_count} 个文件")

        # 准备批处理请求
        batch_requests = api_client.prepare_batch_requests(file_chunks, file_metadata)

        # 创建批处理任务
        print(f"创建批处理任务，共 {len(batch_requests)} 个请求...")
        batch_results, error_msg = api_client.create_batch_job(
            batch_requests,
            max_wait_seconds=3600,  # 1小时超时
            progress_callback=batch_progress_callback
        )

        if error_msg:
            print(f"批处理任务失败: {error_msg}")
            return

        # 处理批处理结果
        success_count = process_batch_results(batch_results, file_chunks, file_metadata, progress_tracker)

        print(f"批处理完成，成功处理 {success_count} 个文件")
    else:
        print("使用标准模式处理文件...")

        # 初始化进度条
        global global_pbar
        global_pbar = tqdm.tqdm(total=len(target_files), desc=f"处理进度 (使用 {config['threads']} 线程)", unit="文件")

        # 多线程处理文件
        with concurrent.futures.ThreadPoolExecutor(max_workers=config['threads']) as executor:
            # 提交所有文件处理任务
            futures = [executor.submit(process_file_standard, file_path, api_client, progress_tracker, config)
                      for file_path in target_files]

            # 等待所有任务完成
            concurrent.futures.wait(futures)

        # 关闭进度条
        global_pbar.close()

    # 保存进度
    progress_tracker.save_progress()

    # 生成报告
    progress_tracker.generate_report(target_files)

    # 打印结果
    progress = progress_tracker.get_progress()
    print(f"\n处理完成! 共处理 {progress['processed']} 个文件，成功率: {progress['success_rate']:.2f}%")
    print(f"总耗时: {progress_tracker.format_time_delta()}")
    print(f"详细报告已保存至: {config['output_report']}")

if __name__ == "__main__":
    main()
