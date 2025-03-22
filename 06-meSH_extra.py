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

def main():
    # 可以处理单个URL或多个URL
    urls = [
        "https://pubmed.ncbi.nlm.nih.gov/31928354/",
        # 添加更多URL...
    ]
    
    # 如果只有一个URL
    if len(urls) == 1:
        results = {urls[0]: get_mesh_terms(urls[0])}
    else:
        # 批量处理多个URL
        results = {}
        for url in urls:
            print(f"正在处理: {url}")
            mesh_terms = get_mesh_terms(url)
            results[url] = mesh_terms
            time.sleep(2)  # 添加延时，避免请求过于频繁
    
    # 保存结果到Excel
    save_to_excel(results)
    
    # 打印结果预览
    print("\n爬取结果预览：")
    for url, terms in results.items():
        print(f"\nURL: {url}")
        print("MeSH术语：")
        for i, term in enumerate(terms, 1):
            print(f"{i}. {term}")

if __name__ == "__main__":
    main()
