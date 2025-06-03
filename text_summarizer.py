# text_summarizer.py
from llm_interface import DeepSeekLLM
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class TextSummarizer:
    def __init__(self, llm_client: DeepSeekLLM):
        self.llm = llm_client

    def summarize(self, paragraph: str) -> dict:
        """
        调用LLM梳理文本段落的重点。
        返回JSON格式的重点列表，或包含错误信息的字典。
        """
        if not paragraph.strip():
            return {"error": "Paragraph cannot be empty."}

        logging.info("Calling DeepSeek to summarize paragraph...")
        try:
            summary = self.llm.summarize_paragraph(paragraph)
            if "error" in summary:
                logging.error(f"Summarization failed: {summary['error']}")
            return summary
        except Exception as e:
            logging.error(f"An error occurred during summarization: {e}")
            return {"error": str(e)}

