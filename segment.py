import os
import dashscope
from dashscope import MultiModalConversation # 保持API调用结构
import math # math模块在此版本中未直接使用，但保留以防未来扩展
import csv
import io # 用于在内存中处理CSV字符串
import time # 用于API调用之间的延迟
import sys # 用于状态消息/错误输出
import re # 用于解析标志

# --- Configuration ---
# 输出最终拼接结果的CSV文件名
OUTPUT_CSV_FILE = "/home/leo/studying_helper/segmented_humanities_final.csv" # <<< 根据需要调整输出文件名
# 安全地设置您的API Key
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY')
if not DASHSCOPE_API_KEY:
    raise ValueError("请设置 DASHSCOPE_API_KEY 环境变量。")
# 指定模型
MODEL_NAME = "qwen-max-latest" # 或您测试效果好的其他兼容模型
# 包含OCR后文本文件的目录
TEXT_DIR = "/home/leo/studying_helper/text_dir/" # <<< 调整为您的OCR文本文件目录
# 教材的总页数 (即.txt文件数量)
TOTAL_PAGES = 364 # <<< 根据您的.txt文件总数调整
# 每批处理的文本文件数量
PAGES_PER_BATCH = 60  # <<< 根据模型限制和期望的重叠进行调整 (例如，设为2或3)
# API调用之间的可选延迟（秒）
API_DELAY = 1

# --- Helper Functions ---

def get_text_content_for_batch(start_page, end_page, text_dir):
    """
    获取指定页面范围内的文本文件内容，并将它们合并成一个字符串。
    还返回实际找到并读取的文件列表，用于信息展示。
    """
    concatenated_text_parts = [] # 更名为 parts 以清晰区分
    files_processed = []
    # 确定页码的零填充位数，至少4位 (基于TOTAL_PAGES)
    page_num_zfill = max(4, len(str(TOTAL_PAGES)))

    for i in range(start_page, end_page + 1):
        page_num_str = str(i).zfill(page_num_zfill)
        # 假设OCR脚本生成的文件名是 page0001.txt, page0002.txt
        file_path = os.path.join(text_dir, f"page{page_num_str}.txt")
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    concatenated_text_parts.append(f.read())
                files_processed.append(file_path)
            except Exception as e:
                print(f"警告: 读取文本文件 {file_path} 时出错: {e}", file=sys.stderr)
        else:
            print(f"警告: 文本文件未找到，已跳过: {file_path}", file=sys.stderr)
    
    if not concatenated_text_parts:
        return None, []
        
    # 在不同页面的文本之间插入明确的分页提示，帮助LLM理解内容来源
    separator = "\n\n--- [新页面内容开始] ---\n\n"
    return separator.join(concatenated_text_parts), files_processed

# --- Main Processing Logic ---

