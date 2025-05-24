import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys

import dashscope

# --- Configuration ---
SCRIPT_DIR = Path(__file__).parent.resolve()
TEXT_DIR_NAME = 'text_dir'  # Directory where pageXXXX.txt files are
INPUT_CATALOG_JSON = SCRIPT_DIR / 'result.json' # From get_catalog.py
MERMAID_OUTPUT_DIR = SCRIPT_DIR / 'mermaid_code' # New directory for mermaid outputs

DEFAULT_TEXT_DIR = SCRIPT_DIR / TEXT_DIR_NAME

DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY')
LLM_MODEL_MERMAID = 'qwen-max' # Model for generating mermaid code

# --- Prompt for LLM to Generate Mermaid Mindmap in JSON ---
PROMPT_TEXT_MERMAID_TEMPLATE = """
你是一个专业的AI助手，擅长将文本内容总结为Mermaid格式的思维导图 (mindmap)。
你将收到一个章节的标题和其完整的文本内容。

你的任务是：
1.  阅读并理解提供的章节文本内容。
2.  为该章节内容创建一个详细的Mermaid思维导图。思维导图应该以 `mindmap` 关键字开始，并遵循Mermaid的mindmap语法，其中**层级关系通过缩进表示**。
3.  将生成的Mermaid代码嵌入到一个JSON对象中。

你必须严格按照以下JSON格式输出。JSON对象中的 `chapter`，`name`，`actual_starting_page` 和 `actual_ending_page` 字段的值会由系统提供，你只需要专注于生成准确的 `mermaid_code`。

**Mermaid代码生成规则 (非常重要):**
-   在 `mermaid_code` 字符串中，**必须使用 `\\n` 来表示换行符**。
-   在 `mermaid_code` 字符串中，**必须使用 `\\t` 来表示每个层级的缩进 (一个制表符)**。例如，一级子节点前有一个 `\\t`，二级子节点前有两个 `\\t\\t`，以此类推。
-   Mermaid代码本身不应包含文字 `\\n` 或 `\\t`，而是这些字符的转义表示，以便它们在JSON字符串中正确表示实际的换行和制表符。

JSON输出格式示例:
{{
  "chapter": "{chapter_identifier_placeholder}",
  "name": "{chapter_name_placeholder}",
  "actual_starting_page": "{start_file_placeholder}",
  "actual_ending_page": "{end_file_placeholder}",
  "mermaid_code": "mindmap\\n\\troot(({chapter_name_placeholder}))\\n\\t\\t主要观点1\\n\\t\\t\\t子观点1.1\\n\\t\\t\\t\\t子观点1.1.1\\n\\t\\t主要观点2\\n\\t\\t\\t子观点2.1\\n\\t\\t\\t子观点2.2"
}}

请确保：
- `mermaid_code` 字段中的Mermaid代码是一个有效的、表示思维导图的字符串，严格遵循上述换行和缩进规则。
- 整个回复 **只有** 这个JSON对象，不包含任何其他文本、解释或Markdown代码块标记。

章节标题是: "{chapter_name_placeholder}"
章节内容如下:
---
{chapter_content_placeholder}
---
请生成上述内容的Mermaid思维导图，并按指定JSON格式返回。
"""

# --- Helper Functions (File I/O, etc.) ---
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

def save_json_data(data: Dict, output_file: Path, message_prefix: str = "数据"):
    """Saves dictionary data to a JSON file."""
    if not data:
        print(f"警告: 没有 {message_prefix} 可保存至 {output_file}。", file=sys.stderr)
        return False
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True) # Ensure directory exists
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"{message_prefix}已成功保存到 '{output_file}'")
        return True
    except Exception as e:
        print(f"保存文件 '{output_file}' 时出错: {e}", file=sys.stderr)
        return False

