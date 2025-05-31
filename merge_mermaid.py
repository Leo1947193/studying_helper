import os # Not strictly needed if only using pathlib for paths, but good for os.getenv if used later
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys

# --- 默认配置文件名 ---
DEFAULT_CONFIG_FILENAME = "config.json" # 使用统一的配置文件名

def load_merge_config(config_file_path: Path) -> Optional[Dict]:
    """
    从指定的 JSON 文件加载合并 Mermaid 相关的配置。

    Args:
        config_file_path (Path): 配置文件的完整路径。

    Returns:
        Optional[Dict]: 如果加载成功则返回配置字典，否则返回 None。
    """
    print(f"正在从 '{config_file_path}' 加载 Mermaid 合并配置...")
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        # 验证合并脚本所需的键是否存在且类型正确
        required_keys = {
            "catalog": str,       # 输入的目录结构文件名
            "parsed_mermaid_dir": str, # 输入的已解析 .mmd 文件目录名
            "combined_mermaid": str, # 输出的合并后 .mmd 文件名
            "book_root_title": str            # 合并后思维导图的根节点标题
        }
        for key, expected_type in required_keys.items():
            if key not in config_data:
                print(f"错误：配置文件 '{config_file_path}' 中缺少键 '{key}' (Mermaid 合并配置需要)。", file=sys.stderr)
                return None
            if not isinstance(config_data[key], expected_type):
                print(f"错误：配置文件 '{config_file_path}' 中键 '{key}' 的类型不正确。期望类型：{expected_type}, 实际类型：{type(config_data[key])}。", file=sys.stderr)
                return None
        
        print("Mermaid 合并配置加载成功。")
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

def load_json_file(file_path: Path) -> Optional[Dict]:
    """加载JSON文件并返回其内容。"""
    if not file_path.exists():
        print(f"错误: JSON文件未找到 - {file_path}", file=sys.stderr)
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载JSON文件 '{file_path}' 时出错: {e}", file=sys.stderr)
        return None

def read_mermaid_file_content(file_path: Path) -> List[str]:
    """
    读取 .mmd 文件，跳过 'mindmap' 和 'root(...)' 行，
    并返回内容行。
    """
    content_lines = []
    if not file_path.exists():
        print(f"警告: Mermaid文件未找到 - {file_path}", file=sys.stderr)
        return [f"\t(Mermaid内容未找到: {file_path.stem})"] # 添加一个制表符以适应合并后的结构

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        start_index = 0
        if lines:
            # 跳过 'mindmap' 行 (如果存在)
            if lines[0].strip().lower() == "mindmap":
                start_index += 1
            # 跳过 'root((...))' 行 (如果存在于下一行)
            if start_index < len(lines) and lines[start_index].strip().lower().startswith(("root((", "\troot((", "    root((")): # 允许一些前导空格/制表符
                start_index += 1
        
        for line in lines[start_index:]:
            content_lines.append(line.rstrip('\n')) # 保留原始缩进，移除行尾换行符
        
        if not content_lines and lines: # 如果文件只包含mindmap/root行或为空
             return [f"\t(Mermaid内容为空或仅含根节点: {file_path.stem})"]
        elif not lines: # 如果文件完全为空
            return [f"\t(Mermaid文件为空: {file_path.stem})"]
        return content_lines
    except Exception as e:
        print(f"读取Mermaid文件 '{file_path}' 时出错: {e}", file=sys.stderr)
        return [f"\t(读取Mermaid文件时出错: {file_path.stem})"]

def build_mermaid_for_node_recursive(
    node_data: Dict, 
    current_indent_level: int, 
    chapter_id_prefix: str, 
    output_lines: List[str],
    parsed_mermaid_dir_path: Path
    ):
    """
    递归地为节点及其子节点构建Mermaid思维导图行。
    """
    node_name = node_data.get("name", "未命名节点")
    node_type = node_data.get("type")
    # 确保索引是字符串，即使它是数字
    node_index_val = node_data.get("index")
    current_index_str = str(node_index_val) if node_index_val is not None else ""
    
    # 构建完整的章节ID (例如, "1", "1.1", "1.1.1")
    if chapter_id_prefix and current_index_str:
        current_chapter_id = f"{chapter_id_prefix}.{current_index_str}"
    elif current_index_str:
        current_chapter_id = current_index_str
    else: # 顶级节点可能没有显式索引，或我们不希望在最顶层使用点号
        current_chapter_id = chapter_id_prefix if chapter_id_prefix else "node" # 避免前导点

    indent = "\t" * current_indent_level
    # 为节点名称添加括号，使其在Mermaid中更突出，特别是对于父节点
    # 对于叶节点，其内容将是子节点，所以叶节点本身不需要括号
    # if node_type == "tree" or not node_data.get("children"): # 如果是树节点或者没有子节点的叶节点（虽然叶节点通常不应该有子节点字段）
    #    node_display_name = f"(({node_name}))" # 双括号使其成为圆形
    # else:
    node_display_name = node_name

    output_lines.append(f"{indent}{node_display_name}")

    if node_type == "leaf":
        # 为叶节点的 .mmd 文件构建文件名 (例如, 1_1_1.mmd)
        mermaid_file_name = f"{current_chapter_id.replace('.', '_')}.mmd"
        mermaid_file_path = parsed_mermaid_dir_path / mermaid_file_name
        
        leaf_content_lines = read_mermaid_file_content(mermaid_file_path)
        
        # 叶节点的内容应该在当前节点下再缩进一级
        child_indent_str = "\t" * (current_indent_level + 1)
        for line in leaf_content_lines:
            # 确保从文件读取的行正确地附加了新的父级缩进
            # 如果行本身已经有缩进，lstrip() 会移除它们，然后我们添加正确的缩进
            # 更好的方法是规范化读取内容的缩进，但 lstrip() 是一个简单的方法
            output_lines.append(f"{child_indent_str}{line.lstrip()}") 
            
    elif node_type == "tree" and "children" in node_data and isinstance(node_data["children"], list):
        for child_node in node_data["children"]:
            build_mermaid_for_node_recursive(child_node, current_indent_level + 1, current_chapter_id, output_lines, parsed_mermaid_dir_path)

