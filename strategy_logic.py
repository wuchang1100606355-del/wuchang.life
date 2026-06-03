import os, time

USE_CLOUD = os.getenv("USE_CLOUD","1")=="1"
CACHE = {}

def cache_get(k):
    v = CACHE.get(k)
    if not v: return None
    if time.time() - v["t"] > 300: return None
    return v["r"]

def cache_set(k, r):
    CACHE[k] = {"t": time.time(), "r": r}

def local_reply(text):
    if "松哥" in text:
        return {"reply":"松哥早，今天一樣卡布奇諾嗎？","node":"local"}
    if "推薦" in text:
        return {"reply":"推薦卡布奇諾（熱）","node":"local"}
    return {"reply":"好的，我幫你看看～","node":"local"}

def cloud_reply(text):
    return {"reply":"（雲端強化）今日主打：卡布奇諾＋甜點組合","node":"cloud"}

def route(text):
    k = text.strip()
    c = cache_get(k)
    if c:
        return c

    if any(x in text for x in ["松哥","推薦","卡布"]):
        r = local_reply(text)
        cache_set(k, r)
        return r

    if USE_CLOUD:
        r = cloud_reply(text)
        cache_set(k, r)
        return r

    r = local_reply(text)
    cache_set(k, r)
    return r
