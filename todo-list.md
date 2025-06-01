# @app.route('/api/upload', methods=['POST'])的改变
上传文件时就依次:
1. images_and_ocr.py
2. get_catalog.py
3. get_segment.py
4. get_orgchart.py
5. embedding.py
然后在获取回答时直接遍历catalog_with_segments.json找到其中知识点

# orgchart渲染引擎
