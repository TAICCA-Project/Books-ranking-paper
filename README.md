# 台灣書店排行榜爬蟲 / Taiwan Bookstore Ranking Scrapers

台灣主要線上書店的圖書排行榜與詳細資訊爬取工具，支援 Books.com.tw（博客來）、誠品線上、金石堂、三民書局等平台。

## 📚 專案簡介

本專案提供多個 Python 爬蟲程式，用於自動化收集台灣主要線上書店的圖書排行榜資訊及詳細書籍資料。

### 📋 程式類型說明
- **Python 腳本 (`.py`)**: 生產級爬蟲，支援多線程、錯誤處理、自動重試等進階功能
- **Jupyter Notebook (`.ipynb`)**: ⭐ **重要的初步爬蟲程式**，提供互動式開發環境，適合：
  - 初步資料探索與測試
  - 視覺化爬取進度
  - 快速原型開發與除錯
  - 分步驟執行與驗證

### 🎯 應用場景
- 圖書市場趨勢分析
- 出版業研究
- 圖書推薦系統開發
- 學術研究資料收集

## 🎯 支援平台

### Python 腳本爬蟲（生產級）

| 書店 | 腳本檔案 | 功能特色 |
|------|---------|---------|
| **博客來 (Books.com.tw)** | `bookscom_ranking_detail.py` | ✅ 多瀏覽器手動登入<br>✅ 多線程並行爬取<br>✅ 完整書籍資訊 |
| **誠品線上 (Eslite)** | `eslite_ranking_detail.py` | ✅ Cookie 管理<br>✅ OCR 圖片識別支援<br>✅ 自動重試機制 |
| **金石堂 (Kingstone)** | `kingstone_ranking_detail.py` | ✅ 即時 CSV 更新<br>✅ 錯誤記錄追蹤<br>✅ 反爬蟲對策 |

### Jupyter Notebook 初步爬蟲（⭐ 重要）

| 書店 | Notebook 檔案 | 說明 |
|------|--------------|------|
| **博客來 + 金石堂 + 誠品<br>三大平台** | `ranking_30pbooks_daily_update.ipynb` | 📓 **三合一初步排行榜爬蟲**<br>✅ 博客來總榜 (Books.com.tw)<br>✅ 金石堂月排行 (Kingstone)<br>✅ 誠品排行榜 (Eslite)<br>✅ 每日更新功能<br>✅ 統一 CSV 格式輸出 |
| **三民書局 (Sanmin)** | `sanmin_ranking.ipynb` | 📓 初步爬蟲程式<br>✅ 互動式開發與測試<br>✅ 分步驟執行<br>✅ 視覺化結果 |

> 💡 **提示**：`ranking_30pbooks_daily_update.ipynb` 是一個整合型 notebook，包含博客來、金石堂、誠品三大平台的排行榜初步爬蟲，適合快速測試和資料收集。建議先執行 Notebook 版本熟悉爬取流程，再使用 Python 腳本進行大規模資料收集。

## 🔧 環境需求

### Python 版本
- Python 3.8 或以上

### 主要套件
```bash
pip install -r 實體書排行榜code/requirements.txt
```

**核心依賴：**
- `selenium>=4.15.0` - 網頁自動化
- `beautifulsoup4>=4.12.0` - HTML 解析
- `pandas>=2.0.0` - 資料處理
- `requests>=2.31.0` - HTTP 請求
- `webdriver-manager>=4.0.0` - ChromeDriver 管理

## ⚙️ 安裝步驟

### 1️⃣ 克隆專案
```bash
git clone https://github.com/TAICCA-Project/Books-ranking-paper.git
cd Books-ranking-paper
```

### 2️⃣ 安裝依賴
```bash
cd 實體書排行榜code
pip install -r requirements.txt
```

### 3️⃣ 配置環境

複製配置範本並填入您的憑證：
```bash
cp config.example.py config.py
```

編輯 `config.py`，填入以下資訊：
- **Google API Key**（如需使用 GenAI 功能）
- **各書店帳號密碼**（用於登入爬取會員專屬內容）

```python
class Config:
    GOOGLE_API_KEY = 'YOUR_API_KEY'
    BOOKSCOM_ACCOUNT = "your_email@example.com"
    BOOKSCOM_PASSWORD = "your_password"
    # ... 其他設定
```

