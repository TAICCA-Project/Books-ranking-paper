#!/usr/bin/env python
import sys
import os
import re

# 確保能找到helper模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import time
import json
import pandas as pd
import traceback
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from helper.log_helper import LogHelper
from helper.selenium_helper import SeleniumHelper
from helper.common_helper import CommonHelper

log = LogHelper('kingstone_detail_books_service')

base_url = 'https://www.kingstone.com.tw'
max_retries = 3

class DetailBook:
    def __init__(self, production_id="", title="", url="", Publisher="", author="", translator="",
                 publish_date="", fixed_price="", isbn="", category="", original_title=""):
        self.production_id = production_id
        self.title = title
        self.url = url
        self.Publisher = Publisher
        self.author = author
        self.translator = translator
        self.publish_date = publish_date
        self.fixed_price = fixed_price
        self.isbn = isbn
        self.category = category
        self.original_title = original_title

    def to_dict(self):
        return {
            'ISBN': self.isbn,  # 改為大寫 ISBN 以匹配 CSV 欄位名稱
            'production_id': str(self.production_id),
            'Publisher': self.Publisher,
            'translator': self.translator,
            'original_title': self.original_title,
            'publish_date': self.publish_date,
            'fixed_price': self.fixed_price,
            'category': self.category
        }

