import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys
import logging

import dashscope # 假设已安装: pip install dashscope

# 设置基本日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s] %(message)s')

# --- Constants defined as per requirements ---
BERT_MODEL = "bert-base-chinese"
CATALOG_FILENAME = "catalog.json" # Used by get_catalog.py
CATALOG_SEGMENTS_FILENAME = "catalog_with_segments.json" # Input for this script
EMBEDDING_BATCH_SIZE = 32
FAISS_INDEX_FILENAME = "knowledge_points.index"
IMAGES_SUBDIR_NAME = "textbook_images_dir"
LLM_MODEL = "qwen-max"
MAPPING_FILE_SUFFIX = ".mapping.json"
ORGCHART_SUBDIR_NAME = "orgchart_dir" # Directory to store per-chapter orgchart JSONs
TEXTBOOK_ORGCHART_FILENAME = "textbook_orgchart.json" # Final merged orgchart for the textbook
PAGES_FOR_CATALOG = 30
SEARCH_TOP_K = 3
TEXT_SUBDIR_NAME = "textbook_text_dir"
# This constant is used by this script for the root of the org chart.
# Its value was provided in an earlier context. Adjust if necessary.
BOOK_ROOT_TITLE = "马克思主义基本原理概论"
# --- End of defined constants ---


# --- LLM 提示 ---
PROMPT_ORGCHART_CHAPTER_TEMPLATE = """
你是一位专业的AI助手，擅长将章节的详细文本内容结构化为适用于 OrgChart JS 的JSON节点列表。
你将收到一个章节的标题 (name) 和其唯一路径ID (path_id)，以及该章节的完整文本内容。

你的任务是：
1.  阅读并理解提供的章节文本内容。
2.  为该章节内容创建一个层级结构，并将其转换为一个JSON节点对象列表。这个列表可以直接用于 OrgChart JS。
3.  列表中的第一个节点应该是代表整个章节内容的根节点。你可以使用章节标题作为这个根节点的名称。给这个根节点一个固定的、简单的ID，例如 "chapter_content_root"。它的 `pid` 应该为 `null` 或者不存在。
4.  其他所有内部节点都应该有唯一的 `id` (在此章节内部唯一即可，例如 "topic_1", "subtopic_1a") 和一个 `pid`，指向其父节点的 `id`。
5.  提取核心概念和它们之间的层级关系来构建这个结构。可以适当调整层级深度，不必过于细碎。

你必须严格按照以下JSON格式输出。整个输出应该是一个JSON列表，包含多个节点对象。

JSON输出格式示例 (这是一个节点列表):
[
  {{ "id": "chapter_content_root", "name": "{chapter_name_placeholder}", "pid": null, "title": "本章核心" }},
  {{ "id": "topic_A", "name": "主要议题A", "pid": "chapter_content_root", "title": "议题" }},
  {{ "id": "subtopic_A1", "name": "子议题A1", "pid": "topic_A", "title": "子议题" }},
  {{ "id": "subtopic_A2", "name": "子议题A2", "pid": "topic_A", "title": "子议题" }},
  {{ "id": "topic_B", "name": "主要议题B", "pid": "chapter_content_root", "title": "议题" }}
]

请确保：
- 整个回复 **只有** 这个JSON列表 (以 `[` 开始，以 `]` 结束)，不包含任何其他文本、解释或Markdown代码块标记。
- 每个节点对象至少包含 "id", "name", "pid" (根节点除外)。可以酌情添加 "title" 字段来描述节点类型或角色。
- "id" 在此章节的JSON列表中必须是唯一的。
- "pid" 必须引用同一列表中另一个节点的 "id"。

章节路径ID (供参考，不直接用于本JSON列表内的节点ID): "{path_id_placeholder}"
章节标题 (可用作 chapter_content_root 的 name): "{chapter_name_placeholder}"
章节内容如下:
---
{chapter_content_placeholder}
---
请为上述章节内容生成OrgChart JS的JSON节点列表。
"""

# --- 辅助函数 ---
def ensure_dir_exists(dir_path: Path):
    if not dir_path.exists():
        logging.info(f"创建目录: {dir_path}")
        dir_path.mkdir(parents=True, exist_ok=True)
    elif not dir_path.is_dir():
        logging.error(f"错误: {dir_path} 已存在但不是一个目录。")
        raise NotADirectoryError(f"{dir_path} 已存在但不是一个目录。")

