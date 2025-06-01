import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys

import dashscope # 假设已安装: pip install dashscope

# --- Constants defined as per requirements ---
BERT_MODEL = "bert-base-chinese"
CATALOG_FILENAME = "catalog.json"
CATALOG_SEGMENTS_FILENAME = "catalog_with_segments.json"
EMBEDDING_BATCH_SIZE = 32
FAISS_INDEX_FILENAME = "knowledge_points.index"
IMAGES_SUBDIR_NAME = "textbook_images_dir"
LLM_MODEL = "qwen-max" # As per user's list (hyphenated)
MAPPING_FILE_SUFFIX = ".mapping.json"
ORGCHART_SUBDIR_NAME = "orgchart_dir"
TEXTBOOK_ORGCHART_FILENAME = "textbook_orgchart.json"
PAGES_FOR_CATALOG = 30 # Although not directly used in this script, defined for consistency
SEARCH_TOP_K = 3
TEXT_SUBDIR_NAME = "textbook_text_dir"
# --- End of defined constants ---

# --- LLM 提示 (Specific to this script's functionality) ---
PROMPT_TEXT_SEGMENT_TEMPLATE = """
你是一位专业的AI文本分析助手，擅长从学术文本中提炼核心知识。
你将收到一个章节的标题和其完整的文本内容。该文本内容可能包含一些OCR引入的无关信息（如页眉、页脚、页码）或一些不影响核心语义的冗余表达。

你的任务是：
1.  **文本预处理与清理**:
    * 仔细阅读提供的章节文本。
    * **移除** 明显无助于理解核心内容的文本，例如：重复的页眉、页脚、孤立的页码、不连贯的OCR错误片段，以及对核心知识点贡献极小的非常简短或不完整的句子。目标是得到一段更精炼、专注于核心论述的文本。
2.  **语义切分与知识点提取**:
    * 在清理后的文本基础上，进行语义切分，将其分解为独立的、有意义的知识单元。
    * **提取核心知识点**。每个知识点应该是对一个概念、原理、论点或重要事实的清晰、简洁的陈述。
3.  **JSON格式输出**:
    * 将处理结果以指定的JSON格式输出。

你必须严格按照以下JSON格式输出。JSON对象中的 `chapter_id` 和 `chapter_name` 字段的值会由系统提供，你只需要专注于生成 `knowledge_points`。
{{
  "chapter_id": "{chapter_identifier_placeholder}",
  "chapter_name": "{chapter_name_placeholder}",
  "knowledge_points": [
    "知识点1：对某个概念的定义或解释。",
    "知识点2：关于某个原理的详细阐述。",
    "知识点3：一个重要的论点或事实总结。"
  ]
}}

请确保：
- `knowledge_points` 是一个字符串列表，每个字符串是一个独立的知识点。
- 整个回复 **只有** 这个JSON对象，不包含任何其他文本、解释或Markdown代码块标记。

章节标题是: "{chapter_name_placeholder}"
章节内容如下:
---
{chapter_content_placeholder}
---
请对上述内容进行处理，并按指定JSON格式返回。
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

def save_json_data(data: Optional[Dict], output_file: Path, message_prefix: str = "数据") -> bool:
    """将字典数据保存到 JSON 文件。"""
    if data is None:
        print(f"警告: {message_prefix} 数据为 None，不保存文件 {output_file}。", file=sys.stderr)
        return False
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"{message_prefix}已成功保存到 '{output_file}'")
        return True
    except Exception as e:
        print(f"保存文件 '{output_file}' 时出错: {e}", file=sys.stderr)
        return False

# --- LLM 交互与解析 ---
def call_llm_dashscope_text(api_key: Optional[str], system_prompt_with_content: str, model_to_use: str) -> str: # Renamed model_name to model_to_use
    """
    调用 DashScope Generation API。
    system_prompt_with_content 应为包含章节文本的完整格式化提示。
    """
    if not api_key:
        print("错误：DASHSCOPE_API_KEY 未设置。无法调用LLM。", file=sys.stderr)
        return "ERROR:API_KEY_MISSING"

    messages = [
        {"role": "system", "content": system_prompt_with_content},
        {"role": "user", "content": "请根据系统提示生成所需的JSON输出。"}
    ]

    print(f"\n--- 正在调用文本模型: {model_to_use} ---")
    try:
        response = dashscope.Generation.call(
            api_key=api_key,
            model=model_to_use, # Use the passed model_to_use
            messages=messages,
            result_format='message',
            stream=False
        )
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

# --- 核心逻辑 ---
def get_text_content_for_leaf(leaf_node: Dict, all_text_files: List[Path]) -> Optional[str]:
    """读取并连接给定叶节点的文本内容。"""
    start_file_name = leaf_node.get("actual_starting_page")
    end_file_name = leaf_node.get("actual_ending_page")

    if not start_file_name or not end_file_name or start_file_name in ["UNKNOWN", "PAGE_NOT_SPECIFIED", "INVALID_PAGE_FORMAT", "OFFSET_ERROR"] or end_file_name in ["UNKNOWN", "PAGE_NOT_SPECIFIED", "INVALID_PAGE_FORMAT", "OFFSET_ERROR"]:
        print(f"警告: 节点 '{leaf_node.get('name')}' 缺少有效的文件名范围 ({start_file_name} - {end_file_name})。跳过。", file=sys.stderr)
        return None

    try:
        filename_to_path = {p.name: p for p in all_text_files}

        if start_file_name not in filename_to_path or end_file_name not in filename_to_path:
            print(f"警告: 节点 '{leaf_node.get('name')}' 的起始/结束文件 ({start_file_name} / {end_file_name}) 在文件列表中未找到。", file=sys.stderr)
            return None

        sorted_filenames = [p.name for p in all_text_files]
        start_idx = sorted_filenames.index(start_file_name)
        end_idx = sorted_filenames.index(end_file_name)

        if start_idx > end_idx:
            print(f"警告: 节点 '{leaf_node.get('name')}' 的起始文件索引 ({start_idx}) 大于结束文件索引 ({end_idx})。将只使用起始文件。", file=sys.stderr)
            end_idx = start_idx

        content_parts = []
        print(f"信息: 读取文件范围 {start_file_name} 到 {end_file_name} (索引 {start_idx} 到 {end_idx})")
        for i in range(start_idx, end_idx + 1):
            file_path = filename_to_path[sorted_filenames[i]]
            content = read_text_file(file_path)
            if content:
                content_parts.append(content)
            else:
                print(f"警告: 无法读取文件 {file_path} 的内容。", file=sys.stderr)

        return "\n\n".join(content_parts) if content_parts else None

    except ValueError:
        print(f"错误: 文件名 '{start_file_name}' 或 '{end_file_name}' 未在排序的文件列表中找到。", file=sys.stderr)
        return None
    except Exception as e:
        print(f"获取 '{leaf_node.get('name')}' 的文本内容时出错: {e}", file=sys.stderr)
        return None

def process_chapters_for_segmentation(
    chapter_nodes: List[Dict],
    all_text_files: List[Path],
    api_key: str,
    model_for_segmentation: str, # Renamed from llm_model_for_segmentation
    parent_chapter_id: str = ""
    ):
    """
    递归遍历章节，处理叶节点以进行分段，并将 knowledge_points 就地添加到 chapter_nodes 中。
    """
    for i, chapter_data_node in enumerate(chapter_nodes):
        current_index_val = chapter_data_node.get("index")
        current_index_str = str(current_index_val) if current_index_val is not None else str(i + 1)

        current_chapter_id = f"{parent_chapter_id}{'.' if parent_chapter_id else ''}{current_index_str}"
        chapter_name = chapter_data_node.get("name", f"未知章节 {current_chapter_id}")

        if chapter_data_node.get("type") == "leaf":
            print(f"\n--- 正在处理叶节点进行分段: {current_chapter_id} - {chapter_name} ---")
            leaf_content = get_text_content_for_leaf(chapter_data_node, all_text_files)

            if not leaf_content:
                print(f"未能获取叶节点 '{chapter_name}' 的内容，为该节点添加空知识点列表。", file=sys.stderr)
                chapter_data_node["knowledge_points"] = []
                continue

            final_system_prompt = PROMPT_TEXT_SEGMENT_TEMPLATE.replace("{chapter_identifier_placeholder}", current_chapter_id)
            final_system_prompt = final_system_prompt.replace("{chapter_name_placeholder}", chapter_name)
            final_system_prompt = final_system_prompt.replace("{chapter_content_placeholder}", leaf_content)

            llm_response_str = call_llm_dashscope_text(api_key, final_system_prompt, model_for_segmentation)
            segmentation_json_data = parse_json_from_llm(llm_response_str)

            if segmentation_json_data and "knowledge_points" in segmentation_json_data:
                kps = segmentation_json_data.get("knowledge_points", [])
                if isinstance(kps, list) and all(isinstance(kp, str) for kp in kps):
                    chapter_data_node["knowledge_points"] = kps
                    print(f"信息: 已为章节 '{chapter_name}' 添加了 {len(kps)} 个知识点。")
                else:
                    chapter_data_node["knowledge_points"] = []
                    print(f"警告: LLM为章节 '{chapter_name}' 返回的 'knowledge_points' 不是字符串列表。已添加空列表。", file=sys.stderr)
            else:
                chapter_data_node["knowledge_points"] = []
                print(f"未能为章节 '{chapter_name}' 生成或解析分段JSON（或缺少knowledge_points）。添加空知识点列表。", file=sys.stderr)

        elif "children" in chapter_data_node and isinstance(chapter_data_node["children"], list):
            process_chapters_for_segmentation(
                chapter_data_node["children"],
                all_text_files,
                api_key,
                model_for_segmentation,
                current_chapter_id
            )

# --- 主流程函数 ---
def run_segmentation_process(textbook_name: str, script_dir_path: Path):
    """
    为指定的教材编排文本分段和知识点提取过程。
    """
    print(f"开始为教材 '{textbook_name}' 进行文本分段和知识点提取...")
    dashscope_api_key = os.getenv('DASHSCOPE_API_KEY')
    if not dashscope_api_key:
        print("致命错误: 环境变量 DASHSCOPE_API_KEY 未设置。程序无法执行LLM调用。", file=sys.stderr)
        return

    # Path definitions based on requirements
    # Example: /a/b/c/uploads/book1/
    textbook_base_dir = script_dir_path / "uploads" / textbook_name
    # Example: /a/b/c/uploads/book1/textbook_information/
    info_storage_dir = textbook_base_dir / "textbook_information"

    # Input text directory using global constant TEXT_SUBDIR_NAME
    # Example: /a/b/c/uploads/book1/textbook_information/textbook_text_dir/
    text_dir_full_path = info_storage_dir / TEXT_SUBDIR_NAME
    # Input catalog file using global constant CATALOG_FILENAME
    # Example: /a/b/c/uploads/book1/textbook_information/catalog.json
    input_catalog_json_full_path = info_storage_dir / CATALOG_FILENAME
    # Output catalog with segments file using global constant CATALOG_SEGMENTS_FILENAME
    # Example: /a/b/c/uploads/book1/textbook_information/catalog_with_segments.json
    final_output_json_full_path = info_storage_dir / CATALOG_SEGMENTS_FILENAME

    print(f"脚本目录: {script_dir_path}")
    print(f"教材根目录 (uploads/{textbook_name}): {textbook_base_dir}")
    print(f"信息存储目录 (textbook_information): {info_storage_dir}")
    print(f"文本输入目录 (来自全局常量 TEXT_SUBDIR_NAME): {text_dir_full_path}")
    print(f"输入目录JSON (来自全局常量 CATALOG_FILENAME): {input_catalog_json_full_path}")
    print(f"最终输出JSON (来自全局常量 CATALOG_SEGMENTS_FILENAME): {final_output_json_full_path}")
    print(f"用于分段的LLM模型 (来自全局常量 LLM_MODEL): {LLM_MODEL}")


    if not input_catalog_json_full_path.exists():
        print(f"错误: 输入的目录JSON文件 '{input_catalog_json_full_path}' 未找到。", file=sys.stderr)
        return

    if not text_dir_full_path.is_dir():
        print(f"错误: 文本目录 '{text_dir_full_path}' 未找到。", file=sys.stderr)
        return

    try:
        with open(input_catalog_json_full_path, 'r', encoding='utf-8') as f:
            catalog_data = json.load(f)
        print(f"成功加载目录结构从 '{input_catalog_json_full_path}'")
    except Exception as e:
        print(f"加载目录JSON文件 '{input_catalog_json_full_path}' 时出错: {e}", file=sys.stderr)
        return

    all_text_files = list_text_files(text_dir_full_path)
    if not all_text_files:
        print(f"错误: 在文本目录 '{text_dir_full_path}' 中未找到任何文本文件。", file=sys.stderr)
        save_json_data(catalog_data, final_output_json_full_path, "原始目录（无文本文件处理知识点）")
        return

    if "chapters" in catalog_data and isinstance(catalog_data["chapters"], list):
        # Use global constant LLM_MODEL for the model name
        process_chapters_for_segmentation(
            catalog_data["chapters"],
            all_text_files,
            dashscope_api_key,
            LLM_MODEL # Pass the global LLM_MODEL constant
        )
    else:
        print("错误: 加载的目录数据中未找到 'chapters' 键或其不是列表。", file=sys.stderr)
        save_json_data(catalog_data, final_output_json_full_path, "部分目录（'chapters'键缺失或无效）")
        return

    if catalog_data:
        save_json_data(catalog_data, final_output_json_full_path, "包含知识点的完整目录")
    else:
        print("警告: 未生成任何分段数据，因为 catalog_data 为空。")

    print(f"\n教材 '{textbook_name}' 的文本分段和知识点提取过程完成。")

def main(textbook_name_param: str):
    """
    主入口函数，设置环境并调用核心处理逻辑。
    Args:
        textbook_name_param (str): 教材的名称。
    """
    try:
        current_script_dir = Path(__file__).parent.resolve()
    except NameError:
        current_script_dir = Path(os.getcwd()).resolve()

    if not textbook_name_param or "/" in textbook_name_param or "\\" in textbook_name_param:
        print("错误：提供的教材名称无效。请提供不含路径分隔符的有效名称。", file=sys.stderr)
        return

    run_segmentation_process(textbook_name_param, current_script_dir)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        textbook_name_arg = sys.argv[1]
        # Ensuring the name is a base name, common practice if it might have an extension
        if textbook_name_arg.lower().endswith(".pdf"):
            textbook_name_arg = textbook_name_arg[:-4]
        main(textbook_name_arg)
    else:
        print("用法: python get_segment.py <textbook_name_without_extension>")
        print("示例: python get_segment.py my_physics_book")