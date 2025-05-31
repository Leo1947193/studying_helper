# 环境配置
我使用的是wsl2 ubuntu22.04, cuda 12.1.1, conda环境, python3.10

## python包的安装
1. 安装pytorch
'''sh
conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia
'''

2. 安装paddlepaddle(cpu版)
'''sh
pip install paddlepaddle==3.0.0 -f https://www.paddlepaddle.org.cn/whl/linux/cpu/openblas/stable.html --no-cache-dir
'''

3. 安装paddleocr
'''sh
pip install paddleocr==2.7
'''

4. 安装faiss-gpu
'''sh
conda install faiss-gpu -c pytorch
'''

5. 安装numpy(一般来说，到这一步numpy已经安装好了)
'''sh
conda install numpy
'''

6. 安装transformers
'''sh
conda install -c conda-forge transformers
'''

7. 安装dashscope, openai, scikit-image, pdf2image
'''sh
pip install dashscope openai scikit-image pdf2image

# 各部分代码说明
## config.json
各个python脚本会从这个json文件中读取数据
    "bert_model": "bert-base-chinese", #embedding时用到的bert微调模型
    "book_root_title":"马克思主义基本原理概论", #整本教材mermaid代码中根节点的名称
    "catalog": "catalog.json", #目录
    "catalog_segments": "catalog_with_segments.json", #包含知识点的目录
    "combined_mermaid":"combined_mermaid.json", #整本书的mermaid代码
    "embedding_batch_size": 32,
    "faiss_index_filename": "knowledge_points.index",
    "images_dir":"textbook_images_dir", #每页的图像存放的文件夹
    "llm_model": "qwen-max", #调用的大模型，阿里系不同大模型调用方式不同，不要轻易修改
    "mapping_file_suffix": ".mapping.json", 
    "mermaid_dir":"mermaid_dir", #存放未解析的mermaid代码的文件夹
    "pages_for_catalog": 20, #为获取目录所上传的前n页
    "parsed_mermaid_dir":"parsed_mermaid_dir", #解析后的可以渲染的mermaid代码
    "search_top_k": 5, #找相似知识点中返回的前k相似的知识点
    "textbook_name":"marxism_theory.pdf", #教材pdf名称
    "text_dir":"textbook_text_dir", #每页文本的目录
    "use_gpu":true #是否使用gpu

## images_