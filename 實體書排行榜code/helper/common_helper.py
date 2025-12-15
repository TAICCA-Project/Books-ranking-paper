import os
from datetime import datetime
import json
class CommonHelper():
    @staticmethod
    def get_save_file_path( base_file_path,file_name):
        today_str = datetime.today().strftime('%Y%m%d')
        csv_filename = f'{today_str}_{file_name}.csv'

        year = datetime.today().strftime('%Y')
        month = datetime.today().strftime('%m')
        
        directory_path = os.path.join('spider_data', year, month, base_file_path, file_name)
        
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)

        file_path = os.path.join(directory_path, csv_filename)
        return file_path
    
    @staticmethod
    def save_cookies_to_json(cookie_list, filename):
        # 確保cookies目錄存在
        cookie_dir = os.path.dirname(filename)
        if cookie_dir and not os.path.exists(cookie_dir):
            os.makedirs(cookie_dir)
        
        # 直接使用傳入的完整檔案路徑
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(cookie_list, file, ensure_ascii=False, indent=4)