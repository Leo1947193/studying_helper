import os
from skimage import io as skio
# 如果需要更复杂的scikit-image处理，可以导入其他模块:
# from skimage import filters, color, transform, exposure
from paddleocr import PaddleOCR
import logging

image_dir="marxism_theory_images"
# 设置日志记录，以便更好地跟踪 PaddleOCR 的内部消息（可选）
logging.basicConfig(level=logging.INFO) # 可以设置为 logging.DEBUG 获取更详细信息

def process_images():
    # 1. 设置路径
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError: # 处理在某些IDE或直接执行时 __file__ 未定义的情况
        script_dir = os.getcwd()

    images_dir = os.path.join(script_dir, image_dir)
    text_dir = os.path.join(script_dir, "text_dir")

    # 如果 text_dir 不存在，则创建它
    if not os.path.exists(text_dir):
        os.makedirs(text_dir)
        print(f"已创建目录: {text_dir}")

    # 2. 初始化 PaddleOCR
    # lang='ch' 支持中英文混合识别。
    # use_angle_cls=True 会启用文本角度分类，有助于识别旋转文本。
    # use_gpu=False 表示使用CPU。如果安装了paddlepaddle-gpu并想用GPU，请设为True。
    try:
        ocr_engine = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=True, show_log=False)
        print("PaddleOCR 初始化成功。")
    except Exception as e:
        print(f"初始化 PaddleOCR 时发生错误: {e}")
        print("请确保已正确安装 PaddleOCR 及其依赖项 (如 PaddlePaddle)。")
        print("您可能需要运行: pip install paddleocr paddlepaddle")
        return

    # 3. 遍历图像目录中的文件
    try:
        # 获取所有文件并排序，确保按数字顺序处理
        all_files = os.listdir(images_dir)
        image_files = sorted([f for f in all_files if f.lower().startswith("page_") and f.lower().endswith(".jpg")])
    except FileNotFoundError:
        print(f"错误: 目录 '{images_dir}' 未找到。")
        print("请确保 'images' 目录与脚本位于同一位置，并且包含您的图像文件。")
        return
    except Exception as e:
        print(f"列出 '{images_dir}' 中的文件时发生错误: {e}")
        return

    if not image_files:
        print(f"在 '{images_dir}' 中没有找到符合 'page_xxxx.jpg' 格式的图像。")
        return

    print(f"找到以下图像文件: {image_files}")

    for image_filename in image_files:
        image_path = os.path.join(images_dir, image_filename)
        print(f"\n正在处理图像: {image_path}")

        # 4. 使用 scikit-image 读取和处理图像
        processed_image_data = None
        try:
            # 使用 scikit-image 读取图像数据 (返回 NumPy 数组)
            image_data_from_skimage = skio.imread(image_path)

            # --- scikit-image 图像处理占位符 ---
            # 在这里，您可以添加特定的 scikit-image 图像处理步骤。
            # 例如：灰度化、滤波、对比度增强等。
            # from skimage.color import rgb2gray
            # from skimage import filters
            #
            # if image_data_from_skimage.ndim == 3 and image_data_from_skimage.shape[2] == 4: # 如果是RGBA图像
            #     from skimage.color import rgba2rgb
            #     image_data_from_skimage = rgba2rgb(image_data_from_skimage)
            #
            # if image_data_from_skimage.ndim == 3: # 如果是彩色图像
            #     processed_image_data = rgb2gray(image_data_from_skimage)
            # else: # 如果已经是灰度图像
            #     processed_image_data = image_data_from_skimage
            #
            # processed_image_data = filters.gaussian(processed_image_data, sigma=0.5)
            # processed_image_data = exposure.equalize_adapthist(processed_image_data) # 自适应直方图均衡

            # 当前，我们将直接使用 scikit-image 加载的原始图像数据 (NumPy 数组)
            # PaddleOCR 可以接受图像路径或 NumPy 数组。为了确保 "用scikit-image处理后"，我们传递 NumPy 数组。
            processed_image_data = image_data_from_skimage

        except FileNotFoundError:
            print(f"错误: 图像文件 '{image_path}' 未找到。")
            continue # 跳过当前图像，处理下一个
        except Exception as e:
            print(f"使用 scikit-image 读取或处理图像 '{image_filename}' 时发生错误: {e}")
            continue

        # 5. 使用 PaddleOCR 进行文字识别
        if processed_image_data is None:
            print(f"由于之前的错误，跳过对 '{image_filename}' 的 OCR 处理。")
            continue
        try:
            # 将 scikit-image 处理后的图像数据 (NumPy 数组) 传递给 PaddleOCR
            # cls=True 表示使用方向分类器
            ocr_result = ocr_engine.ocr(processed_image_data, cls=True)

            extracted_text_lines = []
            if ocr_result and ocr_result[0] is not None: # 检查结果是否有效且不为 [None]
                # ocr_result 是一个列表，通常包含一个元素，该元素又是一个包含所有识别行的列表
                # 例如: [[line1_info, line2_info, ...]]
                # line_info 结构: [bbox, (text, confidence)]
                for line_info_list in ocr_result: # 遍历每个检测到的文本块/页 (通常只有一个)
                    for line_info in line_info_list:
                        extracted_text_lines.append(line_info[1][0]) # 提取文本内容
            else:
                print(f"图像 '{image_filename}' 未检测到文本或 OCR 处理时发生内部错误。")

            final_text = "\n".join(extracted_text_lines)
            if final_text:
                 print(f"从 '{image_filename}' 提取的文本 (前200字符): \n{final_text[:200]}...")
            else:
                 print(f"从 '{image_filename}' 未提取到文本。")


        except Exception as e:
            print(f"对 '{image_filename}' 执行 OCR 时发生错误: {e}")
            continue

        # 6. 保存提取的文本到 .txt 文件
        # 文件名转换: page_0001.jpg -> page0001.txt
        base_name_no_ext = os.path.splitext(image_filename)[0] # 例如 "page_0001"
        # 移除 "page_" 中的下划线，得到 "page0001"
        output_txt_basename = base_name_no_ext.replace("_", "") # "page0001"
        output_txt_filename = f"{output_txt_basename}.txt"
        output_txt_filepath = os.path.join(text_dir, output_txt_filename)

        try:
            with open(output_txt_filepath, "w", encoding="utf-8") as f:
                f.write(final_text)
            print(f"文本已保存到: {output_txt_filepath}")
        except Exception as e:
            print(f"将文本写入 '{output_txt_filepath}' 时发生错误: {e}")

if __name__ == "__main__":
    process_images()
    print("\n所有图像处理完毕。")