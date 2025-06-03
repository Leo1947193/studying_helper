# data_manager.py
import json
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class TemplateMethodManager:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = self._load_data()

    def _load_data(self) -> list:
        """从文件中加载出题模板和答题方法数据."""
        if not os.path.exists(self.file_path):
            logging.info(f"Data file not found: {self.file_path}. Initializing with empty data.")
            return []
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    logging.warning(f"Data file {self.file_path} content is not a list. Resetting.")
                    return []
                return data
        except json.JSONDecodeError:
            logging.error(
                f"Error decoding JSON from {self.file_path}. File might be corrupted. Initializing with empty data.")
            return []
        except Exception as e:
            logging.error(f"An unexpected error occurred while loading data from {self.file_path}: {e}")
            return []

    def _save_data(self):
        """将当前的出题模板和答题方法数据保存到文件."""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
            logging.info(f"Data successfully saved to {self.file_path}")
        except Exception as e:
            logging.error(f"Error saving data to {self.file_path}: {e}")

    def add_template_method(self, question_template: str, answer_method: str):
        """
        增加一个新的出题模板和答题方法。
        如果模板和方法完全相同，则不重复添加。
        """
        new_entry = {
            "question_template": question_template,
            "answer_method": answer_method
        }
        # 检查是否已存在
        if new_entry in self.data:
            logging.info("Template and method already exist. Not adding duplicate.")
            return False

        self.data.append(new_entry)
        self._save_data()
        logging.info(f"Added new template: '{question_template}' with method: '{answer_method}'")
        return True

    def get_all_templates_methods(self) -> list:
        """获取所有已存储的出题模板和答题方法."""
        return self.data

    def get_answer_method_by_index(self, index: int) -> str | None:
        """根据索引获取对应的答题方法."""
        if 0 <= index < len(self.data):
            return self.data[index].get("answer_method")
        logging.warning(f"Invalid index: {index}. No answer method found.")
        return None
