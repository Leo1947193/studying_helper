# images_and_ocr.py
import os
import json # 用于读取配置文件
from pathlib import Path
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError, PDFSyntaxError
from skimage import io as skio
# 如果需要更复杂的scikit-image处理，可以导入其他模块:
# from skimage import filters, color, transform, exposure
from paddleocr import PaddleOCR
import logging
import torch # 导入 torch 用于在配置要求使用GPU时发出警告

# --- (可选) Poppler 配置 ---
# 对于 WINDOWS 或 Poppler 不在 PATH 中的情况:
#    取消下面一行的注释，并设置到你的 Poppler 'bin' 目录的正确路径。
#    在 Windows 上，请在字符串前使用 'r' 以处理原始路径。
# poppler_bin_path = r"C:\path\to\your\poppler-x.x.x\bin"
poppler_bin_path = None  # 如果 Poppler 在系统 PATH 中或在具有标准安装的 Linux/macOS 上，则设置为 None

# --- 基础 PaddleOCR 配置 (use_gpu 将从 config.json 读取) ---
# lang='ch' 支持中英文混合识别。
# use_angle_cls=True 会启用文本角度分类，有助于识别旋转文本。
# show_log=False 可以减少 PaddleOCR 的日志输出。
ocr_config_base = {
    "use_angle_cls": True,
    "lang": 'ch',
    "show_log": False
    # "use_gpu" 会从 config.json 动态添加
}

# 设置日志记录，以便更好地跟踪 PaddleOCR 的内部消息（可选）
# logging.basicConfig(level=logging.INFO) # 可以设置为 logging.DEBUG 获取更详细信息

def load_config(config_file_path):
    """
    从指定的 JSON 文件加载配置。

    Args:
        config_file_path (Path): 配置文件的完整路径。

    Returns:
        dict or None: 如果加载成功则返回配置字典，否则返回 None。
    """
    print(f"正在从 '{config_file_path}' 加载配置...")
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # 验证必要的键是否存在且类型正确
        required_keys = {
            "textbook_name": str,
            "images_dir": str,
            "text_dir": str,
            "use_gpu": bool
        }
        for key, expected_type in required_keys.items():
            if key not in config_data:
                print(f"错误：配置文件 '{config_file_path}' 中缺少键 '{key}'。")
                return None
            if not isinstance(config_data[key], expected_type):
                print(f"错误：配置文件 '{config_file_path}' 中键 '{key}' 的类型不正确。期望类型：{expected_type}, 实际类型：{type(config_data[key])}。")
                return None
        
        print("配置加载成功。")
        return config_data
    except FileNotFoundError:
        print(f"错误：配置文件 '{config_file_path}' 未找到。")
        return None
    except json.JSONDecodeError as e:
        print(f"错误：解析配置文件 '{config_file_path}' 失败：{e}")
        return None
    except Exception as e:
        print(f"加载配置文件时发生未知错误：{e}")
        return None

def convert_pdf_to_images(pdf_full_path, images_output_full_path, poppler_path_config):
    """
    将 PDF 文件转换为图像。

    Args:
        pdf_full_path (Path): PDF 文件的完整路径。
        images_output_full_path (Path): 保存图像的输出目录的完整路径。
        poppler_path_config (str or None): Poppler bin 目录的路径，如果需要的话。

    Returns:
        bool: 如果转换成功则返回 True，否则返回 False。
    """
    print(f"\n--- PDF 到图像转换开始 ---")
    print(f"寻找 PDF: {pdf_full_path}")
    print(f"图像输出目录: {images_output_full_path}")

    if not pdf_full_path.is_file():
        print(f"错误：输入 PDF 文件未在以下位置找到： '{pdf_full_path}'")
        return False

    images_output_full_path.mkdir(parents=True, exist_ok=True)
    print(f"已确保图像输出目录 '{images_output_full_path}' 存在。")

    try:
        print(f"\n开始将 '{pdf_full_path.name}' 转换为内存中的图像...")
        images = convert_from_path(
            pdf_path=pdf_full_path,
            fmt='jpeg',  # 内部转换时仍指定期望的格式
            poppler_path=poppler_path_config
            # dpi=300  # 取消注释以设置分辨率 (每英寸点数)
        )
        print(f"转换完成。正在保存 {len(images)} 张图像...")

        for i, image in enumerate(images):
            page_num_str = str(i + 1).zfill(4) # 例如：0001, 0002
            output_filename = f"page_{page_num_str}.jpg"
            output_filepath = images_output_full_path / output_filename
            image.save(output_filepath, 'JPEG')

        print(f"\n成功保存 {len(images)} 张 JPG 图像。")
        print(f"图像保存在: '{images_output_full_path}'")
        print(f"--- PDF 到图像转换结束 ---")
        return True

    except PDFInfoNotInstalledError:
        print("\n--- PDF 转换错误 ---")
        print("未找到 Poppler 或 Poppler 不在 PATH 中。 `pdf2image` 需要 Poppler。")
        print("请为你的操作系统安装 Poppler:")
        print("  - macOS: brew install poppler")
        print("  - Debian/Ubuntu: sudo apt-get install poppler-utils")
        print("  - Windows: 下载 Poppler，解压它，然后将其 'bin' 目录添加到 PATH")
        print("             或者在此脚本中设置 'poppler_bin_path' 变量。")
        print("-----------------------")
        return False
    except (PDFPageCountError, PDFSyntaxError) as e:
        print(f"\n--- PDF 转换错误 ---")
        print(f"处理 '{pdf_full_path.name}' 失败。它可能已损坏、受密码保护或不是有效的 PDF。")
        print(f"详细信息: {e}")
        print("-----------------------")
        return False
    except FileNotFoundError as e: # 这个应该由顶部的检查捕获，但以防万一
        print(f"\n--- PDF 转换错误 ---")
        print(e)
        print("请确保脚本中的 PDF 文件名正确，并且文件位于同一目录中。")
        print("-----------------------")
        return False
    except Exception as e:
        print(f"\n--- PDF 到图像转换过程中发生意外错误 ---")
        print(e)
        print("--------------------------------------")
        return False

