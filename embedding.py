# embedding.py
import json
import os
from pathlib import Path # For easier path manipulation
import numpy as np
import torch
from transformers import BertTokenizer, BertModel
import faiss # For FAISS indexing

# 默认配置文件名
DEFAULT_CONFIG_FILENAME = "config.json" # 使用统一的配置文件名

def load_embedding_config(config_file_path):
    """
    从指定的 JSON 文件加载嵌入相关的配置。

    Args:
        config_file_path (Path): 配置文件的完整路径。

    Returns:
        dict or None: 如果加载成功则返回配置字典，否则返回 None。
    """
    print(f"正在从 '{config_file_path}' 加载嵌入配置...")
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # 验证嵌入脚本所需的键是否存在且类型正确
        required_keys = {
            "use_gpu": bool,
            "bert_model": str,
            "catalog_segments": str,
            "faiss_index_filename": str,
            "mapping_file_suffix": str,
            "embedding_batch_size": int
        }
        for key, expected_type in required_keys.items():
            if key not in config_data:
                print(f"错误：配置文件 '{config_file_path}' 中缺少键 '{key}' (嵌入配置需要)。")
                return None
            if not isinstance(config_data[key], expected_type):
                print(f"错误：配置文件 '{config_file_path}' 中键 '{key}' 的类型不正确。期望类型：{expected_type}, 实际类型：{type(config_data[key])}。")
                return None
        
        if not 0 < config_data["embedding_batch_size"] < 1024: # 对批处理大小进行合理性检查
             print(f"警告：嵌入批处理大小 '{config_data['embedding_batch_size']}' 可能不合理。请检查配置。")

        print("嵌入配置加载成功。")
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

def _extract_recursive(node_list, all_kps_list):
    """
    辅助递归函数，用于遍历 JSON 结构并提取 knowledge_points。
    直接修改 all_kps_list。
    """
    if not isinstance(node_list, list):
        return

    for node in node_list:
        if not isinstance(node, dict):
            continue

        # 从当前节点提取 knowledge_points
        if "knowledge_points" in node and node["knowledge_points"]:
            if isinstance(node["knowledge_points"], list):
                for item in node["knowledge_points"]:
                    if isinstance(item, str) and item.strip(): # 添加非空字符串
                        all_kps_list.append(item.strip())
                    elif isinstance(item, str):
                        print(f"警告：在节点 '{node.get('name', '未命名节点')}' 的 knowledge_points 中找到空字符串。")
                    else:
                        print(f"警告：在节点 '{node.get('name', '未命名节点')}' 的 knowledge_points 中找到非字符串项目：{item}")
            else:
                print(f"警告：节点 '{node.get('name', '未命名节点')}' 中的 'knowledge_points' 不是列表。")

        # 递归处理子节点
        if "children" in node and isinstance(node["children"], list) and node["children"]:
            _extract_recursive(node["children"], all_kps_list)

def extract_knowledge_points_from_json(json_file_path):
    """
    读取 JSON 文件并提取所有 'knowledge_points' 字符串。
    返回唯一知识点的列表，保留首次出现的顺序。
    """
    print(f"尝试从以下位置加载 JSON： {json_file_path}")
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误：在 {json_file_path} 未找到 JSON 文件。")
        print("请确保输入 JSON 文件存在于指定路径。")
        return []
    except json.JSONDecodeError as e:
        print(f"错误：无法从 {json_file_path} 解码 JSON。详细信息： {e}")
        return []
    except Exception as e:
        print(f"读取 {json_file_path} 时发生意外错误： {e}")
        return []

    extracted_kps = []
    if "chapters" in data and isinstance(data["chapters"], list):
        _extract_recursive(data["chapters"], extracted_kps)
    else:
        print("警告：JSON 根目录中未找到 'chapters' 键或其不是列表。")

    # 去重同时保留首次出现的顺序
    unique_ordered_kps = list(dict.fromkeys(extracted_kps))
    print(f"提取了 {len(unique_ordered_kps)} 个唯一的知识点。")
    return unique_ordered_kps

