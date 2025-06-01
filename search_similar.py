import json
import os
from pathlib import Path
import argparse
import numpy as np
import torch
from transformers import BertTokenizer, BertModel
import faiss
import sys # For CLI argument parsing
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s] %(message)s')

# --- Constants defined as per requirements (shared across scripts) ---
BERT_MODEL = "bert-base-chinese"
CATALOG_FILENAME = "catalog.json"
CATALOG_SEGMENTS_FILENAME = "catalog_with_segments.json"
EMBEDDING_BATCH_SIZE = 32
FAISS_INDEX_FILENAME = "knowledge_points.index" # Default name for FAISS index
IMAGES_SUBDIR_NAME = "textbook_images_dir"
LLM_MODEL = "qwen-max"
MAPPING_FILE_SUFFIX = ".mapping.json"    # Default suffix for mapping file
ORGCHART_SUBDIR_NAME = "orgchart_dir"
TEXTBOOK_ORGCHART_FILENAME = "textbook_orgchart.json"
PAGES_FOR_CATALOG = 30
SEARCH_TOP_K = 3                         # Default K for search
TEXT_SUBDIR_NAME = "textbook_text_dir"
BOOK_ROOT_TITLE = "马克思主义基本原理概论"
USE_GPU = torch.cuda.is_available()      # Default for GPU, auto-detect
# --- End of defined constants ---


def get_bert_embedding_for_query(text: str, tokenizer, model, device) -> Optional[np.ndarray]:
    """
    Generates BERT embedding for a single text query.
    """
    if not text or not text.strip():
        logging.error("Query text is empty.")
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

def search_in_faiss_index(query_text: str, faiss_index_obj, id_to_text_mapping_list: list,
                          tokenizer_obj, model_obj, device_obj, top_k_val: int) -> List[Dict]:
    """
    Embeds query, searches FAISS index, and returns top_k similar texts.
    """
    if not query_text.strip():
        logging.warning("Query is empty, cannot search.")
        return []
    logging.info(f"\nSearching for knowledge points similar to: \"{query_text}\"")
    query_embedding = get_bert_embedding_for_query(query_text, tokenizer_obj, model_obj, device_obj)
    if query_embedding is None or query_embedding.size == 0:
        logging.error("Could not generate embedding for the query.")
        return []

    actual_top_k = min(top_k_val, faiss_index_obj.ntotal)
    if actual_top_k < top_k_val:
        logging.warning(f"Requested top_k ({top_k_val}) is greater than the number of vectors in the index ({faiss_index_obj.ntotal}). Using top_k={actual_top_k}.")
    if actual_top_k <= 0:
        logging.warning(f"No vectors to search in the index or invalid top_k ({top_k_val}).")
        return []

    logging.info(f"Searching FAISS index for top {actual_top_k} results...")
    try:
        distances, indices = faiss_index_obj.search(query_embedding, actual_top_k)
    except Exception as e:
        logging.error(f"Error during FAISS search: {e}")
        return []

    results = []
    if indices.size > 0:
        for i in range(indices.shape[1]):
            idx = indices[0, i]
            dist = distances[0, i]
            if idx == -1: # FAISS can return -1 if distance is too large or other issues
                logging.warning(f"FAISS returned -1 index at position {i}.")
                continue
            if 0 <= idx < len(id_to_text_mapping_list):
                original_text = id_to_text_mapping_list[idx]
                results.append({"text": original_text, "distance": float(dist), "id": int(idx)})
            else:
                logging.warning(f"Index {idx} out of bounds for mapping file (size {len(id_to_text_mapping_list)}).")
    logging.info(f"Found {len(results)} similar knowledge points.")
    return results