base_prompt = """
**任务目标：** 将提供的教科书OCR文字内容进行语义分段，提取出连贯的知识单元、论述段落或重要信息点，并以CSV格式输出。请专注于中文内容处理。

**输入：** 一段或多段连续的教科书页面OCR文字内容。这些文字可能包含OCR识别引入的噪声、页眉、页脚、页码、章节标题、图表标题、以及其他非主体内容的排版元素。OCR文本中的换行符可能不代表实际段落分隔。

**输出格式要求 (必须严格遵守)：**

1.  **边界标志 (关键)：**
    * 在您回复的**最开始**，**不允许有任何前导字符、空格或换行**，请输出**两位数字**表示边界状态：
        * **第一位数字：** 如果所提供文本块的**末尾内容**在语义上**不完整**（例如，一个段落、论点或叙述明显没有结束，预计会在后续文本中继续），则输出 '0'。如果内容在当前文本块末尾**已完结**，或者是全书的最后内容，则输出 '1'。
        * **第二位数字：** 如果所提供文本块的**起始内容**在语义上是**不完整开头**（例如，是上一段文字的延续），则输出 '2'。如果是一个**全新的段落、主题或论点开始**，或者是全书的起始内容，则输出 '3'。
    * 紧随这两位数字之后，必须是一个**英文逗号 (,)**。例如，回复的开头应为：`03,` 或 `12,`。
    * **除此 `XY,` 标志外，前面不可有任何其他文本。**

2.  **CSV 数据 (紧跟在 `XY,` 标志之后)：**
    * 以CSV格式输出提取的信息，**不需要表头行**。
    * 每行代表一个独立的、语义完整的知识单元、论述段落或核心观点。
    * CSV 列定义为：`id`, `起始页码`, `结束页码`, `文本内容`。
        * 所有字段值**必须用英文双引号 ("") 包围**。
        * `id`：整数，从1开始，为**当前批次输出内**的行号，后续会全局重新编号。
        * `起始页码`：整数，表示此文本段落在原始书籍中开始的页码。你需要根据上下文和输入文本中可能存在的页面分隔提示（如“--- [新页面内容开始] ---”）进行推断。
        * `结束页码`：整数，表示此文本段落在原始书籍中结束的页码。如果一个分段内容来源于单个原始页面，则起始页码和结束页码相同。
        * `文本内容`：提取并分段后的中文文本。**此文本内容应尽可能纯净，去除OCR噪声、页眉、页脚、孤立的页码标记以及与核心内容无关的旁注或图表说明。重点是语义内容的完整性和连贯性。**

3.  **语言：** 整个CSV输出（包括`文本内容`字段）**必须是中文**。

4.  **内容提取与分段规则：**
    * **核心任务是语义连贯性分段。** 将文本分割成有意义的、相对独立的单元，例如：
        * 阐述特定主题、概念或论点的段落。
        * 关键术语的定义或解释。
        * 对某一历史事件、人物、或文化现象的描述或分析。
        * 对文学作品、艺术品、哲学思想等的评述或解读。
        * 案例分析、引用的故事或作为例证的叙述片段。
        * 一个完整的思想观点或一个论证的主要步骤。
    * **忽略和清理：**
        * **必须尽力识别并忽略/删除**夹杂在文本中的页眉、页脚、独立的页码数字/文字（例如“第 5 页”）、大部分章节和小节标题（除非它们是引出核心知识点的必要部分或本身就是知识点概要）、独立的图表标题/编号、以及不属于主体论述内容的OCR识别错误或排版元素。
        * 目标是输出纯净的、可阅读的正文内容。对于OCR引入的错误换行，应尝试根据语义合并成连贯的句子和段落。
    * **特殊格式：** 如果原文中包含对理解至关重要的特殊排版（如引文格式、列表项），请在分段时尽量保持其结构和可读性，但将其整合到相关的语义单元内。
    * **段落长度：** 段落长度应自然，避免将过短且无独立意义的碎句切分为独立段落。也要避免将多个独立主题强行合并为一个超长段落。分段应基于意义的完整性和转换点。
    * **上下文利用：** 如果输入文本包含如 "--- [新页面内容开始] ---" 这样的分隔符，请利用此信息辅助判断内容是否跨页，以及正确分配 `起始页码` 和 `结束页码`。原始文本中的页码信息（如有）也应被考虑，但最终输出的CSV中不应再包含这些页码标记本身，而是体现在 `起始页码` 和 `结束页码` 字段。

5.  **输出纯净性：** 您的整个回复必须**仅由** `XY,` 标志及其后紧跟的、双引号包围的CSV数据组成。不要包含任何解释、问候语或CSV格式之外的任何文本。

**输入文本示例（OCR结果，可能包含噪声和页码标记）：**

```text
...上一段讨论的结尾部分。这一观点在学界引发了广泛的讨论。
--- [新页面内容开始] ---
第 78 页
接下来，我们将探讨该理论在实际案例中的应用。首先，需要明确“文化语境”这一核心概念的定义。文化语境指的是在特定社会历史时期，影响人们交流和理解的各种文化因素的总和。
例如，在分析古代文学作品时，理解其创作时的文化语境至关重要。某某学者的研究（2010）指出，缺乏这种理解可能导致对作品主题的严重误读。
这一节的主要论点是，任何文本的解读都离不开对其文化语境的深入考察。
--- [新页面内容开始] ---
图5.1 某某时期的社会结构图 (此为图注，应忽略)
第 79 页
承接前文，对文化语境的考察还应包括当时的社会结构、价值观念以及主流意识形态等方面。这些因素共同构成了复杂的意义网络。
关于这一点，可以参考历史学家李明对XX王朝社会变迁的研究，他认为... (此处开始一个新的论述，但可能在本批次文本末尾未结束)
```

**期望的CSV输出示例 (假设批次内ID从1开始，边界标志`02`表示末尾不完整、开头是延续)：**
`02,`
`"1","78","78","...上一段讨论的结尾部分。这一观点在学界引发了广泛的讨论。接下来，我们将探讨该理论在实际案例中的应用。首先，需要明确“文化语境”这一核心概念的定义。文化语境指的是在特定社会历史时期，影响人们交流和理解的各种文化因素的总和。"`
`"2","78","78","例如，在分析古代文学作品时，理解其创作时的文化语境至关重要。某某学者的研究（2010）指出，缺乏这种理解可能导致对作品主题的严重误读。"`
`"3","78","78","这一节的主要论点是，任何文本的解读都离不开对其文化语境的深入考察。"`
`"4","79","79","承接前文，对文化语境的考察还应包括当时的社会结构、价值观念以及主流意识形态等方面。这些因素共同构成了复杂的意义网络。"`
`"5","79","79","关于这一点，可以参考历史学家李明对XX王朝社会变迁的研究，他认为... (此处开始一个新的论述，但可能在本批次文本末尾未结束)"`

*(请注意，上述输出中的 `起始页码` 和 `结束页码` 是LLM根据输入文本中的页码信息和分页提示推断的。实际的页码需要LLM准确识别和分配。图注等内容已被忽略。)*
"""