def run_merge_pipeline(
    input_catalog_json_path: Path, 
    parsed_mermaid_dir_path: Path, 
    combined_mermaid_output_file_path: Path, 
    book_root_title_str: str
    ):
    """
    执行 Mermaid 文件合并的完整流程。
    """
    print("开始合并Mermaid代码文件...")

    catalog_data = load_json_file(input_catalog_json_path)
    if not catalog_data or "chapters" not in catalog_data:
        print(f"错误: 未能从 '{input_catalog_json_path}' 加载有效的目录结构。", file=sys.stderr)
        return

    if not parsed_mermaid_dir_path.is_dir():
        print(f"错误: 已解析的Mermaid目录 '{parsed_mermaid_dir_path}' 未找到。", file=sys.stderr)
        return

    # 确保合并文件的输出目录存在
    combined_mermaid_output_file_path.parent.mkdir(parents=True, exist_ok=True)

    full_mermaid_lines = ["mindmap"]
    # 为整本书添加主根节点
    full_mermaid_lines.append(f"\troot(({book_root_title_str}))") # 根节点在第一级缩进

    # 开始处理顶级章节
    # 顶级章节的标题将在第二级缩进 (current_indent_level=2)
    if isinstance(catalog_data["chapters"], list):
        for chapter in catalog_data["chapters"]:
            # 顶级章节的 chapter_id_prefix 为空
            build_mermaid_for_node_recursive(chapter, 2, "", full_mermaid_lines, parsed_mermaid_dir_path) 
    else:
        print("错误：目录数据中的 'chapters' 不是列表。", file=sys.stderr)
        return

    try:
        with open(combined_mermaid_output_file_path, 'w', encoding='utf-8') as f:
            for line in full_mermaid_lines:
                f.write(line + "\n")
        print(f"已成功将合并后的Mermaid代码保存到: {combined_mermaid_output_file_path}")
    except Exception as e:
        print(f"保存合并后的Mermaid文件时出错: {e}", file=sys.stderr)

    print("\n--- 合并完成 ---")

def main():
    """
    主函数，加载配置并启动合并过程。
    """
    try:
        # 确定脚本所在的目录
        script_dir = Path(__file__).parent.resolve()
    except NameError: # 处理在某些IDE或直接执行时 __file__ 未定义的情况
        script_dir = Path(os.getcwd()).resolve()
    print(f"脚本运行目录: {script_dir}")

    # 加载配置
    config_file_full_path = script_dir / DEFAULT_CONFIG_FILENAME
    config = load_merge_config(config_file_full_path)

    if not config:
        print("由于配置加载失败，Mermaid 合并流程无法启动。")
        return

    # 从配置中获取文件名和目录名
    catalog_json_filename_from_config = config["catalog"]
    parsed_mermaid_dir_name_from_config = config["parsed_mermaid_dir"] # 这是 parse_mermaid.py 的输出目录
    combined_mermaid_filename_from_config = config["combined_mermaid"]
    book_root_title_from_config = config["book_root_title"]

    # 构建完整路径
    input_catalog_json_full_path = script_dir / catalog_json_filename_from_config
    parsed_mermaid_full_dir = script_dir / parsed_mermaid_dir_name_from_config
    combined_mermaid_output_full_file = script_dir / combined_mermaid_filename_from_config
    
    run_merge_pipeline(
        input_catalog_json_full_path,
        parsed_mermaid_full_dir,
        combined_mermaid_output_full_file,
        book_root_title_from_config
    )

if __name__ == "__main__":
    main()
