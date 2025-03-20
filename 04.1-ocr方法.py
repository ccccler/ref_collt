import pytesseract
from PIL import Image

# 打开用户上传的图片
image_path = "/mnt/data/BreastCancer_2024.V5_EN_NCCN_120.png"
image = Image.open(image_path)

# 使用OCR提取文本
extracted_text = pytesseract.image_to_string(image)

# 输出提取的文本以便分析
extracted_text