def perform_ocr_on_images(images_input_full_path, texts_output_full_path, ocr_engine_config):
    """
    对指定目录中的图像执行 OCR。

    Args:
        images_input_full_path (Path): 包含图像文件的输入目录的完整路径。
        texts_output_full_path (Path): 保存提取文本的输出目录的完整路径。
        ocr_engine_config (dict): PaddleOCR 的完整配置字典 (已包含 use_gpu 设置)。

    Returns:
        bool: 如果 OCR 处理（至少尝试了所有图像）完成则返回 True，否则返回 False。
    """
    print(f"\n--- OCR 处理开始 ---")
    print(f"图像输入目录: {images_input_full_path}")
    print(f"文本输出目录: {texts_output_full_path}")

    if not images_input_full_path.is_dir():
        print(f"错误：图像输入目录 '{images_input_full_path}' 未找到。")
        return False

    texts_output_full_path.mkdir(parents=True, exist_ok=True)
    print(f"已确保文本输出目录 '{texts_output_full_path}' 存在。")

    # 1. 初始化 PaddleOCR
    try:
        ocr_engine = PaddleOCR(**ocr_engine_config)
        if ocr_engine_config.get("use_gpu", False):
            print("PaddleOCR 初始化成功 (尝试使用 GPU，根据配置)。")
        else:
            print("PaddleOCR 初始化成功 (使用 CPU，根据配置)。")
    except Exception as e:
        print(f"初始化 PaddleOCR 时发生错误: {e}")
        print("请确保已正确安装 PaddleOCR 及其依赖项 (如 PaddlePaddle)。")
        print("如果尝试使用 GPU，请确保 paddlepaddle-gpu 版本已安装且 CUDA 环境配置正确。")
        print("你可能需要运行: pip install paddleocr paddlepaddle (或 paddlepaddle-gpu)")
        return False

    # 2. 遍历图像目录中的文件
    try:
        all_files = os.listdir(images_input_full_path)
        # 获取所有以 "page_" 开头并以 ".jpg" 结尾的文件，并排序
        image_files = sorted([f for f in all_files if f.lower().startswith("page_") and f.lower().endswith(".jpg")])
    except Exception as e:
        print(f"列出 '{images_input_full_path}' 中的文件时发生错误: {e}")
        return False

    if not image_files:
        print(f"在 '{images_input_full_path}' 中没有找到符合 'page_xxxx.jpg' 格式的图像。")
        return True # 没有文件可处理，但不算是一个失败

    print(f"找到以下图像文件进行 OCR: {image_files}")

    for image_filename in image_files:
        image_path = images_input_full_path / image_filename
        print(f"\n正在处理图像: {image_path}")

        # 3. 使用 scikit-image 读取和（可选）处理图像
        processed_image_data = None
        try:
            image_data_from_skimage = skio.imread(image_path)
            processed_image_data = image_data_from_skimage
        except FileNotFoundError:
            print(f"错误: 图像文件 '{image_path}' 未找到（在OCR阶段）。")
            continue # 跳过当前图像，处理下一个
        except Exception as e:
            print(f"使用 scikit-image 读取或处理图像 '{image_filename}' 时发生错误: {e}")
            continue

        # 4. 使用 PaddleOCR 进行文字识别
        if processed_image_data is None:
            print(f"由于之前的错误，跳过对 '{image_filename}' 的 OCR 处理。")
            continue
        try:
            ocr_result = ocr_engine.ocr(processed_image_data, cls=ocr_engine_config.get("use_angle_cls", True))
            extracted_text_lines = []
            if ocr_result and ocr_result[0] is not None:
                for line_info_list in ocr_result:
                    for line_info in line_info_list:
                        extracted_text_lines.append(line_info[1][0]) # 提取文本内容
            else:
                print(f"图像 '{image_filename}' 未检测到文本或 OCR 处理时发生内部错误。")

            final_text = "\n".join(extracted_text_lines)
            if final_text:
                print(f"从 '{image_filename}' 提取的文本 (前100字符): \n{final_text[:100].strip()}...")
            else:
                print(f"从 '{image_filename}' 未提取到文本。")

        except Exception as e:
            print(f"对 '{image_filename}' 执行 OCR 时发生错误: {e}")
            continue

        # 5. 保存提取的文本到 .txt 文件
        base_name_no_ext = image_filename.rsplit('.', 1)[0] # 例如 "page_0001"
        output_txt_basename = base_name_no_ext.replace("_", "") # "page0001"
        output_txt_filename = f"{output_txt_basename}.txt"
        output_txt_filepath = texts_output_full_path / output_txt_filename

        try:
            with open(output_txt_filepath, "w", encoding="utf-8") as f:
                f.write(final_text)
            print(f"文本已保存到: {output_txt_filepath}")
        except Exception as e:
            print(f"将文本写入 '{output_txt_filepath}' 时发生错误: {e}")
            
    print(f"\n--- OCR 处理结束 ---")
    return True

