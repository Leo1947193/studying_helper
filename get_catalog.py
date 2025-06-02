# notebook-backend/get_catalog.py

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import sys

import dashscope

# --- LLM 提示 ---
PROMPT_TEXT_OFFSET_STRATEGY = """
你是一个专业的助手，擅长分析文本文档并提取结构化信息。
你将收到来自一本书前N页（很可能是目录或索引，N会由配置指定）的 **文本内容**。
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
         "actual_starting_page": "page0006.txt", "children": ""},
        {"index": 2, "name": "第二节...", "type": "leaf", "starting_page": 14, "ending_page": 26, "children": ""}
      ]
    }
  ]
}
- 请在你的回复中 **只提供 JSON 对象**。
"""


# --- 辅助函数 ---

def list_text_files(text_dir_path: Path) -> List[Path]:
    """列出并排序所有文本文件 (page*.txt)。"""
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
    """读取文本文件并返回其内容。"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}", file=sys.stderr)
        return None


def call_llm_dashscope_text(api_key: Optional[str], user_content: str, system_prompt: str, model_name: str) -> str:
    """通用函数，用于调用 DashScope Generation API。"""
    if not api_key:
        print("错误：DASHSCOPE_API_KEY 未提供或为空。", file=sys.stderr)
        return "ERROR:API_KEY_MISSING"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
    print(f"\n--- 正在调用文本模型: {model_name} ---")
    try:
        response = dashscope.Generation.call(api_key=api_key, model=model_name, messages=messages,
                                             result_format='message', stream=False)
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
    """清理并解析来自 LLM 输出的 JSON。"""
    if not llm_output or llm_output.startswith("ERROR:"):
        print(f"LLM调用失败或无输出: {llm_output}", file=sys.stderr)
        return None

    print("--- 开始清理并解析 LLM 输出 ---")
    cleaned_string = re.sub(r"```json\s*", "", llm_output, flags=re.IGNORECASE).strip()
    cleaned_string = re.sub(r"```\s*$", "", cleaned_string).strip()
    cleaned_string = re.sub(r'^json\s*', '', cleaned_string, flags=re.IGNORECASE).strip()

    first_brace = cleaned_string.find('{')
    last_brace = cleaned_string.rfind('}')

    if first_brace != -1 and last_brace > first_brace:
        json_string = cleaned_string[first_brace: last_brace + 1]
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


# --- 偏移量计算逻辑 ---

def _find_first_leaf_recursive(nodes: List[Dict]) -> Optional[Dict]:
    """辅助函数：在结构中找到第一个叶节点。"""
    for node in nodes:
        if node.get("type") == "leaf":
            return node
        elif node.get("type") == "tree" and "children" in node and isinstance(node["children"], list):
            found = _find_first_leaf_recursive(node["children"])
            if found:
                return found
    return None


def get_filename_number(filename: str) -> Optional[int]:
    """从文件名中提取数字 (例如, 从 page0009.txt 中提取 9)。"""
    match = re.search(r'page(\d{4})\.txt', filename, re.IGNORECASE)
    return int(match.group(1)) if match else None


def format_filename(number: int) -> str:
    """将数字格式化为 pageXXXX.txt。"""
    return f"page{number:04d}.txt"


def _apply_offset_recursive(nodes: List[Dict], offset: int, parent_path_id_for_recursion: str = ""):
    """
    辅助函数：递归地将偏移量应用于起始/结束页码。
    这里增加了生成 path_id 并存回 node_data['generated_path_id'] 的逻辑。
    """
    for i, node in enumerate(nodes):
        current_index_val = node.get("index")
        current_index_str = str(current_index_val) if current_index_val is not None else str(i + 1)
        current_generated_path_id = f"{parent_path_id_for_recursion}{'.' if parent_path_id_for_recursion else ''}{current_index_str}"
        node["generated_path_id"] = current_generated_path_id

        try:
            if "starting_page" in node and isinstance(node["starting_page"], (int, float)):
                node["actual_starting_page"] = format_filename(int(node["starting_page"]) + offset)
            elif "starting_page" in node:
                print(
                    f"警告：节点 '{node.get('name', '未命名节点')}' 的 'starting_page' 不是有效数字 ({node['starting_page']})，无法应用偏移量。",
                    file=sys.stderr)
                node["actual_starting_page"] = "INVALID_PAGE_FORMAT"
            else:
                node["actual_starting_page"] = "PAGE_NOT_SPECIFIED"

            if "ending_page" in node and isinstance(node["ending_page"], (int, float)):
                node["actual_ending_page"] = format_filename(int(node["ending_page"]) + offset)
            elif "ending_page" in node:
                print(
                    f"警告：节点 '{node.get('name', '未命名节点')}' 的 'ending_page' 不是有效数字 ({node['ending_page']})，无法应用偏移量。",
                    file=sys.stderr)
                node["actual_ending_page"] = "INVALID_PAGE_FORMAT"
            else:
                node["actual_ending_page"] = "PAGE_NOT_SPECIFIED"
        except Exception as e:
            print(f"警告: 应用偏移量时出错于节点 '{node.get('name', '未命名节点')}': {e}", file=sys.stderr)
            node["actual_starting_page"] = "OFFSET_ERROR"
            node["actual_ending_page"] = "OFFSET_ERROR"

        if "children" in node and isinstance(node["children"], list) and node["children"]:
            _apply_offset_recursive(node["children"], offset, current_generated_path_id)


def apply_offset_and_save(data: Dict, output_file: Path):
    """
    从第一个叶节点计算偏移量，将其应用于所有节点，然后保存结果。
    """
    print("--- 步骤 2 & 3: 计算并应用页面偏移量 ---")
    if not data or "chapters" not in data or not isinstance(data["chapters"], list):
        print("错误：提供的目录数据无效或缺少 'chapters' 列表。", file=sys.stderr)
        save_json_data(data if data else {}, output_file, "部分结果（数据无效）")
        return

    first_leaf = _find_first_leaf_recursive(data["chapters"])

    if not first_leaf:
        print("错误：未能在LLM输出中找到第一个叶节点。", file=sys.stderr)
        print("信息：将尝试不应用偏移量并保存当前结构。")
        _apply_offset_recursive(data["chapters"], 0)
        save_json_data(data, output_file, "部分结果（未找到首叶，无偏移量应用）")
        return

    toc_start_page_val = first_leaf.get("starting_page")
    actual_start_file_val = first_leaf.get("actual_starting_page")

    if not isinstance(toc_start_page_val, int):
        print(
            f"错误：第一个叶节点 '{first_leaf.get('name', '未命名节点')}' 的 'starting_page' ({toc_start_page_val}) 不是有效的整数。",
            file=sys.stderr)
        print("信息：将尝试不应用偏移量并保存当前结构。")
        _apply_offset_recursive(data["chapters"], 0)
        save_json_data(data, output_file, "部分结果（页码无效，无偏移量应用）")
        return

    if not actual_start_file_val or not isinstance(actual_start_file_val, str):
        print(
            f"错误：第一个叶节点 '{first_leaf.get('name', '未命名节点')}' 缺少 'actual_starting_page' 字符串或其值无效 ({actual_start_file_val})。",
            file=sys.stderr)
        print("       LLM 应已在步骤1中为第一个叶节点提供了 'actual_starting_page'。", file=sys.stderr)
        print("信息：将尝试不应用偏移量并保存当前结构。")
        _apply_offset_recursive(data["chapters"], 0)
        save_json_data(data, output_file, "部分结果（起始文件缺失，无偏移量应用）")
        return

    actual_start_number = get_filename_number(actual_start_file_val)

    if actual_start_number is None:
        print(f"错误：无法从文件名 '{actual_start_file_val}' 中提取页码。", file=sys.stderr)
        print("信息：将尝试不应用偏移量并保存当前结构。")
        _apply_offset_recursive(data["chapters"], 0)
        save_json_data(data, output_file, "部分结果（文件名解析失败，无偏移量应用）")
        return

    offset = actual_start_number - toc_start_page_val
    print(
        f"信息：计算出的页面偏移量为: {offset} (实际文件页码: {actual_start_number}, 目录声称页码: {toc_start_page_val})")

    _apply_offset_recursive(data["chapters"], offset)
    print("信息：偏移量已应用于所有节点。")
    save_json_data(data, output_file, "最终目录结果 (含偏移量)")


# --- 文件保存 ---
def save_json_data(data: Optional[Dict], output_file: Path, message_prefix: str = "数据") -> bool:
    """将字典数据保存到 JSON 文件。"""
    if data is None:
        print(f"警告: {message_prefix} 数据为 None，将尝试保存空JSON对象至 {output_file}。", file=sys.stderr)
        data_to_save = {}
    else:
        data_to_save = data

    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        print(f"{message_prefix}已成功保存到 '{output_file}'")
        return True
    except Exception as e:
        print(f"保存文件 '{output_file}' 时出错: {e}", file=sys.stderr)
        return False


# 修改 run_catalog_extraction_process 函数以接收两个参数
def run_catalog_extraction_process(textbook_base_name_unique: str, original_filename: str):  # <--- 接收两个参数
    """
    为指定的教材编排目录提取过程。
    """
    print(
        f"开始为教材 '{textbook_base_name_unique}' 提取目录过程 (偏移量策略, 原始文件: {original_filename})...")  # 打印更多调试信息

    dashscope_api_key = "sk-31510d140d0c4af28612ce447f28943e"
    if not dashscope_api_key:
        print("致命错误: 环境变量 DASHSCOPE_API_KEY 未设置。", file=sys.stderr)
        sys.exit(1)

    # 硬编码的配置值
    text_subdir_name = "text_dir"
    catalog_output_filename = "catalog.json"
    pages_for_catalog = 30
    llm_model_name = "qwen-turbo"  # <--- 确保这里是 'qwen-turbo'

    # 构建特定教材的处理根目录路径 (使用唯一的教材基础名作为目录名)
    base_textbook_processing_dir = Path(sys.argv[
                                            0]).parent.resolve() / "uploads" / f"{textbook_base_name_unique}_dir"  # <--- 关键修改：使用 sys.argv[0] 获取脚本自身目录

    text_dir_full_path = base_textbook_processing_dir / text_subdir_name
    result_json_full_path = base_textbook_processing_dir / catalog_output_filename

    print(f"脚本目录: {Path(sys.argv[0]).parent.resolve()}")  # 打印脚本实际目录
    print(f"教材处理根目录: {base_textbook_processing_dir}")
    print(f"文本目录 (用于LLM输入): {text_dir_full_path}")
    print(f"结果文件 (目录输出): {result_json_full_path}")
    print(f"用于目录的页数: {pages_for_catalog}")
    print(f"LLM 模型: {llm_model_name}")

    if not text_dir_full_path.is_dir():
        print(
            f"错误: 文本目录 '{text_dir_full_path}' 未找到。请确保OCR流程已为教材 '{textbook_base_name_unique}' 正确生成文本文件。",
            file=sys.stderr)
        sys.exit(1)

    all_text_paths = list_text_files(text_dir_full_path)
    if not all_text_paths:
        print(f"在目录 '{text_dir_full_path}' 中未找到符合格式 'pageXXXX.txt' 的文本文件。程序退出。")
        sys.exit(1)

    text_paths_to_send = all_text_paths[:pages_for_catalog]
    if len(text_paths_to_send) < pages_for_catalog:
        print(f"警告：找到的文本文件 ({len(text_paths_to_send)}) 少于配置的页数 ({pages_for_catalog})。", file=sys.stderr)
    if not text_paths_to_send:
        print(
            f"警告：没有文本文件可供发送给 LLM (需要最多 {pages_for_catalog} 页，实际找到 {len(all_text_paths)} 页可用的文本文件)。程序退出。",
            file=sys.stderr)
        sys.exit(1)

    print(f"将使用 {len(text_paths_to_send)} 个文本文件（最多 {pages_for_catalog} 页）发送给 LLM。")

    combined_content_parts = []
    for p in text_paths_to_send:
        content = read_text_file(p)
        if content is None:
            print(f"警告：读取文件 {p.name} 失败，将跳过此文件内容。", file=sys.stderr)
            combined_content_parts.append(f"--- 内容来自文本文件 {p.name} ---\n[错误：无法读取文件内容]")
        else:
            combined_content_parts.append(f"--- 内容来自文本文件 {p.name} ---\n{content}")

    if not combined_content_parts:
        print("错误：未能读取任何文本文件内容以发送给 LLM。程序退出。", file=sys.stderr)
        sys.exit(1)

    full_text_content = "\n\n".join(combined_content_parts)

    print("\n--- 步骤 1: 获取结构和首叶起始页 ---")
    llm_output = call_llm_dashscope_text(dashscope_api_key, full_text_content, PROMPT_TEXT_OFFSET_STRATEGY,
                                         llm_model_name)
    initial_structure = parse_json_from_llm(llm_output)

    if not initial_structure:
        print("步骤 1 失败：未能从 LLM 获取或解析有效的初始目录结构。程序退出。", file=sys.stderr)
        error_output_path = result_json_full_path.with_suffix(".llm_error_output.txt")
        try:
            error_output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(error_output_path, 'w', encoding='utf-8') as f_err:
                f_err.write(f"LLM Output that failed parsing for textbook '{textbook_base_name_unique}':\n{llm_output}")
            print(f"LLM 的原始错误输出已保存到: {error_output_path}")
        except Exception as e_save:
            print(f"保存 LLM 错误输出时也发生错误: {e_save}", file=sys.stderr)
        sys.exit(1)

    apply_offset_and_save(initial_structure, result_json_full_path)
    print(f"\n教材 '{textbook_base_name_unique}' 的目录提取过程完成。")
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) == 3:  # <--- 期望两个参数
        textbook_base_name_unique_arg = sys.argv[1]
        original_filename_arg = sys.argv[2]
        try:
            # sys.argv[0] 是脚本自身的路径
            run_catalog_extraction_process(textbook_base_name_unique_arg, original_filename_arg)
        except NameError:
            # Fallback (should not happen with sys.argv[0])
            run_catalog_extraction_process(textbook_base_name_unique_arg, original_filename_arg)
    else:
        print("用法: python get_catalog.py <unique_base_name> <original_filename>")
        print("示例: python get_catalog.py Essay_1 Essay.pdf")
        sys.exit(1)