def find_similar_knowledge_points(question_str: str, index_file_abs_path: Path, mapping_file_abs_path: Path,
                                  model_name_to_use: str, use_gpu_flag: bool, top_k_to_search: int) -> List[Dict]:
    """
    Loads model and index, then performs search for a given question string.
    This function is designed for direct use, with all paths and configurations resolved.
    """
    logging.info("--- Initializing search logic with resolved parameters ---")

    if not index_file_abs_path.is_file():
        logging.error(f"FAISS index file not found at {index_file_abs_path}.")
        return []
    if not mapping_file_abs_path.is_file():
        logging.error(f"Mapping file not found at {mapping_file_abs_path}.")
        return []

    logging.info(f"Loading FAISS index from: {index_file_abs_path}")
    try:
        faiss_index = faiss.read_index(str(index_file_abs_path))
        if faiss_index.ntotal == 0:
            logging.warning(f"Loaded FAISS index '{index_file_abs_path}' contains no vectors. Cannot perform search.")
            return []
        logging.info(f"FAISS index loaded. Contains {faiss_index.ntotal} vectors.")
    except Exception as e:
        logging.error(f"Error loading FAISS index '{index_file_abs_path}': {e}")
        return []

    logging.info(f"Loading ID-to-text mapping from: {mapping_file_abs_path}")
    try:
        with open(mapping_file_abs_path, 'r', encoding='utf-8') as f:
            id_to_text_mapping = json.load(f)
        logging.info(f"Mapping file loaded. Contains {len(id_to_text_mapping)} entries.")
    except Exception as e:
        logging.error(f"Error loading mapping file '{mapping_file_abs_path}': {e}")
        return []

    logging.info(f"Loading tokenizer and model for query embedding: {model_name_to_use}...")
    try:
        tokenizer = BertTokenizer.from_pretrained(model_name_to_use)
        model = BertModel.from_pretrained(model_name_to_use)
    except Exception as e:
        logging.error(f"Error loading model/tokenizer '{model_name_to_use}': {e}")
        return []

    resolved_use_gpu = use_gpu_flag and torch.cuda.is_available()
    device = torch.device("cuda" if resolved_use_gpu else "cpu")

    if resolved_use_gpu:
        logging.info(f"CUDA available, using GPU for query embedding: {torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else 'N/A'}")
    else:
        if use_gpu_flag and not torch.cuda.is_available():
            logging.warning("GPU use was requested, but CUDA is not available. Falling back to CPU for query embedding.")
        logging.info("Using CPU for query embedding.")

    model.to(device)
    model.eval()

    similar_results = search_in_faiss_index(
        question_str, faiss_index, id_to_text_mapping,
        tokenizer, model, device, top_k_val=top_k_to_search
    )
    return similar_results

def search_textbook_knowledge(question: str, textbook_name: str, script_dir: Path,
                              top_k_override: Optional[int] = None) -> List[Dict]:
    """
    Searches knowledge points for a specific textbook.
    This function is intended for programmatic calls from other scripts in the suite.

    Args:
        question (str): The search query.
        textbook_name (str): The base name of the textbook (e.g., "book1").
        script_dir (Path): The directory where this search_similar.py script is located.
        top_k_override (Optional[int]): If provided, overrides the default SEARCH_TOP_K.

    Returns:
        List[Dict]: A list of search results, each a dict with "text", "distance", "id".
    """
    logging.info(f"Programmatic search initiated for textbook '{textbook_name}' with query: '{question}'")

    info_storage_dir = script_dir / "uploads" / textbook_name / "textbook_information"
    index_file_path = info_storage_dir / FAISS_INDEX_FILENAME
    mapping_file_name = Path(FAISS_INDEX_FILENAME).stem + MAPPING_FILE_SUFFIX
    mapping_file_path = info_storage_dir / mapping_file_name

    current_top_k = top_k_override if top_k_override is not None else SEARCH_TOP_K
    current_bert_model = BERT_MODEL
    current_use_gpu = USE_GPU # From global constant

    logging.info(f"Derived index file path: {index_file_path}")
    logging.info(f"Derived mapping file path: {mapping_file_path}")
    logging.info(f"Using BERT model: {current_bert_model}")
    logging.info(f"Search top_k: {current_top_k}")
    logging.info(f"Use GPU: {current_use_gpu}")

    return find_similar_knowledge_points(
        question_str=question,
        index_file_abs_path=index_file_path.resolve(),
        mapping_file_abs_path=mapping_file_path.resolve(),
        model_name_to_use=current_bert_model,
        use_gpu_flag=current_use_gpu,
        top_k_to_search=current_top_k
    )