def main():
    """
    主函数，协调 PDF 到图像的转换和图像的 OCR 处理。
    """
    print("===== 开始 PDF 处理和 OCR 流程 =====")
    try:
        # 获取脚本所在的目录的绝对路径
        script_dir = Path(__file__).parent.resolve()
    except NameError: # 处理在某些IDE或直接执行时 __file__ 未定义的情况
        script_dir = Path(os.getcwd()).resolve()
    print(f"脚本运行目录: {script_dir}")

    # 1. 加载配置
    config_file_path = script_dir / "config.json"
    config = load_config(config_file_path)
    if not config:
        print("错误：无法加载配置文件或配置不完整。程序中止。")
        print("===== 流程结束 (配置错误) =====")
        return

    # 2. 从配置中提取并构建路径
    pdf_file_from_config = config["textbook_name"]
    image_dir_from_config = config["images_dir"]
    text_dir_from_config = config["text_dir"]
    use_gpu_from_config = config["use_gpu"]

    pdf_full_path = script_dir / pdf_file_from_config
    images_output_full_path = script_dir / image_dir_from_config
    texts_output_full_path = script_dir / text_dir_from_config

    # 3. 步骤 1: PDF 转图像
    # poppler_bin_path 仍然是脚本顶部的全局常量
    pdf_conversion_successful = convert_pdf_to_images(
        pdf_full_path,
        images_output_full_path,
        poppler_bin_path 
    )

    if not pdf_conversion_successful:
        print("\nPDF 到图像的转换失败。中止后续 OCR 处理。")
        print("===== 流程结束 (PDF转换错误) =====")
        return

    # 4. 步骤 2: 准备 OCR 配置并对图像进行 OCR
    final_ocr_config = ocr_config_base.copy() # 从基础配置开始
    final_ocr_config["use_gpu"] = use_gpu_from_config # 从 config.json 设置 use_gpu

    if use_gpu_from_config:
        print("配置提示：将尝试使用 GPU 进行 OCR (根据 config.json)。")
        if not torch.cuda.is_available():
            print("警告：config.json 设置为使用 GPU，但 CUDA 当前不可用或 PyTorch 未检测到。")
            print("       PaddleOCR 可能会回退到 CPU，或者如果 paddlepaddle-gpu 未正确安装/配置，则可能失败。")
            print("       请确保已安装 paddlepaddle-gpu 并正确配置了 CUDA 环境。")
        else:
            # 进一步检查，确保 paddlepaddle 本身能用 GPU (如果 paddlepaddle-gpu 版本装对了)
            try:
                import paddle
                if not paddle.is_compiled_with_cuda():
                    print("警告：config.json 设置为使用 GPU，但安装的 PaddlePaddle 版本未编译 CUDA 支持。")
                elif paddle.device.get_device() == 'cpu': # 检查默认设备
                     print("警告：config.json 设置为使用 GPU，PaddlePaddle 支持 CUDA，但当前默认设备是 CPU。PaddleOCR 仍可能尝试使用 GPU。")
            except ImportError:
                print("警告：无法导入 paddle 模块以进行详细的 GPU 支持检查。")
            except Exception as e:
                print(f"检查 PaddlePaddle GPU 支持时发生未知错误：{e}")

    else:
        print("配置提示：将使用 CPU 进行 OCR (根据 config.json)。")

    ocr_processing_successful = perform_ocr_on_images(
        images_output_full_path,
        texts_output_full_path,
        final_ocr_config # 使用包含来自 config.json 的 GPU 设置的配置
    )

    if not ocr_processing_successful:
        print("\nOCR 处理过程中发生错误或未完全成功。")
    else:
        print("\n所有图像的 OCR 处理已尝试完毕。")
        
    print("===== 流程结束 =====")

if __name__ == "__main__":
    main()
