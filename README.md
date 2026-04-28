# API Client - Enterprise Edition 🚀

專業級 API 測試工具，使用 Python (Tkinter) 構建。提供企業級功能，包括多環境管理、認證支援、日誌記錄等。

**版本**: 2.0.0

## ✨ 主要功能

### 核心功能
- **多種 HTTP 方法支援**: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
- **完整請求配置**: Headers、Request Body 設定
- **專業響應檢視**:
  - 自動格式化 JSON 響應
  - **語法高亮 (Syntax Highlighting)**
  - 大型 JSON 響應會自動略過高亮以維持 UI 流暢
  - Response Headers 檢視
  - 狀態碼、響應時間、響應大小監控

### 🏢 企業級功能 (v2.0 新增)

#### 環境管理
- **多環境切換**: Development / Staging / Production
- **變數替換**: 使用 `{{variable_name}}` 語法
- **基礎 URL 自動套用**: 環境中設定的 Base URL 會自動套用
- **預設標頭**: 每個環境可設定預設 Headers

#### 認證支援
- **Bearer Token**: JWT / OAuth2 Token
- **Basic Auth**: 用戶名:密碼 格式
- **API Key**: X-API-Key Header

#### 請求設定
- **逾時設定**: 可自訂請求逾時時間 (最高 300 秒)
- **自動重試**: 連線失敗時自動重試 (可配置次數)
- **SSL 驗證**: 可選擇是否驗證 SSL 憑證
- **Proxy 支援**: HTTP/HTTPS 代理伺服器設定

#### 日誌與監控
- **結構化日誌**: JSON 格式日誌，方便分析
- **檔案日誌**: 自動輪替，避免檔案過大
- **請求追蹤**: 每個請求都有唯一 ID

#### 歷史記錄
- **持久化儲存**: 請求歷史自動保存
- **完整記錄**: 保存 Method、URL、Headers、Body
- **快速載入**: 點擊即可重新載入歷史請求
- **可配置上限**: 依 `max_history_items` 設定自動裁切歷史筆數

## 📁 專案結構

```
api_client/
├── main.py                 # 程式入口與 GUI 介面
├── logic.py                # HTTP 請求協調器
├── utils.py                # 工具函數
├── requirements.txt        # 依賴套件
├── README.md               # 專案說明
│
├── config/                 # 配置模組
│   ├── __init__.py
│   └── settings.py         # 配置管理器
│
├── core/                   # 核心模組
│   ├── __init__.py
│   ├── http_client.py      # HTTP 客戶端
│   ├── logger.py           # 日誌模組
│   └── exceptions.py       # 自定義例外
│
└── (自動生成)
    ├── api_client_history.json    # 歷史記錄
    └── api_client.log             # 日誌檔案
```

## 🛠️ 安裝與執行

### 系統需求
- Python 3.9+
- tkinter (通常隨 Python 安裝)

### 安裝步驟

1. **複製專案**
   ```bash
   git clone <repository_url>
   cd api_client
   ```

2. **安裝依賴**
   ```bash
   pip install -r requirements.txt
   ```

3. **執行程式**
   ```bash
   python main.py
   ```

## ⚙️ 配置說明

### 環境變數

| 變數名稱 | 說明 | 預設值 |
|---------|------|-------|
| `API_CLIENT_TIMEOUT` | 預設逾時時間 (秒) | 30 |
| `API_CLIENT_LOG_LEVEL` | 日誌等級 | INFO |
| `API_CLIENT_VERIFY_SSL` | 是否驗證 SSL | true |
| `HTTP_PROXY` | HTTP 代理 | - |
| `HTTPS_PROXY` | HTTPS 代理 | - |

### 配置檔案位置

配置檔案存放於使用者家目錄下：
- Windows: `C:\Users\<username>\.api_client\`
- Linux/Mac: `~/.api_client/`

包含：
- `config.json` - 應用程式設定
- `environments.json` - 環境配置

## 📖 使用指南

### 環境變數使用

在 URL 或 Headers 中使用 `{{variable}}` 語法：

```
URL: {{base_url}}/api/v1/users/{{user_id}}
Headers:
  Authorization: Bearer {{token}}
  X-Request-ID: {{request_id}}
```

### 建立新環境

1. 點擊「🌐 管理環境」按鈕
2. 點擊「➕ 新增環境」
3. 填入環境名稱、基礎 URL、認證資訊
4. 點擊「儲存」

### 切換環境

使用工具列上的環境下拉選單快速切換。

## 🔒 安全注意事項

- 敏感資訊 (Token、密碼) 儲存於本地配置檔
- 建議將 `~/.api_client/` 加入 `.gitignore`
- 生產環境建議使用環境變數而非配置檔

## 📝 變更日誌

### v2.0.0 (2025-01)
- 🆕 多環境管理功能
- 🆕 認證支援 (Bearer, Basic, API Key)
- 🆕 企業級日誌記錄系統
- 🆕 自動重試機制
- 🆕 SSL/Proxy 設定
- 🆕 請求驗證功能
- 🔧 重構程式碼架構
- 🔧 改善錯誤處理

### v1.0.0
- 初始版本
- 基本 HTTP 請求功能
- 歷史記錄
- 深色/淺色主題

## 📄 授權

MIT License