def list_text_files(text_dir_path: Path) -> List[Path]:
    try:
        all_txts = sorted([
            f for f in text_dir_path.glob("page*.txt")
            if re.match(r"page\d{4}\.txt", f.name.lower())
        ])
        logging.info(f"在 {text_dir_path} 找到 {len(all_txts)} 个文本文件。")
        return all_txts
    except Exception as e:
        logging.error(f"列出文本文件目录 {text_dir_path} 时出错: {e}")
        return []

def read_text_file(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"读取文件 {file_path} 时出错: {e}")
        return None

def get_text_content_for_leaf(leaf_node_data: Dict, all_text_files: List[Path], chapter_path_id_for_log: str) -> Optional[str]:
    """读取并连接给定叶节点的文本内容。"""
    start_file_name = leaf_node_data.get("actual_starting_page")
    end_file_name = leaf_node_data.get("actual_ending_page")

    if not start_file_name or not end_file_name or \
       start_file_name in ["UNKNOWN", "PAGE_NOT_SPECIFIED", "INVALID_PAGE_FORMAT", "OFFSET_ERROR"] or \
       end_file_name in ["UNKNOWN", "PAGE_NOT_SPECIFIED", "INVALID_PAGE_FORMAT", "OFFSET_ERROR"]:
        logging.warning(f"节点 '{leaf_node_data.get('name')}' (生成ID: {chapter_path_id_for_log}) 缺少有效的文件名范围 ({start_file_name} - {end_file_name})。跳过。")
        return None

    try:
        filename_to_path = {p.name: p for p in all_text_files}

        if start_file_name not in filename_to_path or end_file_name not in filename_to_path:
            logging.warning(f"节点 '{leaf_node_data.get('name')}' (生成ID: {chapter_path_id_for_log}) 的起始/结束文件 ({start_file_name} / {end_file_name}) 在文件列表中未找到。")
            return None

        sorted_filenames = [p.name for p in all_text_files]
        start_idx = sorted_filenames.index(start_file_name)
        end_idx = sorted_filenames.index(end_file_name)

        if start_idx > end_idx:
            logging.warning(f"节点 '{leaf_node_data.get('name')}' (生成ID: {chapter_path_id_for_log}) 的起始文件索引 ({start_idx}) 大于结束文件索引 ({end_idx})。将只使用起始文件。")
            end_idx = start_idx

        content_parts = []
        logging.info(f"为节点 {chapter_path_id_for_log} 读取文件范围 {start_file_name} 到 {end_file_name} (索引 {start_idx} 到 {end_idx})")
        for i in range(start_idx, end_idx + 1):
            file_path = filename_to_path[sorted_filenames[i]]
            content = read_text_file(file_path)
            if content:
                content_parts.append(content)
            else:
                logging.warning(f"无法读取文件 {file_path} 的内容。")

        return "\n\n".join(content_parts) if content_parts else None

    except ValueError:
        logging.error(f"文件名 '{start_file_name}' 或 '{end_file_name}' 未在排序的文件列表中找到 (节点生成ID: {chapter_path_id_for_log})。")
        return None
    except Exception as e:
        logging.error(f"获取 '{leaf_node_data.get('name')}' (生成ID: {chapter_path_id_for_log}) 的文本内容时出错: {e}")
        return None

