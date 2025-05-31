# Studying Helper - 教材学习助手

## 项目简介

Studying Helper 是一个旨在辅助用户学习和理解教材内容的工具套件。它通过结合光学字符识别（OCR）、大语言模型（LLM）、文本嵌入和向量检索等技术，实现对PDF教材的深度处理和分析，主要功能包括将教材内容文本化、自动生成目录、提炼核心知识点、构建知识点检索系统以及生成章节内容的思维导图。

## 主要功能

* **PDF处理与OCR**：将PDF格式的教材转换为逐页图片，并利用OCR技术提取每页的文本内容。
* **智能目录生成**：通过LLM分析教材前N页的文本，自动识别并生成层级化的目录结构。
* **核心知识点提取**：针对教材的每个章节，利用LLM进行语义理解和切分，提炼出关键知识点。
* **知识点嵌入与检索**：使用BERT等模型为知识点生成向量嵌入，并构建FAISS索引，支持通过自然语言查询快速找到相关的知识点。
* **Mermaid思维导图生成**：为教材的每个章节内容自动生成Mermaid格式的思维导图代码，方便用户可视化理解章节结构和主要内容。

## 技术栈

* **核心语言**：Python 3.10
* **深度学习框架**：PaddlePaddle, PyTorch
* **OCR**：PaddleOCR
* **自然语言处理**：Transformers (Hugging Face), BERT模型
* **向量检索**：FAISS
* **大语言模型服务**：DashScope (阿里云灵积模型服务)
* **PDF处理**：pdf2image, Poppler
* **其他库**：Numpy, scikit-image, openai (可选，根据实际LLM调用)

## 环境配置

本项目在以下环境测试通过：
* 操作系统：WSL2 Ubuntu 22.04
* CUDA版本：12.1.1 (部分脚本支持GPU，可配置)
* Python版本：3.10 (通过Conda管理)

**详细安装步骤：**

