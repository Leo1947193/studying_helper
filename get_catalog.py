import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import sys

import dashscope # 假设已安装: pip install dashscope

# --- 默认配置文件名 ---
DEFAULT_CONFIG_FILENAME = "config.json" # 您可以更改为 "config.json" 如果希望所有脚本共用一个

# --- LLM 提示 ---
# (PROMPT_TEXT_OFFSET_STRATEGY 保持不变，为了简洁此处省略，实际代码中应包含它)
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
         "actual_starting_page": "page0006.txt", "children": ""}, // 假设这是第一个叶子节点
        {"index": 2, "name": "第二节...", "type": "leaf", "starting_page": 14, "ending_page": 26, "children": ""}
      ]
    }
  ]
}
- 请在你的回复中 **只提供 JSON 对象**。
"""

# --- 辅助函数 ---

def load_app_config(config_file_path: Path) -> Optional[Dict]:
    """
    从指定的 JSON 文件加载应用配置。

    Args:
        config_file_path (Path): 配置文件的完整路径。

    Returns:
        Optional[Dict]: 如果加载成功则返回配置字典，否则返回 None。
    """
    print(f"正在从 '{config_file_path}' 加载应用配置...")
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        # 验证必要的键是否存在且类型正确
        required_keys = {
            "text_dir": str,
            "catalog": str,
            "pages_for_catalog": int,
            "llm_model": str
        }
        for key, expected_type in required_keys.items():
            if key not in config_data:
                print(f"错误：配置文件 '{config_file_path}' 中缺少键 '{key}'。", file=sys.stderr)
                return None
            if not isinstance(config_data[key], expected_type):
                print(f"错误：配置文件 '{config_file_path}' 中键 '{key}' 的类型不正确。期望类型：{expected_type}, 实际类型：{type(config_data[key])}。", file=sys.stderr)
                return None
        
        if not 0 < config_data["pages_for_catalog"] < 200: # 对页数进行合理性检查
             print(f"警告：配置的 'pages_for_catalog' ({config_data['pages_for_catalog']}) 可能不合理。请检查配置。", file=sys.stderr)


        print("应用配置加载成功。")
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

def call_llm_dashscope_text(api_key: Optional[str], user_content: str, system_prompt: str, model_name: str) -> str:
    """通用函数，用于调用 DashScope Generation API。"""
    if not api_key:
        print("错误：DASHSCOPE_API_KEY 未提供或为空。", file=sys.stderr)
        return "ERROR:API_KEY_MISSING"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
    print(f"\n--- 正在调用文本模型: {model_name} ---")
    try:
        response = dashscope.Generation.call(api_key=api_key, model=model_name, messages=messages, result_format='message', stream=False)
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

# --- 偏移量计算逻辑 ---

def _find_first_leaf_recursive(nodes: List[Dict]) -> Optional[Dict]:
    """辅助函数：在结构中找到第一个叶节点。"""
    for node in nodes:
        if node.get("type") == "leaf":
            return node # 找到第一个
        elif node.get("type") == "tree" and "children" in node and isinstance(node["children"], list):
            found = _find_first_leaf_recursive(node["children"])
            if found:
                return found # 将其向上传递
    return None

def get_filename_number(filename: str) -> Optional[int]:
    """从文件名中提取数字 (例如, 从 page0009.txt 中提取 9)。"""
    match = re.search(r'page(\d{4})\.txt', filename, re.IGNORECASE) # 忽略大小写
    return int(match.group(1)) if match else None

def format_filename(number: int) -> str:
    """将数字格式化为 pageXXXX.txt。"""
    return f"page{number:04d}.txt"

def _apply_offset_recursive(nodes: List[Dict], offset: int):
    """辅助函数：递归地将偏移量应用于起始/结束页码。"""
    for node in nodes:
        try:
            # 处理 starting_page
            if "starting_page" in node and isinstance(node["starting_page"], (int, float)): # 允许浮点数以防万一
                node["actual_starting_page"] = format_filename(int(node["starting_page"]) + offset)
            elif "starting_page" in node: # 如果存在但不是数字
                print(f"警告：节点 '{node.get('name', '未命名节点')}' 的 'starting_page' 不是有效数字 ({node['starting_page']})，无法应用偏移量。", file=sys.stderr)
                node["actual_starting_page"] = "INVALID_PAGE_FORMAT"
            else: # 如果不存在
                node["actual_starting_page"] = "PAGE_NOT_SPECIFIED"

            # 处理 ending_page
            if "ending_page" in node and isinstance(node["ending_page"], (int, float)):
                node["actual_ending_page"] = format_filename(int(node["ending_page"]) + offset)
            elif "ending_page" in node:
                print(f"警告：节点 '{node.get('name', '未命名节点')}' 的 'ending_page' 不是有效数字 ({node['ending_page']})，无法应用偏移量。", file=sys.stderr)
                node["actual_ending_page"] = "INVALID_PAGE_FORMAT"
            else:
                node["actual_ending_page"] = "PAGE_NOT_SPECIFIED"

        except Exception as e:
            print(f"警告: 应用偏移量时出错于节点 '{node.get('name', '未命名节点')}': {e}", file=sys.stderr)
            node["actual_starting_page"] = "OFFSET_ERROR"
            node["actual_ending_page"] = "OFFSET_ERROR"

        # 如果存在子节点，则递归
        if "children" in node and isinstance(node["children"], list):
            _apply_offset_recursive(node["children"], offset)


def apply_offset_and_save(data: Dict, output_file: Path):
    """
    从第一个叶节点计算偏移量，并将其应用于所有节点，然后保存结果。
    """
    print("--- 步骤 2 & 3: 计算并应用页面偏移量 ---")
    if not data or "chapters" not in data or not isinstance(data["chapters"], list):
        print("错误：提供的目录数据无效或缺少 'chapters' 列表。", file=sys.stderr)
        save_json_data(data if data else {}, output_file, "部分结果（数据无效）") # 尝试保存任何已有的数据
        return

    first_leaf = _find_first_leaf_recursive(data["chapters"])

    if not first_leaf:
        print("错误：未能在LLM输出中找到第一个叶节点。", file=sys.stderr)
        save_json_data(data, output_file, "部分结果（无偏移量，未找到首叶）")
        return

    toc_start_page_val = first_leaf.get("starting_page")
    actual_start_file_val = first_leaf.get("actual_starting_page") # LLM应该只为第一个叶节点提供这个

    if not isinstance(toc_start_page_val, int):
        print(f"错误：第一个叶节点 '{first_leaf.get('name', '未命名节点')}' 的 'starting_page' 不是有效的整数 ({toc_start_page_val})。", file=sys.stderr)
        save_json_data(data, output_file, "部分结果（无偏移量，页码无效）")
        return
    
    if not actual_start_file_val or not isinstance(actual_start_file_val, str):
        print(f"错误：第一个叶节点 '{first_leaf.get('name', '未命名节点')}' 缺少 'actual_starting_page' 字符串或其值无效 ({actual_start_file_val})。", file=sys.stderr)
        print("       LLM 应已在步骤1中为第一个叶节点提供了 'actual_starting_page'。", file=sys.stderr)
        save_json_data(data, output_file, "部分结果（无偏移量，起始文件缺失）")
        return

    actual_start_number = get_filename_number(actual_start_file_val)

    if actual_start_number is None:
        print(f"错误：无法从文件名 '{actual_start_file_val}' 中提取页码。", file=sys.stderr)
        save_json_data(data, output_file, "部分结果（无偏移量，文件名解析失败）")
        return

    # 计算偏移量
    # 偏移量 = 实际文件页码 - 目录中声称的页码
    # 例如：如果目录说第1节从第5页开始，但内容实际在 page0008.txt (第8页)开始，则偏移量 = 8 - 5 = 3
    # 那么目录中的第10页实际上是第 10 + 3 = 13 页，即 page0013.txt
    offset = actual_start_number - toc_start_page_val
    print(f"信息：计算出的页面偏移量为: {offset} (实际文件页码: {actual_start_number}, 目录声称页码: {toc_start_page_val})")

    # 应用偏移量到所有节点
    _apply_offset_recursive(data["chapters"], offset)
    print("信息：偏移量已应用于所有节点。")

    # 保存最终结果
    save_json_data(data, output_file, "最终目录结果 (含偏移量)")

# --- 文件保存 ---
def save_json_data(data: Optional[Dict], output_file: Path, message_prefix: str = "数据") -> bool:
    """将字典数据保存到 JSON 文件。"""
    if data is None: # 允许保存一个空的JSON对象，如果数据是None
        print(f"警告: {message_prefix} 数据为 None，将尝试保存空JSON对象至 {output_file}。", file=sys.stderr)
        data_to_save = {}
    else:
        data_to_save = data

    try:
        output_file.parent.mkdir(parents=True, exist_ok=True) # 确保输出目录存在
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        print(f"{message_prefix}已成功保存到 '{output_file}'")
        return True
    except Exception as e:
        print(f"保存文件 '{output_file}' 时出错: {e}", file=sys.stderr)
        return False

# --- 主函数 ---
def main_orchestrator(config: Dict, script_dir_path: Path):
    """
    使用加载的配置来编排目录提取过程。
    """
    print("开始提取目录过程 (偏移量策略)...")
    
    dashscope_api_key = os.getenv('DASHSCOPE_API_KEY') # API密钥仍从环境变量获取
    if not dashscope_api_key:
        print("致命错误: 环境变量 DASHSCOPE_API_KEY 未设置。", file=sys.stderr)
        return

    # 从配置中获取值
    text_dir_name = config["text_dir"]
    catalog_output_filename = config["catalog"]
    pages_for_catalog = config["pages_for_catalog"]
    llm_model_name = config["llm_model"]

    # 构建路径
    text_dir_full_path = script_dir_path / text_dir_name
    result_json_full_path = script_dir_path / catalog_output_filename

    print(f"脚本目录: {script_dir_path}")
    print(f"文本目录 (来自配置): {text_dir_full_path}")
    print(f"结果文件 (来自配置): {result_json_full_path}")
    print(f"用于目录的页数 (来自配置): {pages_for_catalog}")
    print(f"LLM 模型 (来自配置): {llm_model_name}")


    if not text_dir_full_path.is_dir():
        print(f"错误: 文本目录 '{text_dir_full_path}' 未找到。", file=sys.stderr)
        return

    all_text_paths = list_text_files(text_dir_full_path)
    if not all_text_paths:
        print(f"在目录 '{text_dir_full_path}' 中未找到符合格式的文本文件。程序退出。")
        return

    text_paths_to_send = all_text_paths[:pages_for_catalog]
    if not text_paths_to_send:
        print(f"警告：没有足够的文本文件可供发送给 LLM (需要 {pages_for_catalog} 页，找到 {len(all_text_paths)} 页)。", file=sys.stderr)
        # 即使页数不足，也尝试继续，LLM 也许能处理
    
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
        return
        
    full_text_content = "\n\n".join(combined_content_parts)

    # --- 步骤 1: 获取结构和首叶起始页 ---
    print("\n--- 步骤 1: 获取结构和首叶起始页 ---")
    # PROMPT_TEXT_OFFSET_STRATEGY 是全局定义的
    # 将配置中的 LLM 模型名称传递给调用函数
    llm_output = call_llm_dashscope_text(dashscope_api_key, full_text_content, PROMPT_TEXT_OFFSET_STRATEGY, llm_model_name)
    initial_structure = parse_json_from_llm(llm_output)
    
    if not initial_structure:
        print("步骤 1 失败：未能从 LLM 获取或解析有效的初始目录结构。程序退出。", file=sys.stderr)
        # 尝试保存 LLM 的原始输出以供调试
        error_output_path = result_json_full_path.with_suffix(".llm_error_output.txt")
        try:
            with open(error_output_path, 'w', encoding='utf-8')as f_err:
                f_err.write(f"LLM Output that failed parsing:\n{llm_output}")
            print(f"LLM 的原始错误输出已保存到: {error_output_path}")
        except Exception as e_save:
            print(f"保存 LLM 错误输出时也发生错误: {e_save}", file=sys.stderr)
        return

    # --- 步骤 2 & 3: 计算偏移量并应用 ---
    apply_offset_and_save(initial_structure, result_json_full_path)

    print("\n目录提取过程完成。")

if __name__ == "__main__":
    try:
        # 确定脚本所在的目录
        current_script_dir = Path(__file__).parent.resolve()
    except NameError: # 处理在某些IDE或直接执行时 __file__ 未定义的情况
        current_script_dir = Path(os.getcwd()).resolve()
    
    # 加载配置
    config_path = current_script_dir / DEFAULT_CONFIG_FILENAME
    app_config = load_app_config(config_path)

    if app_config:
        main_orchestrator(app_config, current_script_dir)
    else:
        print("由于配置加载失败，目录提取流程无法启动。")

