from config import Config
import google.generativeai as genai
import PIL.Image
import time
import traceback
import re

genai_key = Config.GOOGLE_API_KEY
genai.configure(api_key = genai_key)

def verfity_ocr(path):
    try:
        print(f"開始OCR識別驗證碼: {path}")
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 設置超時時間為15秒
        start_time = time.time()
        max_time = 15  # 最大等待時間(秒)
        
        # 嘗試讀取圖片
        try:
            img = PIL.Image.open(f'{path}')
            print(f"已成功載入圖片，尺寸: {img.size}")
        except Exception as e:
            print(f"圖片載入失敗: {e}")
            traceback.print_exc()
            return "0000"  # 返回預設值
        
        # 使用更明確的提示詞
        prompt = "這是一個驗證碼圖片，包含4個數字。請只返回這4個數字，不要添加任何其他文字或符號。"
        
        # 添加超時處理
        try:
            response = model.generate_content([prompt, img], stream=False)
            
            # 檢查是否超時
            if time.time() - start_time > max_time:
                print(f"OCR識別超時，已經等待 {max_time} 秒")
                return "0000"  # 超時返回預設值
                
            result_text = response.text.strip()
            print(f"原始OCR結果: '{result_text}'")
            
            # 提取數字
            digits = re.findall(r'\d', result_text)
            if len(digits) >= 4:
                result = ''.join(digits[:4])
                print(f"提取的4位數字: {result}")
                return result
            else:
                print(f"無法提取4位數字，使用備用策略")
                # 如果無法提取4位數字，嘗試使用所有可見的數字
                all_digits = ''.join(digits)
                if len(all_digits) > 0:
                    # 如果有數字但少於4位，補0
                    return all_digits.ljust(4, '0')[:4]
                else:
                    return "0000"  # 沒有找到任何數字，返回預設值
                
        except Exception as e:
            print(f"OCR處理出錯: {e}")
            traceback.print_exc()
            return "0000"  # 出錯時返回預設值
            
    except Exception as e:
        print(f"OCR識別過程中發生未處理的錯誤: {e}")
        traceback.print_exc()
        return "0000"  # 出錯時返回預設值 