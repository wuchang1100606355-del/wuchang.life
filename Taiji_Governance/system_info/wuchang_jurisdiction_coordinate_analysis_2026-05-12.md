# 五常社區轄區圖座標精密分析

日期：2026-05-12  
來源：`/mnt/c/Users/o0930/Downloads/Google 地球-20260512T094453Z-3-001/Google 地球/五常社區轄區圖.kml`  
模式：本地 KML 解析；未呼叫外部地圖 API；未含會員個資  

## 結論

此 KML 目前解析到 1 個 Placemark：`五常社區`。資料可作為度規資料庫的「轄區錨點 / topology anchor seed」，但尚不能作為完整轄區邊界，因為檔案沒有 Polygon 或 LineString 座標。

## 座標

| 欄位 | 值 |
| --- | --- |
| WGS84 latitude | `25.0804429673534` |
| WGS84 longitude | `121.497961092329` |
| altitude | `1.46854201938258` m |
| geohash12 | `wsqqsvb05tqj` |
| source sha256 | `38c3a7fe82a7fd9edd336c1425632fcb1d9373cd71901d4830011853824ee1ac` |

## 局部公尺換算

在此緯度附近：

- 1 度緯度約 `110774.072` 公尺。
- 1 度經度約 `100884.230` 公尺。

這可用於後續把 GPS/地址節點轉換成相對於五常社區錨點的 local metric coordinate。

## 五維度規映射

| 度規 | 映射 |
| --- | --- |
| Intent | community_jurisdiction_spatial_anchor |
| Resource | low_cost_static_coordinate_seed |
| Time | 2026-05-12 source snapshot |
| Authority | association public-interest geospatial governance |
| Topology | wuchang.life jurisdiction anchor node |

## 可用

- 系統架構圖錨點。
- 服務區域初始中心。
- 後續路徑/距離/派勤模型的 local origin。
- 與正式多邊形邊界做 reconciliation。

## 不可用

- 不可單獨作為法定轄區邊界。
- 不可推論會員住址、個人位置或行為軌跡。
- 不可上雲同步個人位置明文。
- 不可拿點座標取代官方 polygon。



## 法定轄區宣告

依使用者/本會提供之治理資料，五常社區發展協會所轄地區可先宣告為已向主管機關報備之法定服務轄區：五常里、仁忠里、五順里。

本系統目前將此宣告記為：

- `reported_legal_jurisdiction = true`
- `reported_status_source = owner_association_statement`
- `official_polygon_verified = false`

因此，系統可在治理文件、看板與度規資料庫中使用「已報備法定轄區」語意；但本 KML 目前仍只有單點座標，尚未具備完整 polygon，不能取代官方或人工確認的精密邊界圖。

## 專案階段：未啟動 / 待建設

此座標資料目前定義為「未啟動 / 待建設」的座標種子。它可作為度規資料庫養分，用於未來建立服務節點、距離參考、派勤路徑、社區數位孿生初始錨點與後續 polygon reconciliation。

它目前不是正式營運邊界，也不是法定轄區宣告；正式法律、補助、會務、派勤或管轄使用前，仍需補上官方邊界或人工確認的多邊形資料。

## 下一步

1. 重新從 Google Earth 匯出包含 Polygon 的 KML/KMZ。
2. 或以五常里、仁忠里、五順里官方邊界資料建立多邊形。
3. 將此 anchor 作為 `WUCHANG_ANCHOR_20260512`，後續 polygon 以此錨點對齊。