all_batch_responses = [] # 存储每个批次API的原始响应数据
batch_num = 1

# 定义重叠批次的步长 (例如，如果PAGES_PER_BATCH=3, step=2 表示重叠1页)
step = max(1, PAGES_PER_BATCH - 1 if PAGES_PER_BATCH > 1 else 1)

current_page = 1
print("--- 开始处理批次 ---")
while current_page <= TOTAL_PAGES:
    start_page_num_for_batch = current_page
    end_page_num_for_batch = min(start_page_num_for_batch + PAGES_PER_BATCH - 1, TOTAL_PAGES)

    print(f"\n准备处理批次 {batch_num}: 原始页面 {start_page_num_for_batch} 到 {end_page_num_for_batch}")

    # 获取当前批次的文本内容
    concatenated_batch_text, processed_files_in_batch = get_text_content_for_batch(start_page_num_for_batch, end_page_num_for_batch, TEXT_DIR)
    
    if not concatenated_batch_text:
        print(f"警告: 批次 {batch_num} 在页面 {start_page_num_for_batch}-{end_page_num_for_batch} 未找到任何文本文件内容。跳过此范围。", file=sys.stderr)
        current_page = end_page_num_for_batch + 1 # 移动到这个空范围之后
        batch_num +=1
        continue
    
    print(f"  实际处理的文件: {processed_files_in_batch}")
    
    # 构建提示，包含实际的页码信息以辅助LLM
    # 这部分信息帮助LLM理解它正在处理的文本块对应书中的哪些页码
    page_context_info_for_llm = f"以下文本内容来源于教材的第 {start_page_num_for_batch} 页到第 {end_page_num_for_batch} 页。\n"
    # 将页码上下文、OCR文本和主要指令合并为完整的用户请求内容
    full_user_content_for_api = page_context_info_for_llm + \
                                "原始文本内容如下：\n```text\n" + \
                                concatenated_batch_text + \
                                "\n```\n\n" + \
                                "请严格按照以下指示处理上述文本：\n" + \
                                base_prompt
    
    messages_for_api = [{"role": "user", "content": full_user_content_for_api}]
    
    # --- API Call (Streaming + Accumulation per Batch) ---
    accumulated_answer_text_from_api = "" 
    error_occurred_in_stream = False
    print(f"  调用 API (模型: {MODEL_NAME}, 流式)...")
    try:
        # 使用 DashScope 的 MultiModalConversation 或 Generation API
        # MultiModalConversation 通常用于图文，但如果模型支持文本也可以
        # Generation API (dashscope.Generation.call) 可能更适合纯文本任务
        response_stream = MultiModalConversation.call( 
            api_key=DASHSCOPE_API_KEY,
            model=MODEL_NAME, 
            messages=messages_for_api,
            stream=True,
            # top_p=0.8 # 可选：调整生成策略参数
        )

        stream_chunk_count = 0
        for chunk in response_stream:
            if chunk.status_code != 200:
                print(f"\n  错误：API流式传输错误，批次 {batch_num}, 状态码 {chunk.status_code}, 消息: {chunk.message}, RequestId: {chunk.request_id}", file=sys.stderr)
                error_occurred_in_stream = True
                break 

            text_chunk_from_api = ""
            # 根据API响应结构提取文本块
            if hasattr(chunk.output, 'choices') and chunk.output.choices:
                message_content = chunk.output.choices[0].message.content
                if isinstance(message_content, str): 
                    text_chunk_from_api = message_content
                elif isinstance(message_content, list) and message_content and isinstance(message_content[0], dict) and "text" in message_content[0]: 
                    text_chunk_from_api = message_content[0]["text"]
            elif hasattr(chunk.output, 'text'): # 兼容某些可能直接在output下有text的API响应
                 text_chunk_from_api = chunk.output.text
            
            if text_chunk_from_api: # 确保只添加非空文本块
                accumulated_answer_text_from_api += text_chunk_from_api
                stream_chunk_count += 1

        if error_occurred_in_stream:
            print(f"  处理批次 {batch_num} 时流式传输中断。")
            accumulated_answer_text_from_api = None # 标记为无效响应
        elif stream_chunk_count == 0 and not accumulated_answer_text_from_api: # 确保即使只有一个大块也能被捕获
            print(f"  警告: 批次 {batch_num} 流式传输未返回任何文本内容。", file=sys.stderr)
            accumulated_answer_text_from_api = "" # 视为空响应

    except Exception as e:
        print(f"\n  错误：调用 API 时发生异常，批次 {batch_num}: {e}", file=sys.stderr)
        accumulated_answer_text_from_api = None # 标记为无效响应

    # --- Process Accumulated Response for this Batch ---
    if accumulated_answer_text_from_api is not None:
        raw_response_str_from_api = accumulated_answer_text_from_api.strip()
        parsed_flags = None
        csv_data_from_llm = ""

        # 使用正则表达式解析开头的 "XY," 标志
        match_flags = re.match(r"^\s*([01])([23]),", raw_response_str_from_api)

        if match_flags:
            parsed_flags = match_flags.group(1) + match_flags.group(2)
            csv_data_from_llm = raw_response_str_from_api[match_flags.end():].strip() 
            print(f"  批次 {batch_num} 处理完成。检测到标志: {parsed_flags}。CSV 数据长度: {len(csv_data_from_llm)}")
            all_batch_responses.append({
                "flags": parsed_flags,
                "csv_data": csv_data_from_llm,
                "start_page_processed": start_page_num_for_batch, # 记录此批次处理的原始起始页
                "end_page_processed": end_page_num_for_batch,   # 记录此批次处理的原始结束页
            })
        else:
            # 如果标志解析失败
            print(f"  警告: 批次 {batch_num} 的响应开头未能检测到 'XY,' 标志格式。")
            print(f"  响应开头 (前200字符): '{raw_response_str_from_api[:200]}...'")
            print(f"  将尝试将整个响应视为CSV数据，并使用默认标志 '13'（可能导致拼接错误）。")
            all_batch_responses.append({
                "flags": "13", # 默认: 结尾完整, 开头完整
                "csv_data": raw_response_str_from_api, # 将全部响应作为CSV数据
                "start_page_processed": start_page_num_for_batch,
                "end_page_processed": end_page_num_for_batch,
            })
    else:
        # 如果API调用或流处理出错，跳过此批次
        print(f"  批次 {batch_num} 因 API 调用或流错误而被跳过。")

    # --- Advance to the next batch ---
    if end_page_num_for_batch >= TOTAL_PAGES:
        print("\n已到达最后一页文本文件。")
        break # 结束批处理循环

    current_page += step # 按步长前进到下一个批次的起始页
    # 确保 current_page 不会因为步长过大而过早超过总页数
    current_page = min(current_page, TOTAL_PAGES + 1) 
    batch_num += 1

    # 可选的API调用间隔
    if API_DELAY > 0 and current_page <= TOTAL_PAGES:
        print(f"  等待 {API_DELAY} 秒...")
        time.sleep(API_DELAY)

