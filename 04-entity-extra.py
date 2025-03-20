import aiohttp
import asyncio
import json
import pandas as pd
from typing import Dict, List
from datetime import datetime
from pathlib import Path
import base64

class ImageProcessor:
    def __init__(self, api_key: str, max_concurrent: int = 10):
        self.api_key = api_key
        self.results = []
        self.semaphore = asyncio.Semaphore(max_concurrent)

    def encode_image(self, image_path: str) -> str:
        """将图片转换为base64编码"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def call_api_sse(self, file_id: str, idx: int) -> Dict:
        """调用API获取完整响应"""
        url = 'http://192.168.1.90:5000/v1/chat-messages'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        print(f"\n{'='*50}")
        print(f"处理第 {idx} 张图片:")
        print(f"File ID: {file_id}")
        
        # 构造提示词和请求数据
        prompt = '''
        # 我将给你提供一张医学领域英文期刊论文的截图,遵循AMA格式。在文中包含许多引用的内容，这些引用采用角标序号的形式来标注。我需要你帮我阅读这个论文的截图，
        把其中每一句引用的句子提取出来，告诉我引用角标序号和文中原句的对应关系。
        
        # 输出的结果需要严格采用json格式，具体如下：
       {
       {
            "id": 1,
            "reference_id": [1],
            "reference_text": "The available evidence from four randomized trials (NSABP B-39/RTOG 0413,."
        },
        {
            "id": 2,
            "reference_id": [2,3,4],
            "reference_text": "According to the DCIS Consensus Guideline on Margins by SSO/ASTRO/ASCO, the use of at least a 2-mm margin in DCIS treated with WBRT is associated with low rates of IBTR."
        }
        },


        # 请你在阅读论文截图的时候，务必将所有引用的句子都识别出来，不允许有遗漏，而且需要引用关系要准确。

        # 你需要阅读的论文截图如下：
        '''
        
        data = {
            "inputs": {},
            "query": prompt,
            "response_mode": "blocking",  # 改为阻塞模式
            "conversation_id": "",
            "user": "abc-123",
            "files": [
                {
                    "enabled": True,
                    "type": "image",
                    "transfer_method": "local_file",
                    "upload_file_id": f"{file_id}"  # 使用file_id而不是图片路径
                }
            ]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url=url, headers=headers, json=data, timeout=None) as response:
                    if response.status != 200:
                        raise Exception(f"API返回错误状态码: {response.status}")
                    
                    # 直接获取完整的响应
                    response_data = await response.json()
                    model_response = response_data.get('answer', '')
                    
                    return {
                        "id": idx,
                        "file_id": file_id,  # 保存file_id而不是图片路径
                        "model_response": model_response.strip()
                    }

        except Exception as e:
            error_msg = f"处理图片时出错: {str(e)}"
            print(f"\n{'!'*50}")
            print(error_msg)
            print(f"{'!'*50}\n")
            return {
                "id": idx,
                "file_id": file_id,  # 保存file_id而不是图片路径
                "model_response": f"ERROR: {str(e)}"
            }

    async def process_image(self, file_id: str, idx: int) -> Dict:
        """处理单张图片"""
        async with self.semaphore:
            await asyncio.sleep(0.5)  # 添加小延迟避免请求过于频繁
            return await self.call_api_sse(file_id, idx)

    async def process_all_images(self, file_ids: List[str]):
        """分批处理所有图片"""
        batch_size = 10  # 减小批次大小，因为图片处理可能需要更多资源
        results = []
        
        for i in range(0, len(file_ids), batch_size):
            batch = file_ids[i:i + batch_size]
            print(f"正在处理第 {i//batch_size + 1} 批，共 {len(batch)} 张图片")
            
            tasks = [self.process_image(file_id, idx) for idx, file_id in enumerate(batch, start=i)]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    print(f"处理第 {i+j} 张图片时发生错误: {str(result)}")
                    results.append({
                        "id": i+j,
                        "file_id": file_ids[i+j],
                        "model_response": "ERROR"
                    })
                else:
                    results.append(result)
            
            await asyncio.sleep(2)  # 批次间延迟
        
        self.results = results

    def save_to_excel(self, output_file: str):
        """将结果保存到Excel文件"""
        df = pd.DataFrame(self.results)
        df = df[['id', 'file_id', 'model_response']]  # 修改列名
        df.to_excel(output_file, index=False)

async def main():
    # 读取包含file_id的Excel文件
    excel_path = "./ref_collt/a4-png_id_test.xlsx"  # 替换为你的Excel文件路径
    df = pd.read_excel(excel_path)
    file_ids = df['remote_id'].tolist()  # 假设列名为'file_id'，请根据实际列名调整

    # 初始化处理器
    processor = ImageProcessor(api_key="app-2sp4iSClLe2lMN4mCFgIoRUg", max_concurrent=5)
    
    # 处理所有图片
    await processor.process_all_images(file_ids)
    
    # 保存结果
    output_file = f"image_analysis_results.xlsx"
    processor.save_to_excel(output_file)
    print(f"处理完成，结果已保存到 {output_file}")

if __name__ == "__main__":
    asyncio.run(main())