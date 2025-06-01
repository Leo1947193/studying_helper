from pathlib import Path
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
import logging
import os
import sys

# --- Constants defined as per requirements ---
BERT_MODEL = "bert-base-chinese"
CATALOG_FILENAME = "catalog.json"
CATALOG_SEGMENTS_FILENAME = "catalog_with_segments.json"
EMBEDDING_BATCH_SIZE = 32
FAISS_INDEX_FILENAME = "knowledge_points.index"
IMAGES_SUBDIR_NAME = "textbook_images_dir"  # Name for the image subdirectory
LLM_MODEL = "qwen-max"
MAPPING_FILE_SUFFIX = ".mapping.json"
ORGCHART_SUBDIR_NAME = "orgchart_dir"
TEXTBOOK_ORGCHART_FILENAME = "textbook_orgchart.json"
PAGES_FOR_CATALOG = 30
SEARCH_TOP_K = 3
TEXT_SUBDIR_NAME = "textbook_text_dir"      # Name for the text subdirectory

# Other operational constants for this script
PDF_CONVERSION_DPI = 300
OCR_LANGUAGE = 'ch'
# --- End of defined constants ---

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
    # Example output_dir: .../uploads/<textbook_name>/textbook_information/textbook_images_dir/
    ensure_dir_exists(output_dir)
    logging.info(f"正在将 PDF '{pdf_path}' 转换为图像，保存至 '{output_dir}'...")

    try:
        images = convert_from_path(pdf_path, dpi=PDF_CONVERSION_DPI)
    except Exception as e:
        logging.error(f"PDF转换失败: {e}")
        logging.error("如果您使用的是Linux/macOS，请确保已安装poppler并且其路径已添加到PATH环境变量中。")
        logging.error("在Windows上，您可能需要在 convert_from_path 中指定 poppler_path。")
        return False

    if not images:
        logging.warning(f"未能从 {pdf_path} 中提取任何图像。")
        return False

    for i, image in enumerate(images):
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
    # Example text_output_dir: .../uploads/<textbook_name>/textbook_information/textbook_text_dir/
    ensure_dir_exists(text_output_dir)

    logging.info(f"正在初始化 PaddleOCR (CPU版本, lang='{OCR_LANGUAGE}')。这可能需要一些时间...")
    try:
        ocr_engine = PaddleOCR(use_angle_cls=True, lang=OCR_LANGUAGE, use_gpu=False, show_log=False)
    except Exception as e:
        logging.error(f"初始化 PaddleOCR 失败: {e}")
        return

    image_files = sorted(images_source_dir.glob("page_*.jpg"))
    if not image_files:
        logging.warning(f"在目录 {images_source_dir} 中未找到匹配 'page_*.jpg' 格式的JPG图像。")
        return

    logging.info(f"开始对 {len(image_files)} 张图像进行OCR处理...")
    for image_path in image_files:
        logging.info(f"正在处理图像OCR: {image_path.name}")
        try:
            result = ocr_engine.ocr(str(image_path), cls=True)

            extracted_text_parts = []
            if result and result[0] is not None:
                for line_info in result[0]:
                    if line_info and len(line_info) == 2 and isinstance(line_info[1], tuple) and len(line_info[1]) == 2:
                        extracted_text_parts.append(line_info[1][0])

            extracted_text = "\n".join(extracted_text_parts)

            page_num_str = image_path.stem.split('_')[-1]
            text_filename = text_output_dir / f"page{page_num_str}.txt"

            with open(text_filename, "w", encoding="utf-8") as f:
                f.write(extracted_text)
            logging.info(f"已保存OCR文本至: {text_filename}")

        except Exception as e:
            logging.error(f"处理图像 {image_path.name} OCR时发生错误: {e}")

    logging.info("OCR处理已完成。")

def main(textbook_name_cleaned: str):
    """
    主函数，用于编排指定教材的整个OCR流程。
    Args:
        textbook_name_cleaned (str): 教材的名称 (不含.pdf扩展名)。
                                     例如 "book1"
    """
    if not textbook_name_cleaned:
        logging.error("错误: 未提供教材名称。")
        return

    script_dir = Path(__file__).resolve().parent

    # Base directory for this specific textbook's uploads.
    # Example: /a/b/c/uploads/book1/ (if script is in /a/b/c/ and textbook_name_cleaned is "book1")
    textbook_upload_dir = script_dir / "uploads" / textbook_name_cleaned
    ensure_dir_exists(textbook_upload_dir)

    # Full path to the PDF file.
    # Example: /a/b/c/uploads/book1/book1.pdf
    pdf_file_path = textbook_upload_dir / f"{textbook_name_cleaned}.pdf"

    # Directory where all processed information (images, text subdirectories) will be stored.
    # Example: /a/b/c/uploads/book1/textbook_information/
    processed_info_storage_dir = textbook_upload_dir / "textbook_information"

    # Path for image outputs, using the global constant IMAGES_SUBDIR_NAME.
    # Example: /a/b/c/uploads/book1/textbook_information/textbook_images_dir/
    images_output_path = processed_info_storage_dir / IMAGES_SUBDIR_NAME

    # Path for text outputs, using the global constant TEXT_SUBDIR_NAME.
    # Example: /a/b/c/uploads/book1/textbook_information/textbook_text_dir/
    text_output_path = processed_info_storage_dir / TEXT_SUBDIR_NAME

    logging.info(f"开始处理教材: {textbook_name_cleaned}")
    logging.info(f"脚本目录: {script_dir}")
    logging.info(f"教材文件根目录 (PDF expected here): {textbook_upload_dir}")
    logging.info(f"预期的PDF路径: {pdf_file_path}")
    logging.info(f"处理后信息存储根目录: {processed_info_storage_dir}")
    logging.info(f"图像输出目录: {images_output_path}")
    logging.info(f"文本输出目录: {text_output_path}")

    if not pdf_file_path.exists():
        logging.error(f"教材PDF文件未找到: {pdf_file_path}")
        logging.error(f"请确保 '{textbook_name_cleaned}.pdf' 文件位于目录: {textbook_upload_dir} 中。")
        return

    conversion_successful = convert_pdf_to_images(pdf_file_path, images_output_path)

    if not conversion_successful:
        logging.error(f"由于PDF '{pdf_file_path.name}' 转换失败，脚本已停止。")
        return

    ocr_images_in_dir(images_output_path, text_output_path)

    logging.info(f"教材 '{textbook_name_cleaned}' 处理完毕。")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        textbook_name_arg = sys.argv[1]
        if textbook_name_arg.lower().endswith(".pdf"):
            textbook_name_arg = textbook_name_arg[:-4]

        if not textbook_name_arg or "/" in textbook_name_arg or "\\" in textbook_name_arg:
            print("错误：提供的教材名称无效。请提供不含路径分隔符的有效名称。")
            print("用法: python images_and_ocr.py <textbook_name_without_extension>")
        else:
            main(textbook_name_arg)
    else:
        print("用法: python images_and_ocr.py <textbook_name_without_extension>")
        print("示例: python images_and_ocr.py my_textbook")