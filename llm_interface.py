# notebook-backend/llm_interface.py
import openai
import json
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DeepSeekLLM:
    def __init__(self, api_key: str, model: str = "deepseek-chat", base_url: str = "https://api.deepseek.com/v1"):
        if not api_key:
            raise ValueError("API Key is not provided.")
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def _call_llm(self, messages: list, temperature: float = 0.7, max_tokens: int = 1000, response_format_type: str = "text") -> str:
        """通用的LLM调用方法，内部方法."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": response_format_type}
            )

            message_data = response.choices[0].message
            content = getattr(message_data, 'content', None)
            if content is None:
                content = message_data.get('content', None)

            if content is None:
                raise ValueError("Could not extract 'content' from LLM response message.")

            return content

        except openai.APIError as e:
            logging.error(f"DeepSeek API Error: {e}")
            raise
        except Exception as e:
            logging.error(f"An unexpected error occurred during LLM call: {e}")
            logging.error(f"Full LLM response object for debugging: {response.model_dump_json() if 'response' in locals() else 'N/A'}")
            raise

    def call_json(self, messages: list, temperature: float = 0.3, max_tokens: int = 500) -> dict | list:
        """调用LLM，期望返回JSON对象或JSON数组."""
        try:
            response_str = self._call_llm(messages, temperature=temperature, max_tokens=max_tokens, response_format_type="json_object")
            return json.loads(response_str)
        except json.JSONDecodeError:
            logging.error(f"Failed to decode JSON from LLM response: {response_str}")
            raise ValueError(f"Invalid JSON response from LLM: {response_str}")
        except Exception as e:
            raise

    def call_text(self, messages: list, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """调用LLM, 期望返回纯文本."""
        try:
            return self._call_llm(messages, temperature=temperature, max_tokens=max_tokens, response_format_type="text")
        except Exception as e:
            raise

    def summarize_paragraph(self, paragraph: str) -> dict:
        """
        梳理文本段落的重点并以JSON形式返回。
        返回格式: {"main_points": ["point1", "point2", ...]}
        """
        prompt = f"""
        请你作为一名专业的文本分析师，梳理以下段落的重点，并以JSON形式返回。
        JSON应包含一个键 'main_points'，其值是一个字符串数组，每个字符串是段落的一个重点。

        段落:
        {paragraph}

        JSON:
        """
        messages = [
            {"role": "system", "content": "你是一个专业的文本分析师，擅长提取关键信息并以JSON格式返回。"},
            {"role": "user", "content": prompt}
        ]
        try:
            return self.call_json(messages, temperature=0.3)
        except Exception as e:
            logging.error(f"Error summarizing paragraph: {e}")
            return {"error": str(e)}

    def extract_qa_templates(self, question: str, answer: str) -> dict:
        """
        从问答对中提取出题模板和答题方法。
        返回格式: {"question_template": "...", "answer_method": "..."}
        """
        prompt = f"""
        你是一个专业的教育内容分析师。请你从以下问题和答案中提取出通用的出题模板和相应的答题方法。
        出题模板应是抽象的，能够应用于类似的问题，用占位符（如 `[知识点]`）表示可变部分。
        答题方法应是具体的步骤或策略，指导如何解决这类问题。
        请**务必**以JSON格式返回，包含 'question_template' 和 'answer_method' 两个键。
        如果无法提取，请返回空值，例如: {{"question_template": null, "answer_method": null}}。

        问题:
        {question}

