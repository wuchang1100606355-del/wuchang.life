const RESPONSES = Object.freeze({
  resident: {
    title: "我先幫您整理居民服務",
    body: "您可以先瀏覽居民服務，或建立一張服務需求候選。建立候選不會送出資料；需要送出時會先進入「待我確認」。",
    nextView: "services",
    nextLabel: "查看居民服務",
  },
  business: {
    title: "商業雲分為轄區內與轄區外",
    body: "轄區內商家免費訂閱；轄區外採付費訂閱，收入全數歸社區數位發展基金。訂閱不會增加治理或Founder權限。",
    nextView: "professional",
    nextLabel: "查看商業雲",
  },
  property: {
    title: "物業雲協助服務，不取代決策",
    body: "轄區內物業免費訂閱；轄區外採付費訂閱。物業系統提供架構與維護，不取得管委會依法享有的決策權。",
    nextView: "professional",
    nextLabel: "查看物業雲",
  },
  default: {
    title: "我已把您的需要整理成候選",
    body: "目前是隔離驗收模式，我不會呼叫模型或工具。您可以前往居民服務，選擇下一步；任何副作用都必須先由您確認。",
    nextView: "services",
    nextLabel: "查看可用服務",
  },
});

export function getLocalXiaojCandidate(text) {
  const value = String(text || "").trim();
  if (!value) {
    return RESPONSES.default;
  }
  if (/商家|商業|店家|訂閱/.test(value)) {
    return RESPONSES.business;
  }
  if (/物業|管委會|社區管理/.test(value)) {
    return RESPONSES.property;
  }
  if (/居民|服務|協助|不知道/.test(value)) {
    return RESPONSES.resident;
  }
  return RESPONSES.default;
}