> ⚠️ **重要提醒**：`config.py` 包含敏感資訊，已加入 `.gitignore`，請勿提交到版本控制。

## 🚀 使用方法

本專案的爬蟲分為兩個階段：
1. **階段一：排行榜爬蟲** - 使用 Jupyter Notebook 快速獲取排行榜書單
2. **階段二：詳細資訊爬蟲** - 使用 Python 腳本深入爬取每本書的完整資訊

以下按平台說明完整的執行流程、相依檔案與使用方式。

---

## 📖 博客來 (Books.com.tw)

### 執行順序

#### 步驟 1️⃣：爬取排行榜（初步爬蟲）
使用 Jupyter Notebook 獲取排行榜書單：

```bash
jupyter notebook ranking_30pbooks_daily_update.ipynb
```

**執行內容：**
- 開啟 Notebook 後，執行**第一個 Cell**（博客來排行榜爬蟲）
- 爬取博客來總榜前 100 名書籍

**輸出檔案：**
- `ranking_result/bookscom/books_all_categories_YYYYMMDD.csv`
- `實體書排行榜code/log/books_plog_YYYYMMDD.txt`

**CSV 欄位：**
`production_id`, `title`, `author`, `url`, 排名日期 (如 `12/15`)

---

#### 步驟 2️⃣：爬取詳細資訊（生產級爬蟲）
使用 Python 腳本補充完整書籍資訊：

```bash
cd 實體書排行榜code
python bookscom_ranking_detail.py <排行榜CSV路徑> <瀏覽器數量>
```

**範例：**
```bash
python bookscom_ranking_detail.py ../ranking_result/bookscom/books_all_categories_20251215.csv 3
```

**相依檔案（輸入）：**
- 步驟 1 產生的排行榜 CSV 檔案

**功能特色：**
- ✅ 多瀏覽器手動登入（避免驗證碼）
- ✅ 多線程並行爬取（加速處理）
- ✅ 自動補充 ISBN、出版社、出版日期、譯者、原文書名等資訊
- ✅ 即時更新 CSV，防止資料遺失

**輸出檔案：**
- 原 CSV 檔案（新增欄位）
- 錯誤記錄檔（如有失敗）

**配置需求：**
- `config.py` 中設定 `BOOKSCOM_ACCOUNT` 和 `BOOKSCOM_PASSWORD`

---

## 📖 金石堂 (Kingstone)

### 執行順序

#### 步驟 1️⃣：爬取排行榜（初步爬蟲）
使用 Jupyter Notebook 獲取排行榜書單：

```bash
jupyter notebook ranking_30pbooks_daily_update.ipynb
```

**執行內容：**
- 開啟 Notebook 後，執行**第二個 Cell**（金石堂排行榜爬蟲）
- 爬取金石堂月排行榜書籍

**輸出檔案：**
- `ranking_result/kingstone/kingstone_all_categories_YYYYMMDD.csv`
- `實體書排行榜code/log/kingstone_plog_YYYYMMDD.txt`

**CSV 欄位：**
`production_id`, `title`, `author`, `url`, 排名日期

---

#### 步驟 2️⃣：爬取詳細資訊（生產級爬蟲）
使用 Python 腳本補充完整書籍資訊：

```bash
cd 實體書排行榜code
python kingstone_ranking_detail.py
```

執行後會提示輸入 CSV 檔案路徑：
```
請輸入CSV文件路徑: ../ranking_result/kingstone/kingstone_all_categories_20251215.csv
```

**相依檔案（輸入）：**
- 步驟 1 產生的排行榜 CSV 檔案

**功能特色：**
- ✅ 即時 CSV 更新（逐筆寫入）
- ✅ 錯誤記錄與追蹤
- ✅ 反爬蟲對策（隨機延遲、User-Agent）
- ✅ 自動補充 ISBN、出版社、出版日期、譯者、原文書名、分類等

**輸出檔案：**
- 原 CSV 檔案（新增欄位）
- 錯誤記錄 CSV：`ranking_result/kingstone/kingstone_errors_YYYYMMDD.csv`

> ⚠️ **注意**：金石堂爬蟲**不需要登入**，可直接爬取公開資訊。

---

## 📖 誠品線上 (Eslite)

### 執行順序

#### 步驟 1️⃣：爬取排行榜（初步爬蟲）
使用 Jupyter Notebook 獲取排行榜書單：

