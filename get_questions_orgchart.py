# get_questions_orgchart.py (Modified)

import os
import json
import argparse
from pathlib import Path
import logging
from dotenv import load_dotenv
from collections import deque # For BFS/DFS for descendants

# Assuming llm_interface.py and search_similar.py are in the same directory
# or PYTHONPATH is set up correctly.
from llm_interface import DeepSeekLLM
import search_similar

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
load_dotenv()  # Load environment variables from .env file

# Constants for paths and filenames
QUESTIONS_SUBDIR_NAME = "questions"
TEXTBOOK_INFO_SUBDIR_NAME = "textbook_information"
# Input: The main org chart for the entire textbook
TEXTBOOK_ORGCHART_FILENAME = "textbook_orgchart.json"
# Output: The filtered org chart relevant to the questions
OUTPUT_FILTERED_ORGCHART_FILENAME = "questions_filtered_textbook_orgchart.json"
RELATED_KPS_TOP_K = 3  # Number of top related KPs to find for each question-answer pair

# LLM Configuration (can be overridden by environment variables)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEFAULT_DEEPSEEK_MODEL = os.getenv("DEFAULT_DEEPSEEK_MODEL", "deepseek-chat")


def collect_exam_text_from_dir(questions_dir: Path) -> str:
    """
    Collects and concatenates text from all .txt files in the given directory.
    """
    all_text = []
    if not questions_dir.is_dir():
        logging.warning(f"Questions directory not found or is not a directory: {questions_dir}")
        return ""

    logging.info(f"Scanning for .txt files in {questions_dir}...")
    txt_files_found = list(questions_dir.glob("*.txt"))

    if not txt_files_found:
        logging.warning(f"No .txt files found in {questions_dir}.")
        return ""

    for txt_file in txt_files_found:
        try:
            logging.info(f"Reading text from: {txt_file.name}")
            with open(txt_file, 'r', encoding='utf-8') as f:
                all_text.append(f.read())
        except Exception as e:
            logging.error(f"Error reading file {txt_file.name}: {e}")

    concatenated_text = "\n\n---\n\n".join(all_text)
    logging.info(f"Collected {len(concatenated_text)} characters from {len(txt_files_found)} .txt files.")
    return concatenated_text


def get_relevant_kp_names_for_questions(
    qa_pairs: list,
    textbook_name_for_search: str, # e.g., "MyBook" (without _dir)
    current_script_dir: Path      # Dir where search_similar.py is located
) -> set:
    """
    For each Q&A pair, finds similar KPs from the textbook and returns a set of their names.
    """
    all_kp_names = set()
    if not qa_pairs:
        logging.warning("No Q&A pairs provided to find relevant KPs.")
        return all_kp_names

    for i, qa_pair in enumerate(qa_pairs):
        question_text = qa_pair.get("question")
        answer_text = qa_pair.get("answer", "") # LLM-extracted answer

        if not question_text:
            logging.warning(f"Skipping Q&A pair {i+1} due to missing question.")
            continue

        # Concatenate question and its LLM-extracted answer to form a richer query
        query_for_similarity = f"{question_text} {answer_text}".strip()
        logging.info(f"Finding KPs for query (Q&A based): \"{query_for_similarity[:100]}...\"")

        try:
            similar_kps = search_similar.search_textbook_knowledge(
                question=query_for_similarity,
                textbook_name=textbook_name_for_search,
                script_dir=current_script_dir,
                top_k_override=RELATED_KPS_TOP_K
            )
            for kp in similar_kps:
                if kp.get("text"): # 'text' contains the name/content of the KP
                    all_kp_names.add(kp["text"])
        except Exception as e:
            logging.error(f"Error searching KPs for Q '{question_text[:50]}...': {e}")

    logging.info(f"Collected {len(all_kp_names)} unique relevant KP names from textbook similarity search.")
    return all_kp_names


