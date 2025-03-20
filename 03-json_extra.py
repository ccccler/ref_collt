import pandas as pd
import json

def process_json_data(input_file, output_file, json_column_name):
    # 读取Excel文件
    df = pd.read_excel(input_file)
    
    # 创建空列表来存储解析后的数据
    parsed_data = {
        'title': [],
        'authors': [],
        'journal': [],
        'year': [],
        'url': []
    }
    
    # 遍历JSON字符串并解析
    for json_str in df[json_column_name]:
        try:
            data = json.loads(json_str)
            parsed_data['title'].append(data.get('title', ''))
            parsed_data['authors'].append(data.get('authors', ''))
            parsed_data['journal'].append(data.get('journal', ''))
            parsed_data['year'].append(data.get('year', ''))
            parsed_data['url'].append(data.get('url', ''))
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            # 如果解析失败，添加空值
            for key in parsed_data:
                parsed_data[key].append('')
    
    # 创建新的DataFrame
    result_df = pd.DataFrame(parsed_data)
    
    # 保存到新的Excel文件
    result_df.to_excel(output_file, index=False)
    print(f"数据已成功保存到 {output_file}")

# 使用示例
input_file = "./ref_collt/all_processed_references.xlsx"  # 替换为你的输入文件名
output_file = "./ref_collt/分列processed_references.xlsx"  # 替换为你想要的输出文件名
json_column_name = "model_response"  # 替换为包含JSON数据的列名

process_json_data(input_file, output_file, json_column_name)
