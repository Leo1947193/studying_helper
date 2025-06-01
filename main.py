# main.py
import os
import sys
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, TEMPLATES_FILE
from llm_interface import DeepSeekLLM
from data_manager import TemplateMethodManager
from text_summarizer import TextSummarizer
from question_rewriter import QuestionRewriter


def main():
    if not DEEPSEEK_API_KEY:
        print("错误: DeepSeek API Key 未设置。请检查 .env 文件或 config.py。")
        print("请访问 DeepSeek 官网获取 API Key: https://platform.deepseek.com/usage/api-keys")
        sys.exit(1)

    # 初始化各个模块
    llm_client = DeepSeekLLM(api_key=DEEPSEEK_API_KEY, model=DEEPSEEK_MODEL)
    template_manager = TemplateMethodManager(file_path=TEMPLATES_FILE)
    text_summarizer = TextSummarizer(llm_client=llm_client)
    question_rewriter = QuestionRewriter(llm_client=llm_client, template_manager=template_manager)

    print("--- DeepSeek QA 助手 ---")

    while True:
        print("\n请选择功能:")
        print("1. 梳理文本段落重点")
        print("2. 从问答中提取出题模板与答题方法 (并保存)")
        print("3. 查看所有已保存的出题模板与答题方法")
        print("4. 根据选定的答题方法重写答案")
        print("5. 退出")

        choice = input("请输入你的选择 (1-5): ")

        if choice == '1':
            print("\n--- 文本段落重点梳理 ---")
            paragraph = input("请输入要梳理的文本段落 (输入 'END' 结束): \n")
            if paragraph.strip().upper() == 'END':
                continue

            print("正在调用 DeepSeek 梳理重点...")
            summary_result = text_summarizer.summarize(paragraph)
            if "error" in summary_result:
                print(f"梳理失败: {summary_result['error']}")
            else:
                print("\n梳理出的重点:")
                if "main_points" in summary_result and isinstance(summary_result["main_points"], list):
                    for i, point in enumerate(summary_result["main_points"]):
                        print(f"{i + 1}. {point}")
                else:
                    print("未找到有效重点，原始LLM响应可能不符合预期格式。")
                    print(f"原始响应: {summary_result.get('raw_response', 'N/A')}")


        elif choice == '2':
            print("\n--- 提取出题模板与答题方法 ---")
            question = input("请输入题目: ")
            answer = input("请输入答案: ")

            print("正在调用 DeepSeek 提取模板与方法...")
            extraction_result = question_rewriter.extract_and_save_qa_template_method(question, answer)
            if "error" in extraction_result:
                print(f"提取失败: {extraction_result['error']}")
            else:
                print("\n提取并保存成功！")
                print(f"  出题模板: {extraction_result.get('question_template')}")
                print(f"  答题方法: {extraction_result.get('answer_method')}")

        elif choice == '3':
            print("\n--- 所有已保存的出题模板与答题方法 ---")
            templates_methods = question_rewriter.list_all_templates_methods()
            if not templates_methods:
                print("目前没有保存任何出题模板和答题方法。")
            else:
                for i, item in enumerate(templates_methods):
                    print(f"\n--- 索引: {i} ---")
                    print(f"  出题模板: {item.get('question_template', 'N/A')}")
                    print(f"  答题方法: {item.get('answer_method', 'N/A')}")

        elif choice == '4':
            print("\n--- 重写答案 ---")
            templates_methods = question_rewriter.list_all_templates_methods()
            if not templates_methods:
                print("没有可用的答题方法，请先提取或添加。")
                continue

            print("当前已保存的答题方法:")
            for i, item in enumerate(templates_methods):
                print(f"  [{i}] 模板: {item.get('question_template', 'N/A')}")
                print(f"        方法: {item.get('answer_method', 'N/A')}")

            try:
                method_index = int(input("请输入要选择的答题方法的索引号: "))
            except ValueError:
                print("无效的索引号，请输入数字。")
                continue

            question_to_rewrite = input("请输入需要重写的原始题目: ")
            original_answer = input("请输入该题目的原始答案: ")

            print("正在调用 DeepSeek 重写答案...")
            rewritten_answer = question_rewriter.rewrite_answer_with_selected_method(
                question_to_rewrite, original_answer, method_index
            )
            print("\n--- 重写后的答案 ---")
            print(rewritten_answer)

        elif choice == '5':
            print("感谢使用，再见！")
            break
        else:
            print("无效的选择，请重新输入。")


if __name__ == "__main__":
    main()