class KingstoneDetailBooksService:
    def __init__(self):
        self.chrome_options = SeleniumHelper.get_chrome_options()
        # 添加更多的反爬蟲選項
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        # 添加隨機的 user-agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0'
        ]
        self.chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')
        
        self.log_helper = LogHelper('kingstone_detail_books_service')
        self.all_books = []
        self.start_time = datetime.now()
        
    def save_debug_info(self, driver, file_type, name):
        """保存調試信息（截圖或HTML）並立即刪除"""
        try:
            # 使用臨時文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if file_type == "screenshot":
                temp_file = f"{name}_{timestamp}.png"
                driver.save_screenshot(temp_file)
                self.log_helper.info(f"已保存並刪除調試截圖")
                # 立即刪除
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            elif file_type == "html":
                temp_file = f"{name}_{timestamp}.html"
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                self.log_helper.info(f"已保存並刪除調試HTML")
                # 立即刪除
                if os.path.exists(temp_file):
                    os.remove(temp_file)
        except Exception as e:
            self.log_helper.error(f"調試信息處理失敗: {str(e)}")
    
    def cleanup_temp_files(self):
        """不再需要清理臨時文件，因為已經立即刪除"""
        pass

    def __get_book_urls(self, csv_path=None):
        """從CSV文件獲取書籍URL列表"""
        try:
            if csv_path and os.path.exists(csv_path):
                self.log_helper.info(f"從CSV文件讀取書籍URL: {csv_path}")
                # 讀取CSV文件
                df = pd.read_csv(csv_path, dtype={'production_id': str})  # 確保production_id為字串
                
                # 檢查必要的列是否存在
                required_columns = ['url', 'title', 'production_id']
                for col in required_columns:
                    if col not in df.columns:
                        self.log_helper.error(f"CSV文件缺少必要的列: {col}")
                        return []
                
                # 檢查 publish_date 欄位
                publish_date_column = None
                if 'publish_date' in df.columns:
                    publish_date_column = 'publish_date'
                elif '出版日期' in df.columns:
                    publish_date_column = '出版日期'
                elif 'publishDate' in df.columns:
                    publish_date_column = 'publishDate'
                
                if publish_date_column:
                    self.log_helper.info(f"✅ 找到出版日期欄位: {publish_date_column}")
                else:
                    self.log_helper.warning("⚠️ 未找到出版日期欄位，將使用空值")
                
                # 提取URL列表
                book_urls = []
                for idx, row in df.iterrows():
                    url = row['url']
                    title = row['title']
                    production_id = row['production_id']
                    category = row.get('category', '')  # 可選列
                    
                    # 讀取出版日期
                    publish_date = ""
                    if publish_date_column and pd.notna(row[publish_date_column]):
                        publish_date = str(row[publish_date_column]).strip()
                        # 清理可能的前綴符號（如 |）
                        if publish_date.startswith('|'):
                            publish_date = publish_date[1:].strip()
                    
                    # 確保URL是完整的
                    if not url.startswith('http'):
                        url = base_url + url
                    
                    book_urls.append({
                        'url': url,
                        'title': title,
                        'production_id': production_id,
                        'category': category,
                        'publish_date': publish_date,
                        'row_index': idx  # 記錄行索引
                    })
                
                self.log_helper.info(f"從CSV文件中獲取到 {len(book_urls)} 個書籍URL")
                return book_urls
            else:
                self.log_helper.error(f"CSV文件不存在或未提供: {csv_path}")
                return []
        except Exception as e:
            self.log_helper.error(f"獲取書籍URL失敗: {str(e)}")
            return []

    def fetch_book_details(self, driver, book_info):
        """爬取單本書籍的詳細信息"""
        try:
            url = book_info['url']
            title = book_info['title']
            production_id = book_info['production_id']
            category_from_csv = book_info.get('category', '')
            publish_date_from_csv = book_info.get('publish_date', '')  # 從CSV讀取出版日期
            
            self.log_helper.info(f"正在爬取書籍: {title} ({url})")
            
            # 隨機延遲，模擬人類行為
            random_delay = random.uniform(2, 5)
            time.sleep(random_delay)
            
            # 訪問書籍頁面
            driver.get(url)
            
            # 執行JavaScript來模擬人類行為
            scroll_script = """
                // 模擬滾動行為
                function randomScroll() {
                    let scrollAmount = Math.floor(Math.random() * 100) + 50;
                    window.scrollBy(0, scrollAmount);
                }
                
                // 隨機滾動幾次
                let scrollTimes = Math.floor(Math.random() * 5) + 2;
                for (let i = 0; i < scrollTimes; i++) {
                    setTimeout(randomScroll, i * 500);
                }
                
                // 設置一些瀏覽器指紋變量以避免被檢測
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            """
            driver.execute_script(scroll_script)
            
            # 隨機延遲
            time.sleep(random.uniform(1.5, 3.5))
            
            # 等待頁面加載，增加超時時間
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".basicarea"))
            )
            
            # 創建DetailBook對象，使用已知信息和從CSV讀取的出版日期
            book = DetailBook(
                production_id=production_id,
                title=title,
                url=url,
                publish_date=publish_date_from_csv  # 使用從CSV讀取的出版日期
            )
            
            # 提取分類路徑
            try:
                # 方法1: 使用 li.basicunit.linkpill（某些書籍的格式）
                linkpill_li = driver.find_element(By.CSS_SELECTOR, "li.basicunit.linkpill")
                category_links = linkpill_li.find_elements(By.TAG_NAME, "a")
                if category_links:
                    # 提取分類文本並用 > 連接，過濾掉無效內容
                    category_texts = [link.text.strip() for link in category_links 
                                     if link.text.strip() and link.text.strip() not in ['?', '追蹤', '查看更多']]
                    book.category = " > ".join(category_texts)
                    self.log_helper.info(f"提取到分類路徑: {book.category}")
                else:
                    book.category = category_from_csv
            except:
                try:
                    # 方法2: 使用 div.linkpill
                    linkpill_div = driver.find_element(By.CSS_SELECTOR, "div.linkpill")
                    category_links = linkpill_div.find_elements(By.TAG_NAME, "a")
                    if category_links:
                        # 提取分類文本並用 > 連接，過濾掉無效內容
                        category_texts = [link.text.strip() for link in category_links 
                                         if link.text.strip() and link.text.strip() not in ['?', '追蹤', '查看更多']]
                        book.category = " > ".join(category_texts)
                        self.log_helper.info(f"提取到分類路徑(方法2): {book.category}")
                    else:
                        book.category = category_from_csv
                except:
                    try:
                        # 方法3: 完整路徑選擇器
                        linkpill_div = driver.find_element(By.CSS_SELECTOR, "#detaildataid > div > div.content_pcoll > div > div > div.linkpill")
                        category_links = linkpill_div.find_elements(By.TAG_NAME, "a")
                        if category_links:
                            # 提取分類文本並用 > 連接，過濾掉無效內容
                            category_texts = [link.text.strip() for link in category_links 
                                             if link.text.strip() and link.text.strip() not in ['?', '追蹤', '查看更多']]
                            book.category = " > ".join(category_texts)
                            self.log_helper.info(f"提取到分類路徑(方法3): {book.category}")
                        else:
                            book.category = category_from_csv
                    except:
                        try:
                            # 方法4: 使用原有的選擇器
                            category_links = driver.find_elements(By.CSS_SELECTOR, "li.basicunit.catbreadcrumb > a")
                            if category_links:
                                # 提取分類文本並用 > 連接
                                category_texts = [link.text.strip() for link in category_links 
                                                 if link.text.strip() and link.text.strip() not in ['?', '追蹤', '查看更多']]
                                book.category = " > ".join(category_texts)
                                self.log_helper.info(f"提取到分類路徑(方法4): {book.category}")
                            else:
                                book.category = category_from_csv
                        except Exception as cat_error:
                            self.log_helper.warning(f"無法提取分類路徑: {url}, 錯誤: {str(cat_error)}")
                            book.category = category_from_csv
            
            # 提取出版社
            try:
                # 方法1: 使用 XPath 根據文本內容查找
                publisher_elems = driver.find_elements(By.XPATH, "//li[@class='basicunit']//span[contains(text(), '出版社')]/following-sibling::a")
                if publisher_elems:
                    publisher_text = publisher_elems[0].text.strip()
                    # 清理文本，移除 "出版社："、"追蹤"、"?" 等
                    publisher_text = re.sub(r'^出版社[：:]\s*', '', publisher_text)
                    publisher_text = re.sub(r'\s*追蹤\s*', '', publisher_text)
                    publisher_text = re.sub(r'\s*\?\s*', '', publisher_text)
                    book.Publisher = publisher_text.strip()
                    self.log_helper.info(f"提取到出版社: {book.Publisher}")
                else:
                    raise Exception("方法1失敗")
            except:
                try:
                    # 方法2: 備用方法，動態查找包含出版社的元素
                    publisher_elems = driver.find_elements(By.CSS_SELECTOR, "li.basicunit > a[href*='/bookpublish/publist']")
                    if publisher_elems:
                        publisher_text = publisher_elems[0].text.strip()
                        # 清理文本
                        publisher_text = re.sub(r'^出版社[：:]\s*', '', publisher_text)
                        publisher_text = re.sub(r'\s*追蹤\s*', '', publisher_text)
                        publisher_text = re.sub(r'\s*\?\s*', '', publisher_text)
                        book.Publisher = publisher_text.strip()
                        self.log_helper.info(f"提取到出版社(備用): {book.Publisher}")
                    else:
                        self.log_helper.warning(f"無法提取出版社: {url}")
                except:
                    self.log_helper.warning(f"無法提取出版社: {url}")
            
            # 提取作者 - 直接定位到作者連結
            try:
                # 精確定位作者連結元素
                author_elem = driver.find_element(By.CSS_SELECTOR, "li.basicunit > span.title_basic:contains('作者') + a")
                book.author = author_elem.text.strip()
            except:
                try:
                    # 備用方法
                    author_elems = driver.find_elements(By.CSS_SELECTOR, "li.basicunit > a[href*='SearchLink']")
                    if author_elems:
                        book.author = author_elems[0].text.strip()
                    else:
                        self.log_helper.warning(f"無法提取作者: {url}")
                except:
                    self.log_helper.warning(f"無法提取作者: {url}")
            
            # 提取譯者（只提取譯者，忽略繪者）
            try:
                # 方法1: 使用 XPath 根據文本內容查找「譯者」（不包含「繪者」）
                translator_elems = driver.find_elements(By.XPATH, "//li[@class='basicunit']//span[contains(text(), '譯者')]")
                if translator_elems:
                    # 獲取整個 li 元素的文本
                    li_elem = translator_elems[0].find_element(By.XPATH, "..")
                    translator_text = li_elem.text.strip()
                    # 清理文本，移除 "譯者："、"追蹤"、"?" 等
                    translator_text = re.sub(r'^譯者[：:]\s*', '', translator_text)
                    translator_text = re.sub(r'\s*追蹤\s*', '', translator_text)
                    translator_text = re.sub(r'\s*\?\s*', '', translator_text)
                    # 移除換行符
                    translator_text = translator_text.replace('\n', ' ').strip()
                    book.translator = translator_text if translator_text else ""
                    if book.translator:
                        self.log_helper.info(f"提取到譯者: {book.translator}")
                else:
                    book.translator = ""
            except:
                try:
                    # 方法2: 備用方法，使用 JavaScript 提取（只查找「譯者」）
                    translator_elems = driver.find_elements(By.CSS_SELECTOR, "li.basicunit")
                    book.translator = ""
                    
                    for elem in translator_elems:
                        elem_text = elem.text.strip()
                        # 只檢查是否包含「譯者」（不包含「繪者」）
                        if "譯者" in elem_text and "譯者：" in elem_text:
                            # 使用JavaScript提取純文本
                            translator_text = driver.execute_script("""
                                var el = arguments[0];
                                var span = el.querySelector('span.title_basic');
                                if (span) {
                                    // 取得整個li的文本
                                    var fullText = el.textContent.trim();
                                    // 取得span的文本
                                    var spanText = span.textContent.trim();
                                    // 移除span的文本，只保留譯者名字
                                    var translatorName = fullText.replace(spanText, '').trim();
                                    return translatorName;
                                }
                                return '';
                            """, elem)
                            
                            if translator_text:
                                # 清理文本
                                translator_text = re.sub(r'\s*追蹤\s*', '', translator_text)
                                translator_text = re.sub(r'\s*\?\s*', '', translator_text)
                                translator_text = translator_text.replace('\n', ' ').strip()
                                book.translator = translator_text
                                self.log_helper.info(f"提取到譯者(備用): {book.translator}")
                                break
                    
                    if not book.translator:
                        book.translator = ""
                        
                except Exception as translator_error:
                    self.log_helper.warning(f"無法提取譯者: {url}, 錯誤: {str(translator_error)}")
                    book.translator = ""
            
            # 提取出版日期
            try:
                # 方法1: 使用 XPath 根據文本內容查找「出版日」
                publish_date_elems = driver.find_elements(By.XPATH, "//li[@class='basicunit']//span[contains(text(), '出版日')]")
                if publish_date_elems:
                    # 獲取整個 li 元素的文本
                    li_elem = publish_date_elems[0].find_element(By.XPATH, "..")
                    publish_date_text = li_elem.text.strip()
                    # 移除 "出版日期："、"出版日："、"追蹤"、"?" 等
                    publish_date_text = re.sub(r'^出版日期?[：:]\s*', '', publish_date_text)
                    publish_date_text = re.sub(r'\s*追蹤\s*', '', publish_date_text)
                    publish_date_text = re.sub(r'\s*\?\s*', '', publish_date_text)
                    publish_date_text = re.sub(r'^出版社[：:]\s*', '', publish_date_text)  # 避免混淆
                    # 移除換行符
                    publish_date_text = publish_date_text.replace('\n', ' ').strip()
                    if publish_date_text and not '出版社' in publish_date_text:
                        book.publish_date = publish_date_text
                        self.log_helper.info(f"提取到出版日期: {book.publish_date}")
            except Exception as e:
                # 如果爬取失敗，保留從CSV讀取的值
                self.log_helper.debug(f"無法提取出版日期: {url}, 保留CSV值: {book.publish_date}, 錯誤: {str(e)}")
            
            # 提取定價（fixed_price）
            try:
                # 優先使用新的精確選擇器
                price_selectors = [
                    # 方法1: 新的精確選擇器
                    "li.basicunit.price1 > div > div > s > b",
                    "li.basicunit.price1 s > b",
                    # 方法2: 原有的備用選擇器
                    ".basicfield span b.sty2",
                    # 方法3: 更廣泛的備用選擇器
                    "li.basicunit.price1 b",
                    ".basicfield b.sty2"
                ]
                
                price_found = False
                for selector in price_selectors:
                    try:
                        price_elem = driver.find_element(By.CSS_SELECTOR, selector)
                        if price_elem and price_elem.text.strip():
                            book.fixed_price = price_elem.text.strip()
                            price_found = True
                            self.log_helper.info(f"成功提取定價: {book.fixed_price} (使用選擇器: {selector})")
                            break
                    except:
                        continue
                
                if not price_found:
                    self.log_helper.warning(f"無法提取定價: {url}")
            except Exception as e:
                self.log_helper.warning(f"提取定價時發生錯誤: {url}, 錯誤: {str(e)}")
            
            # 提取ISBN
            try:
                # 多種方法嘗試提取ISBN
                isbn_found = False
                
                # 等待一下確保內容加載
                time.sleep(1)
                
                # 方法1: 完整路徑選擇器
                try:
                    isbn_elem = driver.find_element(By.CSS_SELECTOR, "#detaildataid > div > div.content_pcoll > div > div > div.tableregion_deda > div > ul > li:nth-child(2) > ul > li:nth-child(2)")
                    if isbn_elem:
                        isbn_text = isbn_elem.text.strip()
                        self.log_helper.debug(f"ISBN元素原始文本: '{isbn_text}'")
                        if isbn_text:
                            # 清理可能的前綴
                            isbn_text = re.sub(r'^ISBN[：:]*\s*', '', isbn_text, flags=re.IGNORECASE)
                            # 移除連字符和空格
                            isbn_text = isbn_text.replace('-', '').replace(' ', '')
                            # 只保留數字
                            isbn_match = re.search(r'(\d{13})', isbn_text)
                            if isbn_match:
                                book.isbn = isbn_match.group(1)
                                isbn_found = True
                                self.log_helper.info(f"成功提取ISBN (方法1): {book.isbn}")
                            else:
                                self.log_helper.warning(f"找到ISBN元素但無法提取13位數字，文本: '{isbn_text}'")
                except Exception as e:
                    self.log_helper.debug(f"方法1失敗: {e}")
                
                # 方法2: 簡化路徑
                if not isbn_found:
                    try:
                        isbn_elem = driver.find_element(By.CSS_SELECTOR, "div.tableregion_deda > div > ul > li:nth-child(2) > ul > li:nth-child(2)")
                        if isbn_elem:
                            isbn_text = isbn_elem.text.strip()
                            self.log_helper.debug(f"方法2 ISBN元素原始文本: '{isbn_text}'")
                            if isbn_text:
                                isbn_text = re.sub(r'^ISBN[：:]*\s*', '', isbn_text, flags=re.IGNORECASE)
                                isbn_text = isbn_text.replace('-', '').replace(' ', '')
                                isbn_match = re.search(r'(\d{13})', isbn_text)
                                if isbn_match:
                                    book.isbn = isbn_match.group(1)
                                    isbn_found = True
                                    self.log_helper.info(f"成功提取ISBN (方法2): {book.isbn}")
                    except Exception as e:
                        self.log_helper.debug(f"方法2失敗: {e}")
                
                # 方法3: 從table_1col_deda中提取
                if not isbn_found:
                    try:
                        isbn_elem = driver.find_element(By.CSS_SELECTOR, "ul.table_1col_deda > li:nth-of-type(2) > ul > li:nth-of-type(2)")
                        if isbn_elem:
                            isbn_text = isbn_elem.text.strip()
                            self.log_helper.debug(f"方法3 ISBN元素原始文本: '{isbn_text}'")
                            if isbn_text:
                                isbn_text = re.sub(r'^ISBN[：:]*\s*', '', isbn_text, flags=re.IGNORECASE)
                                isbn_text = isbn_text.replace('-', '').replace(' ', '')
                                isbn_match = re.search(r'(\d{13})', isbn_text)
                                if isbn_match:
                                    book.isbn = isbn_match.group(1)
                                    isbn_found = True
                                    self.log_helper.info(f"成功提取ISBN (方法3): {book.isbn}")
                    except Exception as e:
                        self.log_helper.debug(f"方法3失敗: {e}")
                
                # 方法2: 尋找包含「ISBN」文字的元素
                if not isbn_found:
                    try:
                        # 使用BeautifulSoup解析當前頁面
                        html_content = driver.page_source
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # 尋找所有包含「ISBN」的元素
                        all_elements = soup.find_all(string=re.compile(r'ISBN', re.IGNORECASE))
                        for elem in all_elements:
                            parent = elem.parent
                            if parent:
                                # 獲取父元素的文本
                                parent_text = parent.get_text()
                                # 使用正則表達式提取ISBN（13位數字）
                                isbn_match = re.search(r'ISBN[：:]*\s*(\d{13})', parent_text)
                                if not isbn_match:
                                    # 嘗試提取帶連字符的ISBN
                                    isbn_match = re.search(r'ISBN[：:]*\s*([\d-]{17})', parent_text)
                                
                                if isbn_match:
                                    book.isbn = isbn_match.group(1).replace('-', '')
                                    isbn_found = True
                                    self.log_helper.info(f"成功提取ISBN (方法2): {book.isbn}")
                                    break
                    except Exception as e:
                        self.log_helper.debug(f"方法2失敗: {e}")
                
                # 方法3: 從basicunit列表中尋找
                if not isbn_found:
                    try:
                        basic_units = driver.find_elements(By.CSS_SELECTOR, "li.basicunit")
                        for unit in basic_units:
                            unit_text = unit.text
                            if 'ISBN' in unit_text or 'isbn' in unit_text:
                                # 提取數字
                                isbn_match = re.search(r'(\d{13})', unit_text)
                                if isbn_match:
                                    book.isbn = isbn_match.group(1)
                                    isbn_found = True
                                    self.log_helper.info(f"成功提取ISBN (方法3): {book.isbn}")
                                    break
                    except Exception as e:
                        self.log_helper.debug(f"方法3失敗: {e}")
                
                if not isbn_found:
                    book.isbn = ""
                    self.log_helper.warning(f"未找到ISBN: {url}")
                    
            except Exception as e:
                self.log_helper.warning(f"提取ISBN時發生錯誤: {url}, 錯誤: {str(e)}")
                book.isbn = ""
            
            # 提取原文書名（整合自 kingstone_original_title_補正.py）
            try:
                # 獲取HTML內容
                html_content = driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                
                original_title = ""
                
                # 方法1: 使用完整 CSS 選擇器直接定位
                try:
                    pdnamemix_main = soup.find('div', class_='pdnamemix_main')
                    if pdnamemix_main:
                        # 在 pdnamemix_main 下尋找第一個 div
                        target_div = pdnamemix_main.find('div')
                        if target_div:
                            original_title = target_div.get_text(strip=True)
                            if original_title:
                                self.log_helper.info(f"成功提取原文書名 (方法1): {original_title}")
                except Exception as e:
                    self.log_helper.debug(f"方法1失敗: {e}")
                
                # 方法2: 從 pdnamemix_main 下的所有 div 中尋找包含外文的內容
                if not original_title:
                    try:
                        pdnamemix_main = soup.find('div', class_='pdnamemix_main')
                        if pdnamemix_main:
                            all_divs = pdnamemix_main.find_all('div')
                            for div in all_divs:
                                text = div.get_text(strip=True)
                                # 檢查是否包含外文字符
                                if text and (
                                    any('\u3040' <= c <= '\u309F' for c in text) or  # 日文平假名
                                    any('\u30A0' <= c <= '\u30FF' for c in text) or  # 日文片假名
                                    any('\u4E00' <= c <= '\u9FFF' for c in text) or  # 漢字（包括日本漢字）
                                    any(ord(c) < 128 and c.isalpha() for c in text)  # 英文字母
                                ):
                                    original_title = text
                                    self.log_helper.info(f"成功提取原文書名 (方法2): {original_title}")
                                    break
                    except Exception as e:
                        self.log_helper.debug(f"方法2失敗: {e}")
                
                # 方法3: 使用 Selenium 直接定位元素
                if not original_title:
                    try:
                        element = driver.find_element(By.CSS_SELECTOR, 'div.pdnamemix_main > div')
                        if element:
                            original_title = element.text.strip()
                            if original_title:
                                self.log_helper.info(f"成功提取原文書名 (方法3): {original_title}")
                    except Exception as e:
                        self.log_helper.debug(f"方法3失敗: {e}")
                
                # 方法4: 嘗試從其他可能的位置提取原文書名
                if not original_title:
                    try:
                        # 尋找包含「原文」關鍵字的元素
                        all_text_elements = soup.find_all(string=re.compile(r'原文'))
                        for elem in all_text_elements:
                            parent = elem.parent
                            if parent:
                                # 獲取後續的文本
                                next_sibling = parent.find_next_sibling()
                                if next_sibling:
                                    text = next_sibling.get_text(strip=True)
                                    if text:
                                        original_title = text
                                        self.log_helper.info(f"成功提取原文書名 (方法4): {original_title}")
                                        break
                    except Exception as e:
                        self.log_helper.debug(f"方法4失敗: {e}")
                
                book.original_title = original_title if original_title else ""
                
                if not original_title:
                    self.log_helper.warning(f"未找到原文書名 (production_id: {production_id})")
                
            except Exception as e:
                self.log_helper.warning(f"提取原文書名時發生錯誤: {url}, 錯誤: {str(e)}")
                book.original_title = ""
            
            self.log_helper.info(f"成功爬取書籍詳細信息: {title}")
            return book
        except Exception as e:
            self.log_helper.error(f"爬取書籍詳細信息失敗 ({url}): {str(e)}")
            self.save_debug_info(driver, "screenshot", f"book_error_{production_id}")
            self.save_debug_info(driver, "html", f"book_error_{production_id}")
            return None

    def get_output_csv_path(self, test_mode=False):
        """獲取輸出CSV檔案路徑"""
        # 無論測試模式與否，都使用 CommonHelper.get_save_file_path 來獲得正確的路徑和檔名格式
        # 格式: spider_data/2025/10/kingstone/detail_books/20251031_detail_books.csv
        return CommonHelper.get_save_file_path("kingstone", "detail_books")
    
    def update_row_in_csv(self, csv_path, row_index, book_dict):
        """更新 CSV 中指定行的資料"""
        try:
            # 讀取整個 CSV
            df = pd.read_csv(csv_path, encoding='utf-8-sig', dtype={'production_id': str})
            
            # 更新指定行的欄位
            for key, value in book_dict.items():
                if key in df.columns:
                    df.at[row_index, key] = value
            
            # 寫回 CSV
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            self.log_helper.info(f"已更新CSV第 {row_index} 行")
            return True
        except Exception as e:
            self.log_helper.error(f"更新CSV失敗: {str(e)}")
            return False
    
    def write_error_to_csv(self, production_id, title, url, error_message, error_csv_path):
        """將錯誤記錄寫入錯誤CSV"""
        try:
            import csv
            with open(error_csv_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['production_id', 'title', 'url', 'error_message']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerow({
                    'production_id': production_id,
                    'title': title if title else 'N/A',
                    'url': url,
                    'error_message': error_message
                })
            self.log_helper.info(f"已記錄錯誤: {production_id}")
            return True
        except Exception as e:
            self.log_helper.error(f"寫入錯誤記錄失敗: {str(e)}")
            return False
    
    def save_results_to_csv(self, books, test_mode=False):
        """將結果保存為CSV檔案（批次模式，僅用於向後相容）"""
        try:
            # 轉換書籍列表為DataFrame
            books_data = [book.to_dict() for book in books]
            df = pd.DataFrame(books_data)
            
            if df.empty:
                self.log_helper.warning("沒有書籍數據可保存")
                return None
            
            save_path = self.get_output_csv_path(test_mode)
            df.to_csv(save_path, index=False, encoding='utf-8-sig')
            self.log_helper.info(f"已保存結果至 {save_path}")
            
            return save_path
        except Exception as e:
            self.log_helper.error(f"保存結果失敗: {str(e)}")
            return None

    def Excute(self, csv_path=None, test_mode=False, max_books=None):
        """執行爬蟲的主要函數"""
        driver = None
        try:
            self.log_helper.info("開始執行金石堂詳細書目爬蟲")
            
            # 檢查CSV文件是否提供
            if not csv_path:
                self.log_helper.error("未提供CSV文件路徑，爬蟲終止")
                return False
            
            if not os.path.exists(csv_path):
                self.log_helper.error(f"CSV文件不存在: {csv_path}，爬蟲終止")
                return False
                
            # 獲取書籍URL列表
            book_urls = self.__get_book_urls(csv_path)
            if not book_urls:
                self.log_helper.error("未能從CSV文件獲取書籍URL，爬蟲終止")
                return False
                
            self.log_helper.info(f"從CSV文件載入了 {len(book_urls)} 本書籍URL")
            
            # 如果是測試模式，只處理前10本
            if test_mode:
                book_urls = book_urls[:10]
                self.log_helper.info(f"測試模式: 只處理前 {len(book_urls)} 本書籍")
            
            # 如果指定了最大書籍數，限制處理數量
            if max_books and isinstance(max_books, int) and max_books > 0:
                book_urls = book_urls[:max_books]
                self.log_helper.info(f"限制處理數量: {len(book_urls)} 本書籍")
            
            # 直接使用輸入的 CSV 作為輸出（動態更新原始檔案）
            output_csv_path = csv_path
            self.log_helper.info(f"將動態更新原始CSV檔案: {output_csv_path}")
            
            # 準備錯誤記錄CSV檔案（放在同一目錄）
            import csv as csv_module
            today_str = datetime.now().strftime('%Y%m%d')
            csv_dir = os.path.dirname(csv_path)
            csv_name = os.path.basename(csv_path).replace('.csv', '')
            error_csv_path = os.path.join(csv_dir, f"{csv_name}_error.csv")
            with open(error_csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['production_id', 'title', 'url', 'error_message']
                writer = csv_module.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
            self.log_helper.info(f"已創建錯誤記錄CSV檔案: {error_csv_path}")
            
            # 初始化瀏覽器
            driver = webdriver.Chrome(options=self.chrome_options)
            try:
                # 先最小化再設置大小，避免最大化狀態衝突
                driver.minimize_window()
                time.sleep(0.5)
                driver.set_window_size(1200, 800)
            except Exception as e:
                self.log_helper.warning(f"設置窗口大小失敗: {e}，繼續執行")
            
            # 依序處理每本書籍
            consecutive_errors = 0
            max_consecutive_errors = 3
            
            for i, book_info in enumerate(book_urls):
                try:
                    self.log_helper.info(f"處理書籍 {i+1}/{len(book_urls)}: {book_info['title']}")
                    
                    # 檢查是否需要重啟瀏覽器來避免被封鎖
                    if i > 0 and i % 10 == 0:
                        self.log_helper.info("重啟瀏覽器以避免被封鎖...")
                        driver.quit()
                        time.sleep(random.uniform(10, 15))  # 較長的休息時間
                        driver = webdriver.Chrome(options=self.chrome_options)
                        try:
                            # 先最小化再設置大小，避免最大化狀態衝突
                            driver.minimize_window()
                            time.sleep(0.5)
                            driver.set_window_size(1200, 800)
                        except Exception as e:
                            self.log_helper.warning(f"設置窗口大小失敗: {e}，繼續執行")
                    
                    # 較長的隨機延遲，避免請求過於頻繁
                    if i > 0:
                        delay = random.uniform(5, 12)
                        self.log_helper.info(f"等待 {delay:.2f} 秒後繼續...")
                        time.sleep(delay)
                    
                    book = self.fetch_book_details(driver, book_info)
                    if book:
                        self.all_books.append(book)
                        # 動態更新 CSV 的對應行
                        row_index = book_info.get('row_index')
                        self.update_row_in_csv(output_csv_path, row_index, book.to_dict())
                        consecutive_errors = 0  # 重置連續錯誤計數
                    else:
                        consecutive_errors += 1
                        # 記錄失敗到錯誤CSV
                        self.write_error_to_csv(
                            book_info.get('production_id', 'N/A'),
                            book_info.get('title', 'N/A'),
                            book_info.get('url', 'N/A'),
                            "Failed to fetch book details (returned None)",
                            error_csv_path
                        )
                except Exception as book_error:
                    self.log_helper.error(f"處理書籍 {book_info['title']} 時發生錯誤: {str(book_error)}")
                    consecutive_errors += 1
                    # 記錄錯誤到CSV
                    self.write_error_to_csv(
                        book_info.get('production_id', 'N/A'),
                        book_info.get('title', 'N/A'),
                        book_info.get('url', 'N/A'),
                        f"Exception: {str(book_error)}",
                        error_csv_path
                    )
                    
                    # 如果連續發生多次錯誤，可能被封鎖，暫停一段時間
                    if consecutive_errors >= max_consecutive_errors:
                        self.log_helper.warning(f"連續 {consecutive_errors} 次錯誤，可能被封鎖，暫停 60 秒...")
                        time.sleep(60)  # 暫停較長時間
                        
                        # 重啟瀏覽器
                        try:
                            driver.quit()
                        except:
                            pass
                        
                        driver = webdriver.Chrome(options=self.chrome_options)
                        try:
                            # 先最小化再設置大小，避免最大化狀態衝突
                            driver.minimize_window()
                            time.sleep(0.5)
                            driver.set_window_size(1200, 800)
                        except Exception as e:
                            self.log_helper.warning(f"設置窗口大小失敗: {e}，繼續執行")
                        consecutive_errors = 0  # 重置連續錯誤計數
                    
                    continue
            
            # 由於已經即時寫入，這裡只需要記錄結果
            self.log_helper.info(f"共收集了 {len(self.all_books)} 本書籍的詳細信息")
            self.log_helper.info(f"所有書籍已即時寫入至: {output_csv_path}")
            
            # 計算總執行時間
            end_time = datetime.now()
            duration = end_time - self.start_time
            self.log_helper.info(f"爬蟲執行完成，總時間: {duration}")
            
            return True
            
        except Exception as e:
            self.log_helper.error(f"執行爬蟲時發生錯誤: {str(e)}")
            self.log_helper.error(traceback.format_exc())
            return False
            
        finally:
            if driver:
                driver.quit()

def Excute(csv_path=None, test_mode=False, max_books=None):
    """執行爬蟲的入口函數"""
    service = KingstoneDetailBooksService()
    return service.Excute(csv_path, test_mode, max_books)

if __name__ == "__main__":
    # 直接執行時，要求手動輸入CSV路徑
    csv_path = input("請輸入CSV文件路徑: ").strip()
    
    if csv_path and os.path.exists(csv_path):
        print(f"使用CSV文件: {csv_path}")
        Excute(csv_path=csv_path, test_mode=False)
    else:
        print(f"錯誤: 提供的CSV文件不存在或路徑無效: {csv_path}")
        print("爬蟲終止")