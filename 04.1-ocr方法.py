import pytesseract
from PIL import Image
import os
import pandas as pd

def extract_text_from_images(folder_path):
    # 存储结果的列表
    results = []
    
    # 遍历文件夹中的所有文件
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.png'):
            # 构建完整的图片路径
            image_path = os.path.join(folder_path, filename)
            
            try:
                # 打开图片
                image = Image.open(image_path)
                
                # 使用OCR提取文本
                extracted_text = pytesseract.image_to_string(image)
                
                # 将结果添加到列表中
                results.append({
                    'Image_Name': filename,
                    'Extracted_Text': extracted_text
                })
                
                print(f"处理完成: {filename}")
                
            except Exception as e:
                print(f"处理 {filename} 时出错: {str(e)}")
    
    # 创建DataFrame并保存为Excel
    df = pd.DataFrame(results)
    excel_path = os.path.join('test_ocr_results.xlsx')
    df.to_excel(excel_path, index=False)
    print(f"\nOCR结果已保存到: {excel_path}")

# 使用示例
folder_path = "./ref_collt/pictest"  # 替换为你的图片文件夹路径
extract_text_from_images(folder_path)
