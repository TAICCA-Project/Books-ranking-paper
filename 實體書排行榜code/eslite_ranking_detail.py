import sys
import os

# 確保能找到helper模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from helper.log_helper import LogHelper
from helper.common_helper import CommonHelper
from helper.selenium_helper import SeleniumHelper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import json
import csv
import concurrent.futures
import re
import time
import random
import pandas as pd
import glob

log = LogHelper('eslite_allbooks_service')

def get_base_file_path():
    return CommonHelper.get_save_file_path('eslite', 'base_allbook')

def parse_netscape_cookies(cookie_file):
    """解析 Netscape 格式的 cookies 文件"""
    cookies = []
    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            for line in f:
                # 跳過註釋和空行
                if line.startswith('#') or line.strip() == '':
                    continue
                
                # 解析 cookie 行
                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    domain = parts[0]
                    flag = parts[1]
                    path = parts[2]
                    secure = parts[3]
                    expiry = parts[4]
                    name = parts[5]
                    value = parts[6]
                    
                    cookie = {
                        'name': name,
                        'value': value,
                        'domain': domain,
                        'path': path,
                        'secure': secure.upper() == 'TRUE',
                        'httpOnly': False
                    }
                    
                    if expiry != '0':
                        try:
                            cookie['expiry'] = int(expiry)
                        except ValueError:
                            pass
                    
                    cookies.append(cookie)
        
        log.info(f"成功從 Netscape 格式文件讀取 {len(cookies)} 個 cookies")
        return cookies
    except Exception as e:
        log.error(f"解析 Netscape cookies 文件時發生錯誤: {e}")
        return []

base_url = "https://www.eslite.com"
params = "?final_price=0,&publishDate=0&sort=manufacturer_date+desc&display=list&start={}&status=add_to_shopping_cart&categories=[\"{}\"]&exp=o"
books_info = []
processed_production_ids = set()
process_count = 7
date_threshold = datetime.strptime("2025-07-23", "%Y-%m-%d")
record_date = datetime.now().strftime('%Y-%m-%d')
cookies = []
progress = 0
max_retry = 3
temp_files = []

def save_temp_file(file_path):
    """記錄臨時文件，以便程序結束時刪除"""
    global temp_files
    temp_files.append(file_path)

def cleanup_temp_files():
    """清理所有臨時文件（截圖和HTML）"""
    global temp_files
    log.info("開始清理臨時文件...")
    
    # 刪除列表中記錄的文件
    for file_path in temp_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                log.info(f"已刪除: {file_path}")
        except Exception as e:
            log.error(f"無法刪除文件 {file_path}: {e}")
    
    # 再次檢查和刪除可能的遺留截圖和HTML文件
    patterns = [
        "*.png", "detail_*.png", "category_*.png", "display_mode_*.png", "*screenshot*.png",
        "*.html", "*_page_*.html", "*_page_source.html", "source_*.html", "debug_*.html",
        "temp_*.html", "*_source.html", "*_debug.html", "*_html_content.html"
    ]
    
    directories_to_check = [
        ".",
        "test_results",
        os.path.join("Books-main_紙本書目_電子書目與排行榜", "test_results"),
    ]
    
    for directory in directories_to_check:
        if os.path.exists(directory):
            log.info(f"檢查目錄: {directory}")
            for pattern in patterns:
                pattern_path = os.path.join(directory, pattern)
                for file_path in glob.glob(pattern_path):
                    try:
                        os.remove(file_path)
                        log.info(f"已刪除遺留文件: {file_path}")
                    except Exception as e:
                        log.error(f"無法刪除遺留文件 {file_path}: {e}")
    
    temp_files = []
    log.info("臨時文件清理完成")

def switch_to_list_view(driver):
    """點擊列表視圖按鈕"""
    try:
        time.sleep(3)
        
        list_view_selectors = [
            ".icon-size.icon-list-normal",
            ".icon-list-normal",
            "//span[contains(@class, 'icon-list-normal')]",
            "//div[contains(@class, 'search-display-mode')]//span[contains(@class, 'icon-list')]"
        ]
        
        for selector in list_view_selectors:
            try:
                if selector.startswith("//"):
                    button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:
                    button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                
                log.info("找到列表視圖按鈕")
                driver.execute_script("arguments[0].click();", button)
                log.info("已點擊列表視圖按鈕")
                time.sleep(3)
                return True
            except Exception as e:
                log.warning(f"嘗試選擇器 {selector} 失敗: {e}")
                continue
        
        screenshot_path = f"display_mode_not_found.png"
        driver.save_screenshot(screenshot_path)
        save_temp_file(screenshot_path)
        log.warning(f"無法找到列表視圖按鈕，已保存截圖: {screenshot_path}")
        
        return False
    except Exception as e:
        log.error(f"切換列表視圖時出錯: {e}")
        import traceback
        traceback.print_exc()
        return False

def click_next_page(driver, current_page):
    """點擊下一頁按鈕或特定頁碼按鈕"""
    try:
        page_number = current_page + 1
        page_button_selectors = [
            f"div.page-items-group div.item[data-position='{page_number}'] button",
            f"div.page-number div.item[data-position='{page_number}'] button",
            f"div.page-items-group div.item:nth-child({page_number}) button",
            f"//div[contains(@class, 'page-items-group')]/div[contains(@class, 'item') and @data-position='{page_number}']//button",
            f"//div[contains(@class, 'page-number')]//span[text()='{page_number}']/parent::button"
        ]
        
        for selector in page_button_selectors:
            try:
                if selector.startswith("//"):
                    button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:
                    button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                
                print(f"找到頁碼按鈕: {page_number}")
                driver.execute_script("arguments[0].click();", button)
                print(f"已點擊頁碼按鈕: {page_number}")
                return True
            except:
                continue
        
        next_button_selectors = [
            "div.item[data-gid='pagination-next'] button",
            ".page-number .item[data-gid='pagination-next'] button",
            "//div[contains(@class, 'item') and @data-gid='pagination-next']//button",
            "//button//span[contains(@class, 'icon-fa-chevron-right')]/parent::button"
        ]
        
        for selector in next_button_selectors:
            try:
                if selector.startswith("//"):
                    button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:
                    button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                
                print("找到下一頁按鈕")
                driver.execute_script("arguments[0].click();", button)
                print("已點擊下一頁按鈕")
                return True
            except:
                continue
        
        print("無法找到下一頁按鈕，可能已到最後一頁")
        
        screenshot_path = f"pagination_not_found_page_{current_page}.png"
        driver.save_screenshot(screenshot_path)
        save_temp_file(screenshot_path)
        print(f"已保存分頁截圖到: {screenshot_path}")
        
        html_path = f"pagination_not_found_page_{current_page}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        save_temp_file(html_path)
        
        return False
    except Exception as e:
        print(f"點擊下一頁按鈕時出錯: {e}")
        import traceback
        traceback.print_exc()
        return False

