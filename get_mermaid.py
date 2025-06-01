import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys

import dashscope # 假设已安装: pip install dashscope

# --- 默认配置文件名 ---
DEFAULT_CONFIG_FILENAME = "config.json" # 使用统一的配置文件名

# --- LLM 提示 ---
PROMPT_TEXT_MERMAID_TEMPLATE = """
你是一个专业的AI助手，擅长将文本内容总结为Mermaid格式的思维导图 (mindmap)。
你将收到一个章节的标题、其唯一路径ID、以及其完整的文本内容。

你的任务是：
1.  阅读并理解提供的章节文本内容。
2.  为该章节内容创建一个详细的Mermaid思维导图。思维导图应该以 `mindmap` 关键字开始，并遵循Mermaid的mindmap语法，其中**层级关系通过缩进表示**。
3.  将生成的Mermaid代码嵌入到一个JSON对象中。

你必须严格按照以下JSON格式输出。JSON对象中的 `path_id`，`name`，`actual_starting_page` 和 `actual_ending_page` 字段的值会由系统提供，你只需要专注于生成准确的 `mermaid_code`。

**Mermaid代码生成规则 (非常重要):**
-   在 `mermaid_code` 字符串中，**必须使用 `\\n` 来表示换行符**。
-   在 `mermaid_code` 字符串中，**必须使用 `\\t` 来表示每个层级的缩进 (一个制表符)**。例如，一级子节点前有一个 `\\t`，二级子节点前有两个 `\\t\\t`，以此类推。
-   Mermaid代码本身不应包含文字 `\\n` 或 `\\t`，而是这些字符的转义表示，以便它们在JSON字符串中正确表示实际的换行和制表符。

JSON输出格式示例:
{{
  "path_id": "{path_id_placeholder}",
  "name": "{chapter_name_placeholder}",
  "actual_starting_page": "{start_file_placeholder}",
  "actual_ending_page": "{end_file_placeholder}",
  "mermaid_code": "mindmap\\n\\troot(({chapter_name_placeholder}))\\n\\t\\t主要观点1\\n\\t\\t\\t子观点1.1\\n\\t\\t\\t\\t子观点1.1.1\\n\\t\\t主要观点2\\n\\t\\t\\t子观点2.1\\n\\t\\t\\t子观点2.2"
}}

请确保：
- `mermaid_code` 字段中的Mermaid代码是一个有效的、表示思维导图的字符串，严格遵循上述换行和缩进规则。
- 整个回复 **只有** 这个JSON对象，不包含任何其他文本、解释或Markdown代码块标记。

章节路径ID是: "{path_id_placeholder}"
章节标题是: "{chapter_name_placeholder}"
章节内容如下:
---
{chapter_content_placeholder}
---
请生成上述内容的Mermaid思维导图，并按指定JSON格式返回。
"""

# --- 辅助函数 ---

def load_mermaid_config(config_file_path: Path) -> Optional[Dict]:
    """
    从指定的 JSON 文件加载 Mermaid 生成相关的配置。

    Args:
        config_file_path (Path): 配置文件的完整路径。

    Returns:
        Optional[Dict]: 如果加载成功则返回配置字典，否则返回 None。
    """
    print(f"正在从 '{config_file_path}' 加载 Mermaid 生成配置...")
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        # 验证 Mermaid 脚本所需的键是否存在且类型正确
        required_keys = {
            "text_dir": str,      # 作为此脚本的文本输入目录
            "catalog": str, # 作为此脚本的目录输入文件 (应包含 path_id)
            "mermaid_dir": str,
            "llm_model": str
        }
        for key, expected_type in required_keys.items():
            if key not in config_data:
                print(f"错误：配置文件 '{config_file_path}' 中缺少键 '{key}' (Mermaid配置需要)。", file=sys.stderr)
                return None
            if not isinstance(config_data[key], expected_type):
                print(f"错误：配置文件 '{config_file_path}' 中键 '{key}' 的类型不正确。期望类型：{expected_type}, 实际类型：{type(config_data[key])}。", file=sys.stderr)
                return None
        
        print("Mermaid 生成配置加载成功。")
        return config_data
    except FileNotFoundError:
        print(f"错误：配置文件 '{config_file_path}' 未找到。请创建该文件。", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"错误：解析配置文件 '{config_file_path}' 失败：{e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"加载配置文件时发生未知错误：{e}", file=sys.stderr)
        return None

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
        output_file.parent.mkdir(parents=True, exist_ok=True) # 确保输出目录存在
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"{message_prefix}已成功保存到 '{output_file}'")
        return True
    except Exception as e:
        print(f"保存文件 '{output_file}' 时出错: {e}", file=sys.stderr)
        return False

