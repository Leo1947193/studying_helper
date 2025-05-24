import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import sys

import dashscope

# --- Configuration ---
SCRIPT_DIR = Path(__file__).parent.resolve()
TEXT_DIR_NAME = 'text_dir'
RESULT_JSON_NAME = 'result.json' # Final output name

DEFAULT_TEXT_DIR = SCRIPT_DIR / TEXT_DIR_NAME
DEFAULT_RESULT_JSON = SCRIPT_DIR / RESULT_JSON_NAME

DEFAULT_NUM_PAGES = 20
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY')
LLM_MODEL = 'qwen-max'

# --- Prompt for Step 1: Get Structure & First Leaf Start File ---
PROMPT_TEXT_OFFSET_STRATEGY = """
你是一个专业的助手，擅长分析文本文档并提取结构化信息。
你将收到来自一本书前20页（很可能是目录或索引）的 **文本内容**。
文本内容会以 `--- 内容来自文本文件 {文件名} ---` 的格式进行分隔。
你的任务是仔细分析这些文本，并提取出目录的层次结构，包括 **章节标题** 和 **文本中的页码**。

**重要指示：**
1.  **提取标题和页码:** 提取每个章节/小节的 **完整标题** ("name") 和 **文本中写的页码** ("starting_page", "ending_page")。
2.  **识别第一个叶子节点的起始文件名:** 找出整个目录结构中 **第一个最细粒度的小节 (第一个 'leaf' 节点)**。然后，确定这个 **第一个叶子节点** 的 **内容** 实际开始于哪个文本文件。**只为这个第一个叶子节点** 添加一个 "actual_starting_page" 字段，并填入其内容起始文件名 (例如: "page0009.txt")。**其他任何节点都不要添加这个字段。**
3.  **JSON 格式：** 请 **只输出** 一个有效的 JSON 对象。

JSON结构应如下所示（注意只有第一个leaf节点可能有 actual_starting_page）:
{
  "chapters": [
    {
      "index": 1, "name": "第一章...", "type": "tree", "starting_page": 5, "ending_page": 26,
      "children": [
        {"index": 1, "name": "第一节...", "type": "leaf", "starting_page": 5, "ending_page": 13,
         "actual_starting_page": "page0006.txt", "children": ""}, // 假设这是第一个叶子节点
        {"index": 2, "name": "第二节...", "type": "leaf", "starting_page": 14, "ending_page": 26, "children": ""}
      ]
    }
  ]
}
- 请在你的回复中 **只提供 JSON 对象**。
"""

# --- Helper Functions (File I/O) ---
def list_text_files(text_dir_path: Path) -> List[Path]:
    """Lists and sorts all text files (page*.txt)."""
    try:
        all_txts = sorted([
            f for f in text_dir_path.glob("page*.txt")
            if re.match(r"page\d{4}\.txt", f.name.lower())
        ])
        print(f"在 {text_dir_path} 找到 {len(all_txts)} 个文本文件。")
        return all_txts
    except Exception as e:
        print(f"列出文本文件目录 {text_dir_path} 时出错: {e}", file=sys.stderr)
        return []

