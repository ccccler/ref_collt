from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import sqlite3
from sqlite3 import Error

def setup_driver():
    chrome_options = Options()
    # 启用无头模式以减少资源占用
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-extensions')
    # 添加用户代理
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    # 设置页面加载超时时间
    driver.set_page_load_timeout(30)
    return driver

def get_mesh_terms_thread(url, driver_queue):
    """单个线程的处理函数"""
    driver = driver_queue.get()
    try:
        print(f"开始处理URL: {url}")
        # 添加重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                driver.get(url)
                # 添加强制等待
                time.sleep(2)
                
                wait = WebDriverWait(driver, 30)  # 增加等待时间到30秒
                
                # 首先等待页面加载完成
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                
                # 首先定位mesh-terms区域
                mesh_section = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div#mesh-terms.mesh-terms.keywords-section")
                ))
                
                # 在mesh-terms区域内查找keywords-list下的关键词
                mesh_terms = []
                try:
                    keywords_list = mesh_section.find_element(By.CSS_SELECTOR, "ul.keywords-list")
                    buttons = keywords_list.find_elements(By.CSS_SELECTOR, "button.keyword-actions-trigger.trigger.keyword-link")
                    
                    for button in buttons:
                        term = button.text.strip()
                        if term:
                            mesh_terms.append(term)
                            
                except Exception as e:
                    print(f"在mesh-terms区域内查找关键词时出错: {e}")
                
                if not mesh_terms:
                    print(f"警告：在URL {url} 的mesh-terms区域中没有找到MeSH术语")
                    print(f"页面标题: {driver.title}")
                    print("当前页面URL:", driver.current_url)
                else:
                    print(f"成功从 {url} 提取到 {len(mesh_terms)} 个MeSH术语")
                
                return url, mesh_terms
                
            except Exception as e:
                print(f"第 {attempt + 1} 次尝试失败 {url}:")
                print(f"错误类型: {type(e).__name__}")
                print(f"错误信息: {str(e)}")
                if attempt < max_retries - 1:
                    print("等待后重试...")
                    time.sleep(5)  # 重试前等待5秒
                    # 刷新driver
                    driver.quit()
                    driver = setup_driver()
                else:
                    return url, []
                    
    except Exception as e:
        print(f"访问URL时发生错误 {url}:")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        return url, []
        
    finally:
        driver_queue.put(driver)

def save_single_record(url, mesh_terms, connection=None):
    """
    保存单条记录到数据库
    """
    try:
        # 如果没有传入连接，创建新的连接
        should_close = connection is None
        if connection is None:
            connection = sqlite3.connect('./ref_collt/pubmed_mesh.db')
        
        cursor = connection.cursor()
        
        # 获取当前表结构
        cursor.execute("""
        SELECT sql FROM sqlite_master 
        WHERE type='table' AND name='sec_pubmed_mesh_terms'
        """)
        table_info = cursor.fetchone()
        
        if not table_info:
            # 如果表不存在，创建新表
            num_terms = len(mesh_terms)
            create_table_query = """
            CREATE TABLE IF NOT EXISTS sec_pubmed_mesh_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                {}
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """.format(','.join([f'mesh_term_{i+1} TEXT' for i in range(num_terms)]))
            cursor.execute(create_table_query)
        else:
            # 获取现有的列数
            cursor.execute("PRAGMA table_info(sec_pubmed_mesh_terms)")
            existing_columns = len([col for col in cursor.fetchall()]) - 3  # 减去id、url和created_at列
            
            # 如果需要，添加新列
            if len(mesh_terms) > existing_columns:
                for i in range(existing_columns, len(mesh_terms)):
                    try:
                        cursor.execute(f"ALTER TABLE sec_pubmed_mesh_terms ADD COLUMN mesh_term_{i+1} TEXT")
                    except sqlite3.OperationalError:
                        pass  # 列已存在，继续处理
        
        # 准备插入语句
        num_terms = max(len(mesh_terms), existing_columns if 'existing_columns' in locals() else len(mesh_terms))
        columns = ['url'] + [f'mesh_term_{i+1}' for i in range(num_terms)]
        placeholders = ','.join(['?' for _ in range(len(columns))])
        
        insert_query = f"""
        INSERT OR REPLACE INTO sec_pubmed_mesh_terms ({','.join(columns)})
        VALUES ({placeholders})
        """
        
        # 准备数据
        row_data = [url] + mesh_terms + [''] * (num_terms - len(mesh_terms))
        
        # 执行插入
        cursor.execute(insert_query, row_data)
        connection.commit()
        
        print(f"已保存记录: {url} (包含 {len(mesh_terms)} 个MeSH术语)")
        
    except Exception as e:
        print(f"保存记录时发生错误 {url}: {e}")
        print("SQL错误详情:", str(e))
        import traceback
        print(traceback.format_exc())
    
    finally:
        if should_close and connection:
            connection.close()

def process_urls_parallel(urls, num_threads=4):
    """并行处理URLs"""
    # 创建driver队列
    driver_queue = Queue()
    
    # 创建数据库连接
    connection = sqlite3.connect('./ref_collt/pubmed_mesh.db')
    
    # 预先创建多个driver实例
    for _ in range(num_threads):
        driver = setup_driver()
        driver_queue.put(driver)
    
    try:
        # 使用线程池执行任务
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            # 提交所有任务
            future_to_url = {
                executor.submit(get_mesh_terms_thread, url, driver_queue): url 
                for url in urls
            }
            
            # 获取完成的任务结果
            total = len(urls)
            completed = 0
            
            for future in as_completed(future_to_url):
                url, mesh_terms = future.result()
                # 立即保存到数据库
                save_single_record(url, mesh_terms, connection)
                completed += 1
                print(f"进度: {completed}/{total} ({(completed/total)*100:.1f}%)")
                
    finally:
        # 关闭数据库连接
        if connection:
            connection.close()
            
        # 关闭所有driver
        while not driver_queue.empty():
            driver = driver_queue.get()
            driver.quit()

def read_urls_from_excel(excel_file, url_column='url'):
    """
    从Excel文件中读取URL列表
    
    参数:
    excel_file: Excel文件路径
    url_column: 包含URL的列名，默认为'URL'
    
    返回:
    url列表
    """
    try:
        # 读取Excel文件
        df = pd.read_excel(excel_file)
        
        # 检查URL列是否存在
        if url_column not in df.columns:
            raise ValueError(f"Excel文件中未找到'{url_column}'列")
        
        # 获取URL列表并删除重复项和空值
        urls = df[url_column].dropna().unique().tolist()
        
        print(f"从Excel中成功读取了 {len(urls)} 个唯一URL")
        return urls
    
    except Exception as e:
        print(f"读取Excel文件时发生错误: {e}")
        return []

def main():
    # 指定输入Excel文件路径
    input_excel = "./ref_collt/dataset/sa6-pubmed-paper.xlsx"
    
    # 读取URL
    urls = read_urls_from_excel(input_excel)
    if not urls:
        print("没有找到有效的URL，程序退出")
        return
    
    # 显示部分URL作为预览
    print("\nURL预览 (前5个):")
    for i, url in enumerate(urls[:5], 1):
        print(f"{i}. {url}")
    
    if len(urls) > 5:
        print(f"... 共 {len(urls)} 个URL")
    
    # 直接开始处理URLs
    print("\n开始并行处理URLs...")
    num_threads = 4
    process_urls_parallel(urls, num_threads)
    
    print("所有URL处理完成")

if __name__ == "__main__":
    main()