def call_llm_for_orgchart_nodes(api_key: Optional[str], chapter_path_id: str, chapter_name: str, chapter_content: str, model_to_use: str) -> Optional[List[Dict]]:
    """为单个章节调用LLM以生成OrgChart JS的节点列表。"""
    if not api_key:
        logging.error("错误：DASHSCOPE_API_KEY 未设置。无法调用LLM。")
        return None

    system_prompt = PROMPT_ORGCHART_CHAPTER_TEMPLATE.replace("{path_id_placeholder}", chapter_path_id)
    system_prompt = system_prompt.replace("{chapter_name_placeholder}", chapter_name)
    system_prompt = system_prompt.replace("{chapter_content_placeholder}", chapter_content)

    user_content_for_llm = "请根据以上提供的章节内容和系统提示，生成OrgChart JS的JSON节点列表。"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content_for_llm}]

    logging.info(f"\n--- 正在为章节 '{chapter_name}' (ID: {chapter_path_id}) 调用LLM ({model_to_use}) 生成OrgChart节点 ---")
    try:
        response = dashscope.Generation.call(
            api_key=api_key,
            model=model_to_use,
            messages=messages,
            result_format='message',
            stream=False
        )
        if response.status_code == 200 and response.output and response.output.choices:
            raw_text = response.output.choices[0].message.content
            logging.info(f"LLM对章节 '{chapter_name}' 的响应 (前200字符): {raw_text[:200]}...")

            cleaned_text = re.sub(r"```json\s*", "", raw_text, flags=re.IGNORECASE).strip()
            cleaned_text = re.sub(r"```\s*$", "", cleaned_text).strip()
            cleaned_text = re.sub(r'^json\s*', '', cleaned_text, flags=re.IGNORECASE).strip()

            first_bracket = cleaned_text.find('[')
            last_bracket = cleaned_text.rfind(']')

            if first_bracket != -1 and last_bracket > first_bracket:
                json_string = cleaned_text[first_bracket : last_bracket + 1]
                try:
                    parsed_list = json.loads(json_string)
                    if isinstance(parsed_list, list):
                        logging.info(f"章节 '{chapter_name}' 的OrgChart JSON列表解析成功，包含 {len(parsed_list)} 个节点。")
                        return parsed_list
                    else:
                        logging.error(f"LLM为章节 '{chapter_name}' 的输出未解析为列表，而是 {type(parsed_list)}。")
                        logging.debug(f"原始LLM输出:\n{raw_text}")
                        return None
                except json.JSONDecodeError as e:
                    logging.error(f"章节 '{chapter_name}' 的OrgChart JSON列表解析失败: {e}")
                    logging.debug(f"尝试解析的字符串:\n{json_string}")
                    return None
            else:
                logging.error(f"在LLM为章节 '{chapter_name}' 的输出中未能找到有效的JSON列表括号。")
                logging.debug(f"原始LLM输出:\n{raw_text}")
                return None
        else:
            logging.error(f"LLM API 调用失败 (章节 '{chapter_name}'): {response.status_code} - {response.message}")
            return None
    except Exception as e:
        logging.error(f"LLM API 调用异常 (章节 '{chapter_name}'): {e}")
        return None
    finally:
        logging.info(f"--- 结束对章节 '{chapter_name}' 的LLM调用 ---")

def save_chapter_orgchart_json(data: List[Dict], output_file: Path, chapter_path_id_for_file: str):
    ensure_dir_exists(output_file.parent)
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logging.info(f"章节 {chapter_path_id_for_file} 的OrgChart JSON已保存到: {output_file}")
    except Exception as e:
        logging.error(f"保存章节 {chapter_path_id_for_file} 的OrgChart JSON到 {output_file} 时出错: {e}")

def process_leaf_node_for_orgchart(
    leaf_node_data: Dict,
    generated_path_id: str,
    all_text_files: List[Path],
    orgchart_chapter_dir: Path,
    api_key: str,
    model_to_use: str # Changed from llm_model
    ):
    """处理单个叶子节点：获取文本，调用LLM，保存结果。"""
    chapter_name = leaf_node_data.get("name")

    if not chapter_name:
        logging.warning(f"叶子节点缺少 name: {leaf_node_data} (生成ID: {generated_path_id})，跳过。")
        return

    output_filename = orgchart_chapter_dir / f"{generated_path_id.replace('.', '_')}.orgchart.json"
    if output_filename.exists():
        logging.info(f"章节 {chapter_name} (ID: {generated_path_id}) 的OrgChart JSON文件已存在，跳过生成。")
        return

    logging.info(f"开始处理叶子节点 {chapter_name} (ID: {generated_path_id}) 的OrgChart生成...")
    chapter_content = get_text_content_for_leaf(leaf_node_data, all_text_files, generated_path_id)

    if not chapter_content:
        logging.warning(f"未能获取叶子节点 {chapter_name} (ID: {generated_path_id}) 的文本内容。跳过LLM调用。")
        return

    orgchart_nodes_for_chapter = call_llm_for_orgchart_nodes(
        api_key, generated_path_id, chapter_name, chapter_content, model_to_use
    )

    if orgchart_nodes_for_chapter:
        save_chapter_orgchart_json(orgchart_nodes_for_chapter, output_filename, generated_path_id)
    else:
        logging.warning(f"未能为章节 {chapter_name} (ID: {generated_path_id}) 生成OrgChart节点列表。")

def traverse_and_process_leaves(
    nodes: List[Dict],
    all_text_files: List[Path],
    orgchart_chapter_dir: Path,
    api_key: str,
    model_to_use: str, # Changed from llm_model
    parent_path_id: str = ""
    ):
    """递归遍历目录树，对每个叶子节点执行OrgChart JSON生成。"""
    for i, node_data in enumerate(nodes):
        current_index_val = node_data.get("index")
        current_index_str = str(current_index_val) if current_index_val is not None else str(i + 1)
        current_generated_path_id = f"{parent_path_id}{'.' if parent_path_id else ''}{current_index_str}"
        node_data["generated_path_id"] = current_generated_path_id

        if node_data.get("type") == "leaf":
            process_leaf_node_for_orgchart(
                node_data,
                current_generated_path_id,
                all_text_files,
                orgchart_chapter_dir,
                api_key,
                model_to_use
            )

        if node_data.get("children") and isinstance(node_data.get("children"), list):
            traverse_and_process_leaves(
                node_data["children"],
                all_text_files,
                orgchart_chapter_dir,
                api_key,
                model_to_use,
                current_generated_path_id
            )