1.  **安装Conda**：
    请根据您的操作系统从 [Anaconda官网](https://www.anaconda.com/products/distribution) 或 [Miniconda官网](https://docs.conda.io/en/latest/miniconda.html) 下载并安装Conda。

2.  **创建并激活Conda环境**：
    ```bash
    conda create -n studying_helper_env python=3.10 -y
    conda activate studying_helper_env
    ```

3.  **安装PyTorch** (如果需要使用GPU进行嵌入或FAISS-GPU)：
    ```bash
    # CUDA 12.1 版本
    conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia
    ```
    如果仅使用CPU，可以安装CPU版本的PyTorch。

4.  **安装PaddlePaddle (CPU版)**：
    本项目中的OCR和部分LLM辅助功能可能基于PaddlePaddle的CPU版本。
    ```bash
    pip install paddlepaddle==3.0.0 -f [https://www.paddlepaddle.org.cn/whl/linux/cpu/openblas/stable.html](https://www.paddlepaddle.org.cn/whl/linux/cpu/openblas/stable.html) --no-cache-dir
    ```
    *注意：此命令安装的是针对通用CPU的OpenBLAS版本，以避免 "Illegal instruction" 错误。*

5.  **安装PaddleOCR**：
    项目配置为使用PaddleOCR 2.7版本。
    ```bash
    pip install paddleocr==2.7.0.3 # 或者使用 pip install paddleocr~=2.7.0
    ```

6.  **安装FAISS**：
    * **GPU版本** (如果您的环境支持CUDA且 `config.json` 中 `use_gpu` 设置为 `true`):
        ```bash
        conda install faiss-gpu -c pytorch
        ```
    * **CPU版本**:
        ```bash
        conda install faiss-cpu -c pytorch
        ```

7.  **安装transformers**:
    ```bash
    conda install -c conda-forge transformers
    ```

8.  **安装其他Python包**：
    ```bash
    pip install numpydashscope openai scikit-image pdf2image
    ```

8.  **安装Poppler** (用于`pdf2image`)：
    在WSL2 Ubuntu环境下：
    ```bash
    sudo apt update
    sudo apt install poppler-utils -y
    ```

9.  **设置环境变量**：
    本项目使用DashScope SDK调用大语言模型，需要设置API密钥。
    ```bash
    export DASHSCOPE_API_KEY="YOUR_ACTUAL_DASHSCOPE_API_KEY"
    ```
    为了永久生效，可以将上述命令添加到您的 `~/.bashrc` 或 `~/.zshrc` 文件中，并执行 `source ~/.bashrc` (或 `source ~/.zshrc`)。

## 配置文件说明 (`config.json`)

`config.json` 文件是整个项目的中央控制枢纽，各个Python脚本会从中读取所需参数。请根据您的实际情况修改此文件。

```json
{
    "bert_model": "bert-base-chinese", 
    // 字符串，指定用于文本嵌入的BERT模型名称（例如Hugging Face上的模型标识符）。
    "book_root_title":"马克思主义基本原理概论", 
    // 字符串，整本教材在最终合并的Mermaid思维导图中的根节点显示的标题。
    "catalog": "catalog.json", 
    // 字符串，由 get_catalog.py 生成的、包含教材原始目录结构（可能未包含页码偏移校正）的JSON文件名。
    "catalog_segments": "catalog_with_segments.json", 
    // 字符串，由 get_segment.py 生成的、在目录结构叶子节点中增加了"knowledge_points"（知识点列表）的JSON文件名。
    "combined_mermaid":"combined_mermaid.json", 
    // 字符串，由 merge_mermaid.py 生成的、包含整本书所有章节合并后的Mermaid思维导图代码的JSON文件名。
    "embedding_batch_size": 32, 
    // 整数，在 embedding.py 中生成文本嵌入时，每批处理的文本数量。
    "faiss_index_filename": "knowledge_points.index", 
    // 字符串，由 embedding.py 生成的FAISS索引文件的名称。
    "images_dir":"textbook_images_dir", 
    // 字符串，由 images_and_ocr.py 生成的、存放教材每一页图像（JPG格式）的文件夹名称。
    "llm_model": "qwen-max", 
    // 字符串，指定调用DashScope时使用的大语言模型名称。不同模型API调用方式可能不同，请谨慎修改。
    "mapping_file_suffix": ".mapping.json", 
    // 字符串，由 embedding.py 生成的、用于存储FAISS索引ID到原始知识点文本映射的JSON文件的后缀。完整文件名会是 faiss_index_filename + mapping_file_suffix。
    "mermaid_dir":"mermaid_dir", 
    // 字符串，由 get_mermaid.py 生成的、存放每个叶子章节未经解析（转义字符未处理）的Mermaid代码（JSON格式）的文件夹名称。
    "pages_for_catalog": 20, 
    // 整数，在 get_catalog.py 中，指定使用教材OCR结果的前多少页文本来分析和生成目录。
    "parsed_mermaid_dir":"parsed_mermaid_dir", 
    // 字符串，由 parse_mermaid.py 生成的、存放已解析（转义字符已处理）并可直接渲染的Mermaid代码（.mmd格式）的文件夹名称。
    "search_top_k": 5, 
    // 整数，在 search_similar.py 中进行知识点相似度搜索时，返回最相似的前k个结果。
    "textbook_name":"marxism_theory.pdf", 
    // 字符串，需要处理的教材的PDF文件名。此文件应放置在项目的根目录或 images_and_ocr.py 脚本指定的查找路径。
    "text_dir":"textbook_text_dir", 
    // 字符串，由 images_and_ocr.py 生成的、存放教材每一页OCR文本结果（.txt格式）的文件夹名称。
    "use_gpu":true 
    // 布尔值 (true/false)，指定部分脚本（如 embedding.py, search_similar.py）是否尝试使用GPU。如果为true但无可用GPU，通常会自动回退到CPU。
}

## 脚本文件说明
项目包含多个Python脚本，各司其职，共同完成教材处理和分析的流水线。所有脚本都从项目根目录下的`config.json`文件读取配置。

### `images_and_ocr.py`:

功能: 负责处理输入的PDF教材。

首先，使用 pdf2image 库将PDF的每一页转换为JPEG图像，并保存到 config.json 中 images_dir 指定的目录。图像按页码顺序命名（如 page_0001.jpg）。

然后，使用 PaddleOCR 对这些图像进行光学字符识别，提取每页的文本内容，并保存为 .txt 文件到 config.json 中 text_dir 指定的目录（如 page0001.txt）。

OCR默认使用中文模型（lang='ch'）和CPU。

### `get_catalog.py`:

功能: 智能生成教材的目录结构。

读取 config.json 中 text_dir 指定目录下的前 pages_for_catalog 页的OCR文本内容。

将这些文本内容整合后发送给DashScope的大语言模型（由 llm_model 指定）。

LLM根据预设的提示（Prompt）分析文本，提取章节标题和在文本中出现的原始页码，并生成层级化的JSON格式目录结构。此结构还会特殊标记出整个目录中的“第一个叶子节点”实际起始于哪个文本文件名。

脚本进一步处理LLM返回的JSON，计算页面偏移量（基于第一个叶子节点的原始页码和实际起始文件页码），并将校正后的实际起始和结束文件名（如 page0005.txt）添加到目录结构中每个节点的 actual_starting_page 和 actual_ending_page 字段。

最终的目录结构保存到 config.json 中 catalog 指定的JSON文件。

### `get_segment.py`:

功能: 提取教材各章节的核心知识点。

读取 get_catalog.py 生成的目录文件 (config.json 中的 catalog)。

遍历目录中的每个“叶子节点”（最细粒度的章节）。

根据叶子节点记录的 actual_starting_page 和 actual_ending_page，从 text_dir 中读取相应的OCR文本内容。

将章节标题和文本内容发送给DashScope的大语言模型。

LLM根据预设的提示对文本进行预处理、清理，并进行语义切分，提取核心知识点列表。

脚本将LLM返回的知识点列表（字符串数组）就地添加到原始目录数据中对应叶子节点的 knowledge_points 字段。

最终包含知识点的完整目录结构保存到 config.json 中 catalog_segments 指定的JSON文件。

### `embedding.py`:

功能: 为知识点生成向量嵌入并构建检索索引。

读取 get_segment.py 生成的包含知识点的目录文件 (config.json 中的 catalog_segments)。

递归遍历目录结构，提取所有叶子节点中的 knowledge_points 字符串。

使用指定的BERT模型（config.json 中的 bert_model）为每个唯一的知识点文本生成向量嵌入。支持GPU（如果 use_gpu 为 true 且环境可用）。

使用生成的嵌入向量构建一个FAISS索引（IndexFlatL2 类型），用于高效的相似度搜索。

将FAISS索引保存到 config.json 中 faiss_index_filename 指定的文件。

同时，创建一个映射文件（文件名由 faiss_index_filename 和 mapping_file_suffix 组成），该文件是一个JSON列表，按顺序存储了所有被索引的知识点原文。FAISS返回的索引ID即对应此列表的下标。

### `search_similar.py`:

功能: 根据用户提问检索相似知识点。

提供一个命令行接口，接受用户输入的问题字符串。

加载 embedding.py 生成的FAISS索引文件和知识点映射文件。

使用与嵌入时相同的BERT模型为用户的问题生成查询向量。

在FAISS索引中搜索与查询向量最相似的前 k 个知识点（k 由 config.json 中的 search_top_k 或命令行参数指定）。

输出检索到的知识点原文及其与查询的距离（L2距离，越小越相似）。

### `get_mermaid.py`:

功能: 为教材的每个最小单元章节生成Mermaid思维导图代码。

读取 `get_catalog.py` 生成的目录文件 (config.json 中的 catalog)。

遍历目录中的每个“叶子节点”。

读取该叶子章节对应的OCR文本内容。

将章节标题和文本内容发送给DashScope的大语言模型。

LLM根据预设的提示（包含Mermaid代码生成规则，如使用 \\n 代表换行，\\t 代表缩进）生成该章节内容的Mermaid思维导图代码。

LLM返回的结果是一个JSON对象，其中包含 mermaid_code 字段（值为包含转义字符的Mermaid代码字符串）以及章节元数据。

每个叶子章节生成的JSON对象分别保存到 config.json 中 mermaid_dir 指定的目录，文件名基于章节ID（如 1_1.json, 1_2_1.json）。

### `parse_mermaid.py`:

功能: 解析并转换Mermaid代码。

读取 get_mermaid.py 输出目录 (mermaid_dir) 中的所有JSON文件。

对于每个JSON文件，提取 mermaid_code 字段中的字符串。

将字符串中的转义字符 \\n 替换为实际的换行符，将 \\t 替换为实际的制表符。

处理后的、可以直接渲染的Mermaid代码保存为 .mmd 文件到 config.json 中 parsed_mermaid_dir 指定的目录，文件名与输入的JSON文件（不含后缀）相同。

### `merge_mermaid.py`:

功能: 合并所有单个章节的Mermaid代码，生成全书的思维导图。

读取 get_catalog.py 生成的目录文件 (catalog) 和 parse_mermaid.py 输出目录 (parsed_mermaid_dir) 中的所有 .mmd 文件。

基于目录的层级结构，递归地将每个章节（特别是叶子节点对应章节）的 .mmd 文件内容整合起来。

在整合时，会根据目录层级自动添加正确的缩进。

最终生成一个单一的 .mmd 文件，包含一个以 config.json 中 book_root_title 为根节点的、代表整本书内容的巨大Mermaid思维导图。该文件保存到 config.json 中 combined_mermaid 指定的文件名。

