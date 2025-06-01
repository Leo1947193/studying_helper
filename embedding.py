import json
import os
from pathlib import Path
import numpy as np
import torch
from transformers import BertTokenizer, BertModel
import faiss # For FAISS indexing
import sys # For command-line arguments
import logging # Added for better logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s] %(message)s')

# --- Constants defined as per requirements ---
BERT_MODEL = "bert-base-chinese"
CATALOG_FILENAME = "catalog.json" # Not directly used by this script, but part of the standard set
CATALOG_SEGMENTS_FILENAME = "catalog_with_segments.json" # Input for this script
EMBEDDING_BATCH_SIZE = 32
FAISS_INDEX_FILENAME = "knowledge_points.index" # Output FAISS index filename
IMAGES_SUBDIR_NAME = "textbook_images_dir" # Not directly used, but part of the standard set
LLM_MODEL = "qwen-max" # Not directly used, but part of the standard set
MAPPING_FILE_SUFFIX = ".mapping.json" # Suffix for the mapping file
ORGCHART_SUBDIR_NAME = "orgchart_dir" # Not directly used, but part of the standard set
TEXTBOOK_ORGCHART_FILENAME = "textbook_orgchart.json" # Not directly used, but part of the standard set
PAGES_FOR_CATALOG = 30 # Not directly used, but part of the standard set
SEARCH_TOP_K = 3 # Not directly used, but part of the standard set
TEXT_SUBDIR_NAME = "textbook_text_dir" # Not directly used, but part of the standard set
BOOK_ROOT_TITLE = "马克思主义基本原理概论" # Not directly used, but part of the standard set

# New constant for GPU usage, as per plan
USE_GPU = True # Set to False to force CPU
# --- End of defined constants ---

def _extract_recursive(node_list, all_kps_list):
    """
    Helper recursive function to traverse JSON structure and extract knowledge_points.
    Modifies all_kps_list directly.
    """
    if not isinstance(node_list, list):
        return

    for node in node_list:
        if not isinstance(node, dict):
            continue

        if "knowledge_points" in node and node["knowledge_points"]:
            if isinstance(node["knowledge_points"], list):
                for item in node["knowledge_points"]:
                    if isinstance(item, str) and item.strip():
                        all_kps_list.append(item.strip())
                    elif isinstance(item, str):
                        logging.warning(f"Empty string found in knowledge_points for node '{node.get('name', 'Unnamed Node')}'.")
                    else:
                        logging.warning(f"Non-string item found in knowledge_points for node '{node.get('name', 'Unnamed Node')}': {item}")
            else:
                logging.warning(f"'knowledge_points' is not a list in node '{node.get('name', 'Unnamed Node')}'.")

        if "children" in node and isinstance(node["children"], list) and node["children"]:
            _extract_recursive(node["children"], all_kps_list)

def extract_knowledge_points_from_json(json_file_path: Path) -> List[str]:
    """
    Reads a JSON file and extracts all 'knowledge_points' strings.
    Returns a list of unique knowledge points, preserving first-seen order.
    """
    logging.info(f"Attempting to load JSON from: {json_file_path}")
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logging.error(f"JSON file not found at {json_file_path}.")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Cannot decode JSON from {json_file_path}. Details: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error reading {json_file_path}: {e}")
        return []

    extracted_kps = []
    if "chapters" in data and isinstance(data["chapters"], list):
        _extract_recursive(data["chapters"], extracted_kps)
    else:
        logging.warning("'chapters' key not found or not a list in JSON root.")

    unique_ordered_kps = list(dict.fromkeys(extracted_kps))
    logging.info(f"Extracted {len(unique_ordered_kps)} unique knowledge points.")
    return unique_ordered_kps