def merge_all_orgchart_data(
    catalog_data: Dict,
    orgchart_chapter_dir: Path,
    book_title_for_root: str, # Changed from book_root_title
    final_output_file: Path
    ):
    """将主目录结构与各个章节内部的OrgChart JSON数据合并。"""
    logging.info("开始合并所有OrgChart数据...")
    final_orgchart_nodes = []
    textbook_root_node_id = "TEXTBOOK_ROOT"
    final_orgchart_nodes.append({
        "id": textbook_root_node_id,
        "pid": None,
        "name": book_title_for_root, # Use passed parameter
        "title": "全书概览"
    })

    def process_and_merge_recursive(catalog_nodes: List[Dict], parent_orgchart_id: str):
        for cat_node in catalog_nodes:
            current_node_orgchart_id = cat_node.get("generated_path_id")
            if not current_node_orgchart_id:
                logging.warning(f"目录节点 '{cat_node.get('name')}' 缺少 'generated_path_id'，无法合并。")
                continue

            final_orgchart_nodes.append({
                "id": current_node_orgchart_id,
                "pid": parent_orgchart_id,
                "name": cat_node.get("name"),
                "title": "章节" if cat_node.get("type") == "tree" else "知识单元章节",
                "type_from_catalog": cat_node.get("type"),
                "knowledge_points_count": len(cat_node.get("knowledge_points", [])),
            })

            if cat_node.get("type") == "leaf":
                chapter_orgchart_filename = orgchart_chapter_dir / f"{current_node_orgchart_id.replace('.', '_')}.orgchart.json"
                if chapter_orgchart_filename.exists():
                    try:
                        with open(chapter_orgchart_filename, 'r', encoding='utf-8') as f_ch_oc:
                            chapter_internal_nodes = json.load(f_ch_oc)

                        if isinstance(chapter_internal_nodes, list):
                            for internal_node in chapter_internal_nodes:
                                internal_node_id_str = str(internal_node.get('id', 'unknown_internal_id'))
                                internal_node_pid_str = str(internal_node.get('pid')) if internal_node.get('pid') is not None else None
                                new_internal_id = f"{current_node_orgchart_id}__{internal_node_id_str}"
                                new_internal_pid = f"{current_node_orgchart_id}__{internal_node_pid_str}" if internal_node_pid_str else current_node_orgchart_id
                                final_orgchart_nodes.append({
                                    "id": new_internal_id,
                                    "pid": new_internal_pid,
                                    "name": internal_node.get("name"),
                                    "title": internal_node.get("title", "内部节点"),
                                    "isInternal": True
                                })
                        else:
                             logging.warning(f"章节 {current_node_orgchart_id} 的OrgChart文件 '{chapter_orgchart_filename.name}' 内容不是列表。")
                    except Exception as e:
                        logging.error(f"读取或处理章节 {current_node_orgchart_id} 的OrgChart文件 '{chapter_orgchart_filename.name}' 时出错: {e}")
                else:
                    logging.warning(f"未找到章节 {current_node_orgchart_id} 的OrgChart文件: {chapter_orgchart_filename.name}")

            if cat_node.get("children") and isinstance(cat_node.get("children"), list):
                process_and_merge_recursive(cat_node["children"], current_node_orgchart_id)

    if catalog_data.get("chapters") and isinstance(catalog_data.get("chapters"), list):
        process_and_merge_recursive(catalog_data["chapters"], textbook_root_node_id)
    else:
        logging.error("输入的目录数据中缺少 'chapters' 列表。")
        return False

    ensure_dir_exists(final_output_file.parent)
    try:
        with open(final_output_file, 'w', encoding='utf-8') as f_out:
            json.dump(final_orgchart_nodes, f_out, indent=4, ensure_ascii=False)
        logging.info(f"所有章节的OrgChart数据已合并并保存到: {final_output_file}")
        return True
    except Exception as e:
        logging.error(f"保存合并后的OrgChart JSON到 {final_output_file} 时出错: {e}")
        return False

