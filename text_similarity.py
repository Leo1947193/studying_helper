# text_similarity.py (Refactored)
import pandas as pd
import torch
from transformers import AutoModel, AutoTokenizer
import faiss
import numpy as np
import os
import sys # For printing errors/warnings

class TextSimilarityFinder:
    """
    Handles loading models, encoding text, building/loading FAISS index,
    and finding similar texts for mathematical content.
    """
    def __init__(self, model_name='tbs17/MathBERT', index_file='mathbert_faiss_gpu_index_refactored.bin'):
        """
        Initializes the finder, sets up the device, and loads the model/tokenizer.

        Args:
            model_name (str): The name of the Hugging Face model to use.
            index_file (str): The path to save/load the FAISS index file.
        """
        self.model_name = model_name
        self.index_file = index_file
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")

        self.tokenizer = None
        self.model = None
        self.index = None # The active FAISS index (CPU or GPU)
        self.index_cpu = None # Always keep a copy of the CPU index for saving
        self.texts = None # List of original texts used for the index
        self.original_indices = None # Mapping from index position (0,1,..) to original df index

        self._load_model_and_tokenizer()

    def _load_model_and_tokenizer(self):
        """Loads the Hugging Face model and tokenizer."""
        print(f"Loading model and tokenizer: {self.model_name}...")
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            # Load model and move to appropriate device
            self.model = AutoModel.from_pretrained(self.model_name).to(self.device)
            self.model.eval() # Set model to evaluation mode
            print(f"Successfully loaded model and tokenizer.")
        except Exception as e:
            print(f"Error loading model or tokenizer: {e}", file=sys.stderr)
            raise # Re-raise the exception to stop initialization

    def encode_texts(self, texts_to_encode, batch_size=32):
        """
        Encodes a list of texts into vectors using the loaded model.

        Args:
            texts_to_encode (list): A list of strings to encode.
            batch_size (int): The batch size for encoding.

        Returns:
            np.ndarray: A numpy array of embeddings (float32).
        """
        if not self.model or not self.tokenizer:
             raise ValueError("Model and tokenizer must be loaded before encoding.")

        all_embeddings = []
        print(f"Encoding {len(texts_to_encode)} texts in batches of {batch_size}...")
        # Determine max length from model config or default to 512
        try:
             max_len = self.model.config.max_position_embeddings
        except AttributeError:
             print("Warning: Could not determine max_length from model config, using 512.", file=sys.stderr)
             max_len = 512

        # Process texts in batches
        for i in range(0, len(texts_to_encode), batch_size):
            batch_texts = texts_to_encode[i:i + batch_size]
            # Tokenize batch with padding and truncation
            encoded_input = self.tokenizer(
                batch_texts,
                padding=True,          # Pad sequences to max length in batch or max_length
                truncation=True,       # Truncate sequences longer than max_length
                return_tensors='pt',   # Return PyTorch tensors
                max_length=max_len     # Max sequence length for truncation/padding
            ).to(self.device) # Move tensors to the correct device

            # Perform inference without gradient calculation
            with torch.no_grad():
                model_output = self.model(**encoded_input)

            # --- Mean Pooling Calculation ---
            # Get last hidden state embeddings
            embeddings = model_output.last_hidden_state
            # Get attention mask (1 for real tokens, 0 for padding)
            attention_mask = encoded_input['attention_mask']
            # Expand mask dimensions to match embeddings
            mask_expanded = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
            # Sum embeddings where mask is 1 (zeros out padding)
            sum_embeddings = torch.sum(embeddings * mask_expanded, 1)
            # Count number of non-padding tokens per sequence
            sum_mask = torch.clamp(mask_expanded.sum(1), min=1e-9) # Avoid division by zero
            # Calculate mean by dividing sum by count
            mean_embeddings = sum_embeddings / sum_mask
            # --- End Mean Pooling ---

            # Append batch results (move to CPU, detach, convert to numpy float32)
            all_embeddings.append(mean_embeddings.cpu().detach().numpy().astype('float32'))
            # Optional: Print progress
            # print(f"  Encoded batch {i//batch_size + 1}/{(len(texts_to_encode) + batch_size - 1)//batch_size}")


        print("Finished encoding.")
        # Concatenate embeddings from all batches
        return np.concatenate(all_embeddings)

    def build_or_load_index(self, texts_for_index, original_indices_map=None, force_rebuild=False):
        """
        Builds a FAISS index from text embeddings or loads it from file.

        Args:
            texts_for_index (list): The list of texts corresponding to the vectors
                                     that will be/are in the index.
            original_indices_map (dict, optional): A dictionary mapping the list index
                                                  (0, 1, ...) to the original DataFrame index.
            force_rebuild (bool): If True, always rebuild the index even if a file exists.
        """
        self.texts = texts_for_index # Store the texts associated with the index vectors
        self.original_indices = original_indices_map # Store the mapping

        # Attempt to load index if it exists and not forcing rebuild
        if not force_rebuild and os.path.exists(self.index_file):
            print(f"Attempting to load existing FAISS index from {self.index_file}...")
            try:
                # Load the CPU index from disk
                self.index_cpu = faiss.read_index(self.index_file)
                print(f"Successfully loaded CPU index with {self.index_cpu.ntotal} vectors.")

                # Validate loaded index size against provided texts (optional but recommended)
                if self.index_cpu.ntotal != len(self.texts):
                     print(f"Warning: Loaded index size ({self.index_cpu.ntotal}) does not match "
                           f"number of provided texts ({len(self.texts)}). Rebuilding index.", file=sys.stderr)
                     # Force rebuild if sizes mismatch
                     self._build_index()
                else:
                    # Attempt to move the loaded index to GPU if available
                    if self.device.type == 'cuda':
                        try:
                            print("Moving loaded index to GPU...")
                            res = faiss.StandardGpuResources() # GPU resources
                            # Transfer CPU index to GPU (device 0)
                            self.index = faiss.index_cpu_to_gpu(res, 0, self.index_cpu)
                            print("FAISS index ready on GPU.")
                        except Exception as e:
                            print(f"Warning: Could not move loaded FAISS index to GPU ({e}). Using CPU index.", file=sys.stderr)
                            self.index = self.index_cpu # Fallback to CPU index
                    else:
                        self.index = self.index_cpu # Use CPU index directly if no GPU
                        print("FAISS index ready on CPU.")
                return # Index loaded successfully (or rebuilt due to size mismatch)
            except Exception as e:
                print(f"Warning: Failed to load index from {self.index_file} ({e}). Rebuilding index.", file=sys.stderr)
                self._build_index() # Build index if loading fails
        else:
            # Build index if file doesn't exist or force_rebuild is True
            if force_rebuild:
                 print("Forcing index rebuild...")
            else:
                 print(f"Index file '{self.index_file}' not found. Building new index...")
            self._build_index()

    def _build_index(self):
        """Internal helper function to build the FAISS index."""
        if not self.texts:
            raise ValueError("Cannot build index without texts. Call build_or_load_index with texts_for_index.")

        # Encode the texts to get embeddings
        text_embeddings = self.encode_texts(self.texts)
        if text_embeddings.shape[0] == 0:
             print("Error: No embeddings generated. Cannot build index.", file=sys.stderr)
             return

        # Get the dimension of the vectors
        d = text_embeddings.shape[1]
        print(f"Building FAISS index with vector dimension {d}...")

        # Create a flat L2 index on CPU first
        self.index_cpu = faiss.IndexFlatL2(d)

        # Add the embeddings to the CPU index
        self.index_cpu.add(text_embeddings)
        print(f"CPU FAISS index populated with {self.index_cpu.ntotal} vectors.")

        # Save the newly built CPU index
        try:
            faiss.write_index(self.index_cpu, self.index_file)
            print(f"CPU FAISS index saved to {self.index_file}")
        except Exception as e:
            print(f"Warning: Could not save CPU FAISS index: {e}", file=sys.stderr)

        # Attempt to move the new index to GPU if available
        if self.device.type == 'cuda':
            try:
                print("Moving new index to GPU...")
                res = faiss.StandardGpuResources()
                self.index = faiss.index_cpu_to_gpu(res, 0, self.index_cpu)
                print("FAISS index ready on GPU.")
            except Exception as e:
                print(f"Warning: Could not move new FAISS index to GPU ({e}). Using CPU index.", file=sys.stderr)
                self.index = self.index_cpu # Fallback to CPU index
        else:
            self.index = self.index_cpu # Use CPU index directly
            print("FAISS index ready on CPU.")


    def find_similar(self, query_text, k=5):

        if self.index is None or self.texts is None:
            print("Error: Index must be built or loaded before searching.", file=sys.stderr)
            return []
        if not self.model or not self.tokenizer:
             print("Error: Model and tokenizer must be loaded before searching.", file=sys.stderr)
             return []

        # Encode the query text
        # Wrap query in a list as encode_texts expects a list
        query_embedding = self.encode_texts([query_text], batch_size=1)

        # Perform the search on the active index (CPU or GPU)
        # FAISS search expects a 2D numpy array of queries
        try:
            distances, indices = self.index.search(query_embedding, k)
        except Exception as e:
             print(f"Error during FAISS search: {e}", file=sys.stderr)
             return []

        # Process and return results
        results = []
        if indices.size > 0: # Check if FAISS returned any indices
            # indices[0] contains the results for the first (and only) query
            for i in range(len(indices[0])):
                idx = indices[0][i] # The index position in self.texts
                dist = distances[0][i] # The L2 distance

                # Check if the index is valid and within the bounds of our text list
                if idx != -1 and 0 <= idx < len(self.texts):
                    # Retrieve the original DataFrame index using the mapping if available
                    original_df_index = self.original_indices.get(idx, None) if self.original_indices else idx

                    results.append({
                        "distance": float(dist), # Ensure distance is standard float
                        "index_position": int(idx),
                        "original_df_index": original_df_index,
                        "text": self.texts[idx]
                    })
                else:
                    # Stop processing if FAISS returns -1 or an out-of-bounds index
                    break
        return results

