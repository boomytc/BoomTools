#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理与智谱 AI API 的连接和调用
"""
import os
import re
import time
import json
import tempfile
from zhipuai import ZhipuAI

class APIClient:
    """智谱 AI API 客户端"""

    def __init__(self, api_key=None, model="glm-4-plus"):
        """
        初始化 API 客户端

        Args:
            api_key: API 密钥，如果为 None，则尝试从环境变量获取
            model: 使用的模型名称
        """
        self.api_key = api_key or os.environ.get("ZHIPUAI_API_KEY", "")
        self.model = model
        self.client = None

        if self.api_key:
            try:
                self.client = ZhipuAI(api_key=self.api_key)
            except Exception as e:
                print(f"初始化智谱 AI 客户端失败: {e}")

    def is_ready(self):
        """检查客户端是否已准备好"""
        return self.client is not None

    def translate_text(self, text, system_prompt=None, user_prompt_template=None):
        """
        调用 API 翻译文本

        Args:
            text: 要翻译的文本
            system_prompt: 系统提示
            user_prompt_template: 用户提示模板，其中 {text} 将被替换为要翻译的文本

        Returns:
            tuple: (翻译后的文本, 错误信息)
        """
        if not self.client:
            return None, "API 客户端未初始化，请检查 API 密钥"

        if not system_prompt:
            system_prompt = "你是一个专业的代码注释翻译专家，能够精确识别C++代码中的注释并将其从英文翻译为中文，同时完全不破坏代码结构和格式。"

        if not user_prompt_template:
            user_prompt_template = (
                "请翻译以下C++代码中的英文注释为中文，保持原有格式和注释符号。\n\n"
                "规则：\n"
                "1. 只翻译注释部分，不修改任何代码、变量名、字符串字面量等非注释内容\n"
                "2. 保持所有注释符号（如//、/*、*/等）完全不变\n"
                "3. 保持代码的缩进和换行格式\n"
                "4. 翻译为专业且地道的中文，保持技术术语准确性\n"
                "5. 不要添加、删除或修改任何非注释内容\n\n"
                "代码：\n\n```cpp\n{text}\n```"
            )

        try:
            user_prompt = user_prompt_template.format(text=text)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
            )
            translated_text = response.choices[0].message.content.strip()

            # 提取代码块内容
            code_match = re.search(r'```(?:cpp)?\n([\s\S]*?)\n```', translated_text)
            if code_match:
                return code_match.group(1), None
            return translated_text, None
        except Exception as e:
            return None, f"API调用出错: {str(e)}"

    def create_batch_job(self, requests, max_wait_seconds=600, progress_callback=None):
        """
        创建批处理任务

        Args:
            requests: 请求列表，每个请求应包含 custom_id, method, url, body
            max_wait_seconds: 最大等待时间（秒）
            progress_callback: 进度回调函数，接收参数 (current, total, status)

        Returns:
            tuple: (结果字典, 错误信息)
        """
        if not self.client:
            return None, "API 客户端未初始化，请检查 API 密钥"

        try:
            # 创建临时文件存储请求
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl", encoding='utf-8') as tmp_file:
                for item in requests:
                    tmp_file.write(json.dumps(item, ensure_ascii=False) + "\n")
                batch_input_file_path = tmp_file.name

            print(f"创建批处理任务，共 {len(requests)} 个请求...")

            # 上传文件
            uploaded_file = self.client.files.create(
                file=open(batch_input_file_path, "rb"),
                purpose="batch"
            )
            print(f"文件上传成功，文件ID: {uploaded_file.id}")

            # 创建批处理任务
            batch_job = self.client.batches.create(
                input_file_id=uploaded_file.id,
                endpoint="/v4/chat/completions",
                completion_window="24h"
            )
            print(f"批处理任务创建成功，任务ID: {batch_job.id}，状态: {batch_job.status}")

            # 等待任务完成
            start_time = time.time()
            last_progress_time = start_time
            last_status = batch_job.status

            while batch_job.status not in ["completed", "failed", "cancelled"]:
                if time.time() - start_time > max_wait_seconds:
                    return None, f"批处理任务超时，当前状态: {batch_job.status}"

                # 每10秒更新一次状态
                time.sleep(10)
                batch_job = self.client.batches.retrieve(batch_job.id)

                # 计算进度
                current_time = time.time()
                if current_time - last_progress_time >= 5 or batch_job.status != last_status:
                    completed = 0
                    total = len(requests)

                    if batch_job.request_counts:
                        completed = batch_job.request_counts.completed + batch_job.request_counts.failed
                        total = batch_job.request_counts.total

                    # 调用进度回调
                    if progress_callback:
                        progress_callback(completed, total, batch_job.status)

                    last_progress_time = current_time
                    last_status = batch_job.status

            # 最终进度更新
            if progress_callback and batch_job.request_counts:
                completed = batch_job.request_counts.completed + batch_job.request_counts.failed
                total = batch_job.request_counts.total
                progress_callback(completed, total, batch_job.status)

            print(f"批处理任务完成，最终状态: {batch_job.status}")

            # 处理结果
            if batch_job.status == "completed" and batch_job.output_file_id:
                print(f"下载批处理结果，输出文件ID: {batch_job.output_file_id}")
                results_content_response = self.client.files.content(batch_job.output_file_id)
                results_raw_text = results_content_response.text

                results = {}
                success_count = 0
                error_count = 0

                for line in results_raw_text.strip().split('\n'):
                    if not line:
                        continue
                    try:
                        result_item = json.loads(line)
                        custom_id = result_item.get("custom_id")
                        if custom_id:
                            results[custom_id] = result_item
                            if "error" in result_item or (result_item.get("response") and result_item["response"].get("status_code") != 200):
                                error_count += 1
                            else:
                                success_count += 1
                    except json.JSONDecodeError:
                        continue

                print(f"批处理结果解析完成，成功: {success_count}，失败: {error_count}")

                # 清理临时文件
                try:
                    os.remove(batch_input_file_path)
                except:
                    pass

                return results, None
            else:
                error_msg = f"批处理任务失败，状态: {batch_job.status}"
                if batch_job.error_file_id:
                    try:
                        error_content = self.client.files.content(batch_job.error_file_id).text
                        error_msg += f", 错误详情: {error_content}"
                    except:
                        pass
                return None, error_msg

        except Exception as e:
            return None, f"创建批处理任务失败: {str(e)}"

    def prepare_batch_requests(self, file_chunks, file_metadata):
        """
        准备批处理请求

        Args:
            file_chunks: 文件块列表，每个元素是 (file_path, chunk_index, chunk_content)
            file_metadata: 文件元数据字典，键为文件路径，值为 (file_name, encoding)

        Returns:
            list: 批处理请求列表
        """
        batch_requests = []

        for file_path, chunk_index, chunk_content in file_chunks:
            file_name, encoding = file_metadata.get(file_path, (os.path.basename(file_path), 'utf-8'))

            # 为每个块创建自定义ID
            custom_id = f"{file_path}::{chunk_index}"

            # 创建系统提示和用户提示
            system_prompt = "你是一个专业的代码注释翻译专家，能够精确识别C++代码中的注释并将其从英文翻译为中文，同时完全不破坏代码结构和格式。请确保翻译准确、专业，保留所有代码结构和格式。"

            user_prompt = (
                "请翻译以下C++代码片段中的英文注释为中文，保持原有格式和注释符号。\n\n"
                "规则：\n"
                "1. 只翻译注释部分，不修改任何代码、变量名、字符串字面量等非注释内容\n"
                "2. 保持所有注释符号（如//、/*、*/等）完全不变\n"
                "3. 保持代码的缩进和换行格式\n"
                "4. 翻译为专业且地道的中文，保持技术术语准确性\n"
                "5. 不要添加、删除或修改任何非注释内容\n"
                "6. 对于专业术语，保留英文原文并在后面添加中文翻译\n"
                "7. 确保翻译后的注释清晰易懂，符合中文表达习惯\n\n"
                f"代码片段 (来自文件: {file_name}):\n\n```cpp\n{chunk_content}\n```"
            )

            # 创建请求体
            api_request_body = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            }

            # 创建批处理请求
            batch_request = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v4/chat/completions",
                "body": api_request_body
            }

            batch_requests.append(batch_request)

        return batch_requests

    def extract_translation_from_response(self, response):
        """
        从 API 响应中提取翻译结果

        Args:
            response: API 响应对象或结果字典

        Returns:
            str: 提取的翻译文本
        """
        if isinstance(response, dict):
            # 批处理响应
            if "response" in response and "body" in response["response"]:
                body = response["response"]["body"]
                if "choices" in body and len(body["choices"]) > 0:
                    content = body["choices"][0].get("message", {}).get("content", "")
                    # 提取代码块
                    code_match = re.search(r'```(?:cpp)?\n([\s\S]*?)\n```', content)
                    if code_match:
                        return code_match.group(1)
                    return content
        return ""