def read_text_file(file_path: Path) -> Optional[str]:
    """Reads a text file and returns its content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}", file=sys.stderr)
        return None

# --- LLM Interaction & Parsing ---
def call_llm_dashscope_text(api_key: str, user_content: str, system_prompt: str) -> str:
    """Generic function to call DashScope Generation API."""
    if not api_key: return "ERROR:API_KEY_MISSING"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
    print(f"\n--- 正在调用文本模型: {LLM_MODEL} ---")
    try:
        response = dashscope.Generation.call(api_key=api_key, model=LLM_MODEL, messages=messages, result_format='message', stream=False)
        if response.status_code == 200 and response.output and response.output.choices:
            raw_text = response.output.choices[0].message.content
            print(f"LLM响应 (前200字符): {raw_text[:200]}...")
            return raw_text.strip()
        else:
            print(f"API 调用失败: {response.status_code} - {response.message}", file=sys.stderr)
            return "ERROR:API_CALL_FAILED"
    except Exception as e:
        print(f"API 调用异常: {e}", file=sys.stderr)
        return f"ERROR:API_EXCEPTION:{e}"
    finally:
        print("--- 结束LLM调用 ---")

def parse_json_from_llm(llm_output: str) -> Optional[Dict]:
    """Cleans and parses JSON from LLM output."""
    if not llm_output or llm_output.startswith("ERROR:"):
        print(f"LLM调用失败或无输出: {llm_output}", file=sys.stderr)
        return None

    print("--- 开始清理并解析 LLM 输出 ---")
    cleaned_string = llm_output.replace("```json", "").replace("```", "").strip()
    cleaned_string = re.sub(r'^json\s*', '', cleaned_string).strip()
    first_brace = cleaned_string.find('{')
    last_brace = cleaned_string.rfind('}')

    if first_brace != -1 and last_brace > first_brace:
        json_string = cleaned_string[first_brace : last_brace + 1]
        try:
            parsed_json = json.loads(json_string)
            print("信息：JSON 解析成功！")
            return parsed_json
        except json.JSONDecodeError as e:
            print(f"错误：JSON 解析失败: {e}", file=sys.stderr)
            print(f"--- 尝试解析的字符串 --- \n{json_string}\n------------------------")
            return None
    else:
        print(f"错误：未能找到有效的 JSON 括号。", file=sys.stderr)
        print(f"--- LLM 原始输出 --- \n{llm_output}\n------------------------")
        return None

# --- New Offset Calculation Logic ---

def _find_first_leaf_recursive(nodes: List[Dict]) -> Optional[Dict]:
    """Helper: Finds the very first leaf node in the structure."""
    for node in nodes:
        if node.get("type") == "leaf":
            return node # Found the first one
        elif node.get("type") == "tree" and "children" in node and isinstance(node["children"], list):
            found = _find_first_leaf_recursive(node["children"])
            if found:
                return found # Return it up the chain
    return None

def get_filename_number(filename: str) -> Optional[int]:
    """Extracts the number (e.g., 9 from page0009.txt)."""
    match = re.search(r'(\d{4})\.txt', filename)
    return int(match.group(1)) if match else None

def format_filename(number: int) -> str:
    """Formats a number into pageXXXX.txt."""
    return f"page{number:04d}.txt"

def _apply_offset_recursive(nodes: List[Dict], offset: int):
    """Helper: Recursively applies offset to starting/ending pages."""
    for node in nodes:
        try:
            if "starting_page" in node and isinstance(node["starting_page"], int):
                node["actual_starting_page"] = format_filename(node["starting_page"] + offset)
            else:
                 node["actual_starting_page"] = "UNKNOWN"

            if "ending_page" in node and isinstance(node["ending_page"], int):
                node["actual_ending_page"] = format_filename(node["ending_page"] + offset)
            else:
                 node["actual_ending_page"] = "UNKNOWN"

        except Exception as e:
            print(f"警告: 应用偏移量时出错于节点 '{node.get('name')}': {e}", file=sys.stderr)
            node["actual_starting_page"] = "ERROR"
            node["actual_ending_page"] = "ERROR"

        # Recurse if children exist
        if "children" in node and isinstance(node["children"], list):
            _apply_offset_recursive(node["children"], offset)


def apply_offset_and_save(data: Dict, output_file: Path):
    """
    Calculates the offset from the first leaf and applies it to all nodes,
    then saves the result.
    """
    print("--- 步骤 2 & 3: 计算并应用页面偏移量 ---")
    first_leaf = _find_first_leaf_recursive(data.get("chapters", []))

    if not first_leaf:
        print("错误：未能在LLM输出中找到第一个叶节点。", file=sys.stderr)
        save_json_data(data, output_file, "部分结果（无偏移量）")
        return

    toc_start_page = first_leaf.get("starting_page")
    actual_start_file = first_leaf.get("actual_starting_page")

    if not isinstance(toc_start_page, int) or not actual_start_file:
        print(f"错误：第一个叶节点 '{first_leaf.get('name')}' 缺少 'starting_page' ({toc_start_page}) 或 'actual_starting_page' ({actual_start_file})。", file=sys.stderr)
        save_json_data(data, output_file, "部分结果（无偏移量）")
        return

    actual_start_number = get_filename_number(actual_start_file)

    if actual_start_number is None:
        print(f"错误：无法从文件名 '{actual_start_file}' 中提取页码。", file=sys.stderr)
        save_json_data(data, output_file, "部分结果（无偏移量）")
        return

    offset = actual_start_number - toc_start_page
    print(f"信息：计算出的页面偏移量为: {offset} (实际: {actual_start_number}, 目录: {toc_start_page})")

    # Apply the offset to all nodes
    _apply_offset_recursive(data.get("chapters", []), offset)
    print("信息：偏移量已应用于所有节点。")

    # Save the final result
    save_json_data(data, output_file, "最终目录结果 (含偏移量)")

# --- File Saving ---
def save_json_data(data: Dict, output_file: Path, message_prefix: str = "数据"):
    """Saves dictionary data to a JSON file."""
    if not data:
        print(f"警告: 没有 {message_prefix} 可保存至 {output_file}。", file=sys.stderr)
        return False
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"{message_prefix}已成功保存到 '{output_file}'")
        return True
    except Exception as e:
        print(f"保存文件 '{output_file}' 时出错: {e}", file=sys.stderr)
        return False

# --- Main Function ---
def main():
    print("开始提取目录过程 (偏移量策略)...")
    if not DASHSCOPE_API_KEY:
        print("致命错误: DASHSCOPE_API_KEY 未设置。", file=sys.stderr)
        return

    print(f"脚本目录: {SCRIPT_DIR}")
    print(f"文本目录: {DEFAULT_TEXT_DIR}")
    print(f"结果文件: {DEFAULT_RESULT_JSON}")

    if not DEFAULT_TEXT_DIR.is_dir():
       print(f"错误: 文本目录 '{TEXT_DIR_NAME}' 未找到。", file=sys.stderr)
       return

    all_text_paths = list_text_files(DEFAULT_TEXT_DIR)
    if not all_text_paths: return

    text_paths_to_send = all_text_paths[:DEFAULT_NUM_PAGES]
    print(f"将使用 {len(text_paths_to_send)} 个文本文件发送给 LLM。")
    combined_content_parts = [f"--- 内容来自文本文件 {p.name} ---\n{read_text_file(p) or '[读取失败]'}" for p in text_paths_to_send]
    full_text_content = "\n\n".join(combined_content_parts)

    # --- Step 1: Get Structure & First Leaf Start ---
    print("\n--- 步骤 1: 获取结构和首叶起始页 ---")
    llm_output = call_llm_dashscope_text(DASHSCOPE_API_KEY, full_text_content, PROMPT_TEXT_OFFSET_STRATEGY)
    initial_structure = parse_json_from_llm(llm_output)
    if not initial_structure:
        print("步骤 1 失败，程序退出。")
        return

    # --- Step 2 & 3: Calculate Offset & Apply ---
    apply_offset_and_save(initial_structure, DEFAULT_RESULT_JSON)

    print("\n目录提取过程完成。")

if __name__ == "__main__":
    main()