# --- Example Main Block (Optional: For direct testing of this script) ---
if __name__ == "__main__":
    # Configuration for direct execution
    # <<< --- ADJUST THESE PATHS IF RUNNING DIRECTLY --- >>>
    CSV_FILE_PATH = '/home/leo/studying_helper/output_test2.csv' # Example CSV for index building
    INDEX_FILE_PATH = 'mathbert_faiss_gpu_index_refactored.bin' # Index file name

    print("--- Running text_similarity.py Directly (Example Usage) ---")

    print("\nInitializing TextSimilarityFinder...")
    try:
        # Initialize the class
        finder = TextSimilarityFinder(index_file=INDEX_FILE_PATH)

        # --- Load Data and Filter for Indexing ---
        print(f"\nLoading data for index from: {CSV_FILE_PATH}")
        try:
            df = pd.read_csv(CSV_FILE_PATH)
        except FileNotFoundError:
            print(f"Error: File not found at {CSV_FILE_PATH}", file=sys.stderr)
            exit()

        # Filter for questions to build the index
        df_questions = df[df['type'] == 'Question'].copy()
        if df_questions.empty:
            print(f"Error: No records with type == 'Question' found in {CSV_FILE_PATH}.", file=sys.stderr)
            exit()

        # Prepare texts and the index mapping
        texts_for_index = df_questions['text'].tolist()
        original_indices_map = {i: idx for i, idx in enumerate(df_questions.index)}
        print(f"Found {len(texts_for_index)} question texts for index.")

        # --- Build or Load Index ---
        # Pass the texts and the index mapping
        finder.build_or_load_index(texts_for_index, original_indices_map=original_indices_map)

        # --- Example Search ---
        if finder.index and finder.texts:
            # Example query (replace with a relevant one if needed)
            query = "Assume the function z is implicitly defined by the equation F(x2+yz,y2+zx)=0, where F(u,v) has continuous first-order partial derivatives, and ∂u∂F​ and ∂v∂F​ are not both zero.Prove that:x(y2−zx)∂x∂z​+y(x2−yz)∂y∂z​=z(x2+y2)"
            print(f"\n--- Example Search ---")
            print(f"Query: '{query[:100]}...'")
            similar_results = finder.find_similar(query, k=3) # Find top 3

            print("\nMost similar texts found:")
            if similar_results:
                for result in similar_results:
                    print(f"  Distance: {result['distance']:.4f}")
                    print(f"  Index Pos: {result['index_position']}")
                    print(f"  Original DF Index: {result['original_df_index']}")
                    print(f"  Text: {result['text'][:150]}...") # Print start of text
                    print("-" * 20)
            else:
                print("  No similar results found.")
        else:
            print("\nIndex or texts not available for searching.")

    except Exception as e:
         print(f"\nAn error occurred during direct execution: {e}", file=sys.stderr)

    print("\n--- Direct execution finished ---")

