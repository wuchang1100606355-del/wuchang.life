# W7TP V2.3 XiaoJ Live Chinese Speech & Real-time Lip-Sync Gateway Route
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path

router = APIRouter()
root_path = Path("/home/taiji_admin/Taiji_Hub")
rig_dir = root_path / "Taiji_Odoo/addons/wuchang_ordering_ui_suite/static/src/data/xiaoj_rig"

@router.get("/static/xiaoj_rig/{filename}")
async def serve_xiaoj_rig_file(filename: str):
    file_p = rig_dir / filename
    if file_p.exists() and file_p.is_file():
        return FileResponse(file_p)
    raise HTTPException(status_code=404, detail="File not found")

@router.get("/xiaoj/chat", response_class=HTMLResponse)
async def xiaoj_chat_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>小J 本地即時影音對話</title>
        <meta charset="utf-8">
        <style>
            body { background: #111; color: #fff; font-family: system-ui, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            #avatar-container { width: 380px; height: 380px; border-radius: 20px; overflow: hidden; box-shadow: 0 12px 40px rgba(0,0,0,0.8); background: #222; position: relative; border: 2px solid #333; }
            #avatar-img { width: 100%; height: 100%; object-fit: cover; }
            #chat-box { width: 380px; margin-top: 20px; display: flex; gap: 10px; }
            input { flex: 1; padding: 14px; border-radius: 10px; border: 1px solid #444; background: #222; color: #fff; font-size: 16px; outline: none; }
            button { padding: 14px 24px; border-radius: 10px; border: none; background: #007acc; color: #fff; font-size: 16px; font-weight: bold; cursor: pointer; }
            button:hover { background: #005999; }
            button:disabled { background: #555; cursor: not-allowed; }
            #status-bar { width: 380px; margin-top: 12px; font-size: 13px; color: #aaa; text-align: center; }
        </style>
    </head>
    <body>
        <div id="avatar-container">
            <img id="avatar-img" src="/static/xiaoj_rig/cell_smile.webp" alt="小J">
        </div>
        <div id="chat-box">
            <input type="text" id="user-msg" value="你好！我是小J，歡迎光臨上品聊國咖啡！" placeholder="跟小J聊聊天...">
            <button id="send-btn" onclick="speakAndAnimate()">發送</button>
        </div>
        <div id="status-bar">正在載入 252 張小J 動態母片...</div>

        <script>
            const assetList = ["cell_blink.webp", "cell_care.webp", "cell_comfort.webp", "cell_doubt.webp", "cell_focus.webp", "cell_frown.webp", "cell_gaze_left.webp", "cell_gaze_right.webp", "cell_happy.webp", "cell_mouth_A.webp", "cell_mouth_E.webp", "cell_mouth_FV.webp", "cell_mouth_I.webp", "cell_mouth_L.webp", "cell_mouth_MBP.webp", "cell_mouth_O.webp", "cell_mouth_SZ.webp", "cell_mouth_U.webp", "cell_neutral.webp", "cell_side.webp", "cell_smile.webp", "cell_surprise.webp", "cell_think.webp", "cell_wink.webp", "cross_care_to_wink_1.webp", "cross_care_to_wink_2.webp", "cross_care_to_wink_3.webp", "cross_care_to_wink_4.webp", "cross_care_to_wink_5.webp", "cross_happy_to_wink_1.webp", "cross_happy_to_wink_2.webp", "cross_happy_to_wink_3.webp", "cross_happy_to_wink_4.webp", "cross_happy_to_wink_5.webp", "cross_mouth_A_to_mouth_I_1.webp", "cross_mouth_A_to_mouth_I_2.webp", "cross_mouth_A_to_mouth_I_3.webp", "cross_mouth_A_to_mouth_I_4.webp", "cross_mouth_A_to_mouth_I_5.webp", "cross_mouth_A_to_mouth_O_1.webp", "cross_mouth_A_to_mouth_O_2.webp", "cross_mouth_A_to_mouth_O_3.webp", "cross_mouth_A_to_mouth_O_4.webp", "cross_mouth_A_to_mouth_O_5.webp", "cross_mouth_E_to_mouth_A_1.webp", "cross_mouth_E_to_mouth_A_2.webp", "cross_mouth_E_to_mouth_A_3.webp", "cross_mouth_E_to_mouth_A_4.webp", "cross_mouth_E_to_mouth_A_5.webp", "cross_mouth_I_to_mouth_E_1.webp", "cross_mouth_I_to_mouth_E_2.webp", "cross_mouth_I_to_mouth_E_3.webp", "cross_mouth_I_to_mouth_E_4.webp", "cross_mouth_I_to_mouth_E_5.webp", "cross_mouth_MBP_to_mouth_A_1.webp", "cross_mouth_MBP_to_mouth_A_2.webp", "cross_mouth_MBP_to_mouth_A_3.webp", "cross_mouth_MBP_to_mouth_A_4.webp", "cross_mouth_MBP_to_mouth_A_5.webp", "cross_mouth_MBP_to_mouth_I_1.webp", "cross_mouth_MBP_to_mouth_I_2.webp", "cross_mouth_MBP_to_mouth_I_3.webp", "cross_mouth_MBP_to_mouth_I_4.webp", "cross_mouth_MBP_to_mouth_I_5.webp", "cross_mouth_MBP_to_mouth_O_1.webp", "cross_mouth_MBP_to_mouth_O_2.webp", "cross_mouth_MBP_to_mouth_O_3.webp", "cross_mouth_MBP_to_mouth_O_4.webp", "cross_mouth_MBP_to_mouth_O_5.webp", "cross_mouth_U_to_mouth_O_1.webp", "cross_mouth_U_to_mouth_O_2.webp", "cross_mouth_U_to_mouth_O_3.webp", "cross_mouth_U_to_mouth_O_4.webp", "cross_mouth_U_to_mouth_O_5.webp", "cross_surprise_to_happy_1.webp", "cross_surprise_to_happy_2.webp", "cross_surprise_to_happy_3.webp", "cross_surprise_to_happy_4.webp", "cross_surprise_to_happy_5.webp", "cross_think_to_smile_1.webp", "cross_think_to_smile_2.webp", "cross_think_to_smile_3.webp", "cross_think_to_smile_4.webp", "cross_think_to_smile_5.webp", "tween_blink_1.webp", "tween_blink_2.webp", "tween_blink_3.webp", "tween_blink_4.webp", "tween_blink_5.webp", "tween_blink_6.webp", "tween_blink_7.webp", "tween_care_1.webp", "tween_care_2.webp", "tween_care_3.webp", "tween_care_4.webp", "tween_care_5.webp", "tween_care_6.webp", "tween_care_7.webp", "tween_comfort_1.webp", "tween_comfort_2.webp", "tween_comfort_3.webp", "tween_comfort_4.webp", "tween_comfort_5.webp", "tween_comfort_6.webp", "tween_comfort_7.webp", "tween_doubt_1.webp", "tween_doubt_2.webp", "tween_doubt_3.webp", "tween_doubt_4.webp", "tween_doubt_5.webp", "tween_doubt_6.webp", "tween_doubt_7.webp", "tween_focus_1.webp", "tween_focus_2.webp", "tween_focus_3.webp", "tween_focus_4.webp", "tween_focus_5.webp", "tween_focus_6.webp", "tween_focus_7.webp", "tween_frown_1.webp", "tween_frown_2.webp", "tween_frown_3.webp", "tween_frown_4.webp", "tween_frown_5.webp", "tween_frown_6.webp", "tween_frown_7.webp", "tween_gaze_left_1.webp", "tween_gaze_left_2.webp", "tween_gaze_left_3.webp", "tween_gaze_left_4.webp", "tween_gaze_left_5.webp", "tween_gaze_left_6.webp", "tween_gaze_left_7.webp", "tween_gaze_right_1.webp", "tween_gaze_right_2.webp", "tween_gaze_right_3.webp", "tween_gaze_right_4.webp", "tween_gaze_right_5.webp", "tween_gaze_right_6.webp", "tween_gaze_right_7.webp", "tween_happy_1.webp", "tween_happy_2.webp", "tween_happy_3.webp", "tween_happy_4.webp", "tween_happy_5.webp", "tween_happy_6.webp", "tween_happy_7.webp", "tween_mouth_A_1.webp", "tween_mouth_A_2.webp", "tween_mouth_A_3.webp", "tween_mouth_A_4.webp", "tween_mouth_A_5.webp", "tween_mouth_A_6.webp", "tween_mouth_A_7.webp", "tween_mouth_E_1.webp", "tween_mouth_E_2.webp", "tween_mouth_E_3.webp", "tween_mouth_E_4.webp", "tween_mouth_E_5.webp", "tween_mouth_E_6.webp", "tween_mouth_E_7.webp", "tween_mouth_FV_1.webp", "tween_mouth_FV_2.webp", "tween_mouth_FV_3.webp", "tween_mouth_FV_4.webp", "tween_mouth_FV_5.webp", "tween_mouth_FV_6.webp", "tween_mouth_FV_7.webp", "tween_mouth_I_1.webp", "tween_mouth_I_2.webp", "tween_mouth_I_3.webp", "tween_mouth_I_4.webp", "tween_mouth_I_5.webp", "tween_mouth_I_6.webp", "tween_mouth_I_7.webp", "tween_mouth_L_1.webp", "tween_mouth_L_2.webp", "tween_mouth_L_3.webp", "tween_mouth_L_4.webp", "tween_mouth_L_5.webp", "tween_mouth_L_6.webp", "tween_mouth_L_7.webp", "tween_mouth_MBP_1.webp", "tween_mouth_MBP_2.webp", "tween_mouth_MBP_3.webp", "tween_mouth_MBP_4.webp", "tween_mouth_MBP_5.webp", "tween_mouth_MBP_6.webp", "tween_mouth_MBP_7.webp", "tween_mouth_O_1.webp", "tween_mouth_O_2.webp", "tween_mouth_O_3.webp", "tween_mouth_O_4.webp", "tween_mouth_O_5.webp", "tween_mouth_O_6.webp", "tween_mouth_O_7.webp", "tween_mouth_SZ_1.webp", "tween_mouth_SZ_2.webp", "tween_mouth_SZ_3.webp", "tween_mouth_SZ_4.webp", "tween_mouth_SZ_5.webp", "tween_mouth_SZ_6.webp", "tween_mouth_SZ_7.webp", "tween_mouth_U_1.webp", "tween_mouth_U_2.webp", "tween_mouth_U_3.webp", "tween_mouth_U_4.webp", "tween_mouth_U_5.webp", "tween_mouth_U_6.webp", "tween_mouth_U_7.webp", "tween_neutral_1.webp", "tween_neutral_2.webp", "tween_neutral_3.webp", "tween_neutral_4.webp", "tween_neutral_5.webp", "tween_neutral_6.webp", "tween_neutral_7.webp", "tween_side_1.webp", "tween_side_2.webp", "tween_side_3.webp", "tween_side_4.webp", "tween_side_5.webp", "tween_side_6.webp", "tween_side_7.webp", "tween_smile_1.webp", "tween_smile_2.webp", "tween_smile_3.webp", "tween_smile_4.webp", "tween_smile_5.webp", "tween_smile_6.webp", "tween_smile_7.webp", "tween_surprise_1.webp", "tween_surprise_2.webp", "tween_surprise_3.webp", "tween_surprise_4.webp", "tween_surprise_5.webp", "tween_surprise_6.webp", "tween_surprise_7.webp", "tween_think_1.webp", "tween_think_2.webp", "tween_think_3.webp", "tween_think_4.webp", "tween_think_5.webp", "tween_think_6.webp", "tween_think_7.webp", "tween_wink_1.webp", "tween_wink_2.webp", "tween_wink_3.webp", "tween_wink_4.webp", "tween_wink_5.webp", "tween_wink_6.webp", "tween_wink_7.webp"];
            const images = {};
            let isReady = false;

            // 預載 252 張圖片
            let loaded = 0;
            const statusBar = document.getElementById('status-bar');
            assetList.forEach(name => {
                const img = new Image();
                img.onload = img.onerror = () => {
                    loaded++;
                    if (loaded === assetList.length) {
                        isReady = true;
                        statusBar.innerText = "小J 準備就緒！請點擊發送進行中文播報與對嘴。";
                        statusBar.style.color = "#4af626";
                    } else {
                        statusBar.innerText = `載入母片池: ${loaded}/${assetList.length}`;
                    }
                };
                img.src = `/static/xiaoj_rig/${name}`;
                images[name] = img;
            });

            const mouthVisemes = ['cell_mouth_A.webp', 'cell_mouth_I.webp', 'cell_mouth_U.webp', 'cell_mouth_E.webp', 'cell_mouth_O.webp', 'cell_mouth_MBP.webp'];

            function setAvatarAsset(name) {
                const avatar = document.getElementById('avatar-img');
                if (images[name]) avatar.src = images[name].src;
            }

            function speakAndAnimate() {
                if (!isReady) return;
                const text = document.getElementById('user-msg').value.trim();
                if (!text) return;

                const sendBtn = document.getElementById('send-btn');
                sendBtn.disabled = true;
                statusBar.innerText = "小J 正在說話中...";

                // 1. 使用 Web Speech API 發出中文真人語音
                window.speechSynthesis.cancel();
                const utter = new SpeechSynthesisUtterance(text);
                utter.lang = 'zh-TW';
                utter.rate = 1.0;
                utter.pitch = 1.2; // 調整女性聲調

                let mouthTimer = null;
                let blinkTimer = null;
                let visIdx = 0;

                utter.onstart = () => {
                    // 2. 說話時進行對嘴與表情自然連動
                    mouthTimer = setInterval(() => {
                        visIdx = (visIdx + 1) % mouthVisemes.length;
                        setAvatarAsset(mouthVisemes[visIdx]);
                    }, 120);

                    // 自然眨眼
                    blinkTimer = setInterval(() => {
                        if (Math.random() > 0.6) {
                            setAvatarAsset('cell_blink.webp');
                            setTimeout(() => { setAvatarAsset(mouthVisemes[visIdx]); }, 150);
                        }
                    }, 2000);
                };

                utter.onend = utter.onerror = () => {
                    clearInterval(mouthTimer);
                    clearInterval(blinkTimer);
                    setAvatarAsset('cell_smile.webp');
                    sendBtn.disabled = false;
                    statusBar.innerText = "播報完成，等待下一條指令。";
                };

                window.speechSynthesis.speak(utter);
            }
        </script>
    </body>
    </html>
    """