# --- Post-processing: Stitching ---
print("\n--- 开始拼接结果 ---")
final_stitched_csv_rows = [] 
previous_incomplete_row_data = None # 用于存储上一个批次未完成的最后一行数据

# LLM prompt 要求输出的CSV列名 (LLM输出的id我们忽略，后续全局重新编号)
fieldnames_from_llm = ['llm_id', 'source_page_start', 'source_page_end', 'text']
# 最终输出CSV文件时使用的列名
final_output_fieldnames = ['id', 'source_page_start', 'source_page_end', 'text'] 

for i, batch_result_data in enumerate(all_batch_responses):
    flags_for_stitching = batch_result_data["flags"]
    csv_data_for_stitching = batch_result_data["csv_data"]
    start_flag_for_stitching = flags_for_stitching[1] # '2' (不完整开头) 或 '3' (完整开头)
    end_flag_for_stitching = flags_for_stitching[0]   # '0' (不完整结尾) 或 '1' (完整结尾)
    batch_num_display_stitching = i + 1 
    batch_pages_info_stitching = f"原始页面 {batch_result_data['start_page_processed']}-{batch_result_data['end_page_processed']}"

    print(f"\n  处理拼接: 批次 {batch_num_display_stitching} ({batch_pages_info_stitching}), Flags: {flags_for_stitching}")

    if not csv_data_for_stitching: # 如果当前批次的CSV数据为空
        print(f"  警告: 批次 {batch_num_display_stitching} 的 CSV 数据为空，跳过。")
        # 如果之前有未完成的行，且当前空批次标记为“完整开头”，则应将之前未完成的行添加
        if previous_incomplete_row_data and start_flag_for_stitching == '3':
            print(f"  警告: 前续块不完整，但此空批次标记为完整开头('3')。添加前续块。")
            final_stitched_csv_rows.append(previous_incomplete_row_data)
            previous_incomplete_row_data = None
        continue # 跳到下一个批次

    # 使用 StringIO 将CSV字符串当作文件处理
    csvfile_in_memory = io.StringIO(csv_data_for_stitching)
    # 配置DictReader - LLM被要求使用双引号包围所有字段，且无表头
    csv_reader = csv.DictReader(csvfile_in_memory, fieldnames=fieldnames_from_llm, quoting=csv.QUOTE_ALL, skipinitialspace=True)

    current_batch_rows_as_dicts = []
    try:
        current_batch_rows_as_dicts = list(csv_reader) # 将CSV行转换为字典列表
        if not current_batch_rows_as_dicts: # 如果解析后没有行
            print(f"  警告: 批次 {batch_num_display_stitching} 未解析出任何 CSV 行。")
            if previous_incomplete_row_data and start_flag_for_stitching == '3':
                print(f"  警告: 前续块不完整，但此无行批次标记为完整开头('3')。添加前续块。")
                final_stitched_csv_rows.append(previous_incomplete_row_data)
                previous_incomplete_row_data = None
            continue 
    except Exception as e:
        print(f"  错误: 解析批次 {batch_num_display_stitching} 的 CSV 时出错: {e}")
        print(f"  --- 有问题的 CSV 数据 (前 500 字符) ---")
        print(csv_data_for_stitching[:500])
        print(f"  ------------------------------------")
        # CSV解析错误时，如果存在之前未完成的行，先添加它
        if previous_incomplete_row_data:
            print(f"  CSV 解析错误，添加之前未完成的块（如果存在）。")
            final_stitched_csv_rows.append(previous_incomplete_row_data)
            previous_incomplete_row_data = None
        continue # 跳过这个有问题的批次

    # --- Stitching Logic ---
    # processed_rows_for_this_batch 用于存放当前批次经过拼接和初步处理后的行
    processed_rows_for_this_batch = [] 

    # 1. 处理批次开头 (是否与上一批次的未完成行拼接)
    if start_flag_for_stitching == '2': # 当前批次开头不完整
        if previous_incomplete_row_data: # 存在上一批次未完成的行
            if current_batch_rows_as_dicts: # 当前批次LLM确实返回了行
                first_row_this_batch = current_batch_rows_as_dicts.pop(0) # 取出当前批次的第一行用于拼接
                
                # 合并文本内容
                text_a = previous_incomplete_row_data.get('text', '').strip()
                text_b = first_row_this_batch.get('text', '').strip()
                merged_text = ""
                if text_a and text_b:
                    merged_text = text_a + " " + text_b # 在文本片段间加空格
                elif text_a:
                    merged_text = text_a
                else: # 包含 text_b 为空或 text_a, text_b都为空的情况
                    merged_text = text_b
                
                # 创建合并后的行字典
                merged_row = {
                    'id': None, # id 后续全局重新编号
                    'source_page_start': previous_incomplete_row_data.get('source_page_start', ''), # 起始页码来自前一个片段
                    'source_page_end': first_row_this_batch.get('source_page_end', previous_incomplete_row_data.get('source_page_end', '')), # 结束页码优先用当前片段的，其次用前一个片段的
                    'text': merged_text
                }
                processed_rows_for_this_batch.append(merged_row)
                print(f"    已拼接：上批次结尾 与 本批次开头。新结束页: {merged_row.get('source_page_end', '')}")
                previous_incomplete_row_data = None # 已拼接，清除存储的未完成行
            else:
                # 上一批次未完成，当前批次标记为不完整开头，但LLM未返回任何行
                print(f"    警告: 批次 {batch_num_display_stitching} 标记开头不完整('2')且有前续块，但当前批次无有效行可拼接。保留前续块。")
                # previous_incomplete_row_data 保持不变，带到下一个批次尝试拼接
        else:
            # 当前批次标记为不完整开头，但没有前序未完成行 (可能是第一个批次，或LLM标记错误)
            print(f"    警告: 批次 {batch_num_display_stitching} 标记开头不完整('2')，但没有前续块可拼接。将按原样处理首行（如果存在）。")
            # 继续处理 current_batch_rows_as_dicts 中的行
    
    elif start_flag_for_stitching == '3': # 当前批次开头是完整的
        if previous_incomplete_row_data:
            # 上一批次结尾不完整，但当前批次开头完整，这通常表示LLM认为上一段已结束或标记有误
            print(f"    警告: 前续块不完整，但本批次标记为完整开头('3')。将前续块单独添加。")
            processed_rows_for_this_batch.append(previous_incomplete_row_data)
            previous_incomplete_row_data = None # 清除已处理的未完成行
        # else: 正常情况，前一批次完整，当前批次也完整开头，无需特殊处理
    
    # 将当前批次LLM返回的剩余行（或所有行，如果未发生起始拼接）添加到处理列表
    # 确保只添加期望的字段，避免后续写入CSV时出错
    for row_dict_from_llm in current_batch_rows_as_dicts:
        clean_row_dict = {
            'id': None, # id 后续全局重新编号
            'source_page_start': row_dict_from_llm.get('source_page_start', ''),
            'source_page_end': row_dict_from_llm.get('source_page_end', ''),
            'text': row_dict_from_llm.get('text', '')
        }
        processed_rows_for_this_batch.append(clean_row_dict)

    # 2. 处理批次结尾 (是否需要将最后一行标记为未完成并存储)
    if end_flag_for_stitching == '0': # 当前批次结尾不完整
        if processed_rows_for_this_batch: # 如果当前批次有处理后的行
            # 取出最后一行作为未完成行存储起来
            previous_incomplete_row_data = processed_rows_for_this_batch.pop(-1)
            print(f"    批次 {batch_num_display_stitching} 结尾标记为不完整('0')。存储最后一块待后续拼接。")
            # 将当前批次中剩余的（已完成的）行添加到最终结果列表
            final_stitched_csv_rows.extend(processed_rows_for_this_batch)
        else:
            # 当前批次标记为不完整结尾，但没有处理后的行
            # (例如，起始拼接消耗了唯一的一行，或者LLM返回空内容)
            # 如果 previous_incomplete_row_data 已有值，说明它是从更早的批次传来的，应继续保留
            if previous_incomplete_row_data:
                print(f"    警告: 批次 {batch_num_display_stitching} 结尾标记不完整('0')，无内部处理行，保留先前未完成块。")
            else:
                print(f"    警告: 批次 {batch_num_display_stitching} 结尾标记不完整('0')，但无内容可存储。")
    
    elif end_flag_for_stitching == '1': # 当前批次结尾是完整的
        # 将当前批次所有处理后的行都添加到最终结果列表
        final_stitched_csv_rows.extend(processed_rows_for_this_batch)
        # 如果结尾完整，应确保清除任何可能残留的 previous_incomplete_row_data
        if previous_incomplete_row_data: 
            print(f"    警告: 批次 {batch_num_display_stitching} 结尾完整('1')，但仍有未处理的前续块。可能是标志错误或之前逻辑未完全清除，现将其丢弃。")
            previous_incomplete_row_data = None
        # previous_incomplete_row_data = None # 确保在完整结尾后清除 (上面已包含此逻辑)
        print(f"    批次 {batch_num_display_stitching} 结尾标记为完整('1')。")

