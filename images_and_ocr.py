import json
from pathlib import Path
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
import logging
import os

# 设置基本日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def ensure_dir_exists(dir_path: Path):
    """确保目录存在，如果不存在则创建它。"""
    if not dir_path.exists():
        logging.info(f"正在创建目录: {dir_path}")
        dir_path.mkdir(parents=True, exist_ok=True)
    elif not dir_path.is_dir():
        logging.error(f"错误: {dir_path} 已存在但不是一个目录。")
        raise NotADirectoryError(f"{dir_path} 已存在但不是一个目录。")

def convert_pdf_to_images(pdf_path: Path, output_dir: Path):
    """
    将PDF文件转换为JPEG图像，每页一张图像。
    图像命名为 page_0001.jpg, page_0002.jpg, 等。
    """
    ensure_dir_exists(output_dir)
    logging.info(f"正在将 PDF '{pdf_path}' 转换为图像，保存至 '{output_dir}'...")
    
    try:
        # 使用常见的DPI进行转换
        images = convert_from_path(pdf_path, dpi=300) 
    except Exception as e:
        logging.error(f"PDF转换失败: {e}")
        logging.error("如果您使用的是Linux/macOS，请确保已安装poppler并且其路径已添加到PATH环境变量中。")
        logging.error("在Windows上，您可能需要在 convert_from_path 中指定 poppler_path。")
        return False

    if not images:
        logging.warning(f"未能从 {pdf_path} 中提取任何图像。")
        return False

    for i, image in enumerate(images):
        # 图像文件名格式为 page_XXXX.jpg
        image_filename = output_dir / f"page_{i + 1:04d}.jpg"
        try:
            image.save(image_filename, "JPEG")
            logging.info(f"已保存图像: {image_filename}")
        except Exception as e:
            logging.error(f"无法保存图像 {image_filename}: {e}")
    
    logging.info("PDF到图像的转换已完成。")
    return True

def ocr_images_in_dir(images_source_dir: Path, text_output_dir: Path):
    """
    对 images_source_dir 中的所有JPG图像执行OCR，
    并将提取的文本保存到 text_output_dir 中的 .txt 文件。
    文本文件命名为 page0001.txt, page0002.txt, 等。
    """
    ensure_dir_exists(text_output_dir)
    
    # 初始化 PaddleOCR - CPU版本，默认使用中文模型。
    logging.info("正在初始化 PaddleOCR (CPU版本, lang='ch')。这可能需要一些时间...")
    try:
        # 使用中文模型 (lang='ch')，不使用GPU，不显示PaddleOCR的日志
        ocr_engine = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False, show_log=False)
    except Exception as e:
        logging.error(f"初始化 PaddleOCR 失败: {e}")
        return

    # 查找所有 'page_*.jpg' 格式的图像文件并排序
    image_files = sorted(images_source_dir.glob("page_*.jpg"))
    if not image_files:
        logging.warning(f"在目录 {images_source_dir} 中未找到匹配 'page_*.jpg' 格式的JPG图像。")
        return

    logging.info(f"开始对 {len(image_files)} 张图像进行OCR处理...")
    for image_path in image_files:
        logging.info(f"正在处理图像OCR: {image_path.name}")
        try:
            # 对单张图片进行OCR
            result = ocr_engine.ocr(str(image_path), cls=True)
            
            extracted_text_parts = []
            # PaddleOCR的ocr方法返回一个列表，每个元素对应一个识别结果列表
            # 对于单张图片，result[0]包含了所有识别出的文本行信息
            if result and result[0] is not None: 
                for line_info in result[0]:
                    # line_info 的结构是 [box_coordinates, (text, confidence_score)]
                    if line_info and len(line_info) == 2 and isinstance(line_info[1], tuple) and len(line_info[1]) == 2:
                        extracted_text_parts.append(line_info[1][0]) # 提取文本内容
            
            extracted_text = "\n".join(extracted_text_parts) # 将所有文本行合并
            
            # 根据图像文件名确定输出文本文件名 (例如: page_0001.jpg -> page0001.txt)
            page_num_str = image_path.stem.split('_')[-1] # 从 "page_0001" 中提取 "0001"
            text_filename = text_output_dir / f"page{page_num_str}.txt"
            
            with open(text_filename, "w", encoding="utf-8") as f:
                f.write(extracted_text)
            logging.info(f"已保存OCR文本至: {text_filename}")

        except Exception as e:
            logging.error(f"处理图像 {image_path.name} OCR时发生错误: {e}")
            
    logging.info("OCR处理已完成。")

def main():
    """主函数，用于编排整个OCR流程。"""
    # 获取脚本所在的目录
    script_dir = Path(__file__).resolve().parent
    config_path = script_dir / "config.json"

    if not config_path.exists():
        logging.error(f"配置文件未找到: {config_path}")
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f: # 指定utf-8编码读取config.json
            config = json.load(f)
    except json.JSONDecodeError:
        logging.error(f"从 {config_path} 解码JSON时出错。")
        return
    except Exception as e:
        logging.error(f"无法读取配置文件 {config_path}: {e}")
        return

    # 从配置中获取值并构建绝对路径
    images_dir_name = config.get("images_dir")
    text_dir_name = config.get("text_dir")
    textbook_filename = config.get("textbook_name")

    if not all([images_dir_name, text_dir_name, textbook_filename]):
        logging.error("config.json 文件中缺少一个或多个必需字段: 'images_dir', 'text_dir', 'textbook_name'")
        return

    # 构建相对于脚本目录的绝对路径
    images_dir_path = script_dir / images_dir_name
    text_dir_path = script_dir / text_dir_name
    # 假设PDF文件与脚本在同一目录
    pdf_file_path = script_dir / textbook_filename 

    if not pdf_file_path.exists():
        logging.error(f"教材PDF文件未找到: {pdf_file_path}")
        logging.error(f"请确保 '{textbook_filename}' 文件位于目录: {script_dir} 中。")
        return

    # 步骤1: 将PDF转换为图像
    conversion_successful = convert_pdf_to_images(pdf_file_path, images_dir_path)
    
    if not conversion_successful:
        logging.error("由于PDF转换失败，脚本已停止。")
        return

    # 步骤2: 对生成的图像执行OCR
    ocr_images_in_dir(images_dir_path, text_dir_path)

    logging.info("脚本执行完毕。")

if __name__ == "__main__":
    main()
