from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
from datetime import datetime

def setup_driver():
    # 设置Chrome选项
    chrome_options = Options()
    # 如果需要无头模式，取消下面这行的注释
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # 初始化driver
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def get_mesh_terms(url):
    driver = setup_driver()
    try:
        # 访问页面
        driver.get(url)
        
        # 等待页面加载，直到关键词按钮出现
        wait = WebDriverWait(driver, 10)
        buttons = wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "button.keyword-actions-trigger.trigger.keyword-link")
        ))
        
        # 提取所有关键词文本
        mesh_terms = []
        for button in buttons:
            term = button.text.strip()
            if term:  # 确保不是空字符串
                mesh_terms.append(term)
        
        return mesh_terms
        
    except Exception as e:
        print(f"发生错误: {e}")
        return []
        
    finally:
        # 关闭浏览器
        driver.quit()

def save_to_excel(results, output_file=None):
    # 如果没有指定输出文件名，使用当前时间创建
    if output_file is None:
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"pubmed_mesh_terms_{current_time}.xlsx"
    
    # 创建一个空的DataFrame
    all_mesh_terms = []
    urls = []
    
    # 获取所有可能的MeSH terms（用于创建列）
    max_terms = 0
    for url, terms in results.items():
        max_terms = max(max_terms, len(terms))
        urls.append(url)
        all_mesh_terms.append(terms)
    
    # 创建列名
    columns = ['URL'] + [f'MeSH_Term_{i+1}' for i in range(max_terms)]
    
    # 创建数据
    data = []
    for url, terms in zip(urls, all_mesh_terms):
        # 填充缺失的terms为空字符串
        terms_padded = terms + [''] * (max_terms - len(terms))
        data.append([url] + terms_padded)
    
    # 创建DataFrame并保存到Excel
    df = pd.DataFrame(data, columns=columns)
    df.to_excel(output_file, index=False)
    print(f"数据已保存到: {output_file}")

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
    input_excel = "./ref_collt/a5-testdata.xlsx"  # 替换为你的Excel文件路径
    
    # 读取URL
    urls = read_urls_from_excel(input_excel)
    if not urls:
        print("没有找到有效的URL，程序退出")
        return
    
    # 显示部分URL作为预览
    print("\nURL预览 (前5个):")
    for i, url in enumerate(urls[:5], 1):
        print(f"{i}. {url}")
    
    # 如果URL数量大于5，显示总数
    if len(urls) > 5:
        print(f"... 共 {len(urls)} 个URL")
    
    # 确认是否继续
    confirm = input("\n是否开始处理这些URL? (y/n): ")
    if confirm.lower() != 'y':
        print("程序已取消")
        return
    
    # 处理URL并获取MeSH terms
    results = {}
    driver = setup_driver()  # 创建一个共用的driver实例
    try:
        for i, url in enumerate(urls, 1):
            print(f"\n处理第 {i}/{len(urls)} 个URL: {url}")
            mesh_terms = get_mesh_terms(url)
            results[url] = mesh_terms
            time.sleep(2)  # 添加延时，避免请求过于频繁
    
    finally:
        driver.quit()
    
    # 保存结果到新的Excel文件
    output_file = f"./ref_collt/a5-testdata_output.xlsx"
    save_to_excel(results, output_file)

if __name__ == "__main__":
    main()
