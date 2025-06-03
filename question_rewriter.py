# question_rewriter.py
from llm_interface import DeepSeekLLM
from data_manager import TemplateMethodManager
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class QuestionRewriter:
    def __init__(self, llm_client: DeepSeekLLM, template_manager: TemplateMethodManager):
        self.llm = llm_client
        self.manager = template_manager

    def extract_and_save_qa_template_method(self, question: str, answer: str) -> dict:
        """
        调用LLM提取出题模板和答题方法，并保存。
        """
        if not question.strip() or not answer.strip():
            return {"error": "Question and answer cannot be empty."}

        logging.info("Calling DeepSeek to extract QA template and method...")
        try:
            extracted_data = self.llm.extract_qa_templates(question, answer)
            if "error" in extracted_data:
                logging.error(f"Extraction failed: {extracted_data['error']}")
                return extracted_data

            question_template = extracted_data.get("question_template")
            answer_method = extracted_data.get("answer_method")

            if question_template and answer_method:
                self.manager.add_template_method(question_template, answer_method)
                logging.info("Extracted template and method saved successfully.")
                return extracted_data
            else:
                logging.warning("Extracted data is incomplete (missing template or method).")
                return {"error": "Incomplete data extracted from LLM", "data": extracted_data}

        except Exception as e:
            logging.error(f"An error occurred during extraction and saving: {e}")
            return {"error": str(e)}

    def list_all_templates_methods(self) -> list:
        """列出所有已存储的出题模板和答题方法。"""
        return self.manager.get_all_templates_methods()

    def rewrite_answer_with_selected_method(self, question: str, original_answer: str, method_index: int) -> str:
        """
        根据用户选择的答题方法（通过索引）重写答案。
        """
        if not question.strip() or not original_answer.strip():
            return "Error: Question or original answer cannot be empty."

        selected_method = self.manager.get_answer_method_by_index(method_index)
        if not selected_method:
            return f"Error: Invalid method index {method_index} or method not found."

        logging.info(f"Rewriting answer using method: '{selected_method}'")
        try:
            rewritten_answer = self.llm.rewrite_answer(question, original_answer, selected_method)
            logging.info("Answer rewritten successfully.")
            return rewritten_answer
        except Exception as e:
            logging.error(f"An error occurred during answer rewriting: {e}")
            return f"Error rewriting answer: {e}"

