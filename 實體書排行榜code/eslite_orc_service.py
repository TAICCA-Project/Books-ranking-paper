"""
誠品線上書店登入服務 - 手動登入模式

此服務用於通過手動登入方式獲取誠品網站的 cookies。

使用方法：
1. 執行此腳本
2. 瀏覽器會自動打開並導航到誠品登入頁面
3. 手動在瀏覽器中完成登入操作
4. 登入完成後，在終端機按 Enter 鍵繼續
5. 腳本會自動獲取並返回 cookies

注意：不要關閉自動打開的瀏覽器視窗，直到腳本完成
"""

import sys
import os

# 確保能找到helper模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from helper.log_helper import LogHelper
from helper.selenium_helper import SeleniumHelper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import Config
import time
import traceback
import json
from datetime import datetime

log = LogHelper('eslite_orc_service')
scale_factor = Config.SCALE_FACTOR

def login_and_get_cookies(use_tor=False):
    driver = None
    try:
        # 根據參數決定是否使用Tor代理，默認不使用
        if use_tor:
            log.info("使用Tor代理進行登入")
            chrome_options = SeleniumHelper.get_chrome_options_with_tor()
        else:
            log.info("使用直接連接進行登入")
            chrome_options = SeleniumHelper.get_chrome_options()
        
        # 改善ChromeDriver初始化，加入更多錯誤處理
        try:
            print("正在初始化ChromeDriver...")
            driver = SeleniumHelper.init_driver_with_options(chrome_options)
            print("ChromeDriver初始化成功")
        except Exception as e:
            print(f"ChromeDriver初始化失敗: {e}")
            # 嘗試清理並重新初始化
            try:
                import subprocess
                import platform
                if platform.system() == "Windows":
                    subprocess.run("taskkill /f /im chrome.exe", shell=True, capture_output=True)
                    subprocess.run("taskkill /f /im chromedriver.exe", shell=True, capture_output=True)
                print("已清理現有Chrome進程，重新嘗試初始化...")
                driver = SeleniumHelper.init_driver_with_options(chrome_options)
                print("ChromeDriver重新初始化成功")
            except Exception as e2:
                print(f"ChromeDriver重新初始化也失敗: {e2}")
                raise e2
        
        # 訪問首頁先
        driver.get("https://www.eslite.com")
        time.sleep(3)
        
        # 檢查是否有cookie接受按鈕，有的話點擊
        try:
            cookie_accept = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '接受')]"))
            )
            cookie_accept.click()
            time.sleep(1)
        except:
            pass  # 可能沒有cookie提示

        # 導航到登入頁面
        print("正在前往登入頁面...")
        driver.get("https://www.eslite.com/login")
        time.sleep(3)
        
        # 等待登入表單載入
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "account"))
            )
            print("登入頁面已載入")
        except:
            print("等待登入頁面載入時發生錯誤，但繼續...")
        
        # 手動登入模式
        print("\n" + "="*60)
        print("請在瀏覽器中手動完成登入")
        print("登入完成後，請在此處按 Enter 繼續...")
        print("="*60 + "\n")
        
        # 等待用戶按 Enter
        input("按 Enter 繼續...")
        
        # 給予額外時間讓登入完成
        time.sleep(2)
        
        # 檢查是否登入成功
        try:
            current_url = driver.current_url
            print(f"當前URL: {current_url}")
            
            # 判斷是否已離開登入頁面
            if "login" not in current_url.lower():
                print("✓ 已離開登入頁面，登入可能成功")
            
            # 嘗試尋找會員相關元素
            try:
                member_element = driver.find_element(By.XPATH, "//*[contains(text(), '會員中心') or contains(text(), '我的帳戶')]")
                print("✓ 找到會員相關元素，確認登入成功！")
            except:
                print("⚠ 未找到明確的會員元素，但繼續嘗試獲取cookies")
            
            # 保存頁面截圖
            driver.save_screenshot("eslite_login_success.png")
            print("已保存登入後截圖: eslite_login_success.png")
            
            # 獲取所有cookies
            cookies = __get_cookies(driver)
            print(f"\n✓ 成功獲取到 {len(cookies)} 個cookies")
            
            # 顯示部分 cookie 信息（用於調試）
            for cookie in cookies[:5]:  # 只顯示前5個
                print(f"  - {cookie['name']}: {cookie['value'][:20]}...")
            
            # 保存 cookies 到文件
            cookie_saved = __save_cookies_to_file(cookies)
            if cookie_saved:
                print(f"✓ Cookies 已保存到文件: {cookie_saved}")
            
            return cookies
            
        except Exception as e:
            print(f"✗ 檢查登入狀態時發生錯誤: {e}")
            traceback.print_exc()
            
            # 即使發生錯誤，仍嘗試獲取cookies
            try:
                cookies = __get_cookies(driver)
                print(f"仍獲取到 {len(cookies)} 個cookies")
                
                # 保存 cookies 到文件
                cookie_saved = __save_cookies_to_file(cookies)
                if cookie_saved:
                    print(f"✓ Cookies 已保存到文件: {cookie_saved}")
                
                return cookies
            except:
                print("無法獲取cookies")
                return None
    except Exception as e:
        log.error(f"登入過程發生異常: {str(e)}")
        traceback.print_exc()
        return None
    finally:
        if driver:
            try:
                driver.save_screenshot("eslite_login_final.png")
                print("已保存最終登入畫面截圖")
            except Exception as e:
                print(f"保存截圖失敗: {e}")
            
            try:
                driver.quit()
                print("ChromeDriver已正常關閉")
            except Exception as e:
                print(f"關閉ChromeDriver時發生錯誤: {e}")
                # 強制終止Chrome進程
                try:
                    import subprocess
                    import platform
                    if platform.system() == "Windows":
                        subprocess.run("taskkill /f /im chrome.exe", shell=True, capture_output=True)
                        subprocess.run("taskkill /f /im chromedriver.exe", shell=True, capture_output=True)
                        print("已強制終止Chrome進程")
                except Exception as e2:
                    print(f"強制終止進程也失敗: {e2}")