# --- Final Check after Loop ---
# 处理循环结束后可能仍然存在的未完成行 (通常是最后一批次结尾不完整的情况)
if previous_incomplete_row_data:
    print("警告: 最后一个批次的结尾标记为不完整，或有未处理的残留不完整块。将其作为最后一块添加。")
    final_stitched_csv_rows.append(previous_incomplete_row_data)

# --- Write Final Stitched CSV ---
print(f"\n--- 写入最终拼接结果到 {OUTPUT_CSV_FILE} ---")
if final_stitched_csv_rows:
    try:
        with open(OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile_output:
            # 使用最终确定的列名进行写入
            csv_writer = csv.DictWriter(csvfile_output, fieldnames=final_output_fieldnames, quoting=csv.QUOTE_ALL)
            csv_writer.writeheader() # 写入CSV表头
            
            for idx, final_row_data in enumerate(final_stitched_csv_rows):
                # 确保只写入在 final_output_fieldnames 中定义的列
                # 并分配全局唯一的ID
                row_to_write = {key: final_row_data.get(key, '') for key in final_output_fieldnames}
                row_to_write['id'] = idx + 1 # 从1开始的全局ID
                csv_writer.writerow(row_to_write)
                
        print(f"成功将 {len(final_stitched_csv_rows)} 行写入到 {OUTPUT_CSV_FILE}")

    except IOError as e:
        print(f"写入最终CSV文件时发生 IO 错误: {e}", file=sys.stderr)
    except Exception as e:
        print(f"写入最终CSV文件时发生未知错误: {e}", file=sys.stderr)
else:
    print("没有最终结果可写入文件。")

print("\n--- 处理完成 ---")