# --- LLM 交互与解析 ---
def call_llm_dashscope_text(api_key: Optional[str], system_prompt_with_content: str, model_name: str) -> str:
    """
    调用 DashScope Generation API。
    system_prompt_with_content 应为包含章节文本的完整格式化提示。
    """
    if not api_key:
        print("错误：DASHSCOPE_API_KEY 未设置。无法调用LLM。", file=sys.stderr)
        return "ERROR:API_KEY_MISSING"

    messages = [
        {"role": "system", "content": system_prompt_with_content},
        {"role": "user", "content": "请根据系统提示生成所需的JSON输出。"} # 通用用户指令
    ]

    print(f"\n--- 正在调用文本模型: {model_name} ---")
    try:
        response = dashscope.Generation.call(
            api_key=api_key,
            model=model_name, # 使用传入的模型名称
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
    # 移除常见的Markdown代码块标记
    cleaned_string = re.sub(r"```json\s*", "", llm_output, flags=re.IGNORECASE).strip()
    cleaned_string = re.sub(r"```\s*$", "", cleaned_string).strip()
    # 移除可能存在于开头的 "json" 关键字
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
        print(f"警告: 节点 '{leaf_node.get('name')}' (ID: {leaf_node.get('path_id', '未知')}) 缺少有效的文件名范围 ({start_file_name} - {end_file_name})。跳过。", file=sys.stderr)
        return None

    try:
        filename_to_path = {p.name: p for p in all_text_files}
        
        if start_file_name not in filename_to_path or end_file_name not in filename_to_path:
            print(f"警告: 节点 '{leaf_node.get('name')}' (ID: {leaf_node.get('path_id', '未知')}) 的起始/结束文件 ({start_file_name} / {end_file_name}) 在文件列表中未找到。", file=sys.stderr)
            return None

        sorted_filenames = [p.name for p in all_text_files]
        start_idx = sorted_filenames.index(start_file_name)
        end_idx = sorted_filenames.index(end_file_name)

        if start_idx > end_idx:
            print(f"警告: 节点 '{leaf_node.get('name')}' (ID: {leaf_node.get('path_id', '未知')}) 的起始文件索引 ({start_idx}) 大于结束文件索引 ({end_idx})。将只使用起始文件。", file=sys.stderr)
            end_idx = start_idx
        
        content_parts = []
        print(f"信息: 为节点 {leaf_node.get('path_id', '未知')} 读取文件范围 {start_file_name} 到 {end_file_name} (索引 {start_idx} 到 {end_idx})")
        for i in range(start_idx, end_idx + 1):
            file_path = filename_to_path[sorted_filenames[i]]
            content = read_text_file(file_path)
            if content:
                content_parts.append(content)
            else:
                print(f"警告: 无法读取文件 {file_path} 的内容。", file=sys.stderr)
        
        return "\n\n".join(content_parts) if content_parts else None

    except ValueError: # .index() 方法在未找到元素时抛出 ValueError
        print(f"错误: 文件名 '{start_file_name}' 或 '{end_file_name}' 未在排序的文件列表中找到 (节点: {leaf_node.get('path_id', '未知')})。", file=sys.stderr)
        return None
    except Exception as e:
        print(f"获取 '{leaf_node.get('name')}' (ID: {leaf_node.get('path_id', '未知')}) 的文本内容时出错: {e}", file=sys.stderr)
        return None


def process_chapters_recursive(chapters: List[Dict], all_text_files: List[Path], mermaid_output_base_path: Path, api_key: str, llm_model_for_mermaid: str):
    """
    递归遍历章节，处理叶节点以生成 Mermaid 代码。
    现在从 chapter_data 中读取 path_id。
    """
    for chapter_data in chapters:
        # 从目录数据中获取 path_id，这是由 get_catalog.py 生成的
        current_path_id = chapter_data.get("path_id")
        if not current_path_id:
            # 如果目录中没有 path_id，记录警告并尝试基于索引构建一个临时的，但这不理想
            # 更好的做法是确保 get_catalog.py 总是生成 path_id
            temp_index = chapter_data.get("index", "unknown_index") # 这是一个简化的回退
            print(f"警告: 节点 '{chapter_data.get('name', '未知名称')}' 缺少 'path_id'。将使用临时ID '{temp_index}'，这可能导致问题。", file=sys.stderr)
            current_path_id = str(temp_index) # 不再需要 parent_chapter_id 来构建

        chapter_name = chapter_data.get("name", f"未知章节 {current_path_id}")

        if chapter_data.get("type") == "leaf":
            print(f"\n--- 正在处理叶节点: {current_path_id} - {chapter_name} ---")
            leaf_content = get_text_content_for_leaf(chapter_data, all_text_files)
            
            if not leaf_content:
                print(f"未能获取叶节点 '{chapter_name}' (ID: {current_path_id}) 的内容，跳过。", file=sys.stderr)
                continue

            start_file = chapter_data.get("actual_starting_page", "未知")
            end_file = chapter_data.get("actual_ending_page", "未知")

            # 准备包含所有占位符已填充的完整系统提示
            final_system_prompt = PROMPT_TEXT_MERMAID_TEMPLATE.replace("{path_id_placeholder}", current_path_id)
            final_system_prompt = final_system_prompt.replace("{chapter_name_placeholder}", chapter_name) # 用于JSON和Mermaid根节点
            final_system_prompt = final_system_prompt.replace("{start_file_placeholder}", start_file)
            final_system_prompt = final_system_prompt.replace("{end_file_placeholder}", end_file)
            final_system_prompt = final_system_prompt.replace("{chapter_content_placeholder}", leaf_content)
            
            llm_response_str = call_llm_dashscope_text(api_key, final_system_prompt, llm_model_for_mermaid)
            mermaid_json_data = parse_json_from_llm(llm_response_str)

            if mermaid_json_data:
                # 验证LLM是否包含了正确的元数据
                if mermaid_json_data.get("path_id") != current_path_id:
                    print(f"警告: LLM返回的path_id '{mermaid_json_data.get('path_id')}' 与期望的 '{current_path_id}' 不符。将使用期望值。", file=sys.stderr)
                    mermaid_json_data["path_id"] = current_path_id
                
                # 确保其他元数据也正确（如果需要）
                mermaid_json_data["name"] = chapter_name 
                mermaid_json_data["actual_starting_page"] = start_file
                mermaid_json_data["actual_ending_page"] = end_file

                # 文件名中的点替换为下划线
                safe_path_id_filename = current_path_id.replace('.', '_')
                output_filename = mermaid_output_base_path / f"{safe_path_id_filename}.json"
                save_json_data(mermaid_json_data, output_filename, f"Mermaid数据 ({current_path_id})")
            else:
                print(f"未能为章节 '{chapter_name}' (ID: {current_path_id}) 生成或解析Mermaid JSON。", file=sys.stderr)
                error_output_path = mermaid_output_base_path / f"{current_path_id.replace('.', '_')}.llm_error_output.txt"
                try:
                    with open(error_output_path, 'w', encoding='utf-8')as f_err:
                        f_err.write(f"LLM Output for chapter {current_path_id} that failed parsing (Mermaid):\n{llm_response_str}")
                    print(f"LLM 的原始错误输出已保存到: {error_output_path}")
                except Exception as e_save:
                    print(f"保存 LLM 错误输出时也发生错误: {e_save}", file=sys.stderr)

        elif "children" in chapter_data and isinstance(chapter_data["children"], list) and chapter_data["children"]:
            process_chapters_recursive(chapter_data["children"], all_text_files, mermaid_output_base_path, api_key, llm_model_for_mermaid) # parent_chapter_id 不再需要传递，因为 path_id 直接从节点读取

# --- 主函数 ---
def main_orchestrator(config: Dict, script_dir_path: Path):
    """
    使用加载的配置来编排 Mermaid 代码生成过程。
    """
    print("开始生成Mermaid代码过程...")
    dashscope_api_key = os.getenv('DASHSCOPE_API_KEY') # API密钥仍从环境变量获取
    if not dashscope_api_key:
        print("致命错误: 环境变量 DASHSCOPE_API_KEY 未设置。", file=sys.stderr)
        return

    # 从配置中获取值
    text_dir_name_from_config = config["text_dir"]
    catalog_input_filename_from_config = config["catalog"] # 这个catalog.json现在应该包含path_id
    mermaid_output_dir_name_from_config = config["mermaid_dir"]
    llm_model_for_mermaid = config["llm_model"]

    # 构建路径
    text_dir_full_path = script_dir_path / text_dir_name_from_config
    input_catalog_json_full_path = script_dir_path / catalog_input_filename_from_config
    mermaid_output_full_path = script_dir_path / mermaid_output_dir_name_from_config

    print(f"脚本目录: {script_dir_path}")
    print(f"文本目录 (来自配置): {text_dir_full_path}")
    print(f"目录输入文件 (来自配置): {input_catalog_json_full_path}")
    print(f"Mermaid输出目录 (来自配置): {mermaid_output_full_path}")
    print(f"用于Mermaid的LLM模型 (来自配置): {llm_model_for_mermaid}")

    if not input_catalog_json_full_path.exists():
        print(f"错误: 输入的目录JSON文件 '{input_catalog_json_full_path}' 未找到。", file=sys.stderr)
        return

    if not text_dir_full_path.is_dir():
        print(f"错误: 文本目录 '{text_dir_full_path}' 未找到。", file=sys.stderr)
        return

    # 加载目录结构
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
        return

    # 创建输出目录
    mermaid_output_full_path.mkdir(parents=True, exist_ok=True)

    # 处理章节
    if "chapters" in catalog_data and isinstance(catalog_data["chapters"], list) :
        process_chapters_recursive(catalog_data["chapters"], all_text_files, mermaid_output_full_path, dashscope_api_key, llm_model_for_mermaid)
    else:
        print("错误: 加载的目录数据中未找到 'chapters' 键或其不是列表。", file=sys.stderr)

    print("\nMermaid代码生成过程完成。")

def main(): # Renamed from __main__ to be callable from main.py
    try:
        # 确定脚本所在的目录
        current_script_dir = Path(__file__).parent.resolve()
    except NameError: # 处理在某些IDE或直接执行时 __file__ 未定义的情况
        current_script_dir = Path(os.getcwd()).resolve()
    
    # 加载配置
    config_path = current_script_dir / DEFAULT_CONFIG_FILENAME
    app_config = load_mermaid_config(config_path)

    if app_config:
        main_orchestrator(app_config, current_script_dir)
    else:
        print("由于配置加载失败，Mermaid代码生成流程无法启动。")

if __name__ == "__main__":
    main()