def __get_cookies(driver):
    """獲取瀏覽器的所有 cookies"""
    all_cookies = driver.get_cookies()
    return all_cookies

def __save_cookies_to_file(cookies):
    """將 cookies 保存到 JSON 文件"""
    try:
        # 創建 cookies 目錄（如果不存在）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_dir = os.path.join(script_dir, "cookies")
        os.makedirs(cookies_dir, exist_ok=True)
        
        # 生成文件名（包含時間戳）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        cookie_file = os.path.join(cookies_dir, f"eslite_cookies_{timestamp}.json")
        
        # 同時保存一份最新的 cookies（覆蓋舊的）
        latest_cookie_file = os.path.join(cookies_dir, "eslite_cookies_latest.json")
        
        # 保存到文件
        cookie_data = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "cookies": cookies
        }
        
        with open(cookie_file, 'w', encoding='utf-8') as f:
            json.dump(cookie_data, f, ensure_ascii=False, indent=2)
        
        with open(latest_cookie_file, 'w', encoding='utf-8') as f:
            json.dump(cookie_data, f, ensure_ascii=False, indent=2)
        
        print(f"  保存時間戳版本: {cookie_file}")
        print(f"  保存最新版本: {latest_cookie_file}")
        
        return cookie_file
        
    except Exception as e:
        print(f"✗ 保存 cookies 到文件時發生錯誤: {e}")
        traceback.print_exc()
        return None

# 手動登入模式下不再需要此函數
# def __set_login_info(driver):
#     此函數已停用，改為手動登入模式

def Excute(use_tor=False):
    log.info("eslite_orc_service.main() - 手動登入模式")
    try:
        cookie_list = login_and_get_cookies(use_tor)
        log.info("eslite_orc_service.main() finished - cookies已獲取")
        return cookie_list
    except Exception as e:
        log.error(f"手動登入獲取cookies失敗: {e}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("\n" + "="*60)
    print("誠品線上書店 - 手動登入並獲取 Cookies")
    print("="*60 + "\n")
    
    cookies = Excute(use_tor=False)
    
    if cookies:
        print("\n" + "="*60)
        print(f"✓ 成功完成！共獲取 {len(cookies)} 個 cookies")
        print("="*60)
        print("\nCookies 已保存到:")
        print("  - 實體書排行榜code/cookies/eslite_cookies_latest.json (最新版本)")
        print("  - 實體書排行榜code/cookies/eslite_cookies_YYYYMMDD_HHMMSS.json (時間戳版本)")
    else:
        print("\n" + "="*60)
        print("✗ 獲取 cookies 失敗")
        print("="*60)