```bash
jupyter notebook ranking_30pbooks_daily_update.ipynb
```

**執行內容：**
- 開啟 Notebook 後，執行**第三個 Cell**（誠品排行榜爬蟲）
- 爬取誠品總榜書籍

**輸出檔案：**
- `ranking_result/eslite/eslite_all_categories_YYYYMMDD.csv`
- `實體書排行榜code/log/eslite_plog_YYYYMMDD.txt`

**CSV 欄位：**
`production_id`, `title`, `author`, `publisher`, `publish_date`, `url`, 排名日期

---

#### 步驟 2️⃣：爬取詳細資訊（生產級爬蟲）

**方式一：使用已存 Cookie（推薦）**
```bash
cd 實體書排行榜code
python eslite_ranking_detail.py <排行榜CSV路徑>
```

**方式二：手動登入取得 Cookie（首次執行）**
```bash
python eslite_ranking_detail.py <排行榜CSV路徑> --use-manual-login
```

**範例：**
```bash
python eslite_ranking_detail.py ../ranking_result/eslite/eslite_all_categories_20251215.csv
```

**相依檔案（輸入）：**
- 步驟 1 產生的排行榜 CSV 檔案
- Cookie 檔案（首次需手動登入產生）：`cookies/eslite_cookies_latest.json`

**功能特色：**
- ✅ Cookie 管理（避免重複登入）
- ✅ OCR 圖片識別支援（價格辨識）
- ✅ 自動重試機制
- ✅ 補充 ISBN、譯者、原文書名等資訊

**輸出檔案：**
- 原 CSV 檔案（新增欄位）
- Cookie 檔案：`cookies/eslite_cookies_latest.json`（自動更新）
- 錯誤記錄 CSV（如有失敗）

**配置需求：**
- `config.py` 中設定 `ESLITE_ACCOUNT` 和 `ESLITE_PASSWORD`（手動登入模式需要）

> 📁 **Cookie 管理注意事項**：Cookie 檔案儲存在 `cookies/` 資料夾（已排除於 Git）。如 Cookie 失效，請使用 `--use-manual-login` 重新登入。

---

## 📖 三民書局 (Sanmin)

### 執行方式

三民書局使用**單一 Jupyter Notebook** 完成所有爬取（排行榜 + 詳細資訊）：

```bash
jupyter notebook sanmin_ranking.ipynb
```

**執行內容：**
- 在 Notebook 中逐步執行 Cell
- 第一部分：爬取排行榜
- 第二部分：爬取每本書的詳細資訊

**輸出檔案：**
- `ranking_result/sanmin/sanmin_books_YYYYMMDD.csv`
- 日誌檔案：`實體書排行榜code/log/sanmin_plog_YYYYMMDD.txt`

> ⚠️ **注意**：三民書局爬蟲**不需要登入**，可直接爬取公開資訊。

**Notebook 優勢：**
- 📊 即時視覺化爬取進度
- 🔍 分步驟執行，便於除錯
- 📝 可加入註解與分析
- 💡 適合初學者理解爬蟲邏輯

---

## 📋 檔案相依關係總覽

| 平台 | 階段一（排行榜） | 輸出 CSV | 階段二（詳細資訊） | 最終輸出 |
|------|-----------------|---------|-------------------|---------|
| **博客來** | `ranking_30pbooks_daily_update.ipynb` (Cell 1) | `ranking_result/bookscom/books_*.csv` | `bookscom_ranking_detail.py` | 完整 CSV |
| **金石堂** | `ranking_30pbooks_daily_update.ipynb` (Cell 2) | `ranking_result/kingstone/kingstone_*.csv` | `kingstone_ranking_detail.py` | 完整 CSV |
| **誠品** | `ranking_30pbooks_daily_update.ipynb` (Cell 3) | `ranking_result/eslite/eslite_*.csv` | `eslite_ranking_detail.py` | 完整 CSV |
| **三民書局** | `sanmin_ranking.ipynb`（一體化） | - | - | `ranking_result/sanmin/sanmin_books_*.csv` |

---

## 🔄 完整工作流程範例

以博客來為例，完整的資料收集流程：