def run_orgchart_generation(textbook_name: str, script_dir: Path):
    """
    为指定教材编排OrgChart生成过程。
    此函数是脚本的主要逻辑入口点，可被其他脚本调用。
    """
    logging.info(f"开始为教材 '{textbook_name}' 生成OrgChart (脚本目录: {script_dir})")

    dashscope_api_key = os.getenv('DASHSCOPE_API_KEY')
    if not dashscope_api_key:
        logging.error("致命错误: 环境变量 DASHSCOPE_API_KEY 未设置。")
        return

    # Path definitions using global constants and textbook_name
    textbook_base_uploads_dir = script_dir / "uploads" / textbook_name
    info_storage_dir = textbook_base_uploads_dir / "textbook_information"

    input_catalog_file = info_storage_dir / CATALOG_SEGMENTS_FILENAME # Assumes output from get_segment.py
    text_files_dir = info_storage_dir / TEXT_SUBDIR_NAME
    orgchart_per_chapter_dir = info_storage_dir / ORGCHART_SUBDIR_NAME
    final_merged_orgchart_file = info_storage_dir / TEXTBOOK_ORGCHART_FILENAME

    # Use global constants for configuration
    current_llm_model = LLM_MODEL
    current_book_root_title = BOOK_ROOT_TITLE # Global constant

    logging.info(f"输入目录文件 (catalog_with_segments.json): {input_catalog_file}")
    logging.info(f"OCR文本文件目录: {text_files_dir}")
    logging.info(f"LLM模型: {current_llm_model}")
    logging.info(f"章节OrgChart输出目录: {orgchart_per_chapter_dir}")
    logging.info(f"最终教材OrgChart输出文件: {final_merged_orgchart_file}")
    logging.info(f"书籍根标题 (用于OrgChart根节点): {current_book_root_title}")

    ensure_dir_exists(orgchart_per_chapter_dir)

    if not input_catalog_file.exists():
        logging.error(f"错误: 输入的目录文件 '{input_catalog_file}' 未找到。请确保 get_segment.py 已成功运行。")
        return
    try:
        with open(input_catalog_file, 'r', encoding='utf-8') as f:
            catalog_data = json.load(f)
        logging.info(f"成功从 '{input_catalog_file}' 加载目录数据。")
    except Exception as e:
        logging.error(f"加载目录文件 '{input_catalog_file}' 时出错: {e}")
        return

    if not text_files_dir.is_dir():
        logging.error(f"错误: 文本目录 '{text_files_dir}' 未找到。请确保 images_and_ocr.py 已成功运行。")
        return

    all_ocr_text_files = list_text_files(text_files_dir)
    if not all_ocr_text_files:
        logging.error(f"错误: 在OCR文本目录 '{text_files_dir}' 中未找到任何文本文件。")
        return

    logging.info("\n--- 步骤1: 为每个叶子章节生成OrgChart内部结构JSON ---")
    if catalog_data.get("chapters") and isinstance(catalog_data.get("chapters"), list):
        traverse_and_process_leaves(
            catalog_data["chapters"],
            all_ocr_text_files,
            orgchart_per_chapter_dir, # Pass the correct directory for individual chapter orgcharts
            dashscope_api_key,
            current_llm_model,
            parent_path_id=""
        )
    else:
        logging.error("目录数据中缺少 'chapters' 列表或格式不正确。")
        return
    logging.info("--- 步骤1完成 ---")

    logging.info("\n--- 步骤2: 合并所有章节的OrgChart数据 ---")
    merge_success = merge_all_orgchart_data(
        catalog_data,
        orgchart_per_chapter_dir,
        current_book_root_title,
        final_merged_orgchart_file
    )
    if merge_success:
        logging.info("--- 步骤2完成 ---")
    else:
        logging.error("合并OrgChart数据失败。")

    logging.info(f"教材 '{textbook_name}' 的OrgChart生成完毕。")


def main_cli():
    """Command-line interface handler."""
    if len(sys.argv) > 1:
        textbook_name_arg = sys.argv[1]
        if textbook_name_arg.lower().endswith(".pdf"):
            textbook_name_arg = textbook_name_arg[:-4] # Use base name

        try:
            current_script_dir = Path(__file__).resolve().parent
        except NameError:
            current_script_dir = Path(os.getcwd()).resolve() # Fallback

        run_orgchart_generation(textbook_name_arg, current_script_dir)
    else:
        print(f"用法: python {Path(sys.argv[0]).name} <textbook_name_without_extension>")
        print(f"示例: python {Path(sys.argv[0]).name} my_history_book")

if __name__ == "__main__":
    main_cli()