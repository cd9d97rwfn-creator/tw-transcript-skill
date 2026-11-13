---
name: tw-transcript-skill
description: 將音訊、影片或既有逐字稿整理為台灣正體中文，保留原始辨識稿並進行有來源的課程專有名詞校稿。可使用使用者自己的轉錄 API 部署網頁服務。
---

使用附帶的 assets/agent 程式。此分享包不含作者金鑰、服務網址、逐字稿或私人資料；雲端轉錄使用安裝者自己設定的 OPENAI_API_KEY，費用由該帳戶負擔。不要尋找或借用作者的金鑰或私人服務。

## 執行

先確認輸入是音檔、影片或既有逐字稿，以及是否需要逐句時間戳。assets/agent/src/tw_transcript_agent/cli.py 保留 MacWhisper 本機流程；雲端網頁由 web.py 與 cloud.py 提供。

雲端部署：在 assets/agent 以 Dockerfile 建置，使用單一服務、單一 worker，持久磁碟掛載 /data。由安裝者以伺服器環境變數設定 OPENAI_API_KEY、至少 20 字元隨機 APP_PASSWORD；透過 HTTPS 使用網站。金鑰不得提交版本控制或嵌入前端。首次轉錄前核對供應商現行模型與費率，並讓使用者知道音訊將送到 API。未設定自己的金鑰時不得呼叫別人的服務。

既有文字可使用本機 CLI 的 --input-is-transcript --polish local；先檢查該環境的 Python、OpenCC 與 CLI --help。雲端轉錄不提供逐句 SRT；需要時間戳時先選擇真正支援時間戳的後端，不能把切段邊界當作逐句時間戳。

## 忠實與校稿

保留意思、順序、例子、否定詞與講者主張，不摘要或補寫。簡轉繁不等於專有名詞校稿。每堂從原稿上下文檢查校名、系所、機構、人名、理論、學派、方法、量表、書名與英文拼寫，再核對講者、學校、學會、作者或出版者來源；必要時回聽或核對投影片。

resources/course_terms.json 僅包含共用規則。新課自行建立有來源、有限定範圍的規則。禁止無條件替換意向／意象、自信／自性、融合／榮格、疫情／移情、情節／情結。正式拼寫來源不能證明音訊實際措辭；未確定處保留原文與時間點／候選詞，不能冒稱已回聽。

保留 raw、原始分段 JSON、校稿前版本、逐筆修改、來源與 SHA-256；已有 TXT/SRT 時同步修正且保持段數與時間戳。驗證原稿雜湊不變及第二次校稿零新增修改。交付標示「專有名詞校稿版」與尚未逐句聽校、尚未獨立核對的範圍。

網站入口與啟動方式見 [網站說明](assets/agent/README.md)，支援 TXT、Markdown、原始 JSON 與 ZIP 下載。執行 `assets/agent/run_web.py` 前，安裝依賴並自行設定 .env；GitHub 連結可由 GITHUB_REPO_URL 指定。
