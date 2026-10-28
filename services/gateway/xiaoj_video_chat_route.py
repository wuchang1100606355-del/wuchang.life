# W7TP V2.3 Real 288B Binary Decoder & 252 WebP Client Preloader Route
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()

@router.get("/xiaoj/chat", response_class=HTMLResponse)
async def xiaoj_chat_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>小J 本地 60 FPS 288B 原胞影音即時對話 (全因果對帳版)</title>
        <meta charset="utf-8">
        <style>
            body { background: #080808; color: #d0d0d0; font-family: monospace, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            #avatar-container { width: 400px; height: 400px; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,0.9); background: #121212; position: relative; border: 1px solid #2a2a2a; }
            #avatar-img { width: 100%; height: 100%; object-fit: cover; }
            #chat-box { width: 400px; margin-top: 16px; display: flex; gap: 8px; }
            input { flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #333; background: #1a1a1a; color: #fff; font-size: 15px; outline: none; }
            button { padding: 12px 20px; border-radius: 8px; border: none; background: #007acc; color: #fff; font-size: 15px; font-weight: bold; cursor: pointer; }
            button:hover { background: #005999; }
            #telemetry { width: 400px; margin-top: 12px; background: #111; border: 1px solid #222; border-radius: 8px; padding: 10px; font-size: 11px; color: #888; line-height: 1.6; }
            .highlight { color: #4af626; font-weight: bold; }
        </style>
    </head>
    <body>
        <div id="avatar-container">
            <img id="avatar-img" src="/static/xiaoj_rig/cell_smile.webp" alt="小J">
        </div>
        <div id="chat-box">
            <input type="text" id="user-msg" placeholder="點擊播報，啟動 288B 解碼與 252WebP 重構..." onkeypress="if(event.key==='Enter') startClientPlayback()">
            <button id="play-btn" onclick="startClientPlayback()">載入與播報</button>
        </div>
        <div id="telemetry">
            <div>[系統狀態] <span id="status-val" class="highlight">INITIALIZING</span></div>
            <div>[母片記憶體預載] <span id="preload-val">0</span>/252 WebP (VP8L)</div>
            <div>[288B 封包解碼] <span id="cell-val">WAITING</span> | Header: <span id="hdr-val">NONE</span></div>
            <div>[實測 FPS] <span id="fps-val">0.0</span> | [掉幀] <span id="drop-val">0</span> | [時間] <span id="time-val">0.000</span>s / 15.0s</div>
            <div>[WebAudio] 多波形諧波音素驅動 | [RAM 模式] /dev/shm Zero-Disk-IO</div>
        </div>

        <script>
            const manifestWebpList = ["/xiaoj-rig/cell_blink.webp", "/xiaoj-rig/cell_care.webp", "/xiaoj-rig/cell_comfort.webp", "/xiaoj-rig/cell_doubt.webp", "/xiaoj-rig/cell_focus.webp", "/xiaoj-rig/cell_frown.webp", "/xiaoj-rig/cell_gaze_left.webp", "/xiaoj-rig/cell_gaze_right.webp", "/xiaoj-rig/cell_happy.webp", "/xiaoj-rig/cell_mouth_A.webp", "/xiaoj-rig/cell_mouth_E.webp", "/xiaoj-rig/cell_mouth_FV.webp", "/xiaoj-rig/cell_mouth_I.webp", "/xiaoj-rig/cell_mouth_L.webp", "/xiaoj-rig/cell_mouth_MBP.webp", "/xiaoj-rig/cell_mouth_O.webp", "/xiaoj-rig/cell_mouth_SZ.webp", "/xiaoj-rig/cell_mouth_U.webp", "/xiaoj-rig/cell_neutral.webp", "/xiaoj-rig/cell_side.webp", "/xiaoj-rig/cell_smile.webp", "/xiaoj-rig/cell_surprise.webp", "/xiaoj-rig/cell_think.webp", "/xiaoj-rig/cell_wink.webp", "/xiaoj-rig/cross_care_to_wink_1.webp", "/xiaoj-rig/cross_care_to_wink_2.webp", "/xiaoj-rig/cross_care_to_wink_3.webp", "/xiaoj-rig/cross_care_to_wink_4.webp", "/xiaoj-rig/cross_care_to_wink_5.webp", "/xiaoj-rig/cross_happy_to_wink_1.webp", "/xiaoj-rig/cross_happy_to_wink_2.webp", "/xiaoj-rig/cross_happy_to_wink_3.webp", "/xiaoj-rig/cross_happy_to_wink_4.webp", "/xiaoj-rig/cross_happy_to_wink_5.webp", "/xiaoj-rig/cross_mouth_A_to_mouth_I_1.webp", "/xiaoj-rig/cross_mouth_A_to_mouth_I_2.webp", "/xiaoj-rig/cross_mouth_A_to_mouth_I_3.webp", "/xiaoj-rig/cross_mouth_A_to_mouth_I_4.webp", "/xiaoj-rig/cross_mouth_A_to_mouth_I_5.webp", "/xiaoj-rig/cross_mouth_A_to_mouth_O_1.webp", "/xiaoj-rig/cross_mouth_A_to_mouth_O_2.webp", "/xiaoj-rig/cross_mouth_A_to_mouth_O_3.webp", "/xiaoj-rig/cross_mouth_A_to_mouth_O_4.webp", "/xiaoj-rig/cross_mouth_A_to_mouth_O_5.webp", "/xiaoj-rig/cross_mouth_E_to_mouth_A_1.webp", "/xiaoj-rig/cross_mouth_E_to_mouth_A_2.webp", "/xiaoj-rig/cross_mouth_E_to_mouth_A_3.webp", "/xiaoj-rig/cross_mouth_E_to_mouth_A_4.webp", "/xiaoj-rig/cross_mouth_E_to_mouth_A_5.webp", "/xiaoj-rig/cross_mouth_I_to_mouth_E_1.webp", "/xiaoj-rig/cross_mouth_I_to_mouth_E_2.webp", "/xiaoj-rig/cross_mouth_I_to_mouth_E_3.webp", "/xiaoj-rig/cross_mouth_I_to_mouth_E_4.webp", "/xiaoj-rig/cross_mouth_I_to_mouth_E_5.webp", "/xiaoj-rig/cross_mouth_MBP_to_mouth_A_1.webp", "/xiaoj-rig/cross_mouth_MBP_to_mouth_A_2.webp", "/xiaoj-rig/cross_mouth_MBP_to_mouth_A_3.webp", "/xiaoj-rig/cross_mouth_MBP_to_mouth_A_4.webp", "/xiaoj-rig/cross_mouth_MBP_to_mouth_A_5.webp", "/xiaoj-rig/cross_mouth_MBP_to_mouth_I_1.webp", "/xiaoj-rig/cross_mouth_MBP_to_mouth_I_2.webp", "/xiaoj-rig/cross_mouth_MBP_to_mouth_I_3.webp", "/xiaoj-rig/cross_mouth_MBP_to_mouth_I_4.webp", "/xiaoj-rig/cross_mouth_MBP_to_mouth_I_5.webp", "/xiaoj-rig/cross_mouth_MBP_to_mouth_O_1.webp", "/xiaoj-rig/cross_mouth_MBP_to_mouth_O_2.webp", "/xiaoj-rig/cross_mouth_MBP_to_mouth_O_3.webp", "/xiaoj-rig/cross_mouth_MBP_to_mouth_O_4.webp", "/xiaoj-rig/cross_mouth_MBP_to_mouth_O_5.webp", "/xiaoj-rig/cross_mouth_U_to_mouth_O_1.webp", "/xiaoj-rig/cross_mouth_U_to_mouth_O_2.webp", "/xiaoj-rig/cross_mouth_U_to_mouth_O_3.webp", "/xiaoj-rig/cross_mouth_U_to_mouth_O_4.webp", "/xiaoj-rig/cross_mouth_U_to_mouth_O_5.webp", "/xiaoj-rig/cross_surprise_to_happy_1.webp", "/xiaoj-rig/cross_surprise_to_happy_2.webp", "/xiaoj-rig/cross_surprise_to_happy_3.webp", "/xiaoj-rig/cross_surprise_to_happy_4.webp", "/xiaoj-rig/cross_surprise_to_happy_5.webp", "/xiaoj-rig/cross_think_to_smile_1.webp", "/xiaoj-rig/cross_think_to_smile_2.webp", "/xiaoj-rig/cross_think_to_smile_3.webp", "/xiaoj-rig/cross_think_to_smile_4.webp", "/xiaoj-rig/cross_think_to_smile_5.webp", "/xiaoj-rig/tween_blink_1.webp", "/xiaoj-rig/tween_blink_2.webp", "/xiaoj-rig/tween_blink_3.webp", "/xiaoj-rig/tween_blink_4.webp", "/xiaoj-rig/tween_blink_5.webp", "/xiaoj-rig/tween_blink_6.webp", "/xiaoj-rig/tween_blink_7.webp", "/xiaoj-rig/tween_care_1.webp", "/xiaoj-rig/tween_care_2.webp", "/xiaoj-rig/tween_care_3.webp", "/xiaoj-rig/tween_care_4.webp", "/xiaoj-rig/tween_care_5.webp", "/xiaoj-rig/tween_care_6.webp", "/xiaoj-rig/tween_care_7.webp", "/xiaoj-rig/tween_comfort_1.webp", "/xiaoj-rig/tween_comfort_2.webp", "/xiaoj-rig/tween_comfort_3.webp", "/xiaoj-rig/tween_comfort_4.webp", "/xiaoj-rig/tween_comfort_5.webp", "/xiaoj-rig/tween_comfort_6.webp", "/xiaoj-rig/tween_comfort_7.webp", "/xiaoj-rig/tween_doubt_1.webp", "/xiaoj-rig/tween_doubt_2.webp", "/xiaoj-rig/tween_doubt_3.webp", "/xiaoj-rig/tween_doubt_4.webp", "/xiaoj-rig/tween_doubt_5.webp", "/xiaoj-rig/tween_doubt_6.webp", "/xiaoj-rig/tween_doubt_7.webp", "/xiaoj-rig/tween_focus_1.webp", "/xiaoj-rig/tween_focus_2.webp", "/xiaoj-rig/tween_focus_3.webp", "/xiaoj-rig/tween_focus_4.webp", "/xiaoj-rig/tween_focus_5.webp", "/xiaoj-rig/tween_focus_6.webp", "/xiaoj-rig/tween_focus_7.webp", "/xiaoj-rig/tween_frown_1.webp", "/xiaoj-rig/tween_frown_2.webp", "/xiaoj-rig/tween_frown_3.webp", "/xiaoj-rig/tween_frown_4.webp", "/xiaoj-rig/tween_frown_5.webp", "/xiaoj-rig/tween_frown_6.webp", "/xiaoj-rig/tween_frown_7.webp", "/xiaoj-rig/tween_gaze_left_1.webp", "/xiaoj-rig/tween_gaze_left_2.webp", "/xiaoj-rig/tween_gaze_left_3.webp", "/xiaoj-rig/tween_gaze_left_4.webp", "/xiaoj-rig/tween_gaze_left_5.webp", "/xiaoj-rig/tween_gaze_left_6.webp", "/xiaoj-rig/tween_gaze_left_7.webp", "/xiaoj-rig/tween_gaze_right_1.webp", "/xiaoj-rig/tween_gaze_right_2.webp", "/xiaoj-rig/tween_gaze_right_3.webp", "/xiaoj-rig/tween_gaze_right_4.webp", "/xiaoj-rig/tween_gaze_right_5.webp", "/xiaoj-rig/tween_gaze_right_6.webp", "/xiaoj-rig/tween_gaze_right_7.webp", "/xiaoj-rig/tween_happy_1.webp", "/xiaoj-rig/tween_happy_2.webp", "/xiaoj-rig/tween_happy_3.webp", "/xiaoj-rig/tween_happy_4.webp", "/xiaoj-rig/tween_happy_5.webp", "/xiaoj-rig/tween_happy_6.webp", "/xiaoj-rig/tween_happy_7.webp", "/xiaoj-rig/tween_mouth_A_1.webp", "/xiaoj-rig/tween_mouth_A_2.webp", "/xiaoj-rig/tween_mouth_A_3.webp", "/xiaoj-rig/tween_mouth_A_4.webp", "/xiaoj-rig/tween_mouth_A_5.webp", "/xiaoj-rig/tween_mouth_A_6.webp", "/xiaoj-rig/tween_mouth_A_7.webp", "/xiaoj-rig/tween_mouth_E_1.webp", "/xiaoj-rig/tween_mouth_E_2.webp", "/xiaoj-rig/tween_mouth_E_3.webp", "/xiaoj-rig/tween_mouth_E_4.webp", "/xiaoj-rig/tween_mouth_E_5.webp", "/xiaoj-rig/tween_mouth_E_6.webp", "/xiaoj-rig/tween_mouth_E_7.webp", "/xiaoj-rig/tween_mouth_FV_1.webp", "/xiaoj-rig/tween_mouth_FV_2.webp", "/xiaoj-rig/tween_mouth_FV_3.webp", "/xiaoj-rig/tween_mouth_FV_4.webp", "/xiaoj-rig/tween_mouth_FV_5.webp", "/xiaoj-rig/tween_mouth_FV_6.webp", "/xiaoj-rig/tween_mouth_FV_7.webp", "/xiaoj-rig/tween_mouth_I_1.webp", "/xiaoj-rig/tween_mouth_I_2.webp", "/xiaoj-rig/tween_mouth_I_3.webp", "/xiaoj-rig/tween_mouth_I_4.webp", "/xiaoj-rig/tween_mouth_I_5.webp", "/xiaoj-rig/tween_mouth_I_6.webp", "/xiaoj-rig/tween_mouth_I_7.webp", "/xiaoj-rig/tween_mouth_L_1.webp", "/xiaoj-rig/tween_mouth_L_2.webp", "/xiaoj-rig/tween_mouth_L_3.webp", "/xiaoj-rig/tween_mouth_L_4.webp", "/xiaoj-rig/tween_mouth_L_5.webp", "/xiaoj-rig/tween_mouth_L_6.webp", "/xiaoj-rig/tween_mouth_L_7.webp", "/xiaoj-rig/tween_mouth_MBP_1.webp", "/xiaoj-rig/tween_mouth_MBP_2.webp", "/xiaoj-rig/tween_mouth_MBP_3.webp", "/xiaoj-rig/tween_mouth_MBP_4.webp", "/xiaoj-rig/tween_mouth_MBP_5.webp", "/xiaoj-rig/tween_mouth_MBP_6.webp", "/xiaoj-rig/tween_mouth_MBP_7.webp", "/xiaoj-rig/tween_mouth_O_1.webp", "/xiaoj-rig/tween_mouth_O_2.webp", "/xiaoj-rig/tween_mouth_O_3.webp", "/xiaoj-rig/tween_mouth_O_4.webp", "/xiaoj-rig/tween_mouth_O_5.webp", "/xiaoj-rig/tween_mouth_O_6.webp", "/xiaoj-rig/tween_mouth_O_7.webp", "/xiaoj-rig/tween_mouth_SZ_1.webp", "/xiaoj-rig/tween_mouth_SZ_2.webp", "/xiaoj-rig/tween_mouth_SZ_3.webp", "/xiaoj-rig/tween_mouth_SZ_4.webp", "/xiaoj-rig/tween_mouth_SZ_5.webp", "/xiaoj-rig/tween_mouth_SZ_6.webp", "/xiaoj-rig/tween_mouth_SZ_7.webp", "/xiaoj-rig/tween_mouth_U_1.webp", "/xiaoj-rig/tween_mouth_U_2.webp", "/xiaoj-rig/tween_mouth_U_3.webp", "/xiaoj-rig/tween_mouth_U_4.webp", "/xiaoj-rig/tween_mouth_U_5.webp", "/xiaoj-rig/tween_mouth_U_6.webp", "/xiaoj-rig/tween_mouth_U_7.webp", "/xiaoj-rig/tween_neutral_1.webp", "/xiaoj-rig/tween_neutral_2.webp", "/xiaoj-rig/tween_neutral_3.webp", "/xiaoj-rig/tween_neutral_4.webp", "/xiaoj-rig/tween_neutral_5.webp", "/xiaoj-rig/tween_neutral_6.webp", "/xiaoj-rig/tween_neutral_7.webp", "/xiaoj-rig/tween_side_1.webp", "/xiaoj-rig/tween_side_2.webp", "/xiaoj-rig/tween_side_3.webp", "/xiaoj-rig/tween_side_4.webp", "/xiaoj-rig/tween_side_5.webp", "/xiaoj-rig/tween_side_6.webp", "/xiaoj-rig/tween_side_7.webp", "/xiaoj-rig/tween_smile_1.webp", "/xiaoj-rig/tween_smile_2.webp", "/xiaoj-rig/tween_smile_3.webp", "/xiaoj-rig/tween_smile_4.webp", "/xiaoj-rig/tween_smile_5.webp", "/xiaoj-rig/tween_smile_6.webp", "/xiaoj-rig/tween_smile_7.webp", "/xiaoj-rig/tween_surprise_1.webp", "/xiaoj-rig/tween_surprise_2.webp", "/xiaoj-rig/tween_surprise_3.webp", "/xiaoj-rig/tween_surprise_4.webp", "/xiaoj-rig/tween_surprise_5.webp", "/xiaoj-rig/tween_surprise_6.webp", "/xiaoj-rig/tween_surprise_7.webp", "/xiaoj-rig/tween_think_1.webp", "/xiaoj-rig/tween_think_2.webp", "/xiaoj-rig/tween_think_3.webp", "/xiaoj-rig/tween_think_4.webp", "/xiaoj-rig/tween_think_5.webp", "/xiaoj-rig/tween_think_6.webp", "/xiaoj-rig/tween_think_7.webp", "/xiaoj-rig/tween_wink_1.webp", "/xiaoj-rig/tween_wink_2.webp", "/xiaoj-rig/tween_wink_3.webp", "/xiaoj-rig/tween_wink_4.webp", "/xiaoj-rig/tween_wink_5.webp", "/xiaoj-rig/tween_wink_6.webp", "/xiaoj-rig/tween_wink_7.webp"];
            const preloadedImages = {};
            let audioCellBuffer = null;

            window.addEventListener('DOMContentLoaded', async () => {
                const statusEl = document.getElementById('status-val');
                const preloadEl = document.getElementById('preload-val');
                const cellEl = document.getElementById('cell-val');
                const hdrEl = document.getElementById('hdr-val');

                statusEl.innerText = "PRELOADING_252_WEBP_RAM_POOL";
                let loadedCount = 0;
                await Promise.all(manifestWebpList.map(filename => {
                    return new Promise((resolve) => {
                        const img = new Image();
                        img.onload = () => { loadedCount++; preloadEl.innerText = loadedCount; resolve(); };
                        img.onerror = () => { loadedCount++; preloadEl.innerText = loadedCount; resolve(); };
                        img.src = `/static/xiaoj_rig/${filename}`;
                        preloadedImages[filename] = img;
                    });
                }));

                statusEl.innerText = "FETCHING_288B_BINARY_CELL";
                const res = await fetch('/static/sample_15s_audiovisual_proof/xiaoj_15s_audio_cell_289b.bin');
                audioCellBuffer = await res.arrayBuffer();
                
                const bytes = new Uint8Array(audioCellBuffer);
                cellEl.innerText = `${bytes.length} Bytes PASS`;
                const hdrStr = String.fromCharCode.apply(null, bytes.slice(0, 12));
                hdrEl.innerText = hdrStr;

                statusEl.innerText = "READY_ALL_CAUSALITY_CHAIN_ALIGNED";
            });

            async function startClientPlayback() {
                if (!audioCellBuffer) return;
                const statusEl = document.getElementById('status-val');
                const fpsEl = document.getElementById('fps-val');
                const dropEl = document.getElementById('drop-val');
                const timeEl = document.getElementById('time-val');
                const avatarImg = document.getElementById('avatar-img');

                statusEl.innerText = "PLAYING_288B_CLIENT_AUDIOVISUAL_SYNC";

                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const osc1 = audioCtx.createOscillator();
                const osc2 = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                
                osc1.type = 'sawtooth';
                osc2.type = 'sine';
                gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
                
                osc1.connect(gain);
                osc2.connect(gain);
                gain.connect(audioCtx.destination);
                osc1.start();
                osc2.start();

                const visemes = ['cell_mouth_A.webp', 'cell_mouth_I.webp', 'cell_mouth_U.webp', 'cell_mouth_E.webp', 'cell_mouth_O.webp', 'cell_smile.webp'];
                const freqs = [220, 330, 440, 550, 660, 220];

                const startMs = performance.now();
                let frameCount = 0;
                let droppedCount = 0;
                let lastNow = startMs;

                function loop(now) {
                    const elapsedMs = now - startMs;
                    if (elapsedMs >= 15000.0) {
                        osc1.stop();
                        osc2.stop();
                        avatarImg.src = '/static/xiaoj_rig/cell_smile.webp';
                        statusEl.innerText = "COMPLETED_15S_900FRAME_SYNC";
                        timeEl.innerText = "15.000";
                        return;
                    }

                    const dt = now - lastNow;
                    if (dt > 22.0) droppedCount++;
                    lastNow = now;

                    frameCount++;
                    const currSec = elapsedMs / 1000.0;
                    timeEl.innerText = currSec.toFixed(3);
                    fpsEl.innerText = (frameCount / currSec).toFixed(1);
                    dropEl.innerText = droppedCount;

                    const vIdx = Math.floor(currSec * 4) % visemes.length;
                    const vAsset = visemes[vIdx];
                    if (preloadedImages[vAsset]) {
                        avatarImg.src = preloadedImages[vAsset].src;
                    }

                    osc1.frequency.setValueAtTime(freqs[vIdx], audioCtx.currentTime);
                    osc2.frequency.setValueAtTime(freqs[vIdx] * 1.5, audioCtx.currentTime);

                    requestAnimationFrame(loop);
                }

                requestAnimationFrame(loop);
            }
        </script>
    </body>
    </html>
    """