class BookRanking:
    def __init__(self, id, title, author, translator, publish_date, publisher, dis_price, discount, url, categories):
        self.production_id = id
        self.title = title
        self.author = author
        self.translator = translator
        self.publish_date = publish_date
        self.publisher = publisher
        self.dis_price = dis_price  # 保留以維持向後兼容
        self.discount = discount  # 保留以維持向後兼容
        self.url = url
        self.categories = categories
        self.price = None  # 新的價格欄位
        self.isbn = ""
        self.original_title = ""  # 新增原文書名欄位
    
    def all_books_data(self):
        return {
            "production_id": self.production_id,
            "title": self.title,
            "author": self.author,
            "translator": self.translator,
            "publisher": self.publisher,
            "publish_date": self.publish_date,
            "price": self.price,
            "isbn": self.isbn,
            "original_title": self.original_title,
            "categories": self.categories,
            "url": self.url
        }

def manual_login_and_get_cookies():
    """手動登入誠品並獲取 cookies"""
    driver = None
    try:
        print("\n" + "="*60)
        print("誠品手動登入模式")
        print("="*60)
        print("即將開啟瀏覽器，請按照以下步驟操作：")
        print("1. 在開啟的瀏覽器中手動登入您的誠品帳號")
        print("2. 確認已成功登入（可看到會員名稱）")
        print("3. 完成後，回到此視窗")
        print("="*60)
        
        log.info("啟動瀏覽器進行手動登入")
        
        # 初始化瀏覽器
        chrome_options = SeleniumHelper.get_chrome_options()
        driver = SeleniumHelper.init_driver_with_options(chrome_options)
        
        # 訪問誠品首頁
        driver.get("https://www.eslite.com")
        time.sleep(3)
        
        # 等待使用者手動登入
        input("\n完成登入後，按 Enter 鍵繼續...")
        
        log.info("使用者確認已登入，開始獲取 cookies")
        print("\n✅ 正在獲取 cookies...")
        
        # 獲取所有 cookies
        cookies = driver.get_cookies()
        
        if cookies:
            print(f"✅ 成功獲取 {len(cookies)} 個 cookies")
            log.info(f"成功獲取 {len(cookies)} 個 cookies")
            
            # 保存 cookies 到文件（JSON 格式，與 eslite_orc_service.py 兼容）
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                cookie_dir = os.path.join(script_dir, 'cookies')
                os.makedirs(cookie_dir, exist_ok=True)
                
                # 生成時間戳文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                cookie_file = os.path.join(cookie_dir, f'eslite_cookies_{timestamp}.json')
                
                # 同時保存最新版本（覆蓋舊的）
                latest_cookie_file = os.path.join(cookie_dir, 'eslite_cookies_latest.json')
                
                # 準備 JSON 數據
                cookie_data = {
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "source": "manual_login_from_detail_script",
                    "cookies": cookies
                }
                
                # 保存時間戳版本
                with open(cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(cookie_data, f, ensure_ascii=False, indent=2)
                
                # 保存最新版本
                with open(latest_cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(cookie_data, f, ensure_ascii=False, indent=2)
                
                print(f"✅ Cookies 已保存 (JSON 格式):")
                print(f"   - 時間戳版本: {os.path.basename(cookie_file)}")
                print(f"   - 最新版本: {os.path.basename(latest_cookie_file)}")
                log.info(f"Cookies 已保存至: {cookie_file}")
                log.info(f"Cookies 已保存至: {latest_cookie_file}")
                
                # 同時保存 Netscape 格式（向後兼容）
                cookie_path_netscape = os.path.join(cookie_dir, 'www.eslite.com_cookies_manual.txt')
                with open(cookie_path_netscape, 'w', encoding='utf-8') as f:
                    f.write("# Netscape HTTP Cookie File\n")
                    f.write("# This is a generated file! Do not edit.\n\n")
                    for cookie in cookies:
                        domain = cookie.get('domain', '')
                        flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                        path = cookie.get('path', '/')
                        secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                        expiry = str(cookie.get('expiry', 0))
                        name = cookie.get('name', '')
                        value = cookie.get('value', '')
                        
                        f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
                log.info(f"也保存了 Netscape 格式: {cookie_path_netscape}")
                
            except Exception as e:
                log.warning(f"保存 cookies 失敗: {e}")
                print(f"⚠️  保存 cookies 失敗: {e}")
            
            return cookies
        else:
            print("❌ 未能獲取 cookies，可能未正確登入")
            log.warning("未能獲取 cookies")
            return []
            
    except Exception as e:
        log.error(f"手動登入過程發生錯誤: {e}")
        print(f"❌ 手動登入過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if driver:
            try:
                driver.quit()
                log.info("已關閉瀏覽器")
            except:
                pass

def Excute(input_cookies=None, csv_path=None, use_manual_login=None):
    global cookies
    global books_info
    global processed_production_ids
    
    books_info = []
    processed_production_ids.clear()
    
    # 決定登入方式
    if input_cookies is not None:
        # 使用傳入的 cookies
        cookies = input_cookies
        log.info("使用傳入的 cookies")
    else:
        # 詢問使用者登入方式
        if use_manual_login is None:
            print("\n" + "="*60)
            print("請選擇登入方式：")
            print("1. 從檔案讀取已保存的 cookies（預設）")
            print("2. 手動登入並獲取 cookies")
            print("3. 不登入，直接爬取")
            print("="*60)
            choice = input("請輸入選項 [1-3, 直接按 Enter 使用選項1]: ").strip()
            
            if choice == '2':
                use_manual_login = True
            elif choice == '3':
                use_manual_login = False
                cookies = []
            else:
                use_manual_login = False
        
        if use_manual_login:
            # 手動登入模式
            log.info("使用手動登入模式")
            print("\n正在啟動手動登入模式...")
            cookies = manual_login_and_get_cookies()
            if not cookies:
                print("\n⚠️  手動登入未成功獲取 cookies，將嘗試使用檔案中的 cookies")
                use_manual_login = False
        
        if not use_manual_login and not cookies:
            # 嘗試從 cookies 文件讀取
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 優先嘗試新的 JSON 格式 cookies（從 eslite_orc_service.py 生成）
            cookie_path_json_latest = os.path.join(script_dir, 'cookies', 'eslite_cookies_latest.json')
            cookie_path_manual = os.path.join(script_dir, 'cookies', 'www.eslite.com_cookies_manual.txt')
            cookie_path_auto = os.path.join(script_dir, 'cookies', 'www.eslite.com_cookies.txt')
            
            cookie_path = None
            cookie_format = None
            
            # 優先順序：JSON 最新版本 > 手動登入 Netscape > 自動登入 Netscape
            if os.path.exists(cookie_path_json_latest):
                cookie_path = cookie_path_json_latest
                cookie_format = 'json'
                log.info(f"使用 JSON 格式 cookies (最新): {cookie_path}")
                print(f"✅ 找到 cookies 文件: {os.path.basename(cookie_path)} (JSON 格式)")
            elif os.path.exists(cookie_path_manual):
                cookie_path = cookie_path_manual
                cookie_format = 'netscape'
                log.info(f"使用手動登入保存的 Netscape cookies: {cookie_path}")
                print(f"✅ 找到 cookies 文件: {os.path.basename(cookie_path)} (Netscape 格式)")
            elif os.path.exists(cookie_path_auto):
                cookie_path = cookie_path_auto
                cookie_format = 'netscape'
                log.info(f"使用自動登入保存的 Netscape cookies: {cookie_path}")
                print(f"✅ 找到 cookies 文件: {os.path.basename(cookie_path)} (Netscape 格式)")
            
            if cookie_path:
                log.info(f"嘗試從文件讀取 cookies: {cookie_path}")
                
                if cookie_format == 'json':
                    # 讀取 JSON 格式
                    try:
                        with open(cookie_path, 'r', encoding='utf-8') as f:
                            cookie_data = json.load(f)
                            cookies = cookie_data.get('cookies', [])
                            log.info(f"成功從 JSON 文件讀取 {len(cookies)} 個 cookies")
                            print(f"✅ 成功讀取 {len(cookies)} 個 cookies")
                    except Exception as e:
                        log.error(f"讀取 JSON cookies 文件失敗: {e}")
                        print(f"❌ 讀取 JSON cookies 文件失敗: {e}")
                        cookies = []
                elif cookie_format == 'netscape':
                    # 讀取 Netscape 格式
                    cookies = parse_netscape_cookies(cookie_path)
            else:
                log.warning(f"❌ 未找到 cookies 文件")
                log.warning("將以未登入模式爬取")
                print("⚠️  未找到 cookies 文件，將以未登入模式爬取")
                cookies = []
    
    log.info("開始處理誠品詳細書目...")
    try:
        # 要求使用者輸入CSV檔案路徑
        if not csv_path:
            csv_path = input("請輸入CSV檔案的完整路徑: ").strip()
        
        if not csv_path:
            log.error("未輸入有效路徑，無法繼續爬取")
            print("未輸入有效路徑，無法繼續爬取")
            return []
        elif not os.path.exists(csv_path):
            log.error(f"檔案不存在: {csv_path}，無法繼續爬取")
            print(f"檔案不存在: {csv_path}，無法繼續爬取")
            return []
        
        log.info(f"從CSV檔案讀取URLs: {csv_path}")
        book_urls = []
        df = None
        column_mappings = {}
        
        try:
            df = pd.read_csv(csv_path, dtype={'production_id': str})
            
            # 檢查URL欄位
            if 'url' in df.columns:
                url_column = 'url'
            elif '書目連結' in df.columns:
                url_column = '書目連結'
            elif 'URL' in df.columns:
                url_column = 'URL'
            else:
                log.error(f"CSV檔案中找不到URL欄位，欄位名稱應為'url'或'書目連結'或'URL'")
                print(f"CSV檔案中找不到URL欄位，欄位名稱應為'url'或'書目連結'或'URL'")
                return []
            
            # 欄位映射：CSV欄位名 -> 內部欄位名
            column_mappings = {
                'ISBN': 'isbn',
                'isbn': 'isbn',
                'production_id': 'production_id',
                'title': 'title',
                'Publisher': 'publisher',
                'publisher': 'publisher',
                'author': 'author',
                'translator': 'translator',
                'original_title': 'original_title',
                'publish_date': 'publish_date',
                '出版日期': 'publish_date',
                'publishDate': 'publish_date',
                'fixed_price': 'price',
                'price': 'price',
                'category': 'categories',
                'categories': 'categories',
                'url': 'url',
                '書目連結': 'url',
                'URL': 'url'
            }
            
            log.info(f"✅ CSV 欄位: {list(df.columns)}")
            
            book_data = []  # 儲存書籍資料
            for _, row in df.iterrows():
                url = row[url_column]
                if isinstance(url, str) and 'product' in url:
                    # 從CSV讀取所有現有欄位的值
                    existing_data = {}
                    for csv_col, internal_col in column_mappings.items():
                        if csv_col in df.columns:
                            value = row[csv_col]
                            # 只保存非空值
                            if pd.notna(value) and str(value).strip() != '':
                                cleaned_value = str(value).strip()
                                # 清理可能的前綴符號（如 |）
                                if cleaned_value.startswith('|'):
                                    cleaned_value = cleaned_value[1:].strip()
                                if cleaned_value:  # 再次確認清理後不為空
                                    existing_data[internal_col] = cleaned_value
                    
                    book_data.append({
                        'url': url,
                        'existing_data': existing_data
                    })
                    book_urls.append(url)
            
            log.info(f"從CSV檔案讀取到 {len(book_urls)} 個URLs")
            print(f"從CSV檔案讀取到 {len(book_urls)} 個URLs")
            
            if not book_urls:
                log.error("CSV檔案中未找到有效的URL，無法繼續爬取")
                print("CSV檔案中未找到有效的URL，無法繼續爬取")
                return []
                
        except Exception as e:
            log.error(f"讀取CSV檔案時發生錯誤: {e}")
            print(f"讀取CSV檔案時發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        # 創建BookRanking對象列表
        books_to_process = []
        for book_item in book_data:
            try:
                url = book_item['url']
                existing_data = book_item.get('existing_data', {})
                
                production_id = re.search(r'/product/(\d+)', url)
                if not production_id:
                    log.warning(f"無法從URL提取ID: {url}")
                    continue
                production_id = production_id.group(1)
                
                # 使用現有資料，如果沒有則使用預設值
                book_info = BookRanking(
                    id=existing_data.get('production_id', production_id),
                    title=existing_data.get('title', '待獲取'),
                    author=existing_data.get('author', ''),
                    translator=existing_data.get('translator', ''),
                    publish_date=existing_data.get('publish_date', ''),
                    publisher=existing_data.get('publisher', ''),
                    dis_price=None,
                    discount=None,
                    url=url,
                    categories=existing_data.get('categories', '')
                )
                # 設置其他欄位
                book_info.isbn = existing_data.get('isbn', '')
                book_info.original_title = existing_data.get('original_title', '')
                book_info.price = existing_data.get('price', None)
                
                # 保存現有資料，用於後續判斷
                book_info.existing_data = existing_data
                
                books_to_process.append(book_info)
                processed_production_ids.add(production_id)
            except Exception as e:
                log.error(f"處理URL時出錯: {url}, 錯誤: {e}")
        
        log.info(f"需要處理 {len(books_to_process)} 本書的詳細信息")
        
        # 保存原CSV路徑和DataFrame，用於動態更新
        save_path = csv_path
        log.info(f"將動態更新原CSV檔案: {save_path}")
        
        # 準備錯誤記錄CSV檔案
        today_str = datetime.now().strftime('%Y%m%d')
        error_csv_dir = os.path.dirname(save_path)
        error_csv_path = os.path.join(error_csv_dir, f"{today_str}_eslite_error.csv")
        with open(error_csv_path, mode='w', newline='', encoding='utf-8-sig') as file:
            fieldnames = ['production_id', 'title', 'url', 'error_message']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
        log.info(f"已創建錯誤記錄CSV檔案: {error_csv_path}")
        
        # 獲取詳細信息（動態即時寫入）
        if books_to_process:
            __fetch_new_books_details(books_to_process, save_path, error_csv_path, df, column_mappings)
            
            log.info(f"完成處理誠品詳細書目，本次爬取 {len(books_info)} 本書，已動態更新至 {save_path}")
            print(f"完成處理誠品詳細書目，本次爬取 {len(books_info)} 本書，已動態更新至 {save_path}")
            
            return books_info
        else:
            log.info("沒有需要獲取詳細信息的書籍，處理完成")
            return []
    except Exception as e:
        log.error(f"處理誠品詳細書目時發生錯誤: {e}")
        print(f"處理誠品詳細書目時發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        cleanup_temp_files()

def __update_single_book_to_csv(book, df, csv_path, column_mappings):
    """即時更新單本書籍資料到CSV，只填充空欄位"""
    try:
        # 優先使用的CSV欄位名稱
        preferred_csv_columns = {
            'isbn': 'ISBN',
            'production_id': 'production_id',
            'title': 'title',
            'publisher': 'Publisher',
            'author': 'author',
            'translator': 'translator',
            'original_title': 'original_title',
            'publish_date': 'publish_date',
            'price': 'fixed_price',
            'categories': 'category',
            'url': 'url'
        }
        
        # 反向映射：內部欄位名 -> CSV欄位名
        reverse_mapping = {}
        for csv_col, internal_col in column_mappings.items():
            if internal_col not in reverse_mapping:
                reverse_mapping[internal_col] = []
            reverse_mapping[internal_col].append(csv_col)
        
        # 找到對應的行（可能有多個相同URL的行）
        url_mask = df['url'] == book.url
        if not url_mask.any():
            log.warning(f"在CSV中找不到URL: {book.url}")
            return False
        
        matching_indices = df[url_mask].index
        row_updated = False
        
        # 更新各個欄位
        internal_fields = {
            'isbn': book.isbn,
            'production_id': book.production_id,
            'title': book.title,
            'publisher': book.publisher,
            'author': book.author,
            'translator': book.translator,
            'original_title': book.original_title,
            'publish_date': book.publish_date,
            'price': book.price,
            'categories': book.categories
        }
        
        # 更新所有匹配的行
        for idx in matching_indices:
            for internal_col, new_value in internal_fields.items():
                # 找到對應的CSV欄位名
                csv_col = preferred_csv_columns.get(internal_col)
                
                # 如果優先欄位不存在，嘗試其他可能的欄位名
                if csv_col not in df.columns and internal_col in reverse_mapping:
                    for possible_col in reverse_mapping[internal_col]:
                        if possible_col in df.columns:
                            csv_col = possible_col
                            break
                
                # 更新欄位（只在為空或無效值時更新）
                if csv_col and csv_col in df.columns:
                    current_value = df.at[idx, csv_col]
                    # 檢查當前值是否為空、N/A 或其他無效值
                    is_empty = pd.isna(current_value) or str(current_value).strip() in ['', 'N/A', '待獲取', '待爬取']
                    # 檢查新值是否有效
                    is_valid_new = new_value and str(new_value).strip() not in ['', 'N/A', '待獲取', '待爬取']
                    
                    if is_empty and is_valid_new:
                        df.at[idx, csv_col] = new_value
                        log.info(f"  行{idx} 更新 {csv_col}: {current_value} -> {new_value}")
                        row_updated = True
        
        # 即時寫回CSV
        if row_updated:
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            log.info(f"✅ 已即時更新至CSV: {book.title}")
        
        return True
    except Exception as e:
        log.error(f"即時更新CSV失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def __write_error_to_csv(production_id, title, url, error_message, error_csv_path):
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
        log.info(f"已記錄錯誤: {production_id}")
        return True
    except Exception as e:
        log.error(f"寫入錯誤記錄失敗: {str(e)}")
        return False

def __fetch_new_books_details(new_books, output_csv_path=None, error_csv_path=None, df=None, column_mappings=None):
    """針對新書列表中的書籍，獲取詳細信息並動態寫入CSV"""
    log.info(f"開始獲取 {len(new_books)} 本書的詳細資料...")
    success_count = 0
    fail_count = 0
    
    # 不使用多線程，逐個處理
    for idx, book in enumerate(new_books, 1):
        try:
            log.info(f"[{idx}/{len(new_books)}] 處理: {book.url}")
            success = __fetch_details(book, error_csv_path)
            if success:
                success_count += 1
                # 即時更新CSV
                if output_csv_path and df is not None and column_mappings is not None:
                    __update_single_book_to_csv(book, df, output_csv_path, column_mappings)
                    print(f"✅ [{idx}/{len(new_books)}] 已即時寫入: {book.title}")
            else:
                fail_count += 1
                # 寫入錯誤記錄
                if error_csv_path:
                    __write_error_to_csv(
                        book.production_id,
                        book.title,
                        book.url,
                        "Failed to fetch details after retries",
                        error_csv_path
                    )
        except Exception as exc:
            log.error(f"獲取詳細資料時發生錯誤: {exc}")
            fail_count += 1
            # 寫入錯誤記錄
            if error_csv_path:
                __write_error_to_csv(
                    book.production_id,
                    book.title,
                    book.url,
                    str(exc),
                    error_csv_path
                )
            continue

    log.info(f"詳細資料獲取完成: 成功 {success_count} 本, 失敗 {fail_count} 本")
    return new_books

def __fetch_details(book_info, error_csv_path=None):
    global cookies, progress, max_retry
    driver = None
    for attempt in range(max_retry):
        try:
            log.info(f"爬取詳細頁面，第 {attempt+1} 次嘗試: {book_info.url}")
            
            chrome_options = SeleniumHelper.get_chrome_options()
            driver = SeleniumHelper.init_driver_with_options(chrome_options)
            
            driver.get(base_url)
            time.sleep(3)
            
            # 添加登入cookies
            if cookies:
                for cookie in cookies:
                    try:
                        driver.add_cookie(cookie)
                    except Exception as e:
                        print(f"添加cookie失敗: {e}")
            
            driver.get(book_info.url)
            time.sleep(random.uniform(8, 12))
            
            # 檢查是否被重定向到登入頁面
            if 'login' in driver.current_url.lower():
                log.warning(f"被重定向到登入頁面，嘗試重新登入")
                driver.quit()
                driver = None
                continue
            
            # 等待頁面完全載入
            try:
                WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(5)
                
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .product-information, .product-title"))
                    )
                    log.info("成功等待關鍵元素載入")
                except:
                    log.warning("等待關鍵元素超時，繼續嘗試爬取")
            except:
                log.warning("頁面載入超時，繼續嘗試爬取")

            # 獲取書籍標題
            if book_info.title == "待獲取" or book_info.title == "待爬取":
                try:
                    title_selectors = [
                        (By.CSS_SELECTOR, "h1.sans-font-semi-bold"),
                        (By.CSS_SELECTOR, "h1.product-title"),
                        (By.CSS_SELECTOR, "div.product-information h1"),
                        (By.CSS_SELECTOR, "div.product-header h1"),
                        (By.XPATH, "//h1[contains(@class, 'product-title')]"),
                        (By.XPATH, "//div[contains(@class, 'product-information')]/div/h1"),
                        (By.XPATH, "//h1")
                    ]
                    
                    for selector_type, selector in title_selectors:
                        try:
                            title_elements = driver.find_elements(selector_type, selector)
                            if title_elements and title_elements[0].text.strip():
                                book_info.title = title_elements[0].text.strip()
                                log.info(f"獲取標題: {book_info.title}")
                                break
                        except Exception as e:
                            log.warning(f"使用選擇器 {selector} 獲取標題失敗: {e}")
                            continue
                    
                    # 如果所有選擇器都失敗，嘗試從頁面標題獲取
                    if book_info.title == "待獲取" or book_info.title == "待爬取":
                        page_title = driver.title
                        if page_title:
                            if "|" in page_title:
                                book_info.title = page_title.split("|")[0].strip()
                                log.info(f"從頁面標題獲取書名: {book_info.title}")
                            else:
                                book_info.title = page_title.strip()
                                log.info(f"從完整頁面標題獲取書名: {book_info.title}")
                    
                    # 如果還是找不到，嘗試從元數據獲取
                    if book_info.title == "待獲取" or book_info.title == "待爬取":
                        try:
                            meta_title = driver.find_element(By.XPATH, "//meta[@property='og:title']").get_attribute("content")
                            if meta_title:
                                book_info.title = meta_title.strip()
                                log.info(f"從meta標籤獲取書名: {book_info.title}")
                        except Exception as e:
                            log.warning(f"從meta標籤獲取標題失敗: {e}")
                except Exception as e:
                    log.error(f"獲取標題失敗: {e}")

            # 獲取分類信息（只在為空時獲取）
            if not book_info.categories or book_info.categories == "":
                try:
                    category_selectors = [
                        (By.CSS_SELECTOR, "ol li.ec-breadcrumb-item a"),
                        (By.XPATH, "//ol[contains(@class, 'flex')]//li[contains(@class, 'ec-breadcrumb-item')]//a"),
                        (By.XPATH, "//nav[@aria-label='breadcrumb']//ol//li//a"),
                        (By.XPATH, "//ol//li[contains(@class, 'ec-breadcrumb-item')]//a"),
                        (By.CSS_SELECTOR, "nav[aria-label='breadcrumb'] ol li a"),
                        (By.XPATH, "//ol[contains(@class, 'ec-breadcrumb')]//a"),
                        (By.XPATH, "//nav[contains(@class, 'breadcrumb')]//a"),
                        (By.XPATH, "//div[contains(@class, 'breadcrumb')]//a"),
                        (By.XPATH, "//ol[contains(@class, 'breadcrumb')]//li"),
                        (By.CSS_SELECTOR, ".category a, .categories a")
                    ]
                    
                    categories = []
                    for selector_type, selector in category_selectors:
                        try:
                            category_elements = driver.find_elements(selector_type, selector)
                            if category_elements and len(category_elements) > 1:
                                categories = []
                                for cat_elem in category_elements[1:]:
                                    cat_text = cat_elem.text.strip()
                                    if cat_text and cat_text != "首頁" and cat_text not in categories:
                                        categories.append(cat_text)
                                
                                if categories:
                                    book_info.categories = " > ".join(categories)
                                    log.info(f"獲取分類: {book_info.categories}")
                                    log.info(f"使用選擇器成功: {selector}")
                                    break
                        except Exception as e:
                            log.warning(f"使用選擇器 {selector} 獲取分類失敗: {e}")
                            continue
                    
                    # 如果仍未找到分類，嘗試使用JavaScript直接獲取
                    if not book_info.categories:
                        try:
                            breadcrumb_js = """
                            var result = [];
                            var links = document.querySelectorAll('nav[aria-label="breadcrumb"] ol li a');
                            if (links.length === 0) {
                                links = document.querySelectorAll('ol li.ec-breadcrumb-item a');
                            }
                            if (links.length === 0) {
                                links = document.querySelectorAll('ol[class*="breadcrumb"] li a');
                            }
                            for (var i = 0; i < links.length; i++) {
                                if (links[i].textContent.trim() !== '首頁') {
                                    result.push(links[i].textContent.trim());
                                }
                            }
                            return result;
                            """
                            breadcrumb_categories = driver.execute_script(breadcrumb_js)
                            if breadcrumb_categories and len(breadcrumb_categories) > 0:
                                book_info.categories = " > ".join(breadcrumb_categories)
                                log.info(f"通過JavaScript獲取分類: {book_info.categories}")
                        except Exception as e:
                            log.warning(f"通過JavaScript獲取分類失敗: {e}")
                    
                    # 如果仍未找到分類，嘗試從頁面文本搜索
                    if not book_info.categories:
                        page_text = driver.find_element(By.TAG_NAME, "body").text
                        category_patterns = [
                            r'分類[：:]\s*([^\n\r]+)',
                            r'類別[：:]\s*([^\n\r]+)',
                            r'書籍分類[：:]\s*([^\n\r]+)'
                        ]
                        
                        for pattern in category_patterns:
                            cat_match = re.search(pattern, page_text)
                            if cat_match:
                                book_info.categories = cat_match.group(1).strip()
                                log.info(f"從頁面文本獲取分類: {book_info.categories}")
                                break
                except Exception as e:
                    log.error(f"獲取分類失敗: {e}")
            else:
                log.info(f"分類已存在，跳過爬取: {book_info.categories}")

            # 獲取其他基本信息
            try:
                # 獲取作者（只在為空時獲取）
                if not book_info.author or book_info.author == "":
                    author_selectors = [
                        (By.XPATH, "//div[contains(@class, 'author')]//div[contains(@class, 'group')]/a/span"),
                        (By.XPATH, "//div[contains(@class, 'author')]//span[contains(@class, 'text-underline')]"),
                        (By.CSS_SELECTOR, '.author .group:nth-child(2) span'),
                        (By.CSS_SELECTOR, '.author .group a span'),
                    ]
                    
                    for selector_type, selector in author_selectors:
                        try:
                            elements = driver.find_elements(selector_type, selector)
                            if elements and elements[0].text.strip():
                                book_info.author = elements[0].text.strip()
                                log.info(f"獲取作者: {book_info.author}")
                                break
                        except Exception as e:
                            log.warning(f"使用選擇器 {selector} 獲取作者失敗: {e}")
                            continue
                else:
                    log.info(f"作者已存在，跳過爬取: {book_info.author}")
                
                # 獲取譯者（只在為空時獲取）
                if not book_info.translator or book_info.translator == "":
                    translator_selectors = [
                        (By.XPATH, "//div[contains(@class, 'translator')]//div[contains(@class, 'group')]/a/span[contains(@class, 'text-underline')]"),
                        (By.XPATH, "//div[contains(@class, 'translator')]//a/span[contains(@class, 'text-underline')]"),
                        (By.CSS_SELECTOR, '.translator .group a span.text-underline'),
                        (By.CSS_SELECTOR, '.translator a span.text-underline'),
                        (By.CSS_SELECTOR, '.translator .group:nth-child(2) span'),
                        (By.XPATH, "//div[contains(@class, 'translator')]//span[contains(@class, 'text-underline')]"),
                    ]
                    
                    for selector_type, selector in translator_selectors:
                        try:
                            elements = driver.find_elements(selector_type, selector)
                            if elements and elements[0].text.strip():
                                book_info.translator = elements[0].text.strip()
                                log.info(f"獲取譯者: {book_info.translator}")
                                break
                        except Exception as e:
                            log.warning(f"使用選擇器 {selector} 獲取譯者失敗: {e}")
                            continue
                    
                    # 如果沒有譯者，設為空字串
                    if not book_info.translator:
                        book_info.translator = ""
                else:
                    log.info(f"譯者已存在，跳過爬取: {book_info.translator}")
                
                # 獲取出版社（只在為空時獲取）
                if not book_info.publisher or book_info.publisher == "":
                    publisher_selectors = [
                        (By.XPATH, "//div[contains(@class, 'publisher')]//div[contains(@class, 'group')]/a/span[contains(@class, 'text-underline')]"),
                        (By.CSS_SELECTOR, '.publisher .group a span.text-underline'),
                        (By.CSS_SELECTOR, '.publisher .group:nth-child(2) span'),
                    ]
                    
                    for selector_type, selector in publisher_selectors:
                        try:
                            publisher_element = driver.find_element(selector_type, selector)
                            if publisher_element and publisher_element.text.strip():
                                book_info.publisher = publisher_element.text.strip()
                                log.info(f"獲取出版社: {book_info.publisher}")
                                break
                        except:
                            continue
                else:
                    log.info(f"出版社已存在，跳過爬取: {book_info.publisher}")
                
                # 獲取出版日期（只在為空時獲取）
                if not book_info.publish_date or book_info.publish_date == "":
                    publish_date_selectors = [
                        # 新的結構：div.publicDate .group:nth-child(2) span
                        (By.CSS_SELECTOR, 'div.publicDate .group:nth-child(2) span'),
                        (By.XPATH, "//div[contains(@class, 'publicDate')]//div[@class='group'][2]//span"),
                        (By.XPATH, "//div[contains(@class, 'publicDate')]//div[contains(@class, 'group')][last()]//span"),
                        # 舊的結構（備用）
                        (By.XPATH, "//div[contains(@class, 'publish-date')]//div[contains(@class, 'group')]/span[contains(@class, 'text-underline')]"),
                        (By.CSS_SELECTOR, '.publish-date .group span.text-underline'),
                        (By.CSS_SELECTOR, '.publish-date .group:nth-child(2) span'),
                        (By.XPATH, "//div[contains(@class, 'date')]//span[contains(@class, 'text-underline')]"),
                        (By.XPATH, "//div[contains(@class, 'product-spec')]//span[contains(text(), '出版日期')]/../following-sibling::div"),
                    ]
                    
                    for selector_type, selector in publish_date_selectors:
                        try:
                            date_element = driver.find_element(selector_type, selector)
                            if date_element and date_element.text.strip():
                                date_text = date_element.text.strip()
                                # 轉換日期格式：2020年09月02日 -> 2020/9/2
                                date_match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_text)
                                if date_match:
                                    year = date_match.group(1)
                                    month = str(int(date_match.group(2)))  # 去掉前導0
                                    day = str(int(date_match.group(3)))    # 去掉前導0
                                    book_info.publish_date = f"{year}/{month}/{day}"
                                    log.info(f"獲取出版日期: {book_info.publish_date} (選擇器: {selector})")
                                    break
                                # 如果已經是 YYYY/M/D 或 YYYY/MM/DD 格式
                                elif re.match(r'\d{4}/\d{1,2}/\d{1,2}', date_text):
                                    # 標準化格式：去掉前導0
                                    date_parts = date_text.split('/')
                                    if len(date_parts) == 3:
                                        year = date_parts[0]
                                        month = str(int(date_parts[1]))
                                        day = str(int(date_parts[2]))
                                        book_info.publish_date = f"{year}/{month}/{day}"
                                    else:
                                        book_info.publish_date = date_text
                                    log.info(f"獲取出版日期: {book_info.publish_date} (選擇器: {selector})")
                                    break
                        except Exception as e:
                            log.warning(f"使用選擇器 {selector} 獲取出版日期失敗: {e}")
                            continue
                    
                    if not book_info.publish_date or book_info.publish_date == "":
                        book_info.publish_date = ""
                        log.warning(f"未找到出版日期")
                else:
                    log.info(f"出版日期已存在，跳過爬取: {book_info.publish_date}")
                
                # 獲取ISBN（只在為空時獲取）
                if not book_info.isbn or book_info.isbn == "" or book_info.isbn == "N/A":
                    isbn_selectors = [
                        # 新的結構：div.ec-col-12 span 包含 "ISBN13 /" 或 "ISBN10 /"
                        (By.XPATH, "//span[contains(text(), 'ISBN13')]"),
                        (By.XPATH, "//span[contains(text(), 'ISBN10')]"),
                        (By.CSS_SELECTOR, "div.ec-col-12 span"),
                        (By.XPATH, "//div[contains(@class, 'ec-col-12')]//span[contains(text(), 'ISBN')]"),
                        # 舊的結構（備用）
                        (By.XPATH, "//div[contains(@class, 'product-spec')]//span[contains(text(), 'ISBN')]/../following-sibling::div"),
                        (By.XPATH, "//div[contains(@class, 'product-spec')]//span[contains(text(), 'ISBN')]/../.."),
                        (By.XPATH, "//div[contains(text(), 'ISBN')]"),
                        (By.XPATH, "//span[contains(text(), 'ISBN')]"),
                    ]
                    
                    for selector_type, selector in isbn_selectors:
                        try:
                            isbn_elements = driver.find_elements(selector_type, selector)
                            for isbn_element in isbn_elements:
                                if isbn_element and isbn_element.text:
                                    isbn_text = isbn_element.text.strip()
                                    # 跳過不相關的文本
                                    if 'ISBN' not in isbn_text:
                                        continue
                                    
                                    # 提取 ISBN 數字
                                    # 支援格式：
                                    # - "ISBN13 / 9786269915231"
                                    # - "ISBN10 / 1234567890"
                                    # - "ISBN: 978-626-991-523-1"
                                    # - "9786269915231"
                                    isbn_match = re.search(r'ISBN(?:10|13)?\s*[:/]\s*(\d[\d-]+[\dXx])', isbn_text)
                                    if isbn_match:
                                        book_info.isbn = isbn_match.group(1).replace('-', '').upper()
                                        log.info(f"獲取ISBN: {book_info.isbn} (選擇器: {selector}, 原文: {isbn_text})")
                                        break
                                    else:
                                        # 如果沒有找到明確格式，嘗試提取任何連續數字（長度至少10位）
                                        isbn_match = re.search(r'(\d{10,13})', isbn_text)
                                        if isbn_match:
                                            book_info.isbn = isbn_match.group(1)
                                            log.info(f"獲取ISBN: {book_info.isbn} (選擇器: {selector}, 原文: {isbn_text})")
                                            break
                            
                            if book_info.isbn and book_info.isbn != 'N/A':
                                break
                        except Exception as e:
                            log.warning(f"使用選擇器 {selector} 獲取ISBN失敗: {e}")
                            continue
                    
                    if not book_info.isbn or book_info.isbn == "":
                        book_info.isbn = 'N/A'
                        log.warning(f"未找到ISBN")
                else:
                    log.info(f"ISBN已存在，跳過爬取: {book_info.isbn}")
                
                # 獲取原文書名（只在為空時獲取）
                if not book_info.original_title or book_info.original_title == "":
                    try:
                        original_title_selectors = [
                            (By.CSS_SELECTOR, "div.product-info h4"),
                            (By.CSS_SELECTOR, "h4.original-title"),
                            (By.CSS_SELECTOR, "div.product-information h4"),
                            (By.XPATH, "//div[contains(@class, 'product-info')]//h4"),
                            (By.XPATH, "//div[contains(@class, 'product-information')]//h4"),
                        ]
                        
                        for selector_type, selector in original_title_selectors:
                            try:
                                original_title_elements = driver.find_elements(selector_type, selector)
                                if original_title_elements and original_title_elements[0].text.strip():
                                    book_info.original_title = original_title_elements[0].text.strip()
                                    log.info(f"獲取原文書名: {book_info.original_title}")
                                    break
                            except Exception as e:
                                log.warning(f"使用選擇器 {selector} 獲取原文書名失敗: {e}")
                                continue
                        
                        if not book_info.original_title:
                            book_info.original_title = ""
                            log.warning(f"未找到原文書名")
                            
                    except Exception as e:
                        log.error(f"獲取原文書名失敗: {e}")
                        book_info.original_title = ""
                else:
                    log.info(f"原文書名已存在，跳過爬取: {book_info.original_title}")
                
                # 獲取價格（只在為空時獲取）
                if not book_info.price or book_info.price == "" or book_info.price == "N/A" or book_info.price is None:
                    try:
                        price_selectors = [
                            # 新的價格選擇器（優先）
                            (By.CSS_SELECTOR, "span.pre-product-price"),
                            (By.CSS_SELECTOR, "div.price-group span.pre-product-price"),
                            (By.XPATH, "//div[contains(@class, 'price-group')]//span[contains(@class, 'pre-product-price')]"),
                            # 原有的選擇器（備用）
                            (By.CSS_SELECTOR, "span.item-price"),
                            (By.CSS_SELECTOR, "span[class*='item-price']"),
                            (By.XPATH, "//span[contains(@class, 'item-price')]"),
                            (By.CSS_SELECTOR, ".product-price span.item-price"),
                            (By.CSS_SELECTOR, ".price-group span.item-price"),
                        ]
                        
                        for selector_type, selector in price_selectors:
                            try:
                                price_elements = driver.find_elements(selector_type, selector)
                                if price_elements and price_elements[0].text.strip():
                                    price_text = price_elements[0].text.strip()
                                    # 清理價格文本，只保留數字
                                    price_clean = re.sub(r'[^\d]', '', price_text)
                                    if price_clean:
                                        book_info.price = price_clean
                                        log.info(f"獲取價格: {book_info.price}")
                                        break
                            except Exception as e:
                                log.warning(f"使用選擇器 {selector} 獲取價格失敗: {e}")
                                continue
                        
                        if not book_info.price or book_info.price == "N/A":
                            # 嘗試使用JavaScript直接獲取
                            try:
                                price_js = """
                                var priceSpan = document.querySelector('span.item-price');
                                if (!priceSpan) {
                                    priceSpan = document.querySelector('span[class*="item-price"]');
                                }
                                if (priceSpan) {
                                    return priceSpan.textContent.trim();
                                }
                                return null;
                                """
                                price_text = driver.execute_script(price_js)
                                if price_text:
                                    price_clean = re.sub(r'[^\d]', '', price_text)
                                    if price_clean:
                                        book_info.price = price_clean
                                        log.info(f"通過JavaScript獲取價格: {book_info.price}")
                            except Exception as e:
                                log.warning(f"通過JavaScript獲取價格失敗: {e}")
                        
                        if not book_info.price or book_info.price == "":
                            book_info.price = 'N/A'
                            log.warning(f"無法獲取價格，設為N/A")
                            
                    except Exception as e:
                        log.error(f"獲取價格失敗: {e}")
                        book_info.price = 'N/A'
                else:
                    log.info(f"價格已存在，跳過爬取: {book_info.price}")
                    
            except Exception as e:
                log.error(f"獲取基本信息失敗: {e}")

            # 檢查 title 是否為空或無效
            if not book_info.title or book_info.title in ["待獲取", "待爬取", "", "N/A"]:
                error_msg = f"Title is null or invalid: {book_info.title}"
                log.error(error_msg)
                # 重置 title 以便重試
                book_info.title = "待獲取"
                if attempt < max_retry - 1:
                    log.info(f"標題無效，將在 {3} 秒後重試...")
                    time.sleep(3)
                    continue  # 觸發重試
                else:
                    # 達到最大重試次數，記錄錯誤
                    if error_csv_path:
                        __write_error_to_csv(
                            book_info.production_id,
                            book_info.title,
                            book_info.url,
                            error_msg,
                            error_csv_path
                        )
                    return False
            
            # 檢查 title 是否包含「│ 誠品線上」（表示爬取失敗，需要重爬）
            if "│ 誠品線上" in book_info.title or "| 誠品線上" in book_info.title:
                error_msg = f"Title contains '誠品線上', page not properly loaded: {book_info.title}"
                log.error(error_msg)
                # 重置 title 以便重試
                book_info.title = "待獲取"
                if attempt < max_retry - 1:
                    log.info(f"檢測到誠品線上標題，將在 {5} 秒後重試...")
                    time.sleep(5)
                    continue  # 觸發重試
                else:
                    # 達到最大重試次數，記錄錯誤
                    if error_csv_path:
                        __write_error_to_csv(
                            book_info.production_id,
                            book_info.title,
                            book_info.url,
                            error_msg,
                            error_csv_path
                        )
                    return False

            # 添加書籍到列表
            books_info.append(book_info)
            log.info(f"成功爬取詳細資訊: {book_info.title}")
            return True
            
        except Exception as e:
            log.error(f"詳細頁面處理錯誤: {e}")
            import traceback
            error_trace = traceback.format_exc()
            log.error(error_trace)
            
            if attempt < max_retry - 1:
                log.info(f"第 {attempt+1} 次嘗試失敗，將重試...")
                time.sleep(random.uniform(3, 5))
            else:
                log.error(f"達到最大重試次數 {max_retry}，放棄爬取詳細頁面")
                # 記錄到錯誤CSV
                if error_csv_path:
                    __write_error_to_csv(
                        book_info.production_id,
                        book_info.title if hasattr(book_info, 'title') else 'N/A',
                        book_info.url,
                        f"Exception after {max_retry} retries: {str(e)}",
                        error_csv_path
                    )
        
        finally:
            if driver:
                driver.quit()
    
    return False

if __name__ == "__main__":
    import sys
    
    # 可以從命令行傳入參數
    csv_path = None
    use_manual_login = None
    
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    
    if len(sys.argv) > 2 and sys.argv[2] == '--manual-login':
        use_manual_login = True
    
    result = Excute(csv_path=csv_path, use_manual_login=use_manual_login)
    
    if result:
        print(f"\n✅ 成功爬取 {len(result)} 本書的資料")
    else:
        print("\n⚠️  爬取完成，但沒有獲取到資料")