答案:
        {answer}

        JSON:
        """
        messages = [
            {"role": "system", "content": "你是一个专业的教育内容分析师，擅长提取出题模板和答题方法。请确保你的输出是有效的JSON格式，且严格遵守指定的JSON结构。"},
            {"role": "user", "content": prompt}
        ]
        try:
            # 调试打印LLM即将接收的Prompt
            logging.info(f"DEBUG LLM_INTERFACE: Prompt for extract_qa_templates: {messages}")
            response_data = self.call_json(messages, temperature=0.5, max_tokens=500)
            # 调试打印LLM原始的JSON响应
            logging.info(f"DEBUG LLM_INTERFACE: Raw JSON response for extract_qa_templates: {response_data}")
            return response_data
        except Exception as e:
            logging.error(f"Error extracting QA templates: {e}")
            return {"error": str(e)}

    def rewrite_answer(self, question: str, original_answer: str, selected_method: str) -> str:
        """
        根据选定的答题方法重写答案。
        """
        prompt = f"""
        你是一个专业的写作助手，擅长根据特定的方法重写答案。
        请根据提供的答题方法，重新组织或润色以下问题的答案。
        确保重写后的答案清晰、准确，并严格遵循指定的答题方法。
        请只返回重写后的答案文本，不要包含任何额外的说明或JSON。

        问题:
        {question}

        原始答案:
        {original_answer}

        答题方法:
        {selected_method}

        重写后的答案:
        """
        messages = [
            {"role": "system", "content": "你是一个专业的写作助手，请严格按照用户指定的答题方法重写答案。只返回答案文本。"},
            {"role": "user", "content": prompt}
        ]
        try:
            return self.call_text(messages, temperature=0.7)
        except Exception as e:
            logging.error(f"An unexpected error occurred during answer rewrite: {e}")
            raise

    def extract_qa_pairs_from_document(self, document_text: str, document_type_tag: str = "未知") -> list:
        """
        从整个文档文本中提取多个问题-答案对。
        返回格式: [{"question": "...", "answer": "..."}, {"question": "...", "answer": "..."}, ...]
        """
        MAX_DOCUMENT_TEXT_FOR_QA_EXTRACTION = 8000
        if len(document_text) > MAX_DOCUMENT_TEXT_FOR_QA_EXTRACTION:
            logging.warning(f"Document text for Q&A extraction too long ({len(document_text)} chars), truncating to {MAX_DOCUMENT_TEXT_FOR_QA_EXTRACTION} chars.")
            document_text = document_text[:MAX_DOCUMENT_TEXT_FOR_QA_EXTRACTION] + "\n... [文档已截断]"

        prompt = f"""
        你是一个专业的教育内容分析师。以下是一份文件（类型：{document_type_tag}）。
        你的任务是：从这份文件中识别出**所有潜在的、明确的“问题-答案”对**。
        每个问题都应该有其对应的、能够直接作为答案的文本片段。
        如果文件中没有明显的问答对，或者你无法明确区分问题和答案，请返回一个空的JSON对象，其中包含一个空的 'qa_pairs' 键，例如: {{"qa_pairs": []}}。

        请以JSON对象的形式返回，包含一个键 'qa_pairs'，其值是一个JSON数组，每个对象包含 'question' 和 'answer' 两个键。

        文件内容:
        ```text
        {document_text}
        ```

        JSON对象:
        """
        messages = [
            {"role": "system", "content": "你是一个严谨的教育内容分析师，擅长从复杂文档中提取结构化问答对，并以JSON对象形式返回，该对象包含一个名为 'qa_pairs' 的JSON数组。"},
            {"role": "user", "content": prompt}
        ]
        try:
            logging.info(f"DEBUG LLM_INTERFACE: Prompt for extract_qa_pairs_from_document: {messages}")
            response_data = self.call_json(messages, temperature=0.2, max_tokens=2000)
            logging.info(f"DEBUG LLM_INTERFACE: Raw JSON response for extract_qa_pairs_from_document: {response_data}")

            # --- 关键修复：从返回的JSON对象中提取 'qa_pairs' 列表 ---
            if isinstance(response_data, dict) and 'qa_pairs' in response_data and isinstance(response_data['qa_pairs'], list):
                return response_data['qa_pairs'] # <--- 正确提取列表
            else:
                logging.error(f"LLM did not return a valid JSON object with 'qa_pairs' list: {response_data}")
                return [] # 返回空列表表示未能正确提取
        except Exception as e:
            logging.error(f"Error extracting Q&A pairs from document: {e}")
            raise
