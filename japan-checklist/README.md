# 日本 700 景點踩點圖鑑 — 分區收藏版

GitHub Pages: https://aaaa0976355849-glitch.github.io/Train1/

## 功能

地區完成度在最上方、下方為篩選列。10 個地區分開顯示，均可收合／展開，也支援全部展開／全部收合。卡片為圖片、景點名稱、勾選框；勾選後立即在該地區排到未勾選景點之前。取消勾選會恢復原始清單順序。支援搜尋、地區／都道府縣篩選、只看已踩。

## 資料與相容性

正式 data.1.txt–data.4.txt 保持原內容：Base64 gzip JSON，700 筆、47 都道府縣。不要覆蓋成測試資料。

主紀錄沿用 `japan700-tracker-v1`，相容舊版 `visited`／`status` 及新版 `checked`。只有不存在主紀錄時才讀取草稿的 `japan700-simple-v1`／`japan700-simple-v2`。原有日期與備註雖不再顯示，仍保留於紀錄與備份內。收合設定獨立保存在 `japan700-simple-collapsed-v1`。

紀錄儲存於目前瀏覽器，不是雲端同步。JSON 匯出／匯入位於頁底的可展開面板，匯入為合併，衝突時以匯入檔為準。儲存失敗會顯示警告。

## 圖片

`photos.js` 依名稱向 ja/zh Wikipedia 的 PageImages 查找自由授權圖片，再由 Wikimedia Commons 取得原圖來源、作者與授權。排除消歧義頁與未識別的授權。圖片依畫面位置載入，最多同時三項查詢，並以 sessionStorage 快取。圖片有裁切顯示，原圖署名／授權連結顯示於照片上。

尚未逐張人工核對 700 張照片；查無照片、網路或 API 出錯時顯示替代圖卡。這不代表已完成 700 張景點實拍照片的蒐集。

## 檢查與發布

此版以正式 700 筆資料完成 35 項 Chromium 本機 DOM／邏輯檢查；儲存與外部圖片 API 使用測試替身，未宣稱實機跨次啟動或所有外部照片皆已實測。JavaScript 另通過 `node --check`。

保留既有 `.github/workflows/japan-checklist-pages.yml`，提交後自動部署。根目錄的 C# 專案不受影響。