def get_bert_embeddings(texts, model_name_str, batch_size_val, use_gpu_flag):
    """
    使用最后隐藏状态的平均池化为文本列表生成 BERT 嵌入。
    """
    if not texts:
        print("未提供用于嵌入的文本。")
        return np.array([])

    print(f"正在加载分词器和模型： {model_name_str}...")
    try:
        tokenizer = BertTokenizer.from_pretrained(model_name_str)
        model = BertModel.from_pretrained(model_name_str)
    except Exception as e:
        print(f"加载模型/分词器 '{model_name_str}' 时出错： {e}")
        print("请确保你有可用的网络连接且模型名称正确。")
        print("你可能需要安装 transformers 库： pip install transformers torch")
        return np.array([])

    if use_gpu_flag:
        if torch.cuda.is_available():
            device = torch.device("cuda")
            print("CUDA 可用，将使用 GPU 进行嵌入。")
        else:
            device = torch.device("cpu")
            print("警告：配置请求使用 GPU，但 CUDA 不可用。将使用 CPU 进行嵌入。")
    else:
        device = torch.device("cpu")
        print("将使用 CPU 进行嵌入 (根据配置)。")
        
    model.to(device)
    model.eval() # 将模型设置为评估模式

    all_embeddings_list = []
    
    print(f"开始为 {len(texts)} 个文本进行嵌入处理，批处理大小为 {batch_size_val}...")
    for i in range(0, len(texts), batch_size_val):
        batch_texts = texts[i:i+batch_size_val]
        
        encoded_input = tokenizer(
            batch_texts,
            padding=True,        # 填充到批次中最长序列
            truncation=True,     # 截断到模型最大输入长度
            return_tensors='pt', # 返回 PyTorch 张量
            max_length=512       # BERT 模型最大长度
        )
        encoded_input = {k: v.to(device) for k, v in encoded_input.items()}

        with torch.no_grad(): # 推理时禁用梯度计算
            outputs = model(**encoded_input)
            last_hidden_states = outputs.last_hidden_state
            attention_mask = encoded_input['attention_mask']
            input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_states.size()).float()
            sum_embeddings = torch.sum(last_hidden_states * input_mask_expanded, 1)
            sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
            mean_pooled_embeddings = sum_embeddings / sum_mask
            
        all_embeddings_list.append(mean_pooled_embeddings.cpu().numpy())

    if not all_embeddings_list:
        print("未生成任何嵌入。")
        return np.array([])
        
    embeddings_np = np.concatenate(all_embeddings_list, axis=0)
    print(f"嵌入生成完成。形状： {embeddings_np.shape}")
    # FAISS 期望 float32 类型
    return embeddings_np.astype('float32')

def create_and_save_faiss_index(embeddings_np, output_index_path):
    """
    从嵌入创建 FAISS 索引并将其保存到文件。
    """
    if not isinstance(embeddings_np, np.ndarray) or embeddings_np.ndim != 2 or embeddings_np.size == 0:
        print("未提供有效的嵌入用于索引，或者嵌入不是二维数组。")
        return False

    dimension = embeddings_np.shape[1]
    num_vectors = embeddings_np.shape[0]
    print(f"正在创建维度为 {dimension} 的 FAISS 索引，包含 {num_vectors} 个向量。")
    
    try:
        index = faiss.IndexFlatL2(dimension) # 使用 IndexFlatL2 进行精确 L2 (欧氏) 距离搜索
    except Exception as e:
        print(f"创建 FAISS 索引对象时出错： {e}")
        print("请确保已正确安装 faiss 库 (例如：pip install faiss-cpu)。")
        return False
    
    print(f"正在将 {num_vectors} 个向量添加到 FAISS 索引...")
    try:
        index.add(embeddings_np)
    except Exception as e:
        print(f"向 FAISS 索引添加向量时出错： {e}")
        return False
    
    print(f"索引中的总向量数： {index.ntotal}")
    
    try:
        print(f"正在将 FAISS 索引保存到： {output_index_path}")
        faiss.write_index(index, str(output_index_path)) # faiss.write_index 需要字符串路径
        print("FAISS 索引保存成功。")
        return True
    except Exception as e:
        print(f"保存 FAISS 索引到 {output_index_path} 时出错： {e}")
        return False

