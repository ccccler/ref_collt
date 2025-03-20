import pandas as pd
import aiohttp
import asyncio
import json
import re
from typing import Dict, List
from datetime import datetime

class ReferenceProcessor:
    def __init__(self, api_key: str, max_concurrent: int = 10):
        self.api_key = api_key
        self.results = []
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def call_api_sse(self, reference: str, idx: int) -> Dict:
        """使用SSE方式调用API"""
        url = 'http://192.168.1.90:5000/v1/completion-messages'  # 修改为正确的API路径
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        print(f"\n{'='*50}")
        print(f"处理第 {idx} 条参考文献:")
        print(f"原文献: {reference[:100]}...")  # 只显示前100个字符
        
        # 构造提示词
        prompt = f"""你是一个MAM格式的参考文献信息提取助手,请从以下AMA格式的参考文献中提取以下信息：
        - 文献标题
        - 作者列表
        - 期刊名称
        - 发表年份
        - URL (如果有)
        
        # 请严格按照以下json格式输出，不允许出现任何其他内容：
        {{
            "title": "",
            "authors": "",
            "journal": "",
            "year": "",
            "url": ""
        }}
        
        参考文献：{reference}
        """

        # 修改为符合API要求的请求体格式
        data = {
            "inputs": {"query": prompt},  # 使用 query 而不是 messages
            "response_mode": "streaming",
            "user": "reference_processor"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url=url, headers=headers, json=data, timeout=None) as response:
                    if response.status != 200:
                        raise Exception(f"API返回错误状态码: {response.status}")
                    
                    print(f"API响应状态码: {response.status}")
                    print("开始接收模型响应...")
                    print('-'*30)
                    
                    model_response = ""
                    buffer = ""
                    chunk_count = 0
                    
                    async for chunk in response.content:
                        if chunk:
                            chunk_count += 1
                            buffer += chunk.decode('utf-8')
                            print(f"\n[接收数据块 {chunk_count}]")
                            print(f"数据块大小: {len(chunk)} 字节")
                            
                            while '\n' in buffer:
                                line, buffer = buffer.split('\n', 1)
                                if line.startswith('data: '):
                                    try:
                                        json_data = json.loads(line[6:])
                                        if 'answer' in json_data:
                                            new_content = json_data['answer']
                                            model_response += new_content
                                            print(f"模型输出: {new_content}", flush=True)
                                        else:
                                            print(f"警告: 数据中没有answer字段: {json_data}")
                                    except json.JSONDecodeError as e:
                                        print(f"JSON解析错误: {e}")
                                        print(f"问题数据: {line[6:]}")
                                        continue
                    
                    print(f"\n{'='*30}")
                    print(f"处理完成! 共接收 {chunk_count} 个数据块")
                    print(f"最终响应内容:")
                    print(f"{model_response.strip()}")
                    print(f"{'='*30}\n")

                    return {
                        "id": idx,
                        "original_reference": reference,
                        "model_response": model_response.strip()
                    }

        except Exception as e:
            error_msg = f"处理参考文献时出错: {str(e)}"
            print(f"\n{'!'*50}")
            print(error_msg)
            print(f"出错的参考文献: {reference}")
            print(f"{'!'*50}\n")
            return {
                "id": idx,
                "original_reference": reference,
                "model_response": f"ERROR: {str(e)}"
            }

    async def process_reference(self, reference: str, idx: int) -> Dict:
        """处理单条参考文献"""
        async with self.semaphore:
            await asyncio.sleep(0.5)  # 添加小延迟避免请求过于频繁
            return await self.call_api_sse(reference, idx)

    async def process_all_references(self, references: List[str]):
        """分批处理所有参考文献"""
        batch_size = 50
        results = []
        
        for i in range(0, len(references), batch_size):
            batch = references[i:i + batch_size]
            print(f"正在处理第 {i//batch_size + 1} 批，共 {len(batch)} 条")
            
            tasks = [self.process_reference(ref, idx) for idx, ref in enumerate(batch, start=i)]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    print(f"处理第 {i+j} 条记录时发生错误: {str(result)}")
                    results.append({
                        "id": i+j,
                        "original_reference": references[i+j],
                        "model_response": "ERROR"
                    })
                else:
                    results.append(result)
            
            await asyncio.sleep(2)  # 批次间延迟
        
        self.results = results

    def save_to_excel(self, output_file: str):
        """将结果保存到Excel文件"""
        df = pd.DataFrame(self.results)
        # 确保列的顺序
        df = df[['id', 'original_reference', 'model_response']]
        df.to_excel(output_file, index=False)

async def main():
    # 读取输入的Excel文件
    input_file = "./ref_collt/raw_ref分列.xlsx"
    df = pd.read_excel(input_file)
    references = df['Content'].tolist()

    # 初始化处理器
    processor = ReferenceProcessor(api_key="app-0vDNiDJUUz7usGZqLn9L1moo", max_concurrent=100)
    
    # 处理所有参考文献
    await processor.process_all_references(references)
    
    # 生成带时间戳的输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"all_processed_references.xlsx"
    
    # 保存结果
    processor.save_to_excel(output_file)
    print(f"处理完成，结果已保存到 {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