```bash
# 1. 開啟 Jupyter Notebook
jupyter notebook ranking_30pbooks_daily_update.ipynb

# 2. 在 Notebook 中執行第一個 Cell（博客來排行榜）
#    → 產生 ranking_result/bookscom/books_all_categories_20251215.csv

# 3. 使用產生的 CSV 爬取詳細資訊
cd 實體書排行榜code
python bookscom_ranking_detail.py ../ranking_result/bookscom/books_all_categories_20251215.csv 3

# 4. 等待爬取完成，最終 CSV 包含完整書籍資訊
```

## 📂 專案架構

```
book-ranking/
├── 實體書排行榜code/
│   ├── bookscom_ranking_detail.py      # 博客來爬蟲（生產級）
│   ├── eslite_ranking_detail.py        # 誠品爬蟲（生產級）
│   ├── eslite_orc_service.py           # 誠品 OCR 服務
│   ├── kingstone_ranking_detail.py     # 金石堂爬蟲（生產級）
│   ├── ranking_30pbooks_daily_update.ipynb  # ⭐ 三平台整合排行榜初步爬蟲（博客來+金石堂+誠品）
│   ├── sanmin_ranking.ipynb            # ⭐ 三民書局初步爬蟲（Notebook）
│   ├── config.py                       # 配置檔（需自行建立，不納入版控）
│   ├── config.example.py               # 配置範本
│   ├── requirements.txt                # Python 依賴
│   └── helper/                         # 輔助模組
│       ├── common_helper.py            # 通用函數
│       ├── selenium_helper.py          # Selenium 工具
│       ├── log_helper.py               # 日誌管理
│       └── genai_helper.py             # GenAI 功能
├── ranking_result/                      # 爬取結果輸出（不納入版控）
│   ├── bookscom/
│   ├── eslite/
│   ├── kingstone/
│   └── sanmin/
├── logs/                                # 執行日誌（不納入版控）
└── README.md                            # 本檔案
```

## 📊 輸出格式

爬取的資料會以 CSV 格式儲存，通常包含以下欄位：

| 欄位 | 說明 |
|------|------|
| `production_id` | 書籍商品 ID |
| `title` | 書名 |
| `author` | 作者 |
| `translator` | 譯者 |
| `publisher` | 出版社 |
| `publish_date` | 出版日期 |
| `isbn` | ISBN |
| `price` / `fixed_price` | 價格 |
| `discount` | 折扣 |
| `category` / `categories` | 分類 |
| `url` | 商品連結 |
| `original_title` | 原文書名（如有） |

> 📝 **注意**：不同書店的欄位名稱可能略有差異。

## 🛠️ 輔助模組說明

### `helper/selenium_helper.py`
提供 Selenium 瀏覽器自動化相關功能：
- 反爬蟲偵測設定
- ChromeDriver 初始化
- Tor 代理支援（進階功能）
- 安全元素查找（自動等待）

### `helper/common_helper.py`
通用輔助函數：
- 檔案路徑管理（按日期建立資料夾）
- Cookie JSON 儲存

### `helper/log_helper.py`
日誌記錄管理：
- 自動按年/月建立日誌資料夾
- 同時輸出到 console 和檔案
- 支援多個 logger 實例

### `helper/genai_helper.py`
GenAI 相關功能（需配置 Google API Key）

## ⚠️ 注意事項與限制

### 法律與道德規範
- 🚨 **請遵守各網站的使用條款與 `robots.txt`**
- 📜 爬取的資料僅供個人研究使用，請勿用於商業用途
- ⏱️ 請設置合理的請求間隔，避免對目標網站造成負擔

### 技術限制
- **需要登入**：部分網站內容需會員權限，需提供有效帳號
- **反爬蟲機制**：網站可能偵測自動化行為並封鎖 IP
- **網站結構變更**：目標網站改版可能導致爬蟲失效，需適時更新程式碼
- **執行時間**：大量資料爬取可能需要數小時，建議分批執行

### 常見問題

**Q: 執行時出現 `ElementNotInteractableException`？**  
A: 網站可能更新了 HTML 結構，請檢查選擇器是否仍然有效。

**Q: Cookie 失效怎麼辦？**  
A: 重新執行手動登入模式，程式會更新 Cookie。

**Q: 可以同時爬取多個網站嗎？**  
A: 可以，但建議分開執行以便追蹤錯誤。

**Q: 日誌檔案在哪裡？**  
A: `logs/` 資料夾，按年月自動分類（例：`logs/2025/12/20251215.log`）

---

**開發單位：** TAICCA (Taiwan Creative Content Agency)  
**最後更新：** 2025-12-15