def filter_textbook_orgchart(
    all_textbook_nodes: list,  # Flat list of all nodes from textbook_orgchart.json
    target_kp_names: set       # Set of knowledge point names to match
) -> list:
    """
    Filters the textbook_orgchart based on target_kp_names.
    Keeps target nodes, their descendants, their ancestors, and the root.
    The input and output are flat lists of node objects.
    """
    if not all_textbook_nodes:
        logging.warning("Main textbook orgchart is empty. Returning empty list.")
        return []

    node_map = {node['id']: node for node in all_textbook_nodes}
    
    parent_to_children_map = {}
    root_node_ids_found = [] # Can be multiple if structure is a forest

    for node in all_textbook_nodes:
        pid = node.get('pid')
        node_id = node['id']
        # Check for root: pid is null, empty string, or the literal string "null"
        if pid is None or pid == "" or str(pid).lower() == "null":
            root_node_ids_found.append(node_id)
        else:
            if pid not in parent_to_children_map:
                parent_to_children_map[pid] = []
            parent_to_children_map[pid].append(node_id)
    
    if not root_node_ids_found:
        logging.error("Critical: Could not identify any root node (pid is null/empty) in the textbook orgchart.")
        # If no root, the concept of "ancestors up to root" is problematic.
        # Depending on requirements, might return empty, all nodes, or try to find nodes with no incoming edges.
        # For now, we'll proceed but ancestor tracing might not work as expected without a clear root.
    else:
        logging.info(f"Identified root node(s): {root_node_ids_found}")


    kept_node_ids = set()

    # 1. Always keep all identified root node(s)
    for root_id in root_node_ids_found:
        kept_node_ids.add(root_id)

    # 2. Identify initial nodes to keep based on target_kp_names matching node['name']
    initially_matched_ids_by_name = set()
    for node_id, node_data in node_map.items():
        if node_data.get('name') in target_kp_names:
            initially_matched_ids_by_name.add(node_id)
            kept_node_ids.add(node_id) # Add these directly
    
    logging.info(f"Initially matched {len(initially_matched_ids_by_name)} nodes by KP name.")

    # 3. Add all descendants of these initially name-matched nodes
    #    We use a queue (deque) for a BFS-like traversal to find all descendants.
    descendant_q = deque(list(initially_matched_ids_by_name)) # Start with nodes matched by name
    
    while descendant_q:
        current_id_for_descendants = descendant_q.popleft()
        
        # Get children of current_id_for_descendants
        if current_id_for_descendants in parent_to_children_map:
            for child_id in parent_to_children_map[current_id_for_descendants]:
                if child_id not in kept_node_ids: # If child not already kept
                    kept_node_ids.add(child_id)   # Keep the child
                    descendant_q.append(child_id) # Add child to queue to process its descendants

    logging.info(f"After adding descendants of name-matched KPs, {len(kept_node_ids)} nodes are marked to be kept.")

    # 4. Add all ancestors of all currently kept nodes up to the root(s)
    #    Iterate over a copy of kept_node_ids as we might modify it during iteration.
    nodes_to_trace_ancestors_for = list(kept_node_ids) 
    for node_id_to_trace_up in nodes_to_trace_ancestors_for:
        current_trace_id = node_id_to_trace_up
        while current_trace_id in node_map: # Ensure node exists
            parent_id = node_map[current_trace_id].get('pid')
            # If parent_id exists, is not null/empty (already handled by root check), and not already kept
            if parent_id and str(parent_id).lower() != "null" and parent_id != "" and parent_id not in kept_node_ids:
                if parent_id in node_map: # Ensure parent itself is a valid node in the chart
                    kept_node_ids.add(parent_id)
                    current_trace_id = parent_id # Continue tracing up from the newly added parent
                else:
                    logging.warning(f"Node {current_trace_id} has parent_id {parent_id} which is not in node_map. Stopping ancestor trace for this path.")
                    break 
            else:
                break # Reached a root, an already kept ancestor, or node with no valid parent_id

    logging.info(f"After adding ancestors, {len(kept_node_ids)} nodes are marked to be kept.")

    # 5. Construct the final list of node objects from the kept_node_ids
    final_filtered_node_list = [node_map[id_] for id_ in kept_node_ids if id_ in node_map]
    
    logging.info(f"Final filtered orgchart will contain {len(final_filtered_node_list)} nodes.")
    return final_filtered_node_list


