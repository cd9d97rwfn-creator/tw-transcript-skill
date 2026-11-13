# 聽見 · 分享版逐字稿網站

上傳音訊／影片，背景轉錄成台灣正體中文；可下載 TXT、Markdown、原始分段 JSON 或完整 ZIP。網站包括工作進度、錯誤提示、上傳進度與重試。

## 啟動

安裝 Python 3.11+ 與 FFmpeg。在本資料夾建立虛擬環境，執行 `pip install -r requirements-cloud.txt`。把 `.env.example` 複製成 `.env`，填入自己的 OPENAI_API_KEY 與至少 20 字元的 APP_PASSWORD。可選填自己的 GitHub 儲存庫 HTTPS 網址到 GITHUB_REPO_URL。

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-cloud.txt
.venv/bin/python run_web.py
```

開啟 http://127.0.0.1:8080，使用者名稱任填，密碼為 APP_PASSWORD。部署到 Railway 時使用 Dockerfile，掛載 /data，設定相同環境變數，使用 HTTPS。單一 worker、單一 replica。所有持有同一密碼的人共用工作清單、檔案與部署者的 API 額度；供不同人各自付費使用時，請讓每人自行部署一份。

## 格式與品質

TXT 是套用共用專有名詞規則的正體中文文字；Markdown 附校稿範圍說明；JSON 是原始 API 分段回應，沒有逐句時間戳；ZIP 包含前述檔案、原始稿、校稿前版本、修改紀錄與雜湊。所有格式皆會保留，可隨時更換下載格式，不需重跑轉錄或重複付費。

尚未逐句聽校，也不代表完成每堂課獨立專有名詞核對。當前後端不提供逐句時間戳，因此不提供 SRT/VTT。音訊送至 OpenAI，費用由部署者金鑰所屬帳戶負擔。此分享包不含原作者金鑰、逐字稿或私人服務連線。

## GitHub

把本資料夾上傳至自己的儲存庫，再設定 GITHUB_REPO_URL，網站會出現「GitHub 原始碼」連結。此功能是連到程式庫，不會自動將音訊或逐字稿提交 GitHub。不設定時會顯示建置說明，沒有虛構儲存庫連結。不要將 .env 或 output 提交版本控制。