# --- LLM Interaction & Parsing ---
def call_llm_dashscope_text(api_key: str, system_prompt_with_content: str) -> str:
    """
    Calls DashScope Generation API.
    The system_prompt_with_content should be the fully formatted prompt including the chapter text.
    """
    if not api_key:
        print("错误：DASHSCOPE_API_KEY 未设置。无法调用LLM。", file=sys.stderr)
        return "ERROR:API_KEY_MISSING"

    messages = [
        {"role": "system", "content": system_prompt_with_content},
        {"role": "user", "content": "请根据系统提示生成所需的JSON输出。"}
    ]

    print(f"\n--- 正在调用文本模型: {LLM_MODEL_MERMAID} ---")
    try:
        response = dashscope.Generation.call(
            api_key=api_key,
            model=LLM_MODEL_MERMAID,
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

# --- Core Logic ---
def get_text_content_for_leaf(leaf_node: Dict, all_text_files: List[Path]) -> Optional[str]:
    """Reads and concatenates text content for a given leaf node."""
    start_file_name = leaf_node.get("actual_starting_page")
    end_file_name = leaf_node.get("actual_ending_page")

    if not start_file_name or not end_file_name or start_file_name == "UNKNOWN" or end_file_name == "UNKNOWN":
        print(f"警告: 节点 '{leaf_node.get('name')}' 缺少有效的文件名范围。跳过。", file=sys.stderr)
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


def process_chapters_recursive(chapters: List[Dict], all_text_files: List[Path], parent_chapter_id: str = ""):
    """
    Recursively traverses chapters, processes leaf nodes to generate mermaid code.
    """
    for i, chapter_data in enumerate(chapters):
        current_index = str(chapter_data.get("index", i + 1))
        current_chapter_id = f"{parent_chapter_id}{'.' if parent_chapter_id else ''}{current_index}"
        chapter_name = chapter_data.get("name", f"未知章节 {current_chapter_id}")

        if chapter_data.get("type") == "leaf":
            print(f"\n--- 正在处理叶节点: {current_chapter_id} - {chapter_name} ---")
            leaf_content = get_text_content_for_leaf(chapter_data, all_text_files)
            
            if not leaf_content:
                print(f"未能获取叶节点 '{chapter_name}' 的内容，跳过。", file=sys.stderr)
                continue

            start_file = chapter_data.get("actual_starting_page", "未知")
            end_file = chapter_data.get("actual_ending_page", "未知")

            # Prepare the full system prompt with all placeholders filled
            final_system_prompt = PROMPT_TEXT_MERMAID_TEMPLATE.replace("{chapter_identifier_placeholder}", current_chapter_id)
            final_system_prompt = final_system_prompt.replace("{chapter_name_placeholder}", chapter_name) # For JSON and mermaid root
            final_system_prompt = final_system_prompt.replace("{start_file_placeholder}", start_file)
            final_system_prompt = final_system_prompt.replace("{end_file_placeholder}", end_file)
            final_system_prompt = final_system_prompt.replace("{chapter_content_placeholder}", leaf_content)

            llm_response_str = call_llm_dashscope_text(DASHSCOPE_API_KEY, final_system_prompt)
            mermaid_json_data = parse_json_from_llm(llm_response_str)

            if mermaid_json_data:
                # Validate if the LLM included the correct metadata (it should, but good to check)
                if mermaid_json_data.get("chapter") != current_chapter_id:
                    print(f"警告: LLM返回的chapter_id '{mermaid_json_data.get('chapter')}' 与期望的 '{current_chapter_id}' 不符。将使用期望值。")
                    mermaid_json_data["chapter"] = current_chapter_id
                if mermaid_json_data.get("name") != chapter_name:
                     mermaid_json_data["name"] = chapter_name # Use our known name
                mermaid_json_data["actual_starting_page"] = start_file # Ensure our known values are used
                mermaid_json_data["actual_ending_page"] = end_file

                output_filename = MERMAID_OUTPUT_DIR / f"{current_chapter_id.replace('.', '_')}.json"
                save_json_data(mermaid_json_data, output_filename, f"Mermaid数据 ({current_chapter_id})")
            else:
                print(f"未能为章节 '{chapter_name}' 生成或解析Mermaid JSON。", file=sys.stderr)

        elif "children" in chapter_data and isinstance(chapter_data["children"], list):
            process_chapters_recursive(chapter_data["children"], all_text_files, current_chapter_id)


# --- Main Function ---
def main():
    print("开始生成Mermaid代码过程...")
    if not DASHSCOPE_API_KEY:
        print("致命错误: DASHSCOPE_API_KEY 环境变量未设置。", file=sys.stderr)
        return

    if not INPUT_CATALOG_JSON.exists():
        print(f"错误: 输入的目录JSON文件 '{INPUT_CATALOG_JSON}' 未找到。", file=sys.stderr)
        return

    if not DEFAULT_TEXT_DIR.is_dir():
       print(f"错误: 文本目录 '{TEXT_DIR_NAME}' 在路径 {DEFAULT_TEXT_DIR} 未找到。", file=sys.stderr)
       return

    # Load the catalog structure
    try:
        with open(INPUT_CATALOG_JSON, 'r', encoding='utf-8') as f:
            catalog_data = json.load(f)
        print(f"成功加载目录结构从 '{INPUT_CATALOG_JSON}'")
    except Exception as e:
        print(f"加载目录JSON文件 '{INPUT_CATALOG_JSON}' 时出错: {e}", file=sys.stderr)
        return

    all_text_files = list_text_files(DEFAULT_TEXT_DIR)
    if not all_text_files:
        print(f"错误: 在文本目录 '{DEFAULT_TEXT_DIR}' 中未找到任何文本文件。", file=sys.stderr)
        return

    # Create output directory
    MERMAID_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Mermaid输出目录: {MERMAID_OUTPUT_DIR}")

    # Process chapters
    if "chapters" in catalog_data:
        process_chapters_recursive(catalog_data["chapters"], all_text_files)
    else:
        print("错误: 加载的目录数据中未找到 'chapters' 键。", file=sys.stderr)

    print("\nMermaid代码生成过程完成。")

if __name__ == "__main__":
    main()