def get_bert_embeddings(texts: List[str], model_name: str, batch_size: int, use_gpu_explicit: bool) -> np.ndarray:
    """
    Generates BERT embeddings for a list of texts using mean pooling of last hidden states.
    """
    if not texts:
        logging.warning("No texts provided for embedding.")
        return np.array([])

    logging.info(f"Loading tokenizer and model: {model_name}...")
    try:
        tokenizer = BertTokenizer.from_pretrained(model_name)
        model = BertModel.from_pretrained(model_name)
    except Exception as e:
        logging.error(f"Error loading model/tokenizer '{model_name}': {e}")
        return np.array([])

    resolved_use_gpu = use_gpu_explicit and torch.cuda.is_available()
    device = torch.device("cuda" if resolved_use_gpu else "cpu")

    if resolved_use_gpu:
        logging.info(f"CUDA available, using GPU: {torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else 'N/A'}")
    else:
        if use_gpu_explicit and not torch.cuda.is_available():
            logging.warning("GPU use was requested, but CUDA is not available. Falling back to CPU.")
        logging.info("Using CPU for embeddings.")

    model.to(device)
    model.eval()

    all_embeddings_list = []
    logging.info(f"Starting embedding for {len(texts)} texts, batch size {batch_size}...")
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        encoded_input = tokenizer(
            batch_texts, padding=True, truncation=True, return_tensors='pt', max_length=512
        )
        encoded_input = {k: v.to(device) for k, v in encoded_input.items()}

        with torch.no_grad():
            outputs = model(**encoded_input)
            last_hidden_states = outputs.last_hidden_state
            attention_mask = encoded_input['attention_mask']
            input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_states.size()).float()
            sum_embeddings = torch.sum(last_hidden_states * input_mask_expanded, 1)
            sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
            mean_pooled_embeddings = sum_embeddings / sum_mask
        all_embeddings_list.append(mean_pooled_embeddings.cpu().numpy())
        if (i // batch_size + 1) % 10 == 0:
             logging.info(f"  Processed batch {i // batch_size + 1} / {(len(texts) + batch_size - 1) // batch_size}")

    if not all_embeddings_list:
        logging.warning("No embeddings were generated.")
        return np.array([])

    embeddings_np = np.concatenate(all_embeddings_list, axis=0)
    logging.info(f"Embedding generation complete. Shape: {embeddings_np.shape}")
    return embeddings_np.astype('float32') # FAISS expects float32

def create_and_save_faiss_index(embeddings_np: np.ndarray, output_index_path: Path) -> bool:
    """
    Creates a FAISS index from embeddings and saves it.
    """
    if not isinstance(embeddings_np, np.ndarray) or embeddings_np.ndim != 2 or embeddings_np.size == 0:
        logging.error("Invalid or empty embeddings provided for FAISS indexing.")
        return False

    dimension = embeddings_np.shape[1]
    num_vectors = embeddings_np.shape[0]
    logging.info(f"Creating FAISS index with dimension {dimension} for {num_vectors} vectors.")

    try:
        index = faiss.IndexFlatL2(dimension)
    except Exception as e:
        logging.error(f"Error creating FAISS index object: {e}. Ensure faiss is installed.")
        return False

    logging.info(f"Adding {num_vectors} vectors to FAISS index...")
    try:
        index.add(embeddings_np)
    except Exception as e:
        logging.error(f"Error adding vectors to FAISS index: {e}")
        return False
    logging.info(f"Total vectors in index: {index.ntotal}")

    try:
        output_index_path.parent.mkdir(parents=True, exist_ok=True)
        logging.info(f"Saving FAISS index to: {output_index_path}")
        faiss.write_index(index, str(output_index_path))
        logging.info("FAISS index saved successfully.")
        return True
    except Exception as e:
        logging.error(f"Error saving FAISS index to {output_index_path}: {e}")
        return False

def run_embedding_generation(textbook_name: str, script_dir: Path):
    """
    Main pipeline for generating embeddings and FAISS index for a textbook.
    Args:
        textbook_name (str): The base name of the textbook (e.g., "book1").
        script_dir (Path): The directory where this script is located.
    """
    logging.info(f"\n--- Starting Embedding and Indexing Pipeline for Textbook: {textbook_name} ---")

    # Construct paths based on requirements and global constants
    textbook_base_uploads_dir = script_dir / "uploads" / textbook_name
    info_storage_dir = textbook_base_uploads_dir / "textbook_information"

    input_catalog_json_path = info_storage_dir / CATALOG_SEGMENTS_FILENAME
    output_faiss_index_path = info_storage_dir / FAISS_INDEX_FILENAME
    # Derive mapping filename from FAISS_INDEX_FILENAME and MAPPING_FILE_SUFFIX
    mapping_file_name = Path(FAISS_INDEX_FILENAME).stem + MAPPING_FILE_SUFFIX
    output_mapping_file_path = info_storage_dir / mapping_file_name

    logging.info(f"Input catalog (segments) JSON: {input_catalog_json_path}")
    logging.info(f"Output FAISS index: {output_faiss_index_path}")
    logging.info(f"Output mapping file: {output_mapping_file_path}")
    logging.info(f"BERT Model: {BERT_MODEL}")
    logging.info(f"Embedding Batch Size: {EMBEDDING_BATCH_SIZE}")
    logging.info(f"Use GPU: {USE_GPU}")


    # Step 1: Extract knowledge points
    logging.info(f"\n[Step 1/4] Extracting knowledge points from: {input_catalog_json_path}")
    knowledge_points_texts = extract_knowledge_points_from_json(input_catalog_json_path)
    if not knowledge_points_texts:
        logging.error("No knowledge points found or error during extraction. Aborting pipeline.")
        return
    logging.info(f"Successfully extracted {len(knowledge_points_texts)} unique knowledge points.")

    # Step 2: Generate BERT embeddings
    logging.info("\n[Step 2/4] Generating BERT embeddings...")
    embeddings = get_bert_embeddings(knowledge_points_texts, BERT_MODEL, EMBEDDING_BATCH_SIZE, USE_GPU)
    if embeddings.size == 0:
        logging.error("Failed to generate embeddings. Aborting pipeline.")
        return
    logging.info(f"Successfully generated {embeddings.shape[0]} embeddings with dimension {embeddings.shape[1]}.")

    # Step 3: Create and save FAISS index
    logging.info("\n[Step 3/4] Creating and saving FAISS index...")
    index_saved = create_and_save_faiss_index(embeddings, output_faiss_index_path)
    if not index_saved:
        logging.error("Failed to create or save FAISS index. Aborting pipeline.")
        return

    # Step 4: Save mapping from FAISS index ID to original text
    logging.info(f"\n[Step 4/4] Saving knowledge point mapping to: {output_mapping_file_path}")
    try:
        output_mapping_file_path.parent.mkdir(parents=True, exist_ok=True) # Ensure dir exists
        with open(output_mapping_file_path, 'w', encoding='utf-8') as f:
            json.dump(knowledge_points_texts, f, ensure_ascii=False, indent=4)
        logging.info(f"Knowledge point mapping saved successfully to {output_mapping_file_path}.")
    except Exception as e:
        logging.error(f"Error saving knowledge point mapping to {output_mapping_file_path}: {e}")

    logging.info(f"\n--- Embedding and Indexing Pipeline for '{textbook_name}' Finished ---")
    logging.info(f"Output files are in directory: {info_storage_dir.resolve()}")

def main_cli():
    """Command-line interface handler."""
    if len(sys.argv) > 1:
        textbook_name_arg = sys.argv[1]
        if textbook_name_arg.lower().endswith(".pdf"):
            textbook_name_arg = textbook_name_arg[:-4]

        try:
            current_script_dir = Path(__file__).resolve().parent
        except NameError:
            current_script_dir = Path(os.getcwd()).resolve()
        logging.info(f"Script running from: {current_script_dir}")

        run_embedding_generation(textbook_name_arg, current_script_dir)
    else:
        script_name = Path(sys.argv[0]).name
        print(f"Usage: python {script_name} <textbook_name_without_extension>")
        print(f"Example: python {script_name} my_history_book")

if __name__ == "__main__":
    main_cli()
    logging.info("\nScript execution finished.")