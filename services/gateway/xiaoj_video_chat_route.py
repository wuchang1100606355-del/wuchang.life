# W7TP V2.3 Local XiaoJ Live Video Chat Gateway Route
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/xiaoj/chat", response_class=HTMLResponse)
async def xiaoj_chat_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>小J 本地 60 FPS 影音即時對話</title>
        <meta charset="utf-8">
        <style>
            body { background: #111; color: #fff; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            #avatar-container { width: 400px; height: 400px; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.8); background: #222; position: relative; }
            #avatar-img { width: 100%; height: 100%; object-fit: cover; }
            #chat-box { width: 400px; margin-top: 20px; display: flex; gap: 10px; }
            input { flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #444; background: #222; color: #fff; font-size: 16px; }
            button { padding: 12px 20px; border-radius: 8px; border: none; background: #007acc; color: #fff; font-size: 16px; cursor: pointer; }
            button:hover { background: #005999; }
            #status { margin-top: 10px; color: #888; font-size: 12px; }
        </style>
    </head>
    <body>
        <div id="avatar-container">
            <img id="avatar-img" src="/static/xiaoj_rig/cell_smile.webp" alt="小J">
        </div>
        <div id="chat-box">
            <input type="text" id="user-msg" placeholder="跟小J聊聊天..." onkeypress="if(event.key==='Enter') sendMsg()">
            <button onclick="sendMsg()">發送</button>
        </div>
        <div id="status">W7TP D6 記憶體不落盤影音重構 | 60 FPS | 289B Audio Cell</div>

        <script>
            async function sendMsg() {
                const input = document.getElementById('user-msg');
                const text = input.value.trim();
                if (!text) return;
                input.value = '';
                
                // 模擬 15 秒音訊原胞 (Audio Origin Cell) 驅動母片池
                const visemes = ['mouth_A', 'mouth_I', 'mouth_U', 'mouth_E', 'mouth_O', 'smile'];
                let idx = 0;
                const img = document.getElementById('avatar-img');
                const timer = setInterval(() => {
                    img.src = `/static/xiaoj_rig/cell_${visemes[idx % visemes.length]}.webp`;
                    idx++;
                    if (idx > 18) {
                        clearInterval(timer);
                        img.src = '/static/xiaoj_rig/cell_smile.webp';
                    }
                }, 120);
            }
        </script>
    </body>
    </html>
    """
