from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import sys
import os
import subprocess

await_time = 10

class SeleniumHelper :
    @staticmethod
    def get_chrome_options():
        options = webdriver.ChromeOptions()
        
        # 反Cloudflare檢測設置
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 模擬真實瀏覽器
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_argument('--accept-language=zh-TW,zh;q=0.9,en;q=0.8')
        
        # 原有設置
        options.add_argument('--ignore-ssl-errors=yes')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--start-maximized')
        options.accept_insecure_certs = True
        
        prefs = {
            "profile.default_content_setting_values.notifications": 2  # 1: 允许, 2: 阻止
        }
        options.add_experimental_option("prefs", prefs)
        options.page_load_strategy = 'eager'
        
        return options
    
    @staticmethod
    def is_tor_available():
        """檢查 Tor 代理是否可用"""
        import socket
        try:
            # 嘗試連接到默認 Tor SOCKS 端口 (9050)
            print(f"正在檢查 Tor 代理是否可用 (localhost:9050)...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)  # 設置超時為3秒
            s.connect(('127.0.0.1', 9050))
            s.close()
            print(f"✅ Tor 代理可用")
            return True
        except socket.error as e:
            print(f"❌ Tor 代理不可用: {e}")
            
            # 檢查是否有其他端口可用 (以防萬一)
            alternate_ports = [9052, 9054, 9056, 9058, 9060]
            for port in alternate_ports:
                try:
                    print(f"嘗試檢查替代端口 {port}...")
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1)
                    s.connect(('127.0.0.1', port))
                    s.close()
                    print(f"✅ 發現可用的替代 Tor 端口: {port}")
                    return True
                except:
                    pass
            
            print("⚠️ 未找到任何可用的 Tor 代理端口")
            return False

    @staticmethod
    def get_chrome_options_with_tor():
        """獲取配置了Tor代理的Chrome選項"""
        options = SeleniumHelper.get_chrome_options()  # 獲取基本配置
        
        # 尋找可用的Tor端口
        tor_port = SeleniumHelper.find_available_tor_port()
        if tor_port:
            # 如果找到可用端口，設置代理
            proxy = f"socks5://127.0.0.1:{tor_port}"
            print(f"使用Tor代理: {proxy}")
            options.add_argument(f'--proxy-server={proxy}')
            
            # 增加Tor相關設置
            options.add_argument("--disable-web-security")  # 禁用部分網頁安全策略，以便Tor工作更順暢
            options.add_argument("--ignore-certificate-errors")  # 忽略SSL錯誤
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")  # 禁用站點隔離
        else:
            # 如果沒有找到可用端口，則不使用代理
            print("⚠️ 無法找到可用的Tor代理端口，將使用直接連接")
            # 嘗試啟動Tor
            try:
                if sys.platform.startswith('win'):  # Windows
                    subprocess.Popen("start /B tor.bat", shell=True)
                elif sys.platform == 'darwin':  # macOS
                    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tor_control.sh")
                    subprocess.Popen(f"bash {script_path} start", shell=True)
                else:  # Linux
                    subprocess.Popen("tor", shell=True)
                
                print("已嘗試啟動Tor服務，可能需要重新執行程序")
            except Exception as e:
                print(f"啟動Tor失敗: {e}")
        
        return options

    @staticmethod
    def find_available_tor_port():
        """找出可用的 Tor SOCKS 端口"""
        import socket
        # 首先嘗試默認端口
        try:
            print(f"檢查默認 Tor 端口 9050...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect(('127.0.0.1', 9050))
            s.close()
            print(f"✅ 默認 Tor 端口 9050 可用")
            return 9050
        except:
            pass
            
        # 嘗試其他可能的端口
        alternate_ports = [9052, 9054, 9056, 9058, 9060]
        for port in alternate_ports:
            try:
                print(f"檢查替代 Tor 端口 {port}...")
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                s.connect(('127.0.0.1', port))
                s.close()
                print(f"✅ 發現可用的替代 Tor 端口: {port}")
                return port
            except:
                pass
        
        print("❌ 未找到任何可用的 Tor 端口")
        return None
    
    @staticmethod
    def init_driver_with_options(options):
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
        
    @staticmethod
    def init_driver():
        # 使用默認選項
        chrome_options = SeleniumHelper.get_chrome_options()
        return SeleniumHelper.init_driver_with_options(chrome_options)
    
    @staticmethod
    def safe_find_element(driver, by, value, attribute=None, await_time=10):
        try:
            element = WebDriverWait(driver, await_time).until(
                EC.presence_of_element_located((by, value))
            )
            if attribute:
                return element.get_attribute(attribute)
            return element.text
        except Exception as e:
            # print(f"无法找到元素 {value}, 错误: {e}")
            return ''
        
    @staticmethod
    def safe_find_elements(driver, by, value, await_time=10):
        try:
            elements = WebDriverWait(driver, await_time).until(
                EC.presence_of_all_elements_located((by, value))
            )
            return elements
        except Exception as e:
            # print(f"无法找到元素 {value}, 错误: {e}")
            return []
        
    @staticmethod
    def safe_find_elements_text(driver, by, value, await_time=await_time):
        try:
            elements = WebDriverWait(driver, await_time).until(
                EC.presence_of_all_elements_located((by, value))
            )
            return [element.text for element in elements]
        except Exception as e:
            # print(f"无法找到元素 {value}, 错误: {e}")
            return []