def run_embedding_pipeline(config_data, script_dir_path):
    """
    协调完整的嵌入和索引流程。
    1. 从输入 JSON 中提取知识点。
    2. 为这些文本生成 BERT 嵌入。
    3. 从嵌入创建 FAISS 索引。
    4. 保存 FAISS 索引和映射文件（原始文本）。
    """
    print("\n--- 开始嵌入和索引流程 ---")
    
    # 从配置中获取参数 (使用小写键名)
    catalog_json_filename = config_data["catalog_segments"]
    faiss_index_filename = config_data["faiss_index_filename"]
    mapping_file_suffix = config_data["mapping_file_suffix"]
    bert_model_name = config_data["bert_model_name"]
    embedding_batch_size = config_data["embedding_batch_size"]
    use_gpu = config_data["use_gpu"]

    # 构建完整路径
    input_json_full_path = script_dir_path / catalog_json_filename
    output_faiss_index_full_path = script_dir_path / faiss_index_filename
    # 映射文件名由 faiss_index_filename 和 mapping_file_suffix 组合而成
    mapping_file_full_path = script_dir_path / (faiss_index_filename + mapping_file_suffix)


    # 步骤 1: 提取知识点
    print(f"\n[步骤 1/4] 从以下位置提取知识点： {input_json_full_path}")
    knowledge_points_texts = extract_knowledge_points_from_json(input_json_full_path)
    
    if not knowledge_points_texts:
        print("未找到知识点或提取过程中出错。中止流程。")
        return
    print(f"成功提取 {len(knowledge_points_texts)} 个唯一的知识点。")

    # 步骤 2: 生成 BERT 嵌入
    print("\n[步骤 2/4] 生成 BERT 嵌入...")
    embeddings = get_bert_embeddings(knowledge_points_texts, bert_model_name, embedding_batch_size, use_gpu)
    
    if embeddings.size == 0:
        print("生成嵌入失败。中止流程。")
        return
    print(f"成功生成 {embeddings.shape[0]} 个嵌入，维度为 {embeddings.shape[1]}。")

    # 步骤 3: 创建并保存 FAISS 索引
    print("\n[步骤 3/4] 创建并保存 FAISS 索引...")
    index_saved = create_and_save_faiss_index(embeddings, output_faiss_index_full_path)
    if not index_saved:
        print("创建或保存 FAISS 索引失败。中止流程。")
        return

    # 步骤 4: 保存从 FAISS 索引 ID 到原始文本的映射
    # knowledge_points_texts 中文本的顺序对应于它们添加到 FAISS 的顺序。
    print(f"\n[步骤 4/4] 将知识点映射保存到： {mapping_file_full_path}")
    try:
        with open(mapping_file_full_path, 'w', encoding='utf-8') as f:
            # 存储为列表，列表中的索引即为 FAISS ID
            json.dump(knowledge_points_texts, f, ensure_ascii=False, indent=4)
        print(f"知识点映射成功保存到 {mapping_file_full_path}。")
    except Exception as e:
        print(f"保存知识点映射到 {mapping_file_full_path} 时出错： {e}")
    
    print("\n--- 嵌入和索引流程结束 ---")

if __name__ == "__main__":
    try:
        # 确定脚本所在的目录
        script_dir = Path(__file__).parent.resolve()
    except NameError: # 处理在某些IDE或直接执行时 __file__ 未定义的情况
        script_dir = Path(os.getcwd()).resolve()
    
    print(f"脚本运行目录: {script_dir}")
    
    # 加载配置
    config_file_full_path = script_dir / DEFAULT_CONFIG_FILENAME
    config = load_embedding_config(config_file_full_path) # 使用特定于嵌入的加载函数

    if config:
        # 调用主处理函数
        run_embedding_pipeline(config, script_dir)
    else:
        print("由于配置加载失败，嵌入流程无法启动。")
    
    print("\n脚本执行完毕。")
    print(f"请检查目录 '{script_dir}' 中的输出文件。")