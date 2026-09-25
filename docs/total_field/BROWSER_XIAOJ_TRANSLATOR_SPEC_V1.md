# BROWSER_XIAOJ_TRANSLATOR_SPEC_V1

## 1. 定位與職責
個人封包小 J (Personal Packet XiaoJ Browser) 位於使用者端。其內建 LLM 嚴格降級為「自然語言到 8D 封包之翻譯官」。

## 2. 輸入與輸出約束
- 輸入: 接收未結構化之自然語言或介面點擊。
- 輸出: 僅允許輸出 W7TP_BROWSER_INTENT_PACKET_V1 草稿，嚴禁呼叫執行端點。
