# search_similar.py
import json
import os
from pathlib import Path # 用于更方便地处理路径
import argparse
import numpy as np
import torch
from transformers import BertTokenizer, BertModel
import faiss

# 默认配置文件名
DEFAULT_CONFIG_FILENAME = "config.json" # 使用统一的配置文件名

def load_search_config(config_file_path):
    """
    从指定的 JSON 文件加载搜索相关的配置。

    Args:
        config_file_path (Path): 配置文件的完整路径。

    Returns:
        dict or None: 如果加载成功则返回配置字典，否则返回 None。
    """
    print(f"正在从 '{config_file_path}' 加载搜索配置...")
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # 验证搜索脚本所需的键是否存在且类型正确
        required_keys = {
            "bert_model": str,
            "faiss_index_filename": str,
            "mapping_file_suffix": str, # 用于构建映射文件名
            "search_top_k": int,
            "use_gpu": bool
        }
        for key, expected_type in required_keys.items():
            if key not in config_data:
                print(f"错误：配置文件 '{config_file_path}' 中缺少键 '{key}' (搜索配置需要)。")
                return None
            if not isinstance(config_data[key], expected_type):
                print(f"错误：配置文件 '{config_file_path}' 中键 '{key}' 的类型不正确。期望类型：{expected_type}, 实际类型：{type(config_data[key])}。")
                return None
        
        if not 0 < config_data["search_top_k"] < 100: # 对 TOP_K 进行合理性检查
             print(f"警告：search_top_k 的值 '{config_data['search_top_k']}' 可能不合理。请检查配置。")

        print("搜索配置加载成功。")
        return config_data
    except FileNotFoundError:
        print(f"错误：配置文件 '{config_file_path}' 未找到。请创建该文件。")
        return None
    except json.JSONDecodeError as e:
        print(f"错误：解析配置文件 '{config_file_path}' 失败：{e}")
        return None
    except Exception as e:
        print(f"加载配置文件时发生未知错误：{e}")
        return None