def main_cli():
    """Handles command-line interface for the script."""
    try:
        script_dir = Path(__file__).parent.resolve()
    except NameError:
        script_dir = Path(os.getcwd()).resolve()
    logging.info(f"Script running from directory: {script_dir}")

    parser = argparse.ArgumentParser(
        description="Search for knowledge points similar to a given question. "
                    "Uses global constants for defaults unless overridden by CLI arguments "
                    "or derived from --textbook_name."
    )
    parser.add_argument("question", type=str, help="The question to search for.")
    parser.add_argument("--textbook_name", type=str, default=None,
                        help="Optional: Name of the textbook to search within. "
                             "If provided, index and mapping file paths are derived. "
                             "E.g., 'my_book'.")
    parser.add_argument("--index_file", type=str, default=None,
                        help="Path to the FAISS index file. Required if --textbook_name is not set.")
    parser.add_argument("--mapping_file", type=str, default=None,
                        help="Path to the ID-text mapping JSON file. Required if --textbook_name is not set.")
    parser.add_argument("--model_name", type=str, default=BERT_MODEL,
                        help=f"BERT model name for query embedding. (Default: {BERT_MODEL})")
    parser.add_argument("--top_k", type=int, default=SEARCH_TOP_K,
                        help=f"Number of top similar results to retrieve. (Default: {SEARCH_TOP_K})")
    parser.add_argument("--use_gpu", action=argparse.BooleanOptionalAction, default=USE_GPU,
                        help=f"Whether to attempt using GPU. Use --use-gpu or --no-use-gpu. (Default: {USE_GPU})")

    args = parser.parse_args()

    final_index_path_str = args.index_file
    final_mapping_path_str = args.mapping_file

    if args.textbook_name:
        logging.info(f"Textbook name '{args.textbook_name}' provided. Deriving index and mapping paths.")
        info_dir = script_dir / "uploads" / args.textbook_name / "textbook_information"
        derived_index_path = info_dir / FAISS_INDEX_FILENAME
        derived_mapping_filename = Path(FAISS_INDEX_FILENAME).stem + MAPPING_FILE_SUFFIX
        derived_mapping_path = info_dir / derived_mapping_filename

        if final_index_path_str is None: # Only use derived if not overridden by CLI
            final_index_path_str = str(derived_index_path)
        if final_mapping_path_str is None: # Only use derived if not overridden by CLI
            final_mapping_path_str = str(derived_mapping_path)
        logging.info(f"Using index file: {final_index_path_str} (derived or overridden)")
        logging.info(f"Using mapping file: {final_mapping_path_str} (derived or overridden)")

    if not final_index_path_str or not final_mapping_path_str:
        parser.error("If --textbook_name is not provided, --index_file and --mapping_file are required.")
        return # Should be unreachable due to parser.error

    final_index_file_path = Path(final_index_path_str).resolve()
    final_mapping_file_path = Path(final_mapping_path_str).resolve()

    logging.info("--- Command-Line Search Initialized ---")
    logging.info(f"Query: \"{args.question}\"")
    logging.info(f"Parameters: Model='{args.model_name}', TopK={args.top_k}, UseGPU={args.use_gpu}")
    logging.info(f"Index File: '{final_index_file_path}', Mapping File: '{final_mapping_file_path}'")

    similar_results = find_similar_knowledge_points(
        args.question,
        final_index_file_path,
        final_mapping_file_path,
        args.model_name, # Use CLI provided or its default (which is global constant)
        args.use_gpu,   # Use CLI provided or its default (which is global constant)
        args.top_k      # Use CLI provided or its default (which is global constant)
    )

    if similar_results:
        print(f"\n--- Top {len(similar_results)} results for \"{args.question}\" ---") # Use print for final user output
        for i, result in enumerate(similar_results):
            print(f"\n{i+1}. Text (ID: {result['id']}): {result['text']}")
            print(f"   Distance: {result['distance']:.4f}")
    else:
        print(f"\nNo relevant knowledge points found for \"{args.question}\", or an error occurred.")

    logging.info("--- Search complete ---")

if __name__ == "__main__":
    main_cli()