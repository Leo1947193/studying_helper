import json
from pathlib import Path
import sys

# --- Configuration ---
SCRIPT_DIR = Path(__file__).parent.resolve()
INPUT_MERMAID_JSON_DIR = SCRIPT_DIR / 'mermaid_code' # Directory with JSON files from get_mermaid.py
PARSED_MERMAID_OUTPUT_DIR = SCRIPT_DIR / 'parsed_mermaid_code' # Directory for processed .mmd files

def process_mermaid_string(mermaid_string: str) -> str:
    """
    Converts escaped newlines (\\n) and tabs (\\t) in a string
    to actual newline and tab characters.
    """
    # The string from JSON already has \\n and \\t as two characters.
    # We need to replace them with single literal characters.
    # Python's string escape sequences handle this naturally when reading/writing.
    # If the LLM literally output '\\' followed by 'n', then a simple replace works.
    # If it output a string that, when parsed by json.loads, results in a string
    # containing actual newline/tab characters, then no processing is needed here.
    # Assuming the LLM outputted the literal "\\n" and "\\t" in the string for the mermaid_code field.
    
    processed_code = mermaid_string.replace("\\n", "\n").replace("\\t", "\t")
    return processed_code

def main():
    print("开始解析Mermaid代码文件...")

    if not INPUT_MERMAID_JSON_DIR.is_dir():
        print(f"错误: 输入目录 '{INPUT_MERMAID_JSON_DIR}' 未找到。", file=sys.stderr)
        return

    PARSED_MERMAID_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"已处理的Mermaid代码将保存到: {PARSED_MERMAID_OUTPUT_DIR}")

    processed_files = 0
    failed_files = 0

    for json_file_path in INPUT_MERMAID_JSON_DIR.glob("*.json"):
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

            # Process the string to replace \\n and \\t
            actual_mermaid_code = process_mermaid_string(mermaid_code_escaped)

            # Create the output filename (e.g., 1_1_1.mmd)
            output_filename = PARSED_MERMAID_OUTPUT_DIR / f"{json_file_path.stem}.mmd"

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

if __name__ == "__main__":
    main()
