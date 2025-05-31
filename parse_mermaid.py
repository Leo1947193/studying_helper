import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys

# --- 默认配置文件名 ---
DEFAULT_CONFIG_FILENAME = "config.json" # 使用统一的配置文件名

def load_parser_config(config_file_path: Path) -> Optional[Dict]:
    """
    从指定的 JSON 文件加载解析 Mermaid 相关的配置。

    Args:
        config_file_path (Path): 配置文件的完整路径。

    Returns:
        Optional[Dict]: 如果加载成功则返回配置字典，否则返回 None。
    """
    print(f"正在从 '{config_file_path}' 加载 Mermaid 解析器配置...")
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        # 验证解析器脚本所需的键是否存在且类型正确
        required_keys = {
            "mermaid_dir": str,      # 作为此脚本的输入目录 (来自 get_mermaid.py 的输出)
            "parsed_mermaid_dir": str  # 此脚本的输出目录
        }
        for key, expected_type in required_keys.items():
            if key not in config_data:
                print(f"错误：配置文件 '{config_file_path}' 中缺少键 '{key}' (Mermaid 解析器配置需要)。", file=sys.stderr)
                return None
            if not isinstance(config_data[key], expected_type):
                print(f"错误：配置文件 '{config_file_path}' 中键 '{key}' 的类型不正确。期望类型：{expected_type}, 实际类型：{type(config_data[key])}。", file=sys.stderr)
                return None
        
        print("Mermaid 解析器配置加载成功。")
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

def process_mermaid_string(mermaid_string: str) -> str:
    """
    将字符串中转义的换行符 (\\n) 和制表符 (\\t)
    转换回实际的换行符和制表符。
    """
    # 来自 JSON 的字符串已经将 \\n 和 \\t 作为两个字符处理。
    # 我们需要将它们替换为单个文字字符。
    # 如果 LLM 在 mermaid_code 字段的字符串中确实输出了字面上的 "\\n" 和 "\\t"。
    
    processed_code = mermaid_string.replace("\\n", "\n").replace("\\t", "\t")
    return processed_code

def run_parser(input_mermaid_json_dir_path: Path, parsed_mermaid_output_dir_path: Path):
    """
    执行 Mermaid JSON 文件的解析和转换过程。

    Args:
        input_mermaid_json_dir_path (Path): 包含 Mermaid JSON 文件的输入目录路径。
        parsed_mermaid_output_dir_path (Path): 保存已处理 .mmd 文件的输出目录路径。
    """
    print("开始解析Mermaid代码文件...")

    if not input_mermaid_json_dir_path.is_dir():
        print(f"错误: 输入目录 '{input_mermaid_json_dir_path}' 未找到。", file=sys.stderr)
        return

    parsed_mermaid_output_dir_path.mkdir(parents=True, exist_ok=True)
    print(f"已处理的Mermaid代码将保存到: {parsed_mermaid_output_dir_path}")

    processed_files = 0
    failed_files = 0

    # 查找所有 .json 文件
    json_files_to_process = list(input_mermaid_json_dir_path.glob("*.json"))
    if not json_files_to_process:
        print(f"警告：在目录 '{input_mermaid_json_dir_path}' 中未找到 .json 文件进行处理。", file=sys.stderr)
        return

    print(f"在 '{input_mermaid_json_dir_path}' 中找到 {len(json_files_to_process)} 个 .json 文件。")

    for json_file_path in json_files_to_process:
        print(f"\n正在处理文件: {json_file_path.name}")
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            mermaid_code_escaped = data.get("mermaid_code")

            if mermaid_code_escaped is None:
                print(f"警告: 文件 '{json_file_path.name}' 中未找到 'mermaid_code' 字段。跳过。", file=sys.stderr)
                failed_files += 1
                continue

            if not isinstance(mermaid_code_escaped, str):
                print(f"警告: 文件 '{json_file_path.name}' 中的 'mermaid_code' 不是字符串。跳过。", file=sys.stderr)
                failed_files += 1
                continue

            # 处理字符串以替换 \\n 和 \\t
            actual_mermaid_code = process_mermaid_string(mermaid_code_escaped)

            # 创建输出文件名 (例如, 1_1_1.mmd)
            # json_file_path.stem 将获取文件名（不含 .json 后缀）
            output_filename = parsed_mermaid_output_dir_path / f"{json_file_path.stem}.mmd"

            with open(output_filename, 'w', encoding='utf-8') as f_out:
                f_out.write(actual_mermaid_code)
            
            print(f"成功将处理后的Mermaid代码保存到: {output_filename}")
            processed_files += 1

        except json.JSONDecodeError:
            print(f"错误: 文件 '{json_file_path.name}' 不是有效的JSON。跳过。", file=sys.stderr)
            failed_files += 1
        except Exception as e:
            print(f"处理文件 '{json_file_path.name}' 时发生意外错误: {e}", file=sys.stderr)
            failed_files += 1

    print("\n--- 处理完成 ---")
    print(f"成功处理文件数: {processed_files}")
    print(f"处理失败文件数: {failed_files}")

def main():
    """
    主函数，加载配置并启动解析过程。
    """
    try:
        # 确定脚本所在的目录
        script_dir = Path(__file__).parent.resolve()
    except NameError: # 处理在某些IDE或直接执行时 __file__ 未定义的情况
        script_dir = Path(os.getcwd()).resolve()
    print(f"脚本运行目录: {script_dir}")

    # 加载配置
    config_file_full_path = script_dir / DEFAULT_CONFIG_FILENAME
    config = load_parser_config(config_file_full_path)

    if not config:
        print("由于配置加载失败，Mermaid 解析流程无法启动。")
        return

    # 从配置中获取目录名称
    input_mermaid_dir_name = config["mermaid_dir"] # 这是 get_mermaid.py 的输出目录
    parsed_output_dir_name = config["parsed_mermaid_dir"]

    # 构建完整路径
    input_mermaid_json_full_dir = script_dir / input_mermaid_dir_name
    parsed_mermaid_output_full_dir = script_dir / parsed_output_dir_name
    
    run_parser(input_mermaid_json_full_dir, parsed_mermaid_output_full_dir)

if __name__ == "__main__":
    main()
