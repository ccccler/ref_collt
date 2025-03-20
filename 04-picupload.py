import aiohttp
import asyncio
from pathlib import Path
from typing import List, Dict
import pandas as pd

class FileUploader:
    def __init__(self, api_key: str, max_concurrent: int = 5):
        self.api_key = api_key
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.results = []

    async def upload_file(self, file_path: str, idx: int) -> Dict:
        """上传单个文件到服务器"""
        url = 'http://192.168.1.90:5000/v1/files/upload'
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }

        print(f"\n{'='*50}")
        print(f"上传第 {idx} 个文件:")
        print(f"文件路径: {file_path}")

        try:
            async with self.semaphore:
                async with aiohttp.ClientSession() as session:
                    # 构造 multipart form data
                    data = aiohttp.FormData()
                    data.add_field('file',
                                 open(file_path, 'rb'),
                                 filename=f'@{Path(file_path).name}',
                                 content_type='image/png')
                    data.add_field('user', 'abc-123')

                    async with session.post(url=url, 
                                          headers=headers, 
                                          data=data, 
                                          timeout=30) as response:
                        if response.status not in [200, 201]:
                            raise Exception(f"API返回错误状态码: {response.status}")
                        
                        response_data = await response.json()
                        return {
                            "local_file": file_path,
                            "file_name": Path(file_path).name,
                            "remote_id": response_data["id"],
                            "status": "success",
                            "size": response_data["size"],
                            "mime_type": response_data["mime_type"],
                            "created_at": response_data["created_at"]
                        }

        except Exception as e:
            error_msg = f"上传文件时出错: {str(e)}"
            print(f"\n{'!'*50}")
            print(error_msg)
            print(f"{'!'*50}\n")
            return {
                "local_file": file_path,
                "file_name": Path(file_path).name,
                "remote_id": None,
                "status": "error",
                "error_message": str(e)
            }

    async def upload_all_files(self, file_paths: List[str]):
        """批量上传所有文件"""
        tasks = [self.upload_file(path, idx) 
                for idx, path in enumerate(file_paths)]
        self.results = await asyncio.gather(*tasks, return_exceptions=True)

    def save_results_to_excel(self, output_file: str = "upload_results.xlsx"):
        """将上传结果保存到Excel文件"""
        # 将结果转换为DataFrame格式
        results_list = []
        for result in self.results:
            if isinstance(result, Exception):
                results_list.append({
                    "local_file": "Unknown",
                    "file_name": "Unknown",
                    "remote_id": None,
                    "status": "error",
                    "error_message": str(result)
                })
            else:
                results_list.append(result)

        df = pd.DataFrame(results_list)
        
        # 保存到Excel
        df.to_excel(output_file, index=False)
        print(f"\n结果已保存到: {output_file}")

async def main():
    # 指定要上传的文件所在文件夹
    file_folder = "./ref_collt/pic"  # 替换为你的文件夹路径
    file_paths = [str(p) for p in Path(file_folder).glob("*.png")]  # 可以根据需要修改文件类型

    # 初始化上传器
    uploader = FileUploader(api_key="app-98gRtXsNNhbcFD1zv9JFniC8", max_concurrent=5)
    
    # 上传所有文件
    await uploader.upload_all_files(file_paths)
    
    # 保存结果到Excel
    uploader.save_results_to_excel()
    
    # 打印上传统计
    success_count = sum(1 for r in uploader.results if isinstance(r, dict) and r["status"] == "success")
    total_count = len(uploader.results)
    print(f"\n上传完成: 成功 {success_count}/{total_count}")

if __name__ == "__main__":
    asyncio.run(main())