def main():
    parser = argparse.ArgumentParser(
        description="Filters a textbook's main orgchart based on knowledge points relevant to exam questions."
    )
    parser.add_argument(
        "bookname_dir", # e.g., MyBook_dir or AnotherSubject_1_dir
        type=str,
        help="The directory name for the book in uploads (e.g., 'MyBook_dir'). This is used to locate exam questions and as a base for output, and to derive the textbook_name."
    )
    args = parser.parse_args()
    bookname_dir_arg = args.bookname_dir

    # Determine script directory and base for 'uploads'
    current_script_dir = Path(__file__).parent.resolve()
    uploads_base_dir = current_script_dir / "uploads"

    # Path to the subdirectory for this specific book's processed files (e.g., uploads/MyBook_dir/)
    book_specific_upload_dir = uploads_base_dir / bookname_dir_arg
    # Path to where exam question .txt files are located for this book
    questions_dir_path = book_specific_upload_dir / QUESTIONS_SUBDIR_NAME
    
    # Derive textbook_name (e.g., "MyBook" from "MyBook_dir") for looking up the main orgchart
    if not bookname_dir_arg.endswith("_dir"):
        logging.error(f"Critical Error: The 'bookname_dir' argument ('{bookname_dir_arg}') must end with '_dir'.")
        print(f"Error: 'bookname_dir' argument ('{bookname_dir_arg}') must end with '_dir'. Exiting.")
        return
    textbook_name_for_search = bookname_dir_arg[:-len("_dir")] 

    # Path to the main textbook orgchart file (which is under textbook_name, not bookname_dir)
    # e.g., uploads/MyBook/textbook_information/textbook_orgchart.json
    main_textbook_orgchart_input_path = uploads_base_dir / textbook_name_for_search / TEXTBOOK_INFO_SUBDIR_NAME / TEXTBOOK_ORGCHART_FILENAME
    
    # Output path for the filtered orgchart (will be under the bookname_dir)
    output_info_dir = book_specific_upload_dir / TEXTBOOK_INFO_SUBDIR_NAME
    output_json_file_path = output_info_dir / OUTPUT_FILTERED_ORGCHART_FILENAME

    # --- Sanity Checks ---
    if not DEEPSEEK_API_KEY:
        logging.error("DEEPSEEK_API_KEY not configured. Cannot use LLM. Exiting.")
        print("Error: DEEPSEEK_API_KEY not configured. Exiting.")
        return
    if not book_specific_upload_dir.is_dir():
        logging.error(f"Book directory for questions/output ('{book_specific_upload_dir}') not found. Exiting.")
        print(f"Error: Book directory '{book_specific_upload_dir}' not found. Exiting.")
        return
    if not main_textbook_orgchart_input_path.is_file():
        logging.error(f"Main textbook orgchart (input) not found at: {main_textbook_orgchart_input_path}. Exiting.")
        print(f"Error: Main textbook orgchart file not found at '{main_textbook_orgchart_input_path}'. Exiting.")
        return

    # --- 1. Initialize LLM Client ---
    logging.info(f"Initializing DeepSeekLLM with model: {DEFAULT_DEEPSEEK_MODEL}")
    llm_client = DeepSeekLLM(
        api_key=DEEPSEEK_API_KEY,
        model=DEFAULT_DEEPSEEK_MODEL,
        base_url=DEEPSEEK_BASE_URL
    )

    # --- 2. Collect Exam Text ---
    logging.info(f"Attempting to collect exam text from: {questions_dir_path}")
    concatenated_exam_text = collect_exam_text_from_dir(questions_dir_path)
    if not concatenated_exam_text:
        logging.error("No text collected from exam paper .txt files. Cannot proceed.")
        print("Error: No text found in exam paper files. Exiting.")
        return

    # --- 3. Extract Q&A Pairs from Exam Text using LLM ---
    qa_pairs = []
    try:
        qa_pairs = llm_client.extract_qa_pairs_from_document(
            concatenated_exam_text,
            document_type_tag="Exam Paper Questions" # Tag for the LLM prompt
        )
        logging.info(f"LLM extracted {len(qa_pairs)} Q&A pairs from exam text.")
        if not qa_pairs:
            logging.warning("LLM did not extract any Q&A pairs from the provided exam text.")
    except Exception as e:
        logging.error(f"Error during Q&A extraction with LLM: {e}")
        print(f"Error: Failed to extract Q&A pairs using LLM. Check logs. Exiting. Error: {e}")
        return # Cannot proceed without Q&A to find relevant KPs
        
    # --- 4. Get Relevant KP Names for these Q&A pairs from the textbook ---
    # These names will be used to find corresponding nodes in textbook_orgchart.json
    target_kp_names_from_exam_analysis = get_relevant_kp_names_for_questions(
        qa_pairs,
        textbook_name_for_search, # e.g., "MyBook"
        current_script_dir        # For search_similar to resolve paths
    )
    if not target_kp_names_from_exam_analysis:
        logging.warning("No relevant knowledge point names were identified from exam questions via similarity search. The filtered orgchart might only contain root node(s).")
        # We can still proceed to filter, as the requirement is to keep the root anyway.

    # --- 5. Load Main Textbook Orgchart ---
    all_textbook_nodes_from_json = []
    try:
        with open(main_textbook_orgchart_input_path, 'r', encoding='utf-8') as f:
            all_textbook_nodes_from_json = json.load(f)
        # Ensure it's a list as expected by filter_textbook_orgchart
        if not isinstance(all_textbook_nodes_from_json, list):
            logging.error(f"Content of {main_textbook_orgchart_input_path.name} is not a JSON list as expected. Found type: {type(all_textbook_nodes_from_json)}")
            # Depending on strictness, either raise error or try to handle (e.g. if it's a dict with a 'nodes' key)
            # For now, assuming it must be a list.
            all_textbook_nodes_from_json = [] 
        logging.info(f"Loaded {len(all_textbook_nodes_from_json)} nodes from {main_textbook_orgchart_input_path.name}.")
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {main_textbook_orgchart_input_path.name}: {e}")
        return # Cannot proceed if main orgchart is unreadable
    except Exception as e: # Catch other file IO errors
        logging.error(f"Error loading {main_textbook_orgchart_input_path.name}: {e}")
        return
    
    final_filtered_nodes_list = []
    if not all_textbook_nodes_from_json and target_kp_names_from_exam_analysis:
        logging.warning("Main textbook orgchart is empty, but target KPs were found. Cannot perform filtering.")
    elif not all_textbook_nodes_from_json:
        logging.warning("Main textbook orgchart is empty. Filtered chart will also be empty.")
    else:
        # --- 6. Filter the Textbook Orgchart based on the identified KP names ---
        logging.info(f"Filtering textbook orgchart using {len(target_kp_names_from_exam_analysis)} target KP names...")
        final_filtered_nodes_list = filter_textbook_orgchart(
            all_textbook_nodes_from_json,
            target_kp_names_from_exam_analysis
        )

    # --- 7. Save the Filtered Orgchart JSON ---
    try:
        output_info_dir.mkdir(parents=True, exist_ok=True) # Ensure output directory exists
        with open(output_json_file_path, 'w', encoding='utf-8') as f:
            json.dump(final_filtered_nodes_list, f, ensure_ascii=False, indent=4)
        logging.info(f"Successfully generated and saved filtered questions orgchart to: {output_json_file_path}")
        print(f"Successfully generated filtered questions orgchart: {output_json_file_path}")
    except Exception as e:
        logging.error(f"Error saving the filtered orgchart JSON to {output_json_file_path}: {e}")
        print(f"Error: Could not save the output JSON file. Check logs. Error: {e}")

if __name__ == "__main__":
    main()