def get_bert_embedding_for_query(text, tokenizer, model, device):
    """
    为单个文本查询生成 BERT 嵌入。
    (此函数与之前版本基本相同)
    """
    if not text or not text.strip():
        print("错误：查询文本为空。")
        return None
    encoded_input = tokenizer(
        [text], padding=True, truncation=True, return_tensors='pt', max_length=512
    )
    encoded_input = {k: v.to(device) for k, v in encoded_input.items()}
    with torch.no_grad():
        outputs = model(**encoded_input)
        last_hidden_states = outputs.last_hidden_state
        attention_mask = encoded_input['attention_mask']
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_states.size()).float()
        sum_embeddings = torch.sum(last_hidden_states * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        mean_pooled_embedding = sum_embeddings / sum_mask
    return mean_pooled_embedding.cpu().numpy().astype('float32')

def search_in_faiss_index(query_text, faiss_index_obj, id_to_text_mapping_list, tokenizer_obj, model_obj, device_obj, top_k_val):
    """
    嵌入查询，搜索 FAISS 索引，并返回 top_k 个相似的文本。
    (此函数与之前版本基本相同, top_k_val 现在是必需参数)
    """
    if not query_text.strip():
        print("查询为空，无法搜索。")
        return []
    print(f"\n正在搜索与以下内容相似的知识点： \"{query_text}\"")
    query_embedding = get_bert_embedding_for_query(query_text, tokenizer_obj, model_obj, device_obj)
    if query_embedding is None or query_embedding.size == 0:
        print("无法为查询生成嵌入。")
        return []
    print(f"正在 FAISS 索引中搜索前 {top_k_val} 个结果...")
    try:
        distances, indices = faiss_index_obj.search(query_embedding, top_k_val)
    except Exception as e:
        print(f"FAISS 搜索过程中出错： {e}")
        return []
    results = []
    if indices.size > 0:
        for i in range(indices.shape[1]):
            idx = indices[0, i]
            dist = distances[0, i]
            if 0 <= idx < len(id_to_text_mapping_list):
                original_text = id_to_text_mapping_list[idx]
                results.append({"text": original_text, "distance": float(dist), "id": int(idx)})
            else:
                print(f"警告：索引 {idx} 超出映射文件范围 (大小 {len(id_to_text_mapping_list)})。")
    print(f"找到 {len(results)} 个相似的知识点。")
    return results

def find_similar_knowledge_points(question_str, index_file_abs_path, mapping_file_abs_path, model_name_str, use_gpu_flag, top_k_int):
    """
    加载模型和索引，然后对给定的问题字符串执行搜索。
    此函数设计为可以从其他 Python 脚本调用，所有路径和配置都已解析。

    Args:
        question_str (str): 要搜索的问题。
        index_file_abs_path (Path): FAISS 索引文件的绝对路径。
        mapping_file_abs_path (Path): ID 到文本映射 JSON 文件的绝对路径。
        model_name_str (str): BERT 模型的名称。
        use_gpu_flag (bool): 是否尝试使用 GPU。
        top_k_int (int): 返回的最相似结果数量。

    Returns:
        list: 包含相似知识点信息的字典列表。如果失败则返回空列表。
    """
    print("--- 初始化搜索逻辑 (已解析参数) ---")

    # --- 1. 加载 FAISS 索引和映射 ---
    if not index_file_abs_path.is_file():
        print(f"错误：在 {index_file_abs_path} 未找到 FAISS 索引文件。")
        return []
    if not mapping_file_abs_path.is_file():
        print(f"错误：在 {mapping_file_abs_path} 未找到映射文件。")
        return []

    print(f"正在从以下位置加载 FAISS 索引： {index_file_abs_path}")
    try:
        faiss_index = faiss.read_index(str(index_file_abs_path)) # faiss 需要字符串路径
        print(f"FAISS 索引已加载。包含 {faiss_index.ntotal} 个向量。")
    except Exception as e:
        print(f"加载 FAISS 索引时出错： {e}")
        return []

    print(f"正在从以下位置加载 ID 到文本的映射： {mapping_file_abs_path}")
    try:
        with open(mapping_file_abs_path, 'r', encoding='utf-8') as f:
            id_to_text_mapping = json.load(f)
        print(f"映射文件已加载。包含 {len(id_to_text_mapping)} 个条目。")
    except Exception as e:
        print(f"加载映射文件时出错： {e}")
        return []

    # --- 2. 加载用于查询嵌入的 BERT 模型和分词器 ---
    print(f"正在为查询嵌入加载分词器和模型： {model_name_str}...")
    try:
        tokenizer = BertTokenizer.from_pretrained(model_name_str)
        model = BertModel.from_pretrained(model_name_str)
    except Exception as e:
        print(f"加载模型/分词器 '{model_name_str}' 时出错： {e}")
        return []
    
    if use_gpu_flag:
        if torch.cuda.is_available():
            device = torch.device("cuda")
            print("CUDA 可用，将使用 GPU 进行查询嵌入。")
        else:
            device = torch.device("cpu")
            print("警告：配置请求使用 GPU，但 CUDA 不可用。将使用 CPU 进行查询嵌入。")
    else:
        device = torch.device("cpu")
        print("将使用 CPU 进行查询嵌入 (根据配置)。")
        
    model.to(device)
    model.eval()

    # --- 3. 执行搜索 ---
    similar_results = search_in_faiss_index(
        question_str,
        faiss_index,
        id_to_text_mapping,
        tokenizer,
        model,
        device,
        top_k_val=top_k_int
    )
    return similar_results

def main():
    try:
        # 确定脚本所在的目录
        script_dir = Path(__file__).parent.resolve()
    except NameError: # 处理在某些IDE或直接执行时 __file__ 未定义的情况
        script_dir = Path(os.getcwd()).resolve()
    print(f"脚本运行目录: {script_dir}")

    # 加载配置文件
    config_file_full_path = script_dir / DEFAULT_CONFIG_FILENAME
    config = load_search_config(config_file_full_path) # 使用特定于搜索的加载函数

    if not config:
        print("由于搜索配置加载失败，程序中止。")
        return

    # 从配置中获取默认值 (使用小写键名)
    default_bert_model_name = config["bert_model"]
    default_faiss_index_filename = config["faiss_index_filename"]
    default_mapping_file_suffix = config["mapping_file_suffix"]
    # 构造默认的映射文件名
    default_mapping_file_filename = default_faiss_index_filename + default_mapping_file_suffix
    default_top_k = config["search_top_k"]
    default_use_gpu = config["use_gpu"]


    parser = argparse.ArgumentParser(description="搜索与给定问题相似的知识点。")
    parser.add_argument("question", type=str, help="要搜索的问题。")
    # 命令行参数现在接受文件名，而不是完整路径
    parser.add_argument("--index_file", type=str, default=default_faiss_index_filename,
                        help=f"FAISS 索引文件的名称 (位于脚本目录中，默认从config: {default_faiss_index_filename})")
    parser.add_argument("--mapping_file", type=str, default=default_mapping_file_filename,
                        help=f"ID-文本映射JSON文件的名称 (位于脚本目录中，默认从config: {default_mapping_file_filename})")
    parser.add_argument("--model_name", type=str, default=default_bert_model_name,
                        help=f"用于查询嵌入的 BERT 模型名称 (默认从config: {default_bert_model_name})")
    parser.add_argument("--top_k", type=int, default=default_top_k,
                        help=f"要检索的最相似结果的数量 (默认从config: {default_top_k})")
    parser.add_argument("--use_gpu", action=argparse.BooleanOptionalAction, default=default_use_gpu,
                        help=f"是否尝试使用GPU (默认从config: {default_use_gpu})。使用 --use-gpu 或 --no-use-gpu。")
    
    args = parser.parse_args()

    # 解析最终使用的参数值 (命令行优先于配置文件)
    final_bert_model_name = args.model_name
    final_top_k = args.top_k
    final_use_gpu = args.use_gpu

    # 构建索引和映射文件的绝对路径 (基于脚本目录和通过参数或配置确定的文件名)
    final_index_file_path = script_dir / args.index_file
    final_mapping_file_path = script_dir / args.mapping_file # mapping_file 参数现在是完整文件名
    
    print("--- 命令行搜索已初始化 ---")
    print(f"最终参数：模型='{final_bert_model_name}', TopK={final_top_k}, 使用GPU={final_use_gpu}")
    print(f"索引文件：'{final_index_file_path}', 映射文件：'{final_mapping_file_path}'")


    similar_results = find_similar_knowledge_points(
        args.question,
        final_index_file_path,
        final_mapping_file_path,
        final_bert_model_name,
        final_use_gpu,
        final_top_k
    )

    # --- 显示结果 (供命令行使用) ---
    if similar_results:
        print(f"\n--- \"{args.question}\" 的前 {len(similar_results)} 个结果 ---")
        for i, result in enumerate(similar_results):
            print(f"\n{i+1}. 文本 (ID: {result['id']}): {result['text']}")
            print(f"   距离: {result['distance']:.4f}") # L2 距离越小越相似
    else:
        print(f"\n未找到与 \"{args.question}\" 相关的知识点，或发生错误。")
    
    print("\n--- 搜索完成 ---")

if __name__ == "__main__":
    main()
