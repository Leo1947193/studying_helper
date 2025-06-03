# notebook-backend/images_and_ocr.py

import json
from pathlib import Path
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
import logging
import os
import sys

# 设置基本日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Windows用户：请在此处配置Poppler路径 ---
POPPLER_PATH = None


# 如果需要，取消下一行的注释并替换为您的Poppler路径
# POPPLER_PATH = r"C:\path\to\poppler-x.y.z\Library\bin" # <--- 替换为您的Poppler路径

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
        images = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)
        logging.info(f"PDF转换成功，提取了 {len(images)} 页。")
    except Exception as e:
        logging.error(f"PDF转换失败: {e}")
        logging.error("如果您使用的是Linux/macOS，请确保已安装poppler并且其路径已添加到PATH环境变量中。")
        logging.error("在Windows上，您可能需要在 images_and_ocr.py 中指定 POPPLER_PATH。")
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
    """
    ensure_dir_exists(text_output_dir)

    logging.info("正在初始化 PaddleOCR (CPU版本, lang='ch')。这可能需要一些时间...")
    try:
        ocr_engine = PaddleOCR(use_textline_orientation=True, lang='ch')
        logging.info("PaddleOCR 初始化成功。")
    except Exception as e:
        logging.error(f"初始化 PaddleOCR 失败: {e}")
        sys.exit(1)
        return

    image_files = sorted(images_source_dir.glob("page_*.jpg"))
    if not image_files:
        logging.warning(f"在目录 {images_source_dir} 中未找到匹配 'page_*.jpg' 格式的JPG图像。")
        sys.exit(1)
        return

    logging.info(f"开始对 {len(image_files)} 张图像进行OCR处理...")
    for image_path in image_files:
        logging.info(f"正在处理图像OCR: {image_path.name}")
        try:
            result = ocr_engine.ocr(str(image_path))
            logging.info(f"DEBUG OCR RAW RESULT for {image_path.name}: {result}")

            extracted_text_parts = []
            if result and isinstance(result, list) and len(result) > 0:
                image_ocr_data = result[0]  # 获取第一张图片的结果字典

                if isinstance(image_ocr_data, dict) and 'rec_texts' in image_ocr_data:
                    extracted_text_parts = image_ocr_data['rec_texts']
                    logging.info(
                        f"DEBUG OCR: OCR for {image_path.name} extracted {len(extracted_text_parts)} text lines from 'rec_texts'.")
                else:
                    logging.warning(
                        f"DEBUG OCR: OCR for {image_path.name} result[0] did not contain 'rec_texts' key or was not a dict: {image_ocr_data}.")
            else:
                logging.warning(
                    f"DEBUG OCR: OCR for {image_path.name} returned no identifiable text (result was empty or not a list).")

            extracted_text = "\n".join(extracted_text_parts)

            page_num_str = image_path.stem.split('_')[-1]
            text_filename = text_output_dir / f"page{page_num_str}.txt"

            with open(text_filename, "w", encoding="utf-8") as f:
                f.write(extracted_text)

            if extracted_text.strip():
                logging.info(f"已保存OCR文本至: {text_filename} (包含 {len(extracted_text)} 字符)。")
            else:
                logging.warning(f"已创建空OCR文本文件: {text_filename} (可能未识别到文本)。")

        except Exception as e:
            logging.error(f"处理图像 {image_path.name} OCR时发生错误: {e}")

    logging.info("OCR处理已完成。")


# 修改 main 函数以接收两个参数
def main(textbook_base_name_unique: str, original_filename: str):  # <--- 接收两个参数
    """
    主函数，用于编排指定教材的整个OCR流程。
    Args:
        textbook_base_name_unique (str): 唯一的教材基础名 (例如 "Essay", "Essay_1")。
        original_filename (str): 原始上传的文件名 (例如 "Essay.pdf")。
    """
    if not textbook_base_name_unique or not original_filename:
        logging.error("错误: 未提供教材名称或原始文件名。")
        sys.exit(1)

    script_dir = Path(__file__).resolve().parent

    images_subdir_name = "images_dir"
    text_subdir_name = "text_dir"

    # 构建特定教材的处理根目录路径 (使用唯一的教材基础名作为目录名)
    base_textbook_processing_dir = script_dir / "uploads" / f"{textbook_base_name_unique}_dir"  # <--- 使用唯一的目录名

    ensure_dir_exists(base_textbook_processing_dir)

    # 构建PDF文件的完整路径 (在唯一的目录下，使用原始文件名)
    pdf_file_path = base_textbook_processing_dir / original_filename  # <--- 使用原始文件名

    images_output_dir_path = base_textbook_processing_dir / images_subdir_name
    text_output_dir_path = base_textbook_processing_dir / text_subdir_name

    logging.info(f"开始处理教材: {textbook_base_name_unique} (原始文件: {original_filename})")
    logging.info(f"脚本目录: {script_dir}")
    logging.info(f"教材处理根目录: {base_textbook_processing_dir}")
    logging.info(f"预期的PDF路径: {pdf_file_path}")
    logging.info(f"图像输出目录: {images_output_dir_path}")
    logging.info(f"文本输出目录: {text_output_dir_path}")

    if not pdf_file_path.exists():
        logging.error(f"教材PDF文件未找到: {pdf_file_path}")
        logging.error(f"请确保 '{original_filename}' 文件位于目录: {base_textbook_processing_dir} 中。")
        sys.exit(1)

    conversion_successful = convert_pdf_to_images(pdf_file_path, images_output_dir_path)

    if not conversion_successful:
        logging.error(f"由于PDF '{pdf_file_path.name}' 转换失败，脚本已停止。")
        sys.exit(1)

    ocr_images_in_dir(images_output_dir_path, text_output_dir_path)

    logging.info(f"教材 '{textbook_base_name_unique}' 处理完毕。")
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) == 3:  # <--- 期望两个参数
        textbook_base_name_unique_arg = sys.argv[1]
        original_filename_arg = sys.argv[2]

        main(textbook_base_name_unique_arg, original_filename_arg)
    else:
        print("用法: python images_and_ocr.py <unique_base_name> <original_filename>")
        print("示例: python images_and_ocr.py Essay_1 Essay.pdf")
        sys.exit(1)
