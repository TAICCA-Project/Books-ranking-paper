#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Books.com.tw 紙本書完整資訊爬取程式 - 多瀏覽器手動登入 + 多線程版本
支援開啟多個 Chrome 瀏覽器，讓用戶逐一手動登入後進行並行爬取
爬取欄位：ISBN, Publisher, translator, fixed_price, original_title, publish_date, category
"""

import sys
import os

# 確保能找到helper模組
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from helper.log_helper import LogHelper
from helper.selenium_helper import SeleniumHelper
from helper.common_helper import CommonHelper
from lxml import html
import pandas as pd
import time
import random
import re
import threading
import queue
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By

log = LogHelper('books_detail_books_service_selenium_multi')

# 線程鎖
file_write_lock = threading.Lock()
progress_lock = threading.Lock()

# 全域計數器
global_success_count = 0
global_fail_count = 0
global_processed_count = 0

# 全域 error 記錄列表
error_records = []
error_lock = threading.Lock()


def repair_encoding(text):
    """修復可能的編碼問題"""
    if not text or text == "N/A":
        return text
    
    # 處理常見的編碼問題
    text = text.replace('\u3000', ' ')  # 全角空格
    text = text.strip()
    return text


def extract_isbn(text):
    """從文本中提取 ISBN"""
    if not text:
        return "N/A"
    
    # 移除常見的 ISBN 前綴標籤
    text = re.sub(r'ISBN[：:：\s]*', '', text, flags=re.IGNORECASE)
    text = text.strip()
    
    # 嘗試查找 ISBN-13 (978 或 979 開頭的 13 位數字)
    isbn_match = re.search(r'(978|979)\d{10}', text)
    if isbn_match:
        return isbn_match.group(0)
    
    # 嘗試查找任何 13 位連續數字
    isbn_match = re.search(r'\d{13}', text)
    if isbn_match:
        return isbn_match.group(0)
    
    # 嘗試查找任何 10 位連續數字
    isbn_match = re.search(r'\d{10}', text)
    if isbn_match:
        return isbn_match.group(0)
    
    return "N/A"


def check_if_blocked(driver):
    """檢查是否被封鎖"""
    try:
        page_source = driver.page_source
        if '您的連線暫時異常' in page_source or 'Connection is temporarily unavailable' in page_source:
            return True
        if '請稍後再試' in page_source or 'Please try again later' in page_source:
            return True
        return False
    except:
        return False


def fetch_paper_book_info_with_selenium(driver, url, production_id="", retry_count=0, max_retries=2):
    """使用 Selenium 爬取 Books.com.tw 紙本書的完整資訊"""
    result = {
        'isbn': 'N/A',
        'Publisher': 'N/A',
        'translator': 'N/A',
        'fixed_price': 'N/A',
        'original_title': 'N/A',
        'publish_date': 'N/A',
        'category': 'N/A'
    }
    
    try:
        # 訪問頁面
        driver.get(url)
        time.sleep(random.uniform(3, 5))
        
        # 檢查是否被封鎖
        if check_if_blocked(driver):
            log.warning(f"⚠️  偵測到連線異常或被封鎖")
            
            if retry_count < max_retries:
                wait_time = random.uniform(5, 10) * (retry_count + 1)
                log.info(f"等待 {wait_time:.1f} 秒後重試 (第 {retry_count + 1}/{max_retries} 次)")
                time.sleep(wait_time)
                
                # 嘗試訪問首頁重新建立正常連線
                driver.get("https://www.books.com.tw/")
                time.sleep(random.uniform(5, 8))
                
                # 重試
                return fetch_paper_book_info_with_selenium(driver, url, production_id, retry_count + 1, max_retries)
            else:
                log.error(f"❌ 達到最大重試次數，放棄此 URL")
                raise Exception("連線被封鎖，無法完成爬取")
        
        # 獲取頁面內容
        page_source = driver.page_source
        tree = html.fromstring(page_source)
        
        # === 提取 ISBN ===
        isbn_li_elements = tree.xpath('//div[@class="mod_b type02_m058 clearfix"]//ul/li[contains(text(), "ISBN")]')
        if isbn_li_elements:
            isbn_text = isbn_li_elements[0].text_content().strip()
            result['isbn'] = extract_isbn(isbn_text)
            if result['isbn'] != "N/A":
                log.debug(f"成功提取 ISBN: {result['isbn']}")
        
        # 備用方法：從表格結構中提取 ISBN
        if result['isbn'] == "N/A":
            isbn_elements = tree.xpath('//div[@class="mod_b type02_m058 clearfix"]//tbody/tr/td/text()')
            for text in isbn_elements:
                if '978' in text or '979' in text:
                    result['isbn'] = extract_isbn(text)
                    if result['isbn'] != "N/A":
                        log.debug(f"從表格結構提取 ISBN: {result['isbn']}")
                        break
        
        # 使用 Selenium 直接查找元素
        if result['isbn'] == "N/A":
            try:
                isbn_elements = driver.find_elements(By.XPATH, "//div[@class='mod_b type02_m058 clearfix']//ul/li")
                for element in isbn_elements:
                    text = element.text
                    if 'ISBN' in text:
                        result['isbn'] = extract_isbn(text)
                        if result['isbn'] != "N/A":
                            break
            except:
                pass
        
        # === 提取譯者 ===
        translator_elements = tree.xpath('//div[@class="type02_p003 clearfix"]//li[contains(., "譯者：")]/a/text()')
        if translator_elements:
            result['translator'] = repair_encoding(translator_elements[0].strip())
            log.debug(f"找到譯者: {result['translator']}")
        else:
            translator_elements = tree.xpath('//div[@class="type02_p003 clearfix"]//ul/li[contains(., "譯者")]/a/text()')
            if translator_elements:
                result['translator'] = repair_encoding(translator_elements[0].strip())
        
        # 使用 Selenium 查找譯者
        if result['translator'] == "N/A":
            try:
                translator_elements = driver.find_elements(By.XPATH, "//div[@class='type02_p003 clearfix']//li")
                for element in translator_elements:
                    text = element.text
                    if '譯者' in text:
                        match = re.search(r'譯者[：:]\s*(.+)', text)
                        if match:
                            translator_name = match.group(1).strip()
                            translator_name = re.sub(r'\s*追蹤.*$', '', translator_name)
                            result['translator'] = repair_encoding(translator_name)
                            break
            except:
                pass
        
        # === 提取出版社 ===
        # 使用 XPath 根據文字內容判斷
        try:
            publisher_elements = tree.xpath('//div[@class="type02_p003 clearfix"]//li[contains(., "出版社：")]/a/text()')
            if publisher_elements:
                result['Publisher'] = repair_encoding(publisher_elements[0].strip())
                log.debug(f"找到出版社: {result['Publisher']}")
        except Exception as e:
            log.debug(f"使用 XPath 提取出版社時發生錯誤: {e}")
        
        # 備用方法：使用 Selenium
        if result['Publisher'] == "N/A":
            try:
                li_elements = driver.find_elements(By.CSS_SELECTOR, "div.type02_p003.clearfix > ul > li")
                for li_element in li_elements:
                    text = li_element.text
                    if '出版社' in text and '：' in text:
                        publisher_text = re.sub(r'出版社[：:]\s*', '', text)
                        publisher_text = re.sub(r'\s*追蹤.*$', '', publisher_text)
                        publisher_text = publisher_text.split('\n')[0].strip()
                        if publisher_text:
                            result['Publisher'] = repair_encoding(publisher_text)
                            log.debug(f"使用 Selenium 找到出版社: {result['Publisher']}")
                            break
            except Exception as e:
                log.debug(f"使用 Selenium 提取出版社時發生錯誤: {e}")
        
        # === 提取出版日期 ===
        # 使用 XPath 根據文字內容判斷
        try:
            publish_date_elements = tree.xpath('//div[@class="type02_p003 clearfix"]//li[contains(., "出版日期：")]/text()[normalize-space()]')
            if publish_date_elements:
                date_text = publish_date_elements[0].strip()
                date_text = re.sub(r'出版日期[：:]\s*', '', date_text)
                if date_text:
                    result['publish_date'] = repair_encoding(date_text)
                    log.debug(f"找到出版日期: {result['publish_date']}")
        except Exception as e:
            log.debug(f"使用 XPath 提取出版日期時發生錯誤: {e}")
        
        # 備用方法：使用 Selenium
        if result['publish_date'] == "N/A":
            try:
                li_elements = driver.find_elements(By.CSS_SELECTOR, "div.type02_p003.clearfix > ul > li")
                for li_element in li_elements:
                    text = li_element.text
                    if '出版日期' in text and '：' in text:
                        date_text = re.sub(r'出版日期[：:]\s*', '', text)
                        date_text = date_text.split('\n')[0].strip()
                        if date_text:
                            result['publish_date'] = repair_encoding(date_text)
                            log.debug(f"使用 Selenium 找到出版日期: {result['publish_date']}")
                            break
            except Exception as e:
                log.debug(f"使用 Selenium 提取出版日期時發生錯誤: {e}")
        
        # === 提取定價（fixed_price）===
        
        # 方法1：查找 "定價"
        price_elements = tree.xpath('//ul[@class="price"]/li[contains(text(), "定價")]/em/text()')
        if price_elements:
            result['fixed_price'] = price_elements[0].strip()
            log.debug(f"找到定價: {result['fixed_price']}")
        
        # 方法2：查找 "組合商品原始售價"
        if result['fixed_price'] == "N/A":
            price_elements = tree.xpath('//ul[@class="price"]/li[contains(text(), "組合商品原始售價")]/em/text()')
            if price_elements:
                result['fixed_price'] = price_elements[0].strip()
                log.debug(f"找到組合商品原始售價: {result['fixed_price']}")
        
        # 方法3：使用 Selenium 遍歷查找（只找定價和組合商品原始售價）
        if result['fixed_price'] == "N/A":
            try:
                price_elements = driver.find_elements(By.XPATH, "//ul[@class='price']/li")
                for element in price_elements:
                    text = element.text
                    # 只查找定價或組合商品原始售價，排除優惠價
                    if '定價' in text or '組合商品原始售價' in text:
                        # 提取數字（可能包含逗號）
                        match = re.search(r'[\d,]+', text)
                        if match:
                            result['fixed_price'] = match.group(0)
                            log.debug(f"使用 Selenium 找到價格: {result['fixed_price']}")
                            break
            except Exception as e:
                log.debug(f"使用 Selenium 提取價格時發生錯誤: {e}")
        
        # === 提取原文書名 ===
        original_title_elements = tree.xpath('//div[@class="mod type02_p002 clearfix"]//h2/a/text()')
        if original_title_elements:
            result['original_title'] = repair_encoding(original_title_elements[0].strip())
            log.debug(f"找到原文書名: {result['original_title']}")
        else:
            try:
                original_title_element = driver.find_element(By.CSS_SELECTOR, "div.mod.type02_p002.clearfix > h2 > a")
                if original_title_element:
                    result['original_title'] = repair_encoding(original_title_element.text.strip())
            except:
                try:
                    original_title_element = driver.find_element(By.XPATH, "//div[contains(@class, 'type02_p002')]//h2/a")
                    if original_title_element:
                        result['original_title'] = repair_encoding(original_title_element.text.strip())
                except:
                    pass
        
        # === 提取分類 ===
        # 方法1：使用 lxml xpath 從 ul.sort 中提取所有 <li> 的分類路徑
        category_list = []
        try:
            sort_ul = tree.xpath('//div[@class="mod_b type02_m058 clearfix"]//ul[@class="sort"]')
            if sort_ul:
                # 找到所有包含 "本書分類：" 的 <li>
                category_lis = sort_ul[0].xpath('.//li[contains(text(), "本書分類：")]')
                for li in category_lis:
                    # 提取該 <li> 中所有 <a> 標籤的文本
                    category_links = li.xpath('.//a/text()')
                    if category_links:
                        # 用 " > " 連接各個分類層級
                        category_path = " > ".join([repair_encoding(c.strip()) for c in category_links])
                        category_list.append(category_path)
                        log.debug(f"找到分類: {category_path}")
        except Exception as e:
            log.debug(f"lxml 提取分類時發生錯誤: {e}")
        
        # 方法2：使用 Selenium 備用方法
        if not category_list:
            try:
                sort_ul_element = driver.find_element(By.CSS_SELECTOR, "ul.sort")
                category_li_elements = sort_ul_element.find_elements(By.TAG_NAME, "li")
                for li_element in category_li_elements:
                    li_text = li_element.text
                    if "本書分類：" in li_text:
                        # 提取該 li 中的所有 <a> 標籤
                        category_links = li_element.find_elements(By.TAG_NAME, "a")
                        if category_links:
                            category_path = " > ".join([repair_encoding(a.text.strip()) for a in category_links if a.text.strip()])
                            category_list.append(category_path)
                            log.debug(f"使用 Selenium 找到分類: {category_path}")
            except Exception as e:
                log.debug(f"Selenium 提取分類時發生錯誤: {e}")
        
        # 將分類列表合併為字串（用分號分隔）
        if category_list:
            result['category'] = '; '.join(category_list)
            log.debug(f"成功提取分類: {result['category']}")
        
        # 記錄結果
        found_items = []
        if result['isbn'] != 'N/A':
            found_items.append(f"ISBN: {result['isbn']}")
        if result['Publisher'] != 'N/A':
            found_items.append(f"出版社: {result['Publisher']}")
        if result['translator'] != 'N/A':
            found_items.append(f"譯者: {result['translator']}")
        if result['fixed_price'] != 'N/A':
            found_items.append(f"定價: {result['fixed_price']}")
        if result['original_title'] != 'N/A':
            found_items.append(f"原文書名: {result['original_title']}")
        if result['publish_date'] != 'N/A':
            found_items.append(f"出版日期: {result['publish_date']}")
        if result['category'] != 'N/A':
            found_items.append(f"分類: {result['category']}")
        
        if found_items:
            log.debug(f"成功提取: {', '.join(found_items)}")
        
        return result
        
    except Exception as e:
        log.error(f"爬取資訊時發生錯誤: {e}")
        return result


def initialize_drivers(num_drivers=3):
    """
    初始化多個 Chrome 瀏覽器供用戶手動登入
    
    Args:
        num_drivers: 要開啟的瀏覽器數量
        
    Returns:
        list: WebDriver 列表
    """
    drivers = []
    
    print(f"\n正在啟動 {num_drivers} 個 Chrome 瀏覽器...")
    print("=" * 60)
    
    for i in range(num_drivers):
        try:
            options = SeleniumHelper.get_chrome_options()
            
            # 反檢測設置
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 設置不同的視窗位置，避免重疊
            window_positions = [
                (0, 0),      # 左上
                (800, 0),    # 右上
                (0, 500),    # 左下
                (800, 500),  # 右下
                (400, 250),  # 中間
            ]
            if i < len(window_positions):
                x, y = window_positions[i]
                options.add_argument(f'--window-position={x},{y}')
            
            driver = webdriver.Chrome(options=options)
            
            # 執行 JavaScript 隱藏 webdriver 屬性
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['zh-TW', 'zh', 'en-US', 'en']
                    });
                    
                    window.chrome = {
                        runtime: {}
                    };
                '''
            })
            
            # 訪問博客來首頁
            driver.get("https://www.books.com.tw/")
            time.sleep(2)
            
            # 設置視窗標題以便識別
            driver.execute_script(f"document.title = '博客來 - 瀏覽器 #{i+1} (請登入)'")
            
            drivers.append(driver)
            print(f"✓ 瀏覽器 #{i+1} 已開啟")
            log.info(f"瀏覽器 #{i+1} 初始化成功")
            
        except Exception as e:
            log.error(f"初始化瀏覽器 #{i+1} 失敗: {e}")
            print(f"❌ 瀏覽器 #{i+1} 啟動失敗: {e}")
            # 關閉已開啟的瀏覽器
            for d in drivers:
                try:
                    d.quit()
                except:
                    pass
            return None
    
    print("=" * 60)
    return drivers


def wait_for_manual_login(drivers):
    """
    等待用戶在所有瀏覽器中完成手動登入
    
    Args:
        drivers: WebDriver 列表
    """
    print("\n" + "="*60)
    print("【重要】請在每個瀏覽器中完成以下步驟：")
    print("="*60)
    print(f"已開啟 {len(drivers)} 個瀏覽器視窗")
    print()
    print("請在每個瀏覽器中：")
    print("  1. 登入您的博客來帳號")
    print("  2. （如需爬取限制級書籍）訪問任意一本限制級書籍")
    print("  3. 確認通過年齡驗證，可以正常瀏覽限制級內容")
    print()
    print(f"提示：瀏覽器視窗標題會顯示 '瀏覽器 #1', '瀏覽器 #2' 等以便識別")
    print("="*60)
    
    input(f"\n完成所有 {len(drivers)} 個瀏覽器的登入後，按 Enter 鍵繼續爬取...")
    
    # 更新視窗標題
    for i, driver in enumerate(drivers):
        try:
            driver.execute_script(f"document.title = '博客來 - 瀏覽器 #{i+1} (爬取中...)'")
        except:
            pass
    
    log.info("用戶確認已完成所有登入，開始爬取資訊")
    print("\n✅ 開始使用多線程爬取...\n")


def fetch_book_with_shared_driver(row_data, driver, driver_id, output_file, total_rows):
    """
    使用共享的已登入 WebDriver 爬取單本書
    
    Args:
        row_data: (idx, row) 元組
        driver: 已登入的 WebDriver
        driver_id: 瀏覽器編號
        output_file: 輸出檔案路徑
        total_rows: 總行數
    """
    global global_success_count, global_fail_count, global_processed_count
    
    idx, row = row_data
    url = row['url']
    production_id = row.get('production_id', '')
    title = row.get('title', 'N/A')
    
    result_data = {
        'idx': idx,
        'isbn': 'N/A',
        'Publisher': 'N/A',
        'translator': 'N/A',
        'fixed_price': 'N/A',
        'original_title': 'N/A',
        'publish_date': 'N/A',
        'category': 'N/A',
        'success': False,
        'error': None
    }
    
    try:
        # 使用傳入的 driver 爬取
        result = fetch_paper_book_info_with_selenium(driver, url, production_id, retry_count=0, max_retries=2)
        
        result_data['isbn'] = result['isbn']
        result_data['Publisher'] = result['Publisher']
        result_data['translator'] = result['translator']
        result_data['fixed_price'] = result['fixed_price']
        result_data['original_title'] = result['original_title']
        result_data['publish_date'] = result['publish_date']
        result_data['category'] = result['category']
        
        # 判斷是否成功
        if any(v != 'N/A' for v in result.values()):
            result_data['success'] = True
            with progress_lock:
                global_success_count += 1
        else:
            with progress_lock:
                global_fail_count += 1
        
        # 隨機延遲（增加延遲時間避免被封鎖）
        time.sleep(random.uniform(5, 10))
        
    except Exception as e:
        result_data['error'] = str(e)
        with progress_lock:
            global_fail_count += 1
        log.error(f"瀏覽器 #{driver_id} 爬取 {url} 失敗: {e}")
    
    # 更新進度計數
    with progress_lock:
        global_processed_count += 1
        current_progress = global_processed_count
    
    # 顯示進度
    with progress_lock:
        if result_data['success']:
            found_items = []
            if result_data['isbn'] != 'N/A':
                found_items.append(f"ISBN: {result_data['isbn']}")
            if result_data['Publisher'] != 'N/A':
                found_items.append(f"出版社: {result_data['Publisher']}")
            if result_data['translator'] != 'N/A':
                found_items.append(f"譯者: {result_data['translator']}")
            if result_data['fixed_price'] != 'N/A':
                found_items.append(f"定價: {result_data['fixed_price']}")
            if result_data['original_title'] != 'N/A':
                found_items.append(f"原文書名: {result_data['original_title']}")
            if result_data['publish_date'] != 'N/A':
                found_items.append(f"出版日期: {result_data['publish_date']}")
            if result_data['category'] != 'N/A':
                found_items.append(f"分類: {result_data['category']}")
            
            print(f"[瀏覽器 #{driver_id}] [{current_progress}/{total_rows}] ✅ {title}: {', '.join(found_items)}")
        else:
            error_msg = f" ({result_data['error'][:30]}...)" if result_data['error'] else ""
            print(f"[瀏覽器 #{driver_id}] [{current_progress}/{total_rows}] ❌ {title}{error_msg}")
    
    # 判斷是否需要記錄到 error 檔案
    should_record_error = (
        result_data['fixed_price'] == 'N/A' or 
        result_data['isbn'] == 'N/A' or 
        result_data['error'] is not None
    )
    
    if should_record_error:
        # 判斷缺失的欄位
        missing_fields = []
        if result_data['isbn'] == 'N/A':
            missing_fields.append('isbn')
        if result_data['fixed_price'] == 'N/A':
            missing_fields.append('fixed_price')
        
        error_reason = result_data['error'] if result_data['error'] else f"缺少欄位: {', '.join(missing_fields)}"
        
        error_record = {
            'url': url,
            'title': title,
            'production_id': production_id,
            'isbn': result_data['isbn'],
            'Publisher': result_data['Publisher'],
            'fixed_price': result_data['fixed_price'],
            'translator': result_data['translator'],
            'original_title': result_data['original_title'],
            'publish_date': result_data['publish_date'],
            'category': result_data['category'],
            'error_reason': error_reason,
            'row_index': idx
        }
        
        with error_lock:
            error_records.append(error_record)
    
    return result_data


def worker_thread(driver, driver_id, task_queue, df, output_file, total_rows):
    """
    工作線程：從佇列中取任務並使用指定的 driver 處理
    
    Args:
        driver: 已登入的 WebDriver
        driver_id: 瀏覽器編號
        task_queue: 任務佇列
        df: DataFrame
        output_file: 輸出檔案路徑
        total_rows: 總行數
    """
    log.info(f"工作線程 (瀏覽器 #{driver_id}) 已啟動")
    
    while True:
        try:
            # 從佇列中取任務（超時 1 秒）
            task = task_queue.get(timeout=1)
            
            if task is None:  # None 是停止信號
                log.info(f"工作線程 (瀏覽器 #{driver_id}) 收到停止信號")
                break
            
            # 處理任務
            result_data = fetch_book_with_shared_driver(task, driver, driver_id, output_file, total_rows)
            
            # 保存結果
            if output_file:
                save_result_to_csv(df, result_data, output_file)
            
            # 標記任務完成
            task_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            log.error(f"工作線程 (瀏覽器 #{driver_id}) 發生錯誤: {e}")
            try:
                task_queue.task_done()
            except:
                pass
    
    log.info(f"工作線程 (瀏覽器 #{driver_id}) 已結束")


def save_result_to_csv(df, result_data, output_file):
    """線程安全地保存結果到 CSV"""
    with file_write_lock:
        try:
            idx = result_data['idx']
            df.at[idx, 'ISBN'] = result_data['isbn']
            df.at[idx, 'Publisher'] = result_data['Publisher']
            df.at[idx, 'translator'] = result_data['translator']
            df.at[idx, 'fixed_price'] = result_data['fixed_price']
            df.at[idx, 'original_title'] = result_data['original_title']
            df.at[idx, 'publish_date'] = result_data['publish_date']
            df.at[idx, 'category'] = result_data['category']
            
            # 即時寫入
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
        except Exception as e:
            log.error(f"保存結果時發生錯誤: {e}")


def read_csv_data(csv_path):
    """讀取 CSV 檔案"""
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        if 'url' not in df.columns:
            log.error(f"CSV 檔案中沒有找到 url 欄位")
            return None, None
        
        # 清理欄位名稱（移除前後空格）
        df.columns = df.columns.str.strip()
        
        # 確保必要欄位存在
        required_fields = ['ISBN', 'Publisher', 'translator', 'fixed_price', 'original_title', 'publish_date', 'category']
        for field in required_fields:
            if field not in df.columns:
                df[field] = 'N/A'
                log.info(f"已創建 {field} 欄位")
        
        # 獲取 production_id 欄位名稱
        production_id_col = None
        for col in df.columns:
            if 'production_id' in col.lower():
                production_id_col = col
                break
        
        log.info(f"從 CSV 檔案中讀取 {len(df)} 筆資料")
        log.info(f"CSV 欄位: {list(df.columns)}")
        return df, production_id_col
    
    except Exception as e:
        log.error(f"讀取 CSV 檔案時發生錯誤: {e}")
        import traceback
        log.error(traceback.format_exc())
        return None, None


def fetch_info_with_multiple_browsers(df, drivers, production_id_col, max_books=None, 
                                      failed_urls_file=None, output_file=None):
    """
    使用多個已登入的瀏覽器進行多線程爬取
    
    Args:
        df: DataFrame
        drivers: 已登入的 WebDriver 列表
        production_id_col: production_id 欄位名稱
        max_books: 最多爬取的書籍數量
        failed_urls_file: 失敗記錄檔案路徑
        output_file: 輸出檔案路徑
    """
    global global_success_count, global_fail_count, global_processed_count
    
    # 重置計數器
    global_success_count = 0
    global_fail_count = 0
    global_processed_count = 0
    
    total_rows = len(df) if max_books is None else min(max_books, len(df))
    num_workers = len(drivers)
    
    # 創建任務佇列
    task_queue = queue.Queue()
    
    # 將所有任務放入佇列
    for idx in range(total_rows):
        task_queue.put((idx, df.iloc[idx]))
    
    print(f"開始多線程爬取，使用 {num_workers} 個已登入的瀏覽器")
    print(f"共 {total_rows} 本書籍")
    print(f"平均每個瀏覽器處理約 {total_rows // num_workers} 本書\n")
    
    log.info(f"開始多線程爬取，{num_workers} 個瀏覽器，{total_rows} 本書")
    
    # 啟動工作線程
    threads = []
    for i, driver in enumerate(drivers):
        thread = threading.Thread(
            target=worker_thread,
            args=(driver, i+1, task_queue, df, output_file, total_rows),
            name=f"Worker-{i+1}"
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    # 等待所有任務完成
    task_queue.join()
    
    # 發送停止信號
    for _ in drivers:
        task_queue.put(None)
    
    # 等待所有線程結束
    for thread in threads:
        thread.join(timeout=5)
    
    print(f"\n{'='*60}")
    print(f"爬取完成: 成功 {global_success_count} 本, 失敗 {global_fail_count} 本")
    print(f"{'='*60}")
    
    log.info(f"爬取完成: 成功 {global_success_count} 本, 失敗 {global_fail_count} 本")
    
    # 保存 error 記錄到檔案
    if error_records:
        try:
            # 構建 error 檔案路徑（確保不會覆蓋原檔案）
            if output_file:
                # 移除 .csv 後綴，加上 _error.csv
                error_file = output_file.replace('.csv', '_error.csv')
            else:
                error_file = failed_urls_file if failed_urls_file else "detail_books_error.csv"
            
            error_df = pd.DataFrame(error_records)
            error_df.to_csv(error_file, index=False, encoding='utf-8-sig')
            
            print(f"\n⚠️  發現 {len(error_records)} 筆錯誤記錄")
            print(f"✓ 錯誤記錄已保存至: {error_file}")
            log.info(f"已保存 {len(error_records)} 筆錯誤記錄到: {error_file}")
            
        except Exception as e:
            log.error(f"保存錯誤記錄時發生錯誤: {e}")
            print(f"❌ 保存錯誤記錄時發生錯誤: {e}")
    else:
        print(f"\n✓ 所有書籍的 ISBN 和 Price 都已成功爬取")
        log.info("所有書籍的 ISBN 和 Price 都已成功爬取")
    
    return df


def Excute(csv_path=None, num_browsers=3):
    """
    主執行函數 - 多瀏覽器手動登入版本
    
    Args:
        csv_path: CSV 檔案路徑
        num_browsers: 瀏覽器數量（建議 3-4）
    """
    global error_records
    
    # 重置 error 記錄
    error_records = []
    
    start_time = datetime.now()
    log.info("=" * 60)
    log.info(f"開始執行 Books.com.tw 紙本書詳細資訊爬取 (多瀏覽器手動登入版本)")
    log.info(f"瀏覽器數: {num_browsers}")
    log.info(f"時間: {start_time}")
    log.info("=" * 60)
    
    print("\n" + "="*60)
    print("博客來紙本書詳細資訊爬取程式 - 多瀏覽器手動登入版本")
    print("="*60)
    print(f"將開啟 {num_browsers} 個 Chrome 瀏覽器")
    print("您可以在每個瀏覽器中分別登入")
    print("登入完成後，這些瀏覽器會並行爬取書籍資訊")
    print("支援即時寫入，每爬取一本書立即保存到 CSV")
    print()
    print("爬取欄位：ISBN、出版社、譯者、定價、原文書名、出版日期、分類")
    print("="*60)
    
    drivers = None
    
    try:
        # 讀取 CSV
        if csv_path is None:
            csv_path = input("\n請輸入 CSV 檔案路徑: ").strip()
        
        csv_path = csv_path.strip('"').strip("'")
        
        if not os.path.exists(csv_path):
            log.error(f"CSV 檔案不存在: {csv_path}")
            print(f"❌ CSV 檔案不存在: {csv_path}")
            return False
        
        df, production_id_col = read_csv_data(csv_path)
        if df is None or len(df) == 0:
            log.error("沒有找到有效的書籍資料，爬蟲終止")
            print("❌ 沒有找到有效的書籍資料")
            return False
        
        print(f"\n✓ 成功讀取 {len(df)} 筆書籍資料")
        
        # 直接使用輸入的 CSV 檔案作為輸出（動態更新原始檔案）
        output_file = csv_path
        
        # 錯誤記錄檔案放在同一目錄
        csv_dir = os.path.dirname(csv_path)
        csv_name = os.path.basename(csv_path).replace('.csv', '')
        failed_urls_file = os.path.join(csv_dir, f"{csv_name}_error.csv")
        
        print(f"將動態更新原始檔案: {output_file}")
        log.info(f"將動態更新原始檔案: {output_file}")
        
        # 初始化多個瀏覽器
        drivers = initialize_drivers(num_browsers)
        if not drivers:
            print("❌ 瀏覽器初始化失敗")
            return False
        
        # 等待手動登入
        wait_for_manual_login(drivers)
        
        # 使用已登入的瀏覽器進行爬取
        df = fetch_info_with_multiple_browsers(
            df, 
            drivers,
            production_id_col, 
            None, 
            failed_urls_file, 
            output_file
        )
        
        # 統計結果
        isbn_count = df['ISBN'].astype(str).ne('N/A').sum()
        publisher_count = df['Publisher'].astype(str).ne('N/A').sum()
        translator_count = df['translator'].astype(str).ne('N/A').sum()
        fixed_price_count = df['fixed_price'].astype(str).ne('N/A').sum()
        original_title_count = df['original_title'].astype(str).ne('N/A').sum()
        publish_date_count = df['publish_date'].astype(str).ne('N/A').sum()
        category_count = df['category'].astype(str).ne('N/A').sum()
        
        print(f"\n{'='*60}")
        print("爬取結果統計：")
        print(f"  ISBN: {isbn_count} 筆")
        print(f"  出版社: {publisher_count} 筆")
        print(f"  譯者: {translator_count} 筆")
        print(f"  定價: {fixed_price_count} 筆")
        print(f"  原文書名: {original_title_count} 筆")
        print(f"  出版日期: {publish_date_count} 筆")
        print(f"  分類: {category_count} 筆")
        print(f"{'='*60}")
        print(f"\n✓ 輸出檔案: {output_file}")
        
        log.info(f"爬取結果: ISBN={isbn_count}, 出版社={publisher_count}, 譯者={translator_count}, 定價={fixed_price_count}, 原文書名={original_title_count}, 出版日期={publish_date_count}, 分類={category_count}")
        
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        print(f"\n總耗時: {elapsed_time}")
        log.info(f"總耗時: {elapsed_time}")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n⚠️  收到中斷信號 (Ctrl+C)")
        log.info("程式已被用戶中斷")
        return False
        
    except Exception as e:
        log.error(f"處理過程中發生錯誤: {e}")
        import traceback
        log.error(traceback.format_exc())
        print(f"\n❌ 處理過程中發生錯誤: {e}")
        return False
    
    finally:
        # 關閉所有瀏覽器
        if drivers:
            print("\n正在關閉所有瀏覽器...")
            for i, driver in enumerate(drivers):
                try:
                    driver.quit()
                    print(f"✓ 瀏覽器 #{i+1} 已關閉")
                    log.info(f"瀏覽器 #{i+1} 已關閉")
                except Exception as e:
                    log.error(f"關閉瀏覽器 #{i+1} 時發生錯誤: {e}")
            log.info("所有瀏覽器已關閉")


if __name__ == "__main__":
    try:
        csv_path = None
        num_browsers = 3  # 預設 3 個瀏覽器
        
        if len(sys.argv) >= 2:
            csv_path = sys.argv[1]
        if len(sys.argv) >= 3:
            try:
                num_browsers = int(sys.argv[2])
            except ValueError:
                print("⚠️  瀏覽器數量必須是整數，使用預設值 3")
                num_browsers = 3
        
        # 限制瀏覽器數量
        if num_browsers < 1:
            print("⚠️  瀏覽器數量至少為 1，已調整為 1")
            num_browsers = 1
        if num_browsers > 5:
            print("⚠️  瀏覽器數量不建議超過 5 個，已限制為 5")
            num_browsers = 5
        
        success = Excute(csv_path, num_browsers)
        
        if success:
            print("\n✅ Books.com.tw 紙本書詳細資訊爬取完成！")
        else:
            print("\n❌ Books.com.tw 紙本書詳細資訊爬取失敗")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  程式已被用戶中斷")
        log.info("程式已被用戶中斷")
    except Exception as e:
        print(f"\n❌ 程式執行發生錯誤: {e}")
        log.error(f"程式執行發生錯誤: {e}")
        import traceback
        traceback.print_exc()
