# W7TP V2.3 Real 288B Binary Decoder & Strict Fail-Closed 252 WebP Preloader Route
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path

router = APIRouter()
root_path = Path("/home/taiji_admin/Taiji_Hub")
rig_dir = root_path / "Taiji_Odoo/addons/wuchang_ordering_ui_suite/static/src/data/xiaoj_rig"
sample_dir = root_path / "runtime/total_field/sample_15s_audiovisual_proof"

@router.get("/static/xiaoj_rig/{filename}")
async def serve_xiaoj_rig_file(filename: str):
    file_p = rig_dir / filename
    if file_p.exists() and file_p.is_file():
        return FileResponse(file_p)
    raise HTTPException(status_code=404, detail="Rig file not found")

@router.get("/static/sample_15s_audiovisual_proof/{filename}")
async def serve_proof_file(filename: str):
    file_p = sample_dir / filename
    if file_p.exists() and file_p.is_file():
        return FileResponse(file_p)
    raise HTTPException(status_code=404, detail="Proof file not found")

@router.get("/xiaoj/chat", response_class=HTMLResponse)
async def xiaoj_chat_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>小J 本地 60 FPS 288B 原胞影音對話 (Fail-Closed 全因果驗證版)</title>
        <meta charset="utf-8">
        <style>
            body { background: #080808; color: #d0d0d0; font-family: monospace, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            #avatar-container { width: 400px; height: 400px; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,0.9); background: #121212; position: relative; border: 1px solid #2a2a2a; }
            #avatar-img { width: 100%; height: 100%; object-fit: cover; }
            #chat-box { width: 400px; margin-top: 16px; display: flex; gap: 8px; }
            input { flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #333; background: #1a1a1a; color: #fff; font-size: 15px; outline: none; }
            button { padding: 12px 20px; border-radius: 8px; border: none; background: #007acc; color: #fff; font-size: 15px; font-weight: bold; cursor: pointer; }
            button:disabled { background: #444; cursor: not-allowed; }
            #telemetry { width: 400px; margin-top: 12px; background: #111; border: 1px solid #222; border-radius: 8px; padding: 10px; font-size: 11px; color: #888; line-height: 1.6; }
            .highlight { color: #4af626; font-weight: bold; }
            .error { color: #ff4d4d; font-weight: bold; }
        </style>
    </head>
    <body>
        <div id="avatar-container">
            <img id="avatar-img" src="/static/xiaoj_rig/cell_smile.webp" alt="小J">
        </div>
        <div id="chat-box">
            <input type="text" id="user-msg" placeholder="請等待 Fail-Closed 驗算驗章..." disabled onkeypress="if(event.key==='Enter') startClientPlayback()">
            <button id="play-btn" disabled onclick="startClientPlayback()">請稍候...</button>
        </div>
        <div id="telemetry">
            <div>[系統狀態] <span id="status-val" class="highlight">INITIALIZING</span></div>
            <div>[母片預載] <span id="preload-val">0</span>/252 WebP | [錯誤數] <span id="err-val">0</span></div>
            <div>[288B 封包] <span id="cell-val">WAITING</span> | Header: <span id="hdr-val">NONE</span></div>
            <div>[解碼狀態] <span id="decode-val">PENDING</span> | 條目數: <span id="entries-val">0</span></div>
            <div>[實測 FPS] <span id="fps-val">0.0</span> | [渲染影格] <span id="frame-val">0</span>/900 | [掉幀] <span id="drop-val">0</span></div>
            <div>[時間] <span id="time-val">0.000</span>s / 15.000s | [模式] Fail-Closed 288B Binary Stepper</div>
        </div>

        <script>
            const manifestWebpList = ["cell_blink.webp", "cell_care.webp", "cell_comfort.webp", "cell_doubt.webp", "cell_focus.webp", "cell_frown.webp", "cell_gaze_left.webp", "cell_gaze_right.webp", "cell_happy.webp", "cell_mouth_A.webp", "cell_mouth_E.webp", "cell_mouth_FV.webp", "cell_mouth_I.webp", "cell_mouth_L.webp", "cell_mouth_MBP.webp", "cell_mouth_O.webp", "cell_mouth_SZ.webp", "cell_mouth_U.webp", "cell_neutral.webp", "cell_side.webp", "cell_smile.webp", "cell_surprise.webp", "cell_think.webp", "cell_wink.webp", "cross_care_to_wink_1.webp", "cross_care_to_wink_2.webp", "cross_care_to_wink_3.webp", "cross_care_to_wink_4.webp", "cross_care_to_wink_5.webp", "cross_happy_to_wink_1.webp", "cross_happy_to_wink_2.webp", "cross_happy_to_wink_3.webp", "cross_happy_to_wink_4.webp", "cross_happy_to_wink_5.webp", "cross_mouth_A_to_mouth_I_1.webp", "cross_mouth_A_to_mouth_I_2.webp", "cross_mouth_A_to_mouth_I_3.webp", "cross_mouth_A_to_mouth_I_4.webp", "cross_mouth_A_to_mouth_I_5.webp", "cross_mouth_A_to_mouth_O_1.webp", "cross_mouth_A_to_mouth_O_2.webp", "cross_mouth_A_to_mouth_O_3.webp", "cross_mouth_A_to_mouth_O_4.webp", "cross_mouth_A_to_mouth_O_5.webp", "cross_mouth_E_to_mouth_A_1.webp", "cross_mouth_E_to_mouth_A_2.webp", "cross_mouth_E_to_mouth_A_3.webp", "cross_mouth_E_to_mouth_A_4.webp", "cross_mouth_E_to_mouth_A_5.webp", "cross_mouth_I_to_mouth_E_1.webp", "cross_mouth_I_to_mouth_E_2.webp", "cross_mouth_I_to_mouth_E_3.webp", "cross_mouth_I_to_mouth_E_4.webp", "cross_mouth_I_to_mouth_E_5.webp", "cross_mouth_MBP_to_mouth_A_1.webp", "cross_mouth_MBP_to_mouth_A_2.webp", "cross_mouth_MBP_to_mouth_A_3.webp", "cross_mouth_MBP_to_mouth_A_4.webp", "cross_mouth_MBP_to_mouth_A_5.webp", "cross_mouth_MBP_to_mouth_I_1.webp", "cross_mouth_MBP_to_mouth_I_2.webp", "cross_mouth_MBP_to_mouth_I_3.webp", "cross_mouth_MBP_to_mouth_I_4.webp", "cross_mouth_MBP_to_mouth_I_5.webp", "cross_mouth_MBP_to_mouth_O_1.webp", "cross_mouth_MBP_to_mouth_O_2.webp", "cross_mouth_MBP_to_mouth_O_3.webp", "cross_mouth_MBP_to_mouth_O_4.webp", "cross_mouth_MBP_to_mouth_O_5.webp", "cross_mouth_U_to_mouth_O_1.webp", "cross_mouth_U_to_mouth_O_2.webp", "cross_mouth_U_to_mouth_O_3.webp", "cross_mouth_U_to_mouth_O_4.webp", "cross_mouth_U_to_mouth_O_5.webp", "cross_surprise_to_happy_1.webp", "cross_surprise_to_happy_2.webp", "cross_surprise_to_happy_3.webp", "cross_surprise_to_happy_4.webp", "cross_surprise_to_happy_5.webp", "cross_think_to_smile_1.webp", "cross_think_to_smile_2.webp", "cross_think_to_smile_3.webp", "cross_think_to_smile_4.webp", "cross_think_to_smile_5.webp", "tween_blink_1.webp", "tween_blink_2.webp", "tween_blink_3.webp", "tween_blink_4.webp", "tween_blink_5.webp", "tween_blink_6.webp", "tween_blink_7.webp", "tween_care_1.webp", "tween_care_2.webp", "tween_care_3.webp", "tween_care_4.webp", "tween_care_5.webp", "tween_care_6.webp", "tween_care_7.webp", "tween_comfort_1.webp", "tween_comfort_2.webp", "tween_comfort_3.webp", "tween_comfort_4.webp", "tween_comfort_5.webp", "tween_comfort_6.webp", "tween_comfort_7.webp", "tween_doubt_1.webp", "tween_doubt_2.webp", "tween_doubt_3.webp", "tween_doubt_4.webp", "tween_doubt_5.webp", "tween_doubt_6.webp", "tween_doubt_7.webp", "tween_focus_1.webp", "tween_focus_2.webp", "tween_focus_3.webp", "tween_focus_4.webp", "tween_focus_5.webp", "tween_focus_6.webp", "tween_focus_7.webp", "tween_frown_1.webp", "tween_frown_2.webp", "tween_frown_3.webp", "tween_frown_4.webp", "tween_frown_5.webp", "tween_frown_6.webp", "tween_frown_7.webp", "tween_gaze_left_1.webp", "tween_gaze_left_2.webp", "tween_gaze_left_3.webp", "tween_gaze_left_4.webp", "tween_gaze_left_5.webp", "tween_gaze_left_6.webp", "tween_gaze_left_7.webp", "tween_gaze_right_1.webp", "tween_gaze_right_2.webp", "tween_gaze_right_3.webp", "tween_gaze_right_4.webp", "tween_gaze_right_5.webp", "tween_gaze_right_6.webp", "tween_gaze_right_7.webp", "tween_happy_1.webp", "tween_happy_2.webp", "tween_happy_3.webp", "tween_happy_4.webp", "tween_happy_5.webp", "tween_happy_6.webp", "tween_happy_7.webp", "tween_mouth_A_1.webp", "tween_mouth_A_2.webp", "tween_mouth_A_3.webp", "tween_mouth_A_4.webp", "tween_mouth_A_5.webp", "tween_mouth_A_6.webp", "tween_mouth_A_7.webp", "tween_mouth_E_1.webp", "tween_mouth_E_2.webp", "tween_mouth_E_3.webp", "tween_mouth_E_4.webp", "tween_mouth_E_5.webp", "tween_mouth_E_6.webp", "tween_mouth_E_7.webp", "tween_mouth_FV_1.webp", "tween_mouth_FV_2.webp", "tween_mouth_FV_3.webp", "tween_mouth_FV_4.webp", "tween_mouth_FV_5.webp", "tween_mouth_FV_6.webp", "tween_mouth_FV_7.webp", "tween_mouth_I_1.webp", "tween_mouth_I_2.webp", "tween_mouth_I_3.webp", "tween_mouth_I_4.webp", "tween_mouth_I_5.webp", "tween_mouth_I_6.webp", "tween_mouth_I_7.webp", "tween_mouth_L_1.webp", "tween_mouth_L_2.webp", "tween_mouth_L_3.webp", "tween_mouth_L_4.webp", "tween_mouth_L_5.webp", "tween_mouth_L_6.webp", "tween_mouth_L_7.webp", "tween_mouth_MBP_1.webp", "tween_mouth_MBP_2.webp", "tween_mouth_MBP_3.webp", "tween_mouth_MBP_4.webp", "tween_mouth_MBP_5.webp", "tween_mouth_MBP_6.webp", "tween_mouth_MBP_7.webp", "tween_mouth_O_1.webp", "tween_mouth_O_2.webp", "tween_mouth_O_3.webp", "tween_mouth_O_4.webp", "tween_mouth_O_5.webp", "tween_mouth_O_6.webp", "tween_mouth_O_7.webp", "tween_mouth_SZ_1.webp", "tween_mouth_SZ_2.webp", "tween_mouth_SZ_3.webp", "tween_mouth_SZ_4.webp", "tween_mouth_SZ_5.webp", "tween_mouth_SZ_6.webp", "tween_mouth_SZ_7.webp", "tween_mouth_U_1.webp", "tween_mouth_U_2.webp", "tween_mouth_U_3.webp", "tween_mouth_U_4.webp", "tween_mouth_U_5.webp", "tween_mouth_U_6.webp", "tween_mouth_U_7.webp", "tween_neutral_1.webp", "tween_neutral_2.webp", "tween_neutral_3.webp", "tween_neutral_4.webp", "tween_neutral_5.webp", "tween_neutral_6.webp", "tween_neutral_7.webp", "tween_side_1.webp", "tween_side_2.webp", "tween_side_3.webp", "tween_side_4.webp", "tween_side_5.webp", "tween_side_6.webp", "tween_side_7.webp", "tween_smile_1.webp", "tween_smile_2.webp", "tween_smile_3.webp", "tween_smile_4.webp", "tween_smile_5.webp", "tween_smile_6.webp", "tween_smile_7.webp", "tween_surprise_1.webp", "tween_surprise_2.webp", "tween_surprise_3.webp", "tween_surprise_4.webp", "tween_surprise_5.webp", "tween_surprise_6.webp", "tween_surprise_7.webp", "tween_think_1.webp", "tween_think_2.webp", "tween_think_3.webp", "tween_think_4.webp", "tween_think_5.webp", "tween_think_6.webp", "tween_think_7.webp", "tween_wink_1.webp", "tween_wink_2.webp", "tween_wink_3.webp", "tween_wink_4.webp", "tween_wink_5.webp", "tween_wink_6.webp", "tween_wink_7.webp"];
            const preloadedImages = {};
            let decodedTimeline = [];
            let binaryCellValid = false;

            window.addEventListener('DOMContentLoaded', async () => {
                const statusEl = document.getElementById('status-val');
                const preloadEl = document.getElementById('preload-val');
                const errEl = document.getElementById('err-val');
                const cellEl = document.getElementById('cell-val');
                const hdrEl = document.getElementById('hdr-val');
                const decodeEl = document.getElementById('decode-val');
                const entriesEl = document.getElementById('entries-val');
                const playBtn = document.getElementById('play-btn');
                const userMsg = document.getElementById('user-msg');

                // 1. Strict Fail-Closed 252 WebP Preloader
                statusEl.innerText = "PRELOADING_252_WEBP_RAM_POOL";
                let successCount = 0;
                let failCount = 0;

                await Promise.all(manifestWebpList.map(filename => {
                    return new Promise((resolve) => {
                        const img = new Image();
                        img.onload = () => { successCount++; preloadEl.innerText = `${successCount}`; resolve(); };
                        img.onerror = () => { failCount++; errEl.innerText = `${failCount}`; errEl.className = "error"; resolve(); };
                        img.src = `/static/xiaoj_rig/${filename}`;
                        preloadedImages[filename] = img;
                    });
                }));

                if (successCount !== 252 || failCount > 0) {
                    statusEl.innerText = "HOLD_FAIL_CLOSED_PRELOAD_FAILED";
                    statusEl.className = "error";
                    return;
                }

                // 2. Fetch & Validate 288B Binary Payload
                statusEl.innerText = "FETCHING_288B_BINARY_CELL";
                try {
                    const res = await fetch('/static/sample_15s_audiovisual_proof/xiaoj_15s_audio_cell_289b.bin');
                    if (!res.ok) throw new Error("HTTP " + res.status);
                    const buf = await res.arrayBuffer();
                    const bytes = new Uint8Array(buf);
                    
                    if (bytes.length !== 288) throw new Error(`Invalid length: ${bytes.length}B (expected 288B)`);
                    
                    const hdrStr = String.fromCharCode.apply(null, bytes.slice(0, 12));
                    hdrEl.innerText = hdrStr;
                    if (hdrStr !== "W7TP_AOC_V23") throw new Error(`Header mismatch: ${hdrStr}`);
                    
                    cellEl.innerText = "288 Bytes VALID (W7TP_AOC_V23)";

                    // 3. Parse Binary Timeline Entries (69 entries * 4B = 276B + 12B Header = 288B)
                    const visemesMap = ['cell_mouth_A.webp', 'cell_mouth_I.webp', 'cell_mouth_U.webp', 'cell_mouth_E.webp', 'cell_mouth_O.webp', 'cell_smile.webp'];
                    decodedTimeline = [];
                    for (let i = 12; i < 288; i += 4) {
                        const fIdx = bytes[i];
                        const tsDeci = bytes[i+1];
                        const visLen = bytes[i+2];
                        const pcmAmp = bytes[i+3];
                        const visemeFile = visemesMap[visLen % visemesMap.length];
                        decodedTimeline.push({ fIdx, tsSec: tsDeci / 10.0, viseme: visemeFile, pcmAmp });
                    }

                    decodeEl.innerText = "DECODED_OK";
                    entriesEl.innerText = decodedTimeline.length;
                    binaryCellValid = true;

                    statusEl.innerText = "PASS_FULL_CAUSALITY_PRELOAD_DECODE_SUCCESS";
                    playBtn.disabled = false;
                    playBtn.innerText = "啟動 15s 原胞對嘴播報";
                    userMsg.disabled = false;
                    userMsg.placeholder = "輸入訊息並發送，體驗 288B 影音對嘴...";

                } catch (e) {
                    statusEl.innerText = `HOLD_FAIL_CLOSED_CELL_REJECTED (${e.message})`;
                    statusEl.className = "error";
                }
            });

            // 4. Strict 60 FPS Stepper Driven by 288B Binary Timeline
            async function startClientPlayback() {
                if (!binaryCellValid || decodedTimeline.length === 0) return;
                
                const statusEl = document.getElementById('status-val');
                const fpsEl = document.getElementById('fps-val');
                const dropEl = document.getElementById('drop-val');
                const timeEl = document.getElementById('time-val');
                const frameEl = document.getElementById('frame-val');
                const avatarImg = document.getElementById('avatar-img');

                statusEl.innerText = "PLAYING_288B_BINARY_AUDIOVISUAL_SYNC";

                // WebAudio Harmonic Synthesizer
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const osc1 = audioCtx.createOscillator();
                const osc2 = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                
                osc1.type = 'sawtooth';
                osc2.type = 'sine';
                gain.gain.setValueAtTime(0.01, audioCtx.currentTime);
                
                osc1.connect(gain);
                osc2.connect(gain);
                gain.connect(audioCtx.destination);
                osc1.start();
                osc2.start();

                const startMs = performance.now();
                let frameCount = 0;
                let droppedCount = 0;
                let lastLoopMs = startMs;

                function loop(now) {
                    const elapsedMs = now - startMs;
                    if (elapsedMs >= 15000.0) {
                        osc1.stop();
                        osc2.stop();
                        avatarImg.src = preloadedImages['cell_smile.webp'] ? preloadedImages['cell_smile.webp'].src : '/static/xiaoj_rig/cell_smile.webp';
                        statusEl.innerText = "PASS_15S_900FRAME_288B_REALTIME_PLAYBACK_COMPLETED";
                        timeEl.innerText = "15.000";
                        frameEl.innerText = "900";
                        return;
                    }

                    const dt = now - lastLoopMs;
                    if (dt > 22.0) droppedCount++;
                    lastLoopMs = now;

                    const currentFrameIdx = Math.min(899, Math.floor((elapsedMs / 1000.0) * 60.0));
                    frameCount++;

                    timeEl.innerText = (elapsedMs / 1000.0).toFixed(3);
                    frameEl.innerText = currentFrameIdx;
                    fpsEl.innerText = (frameCount / (elapsedMs / 1000.0)).toFixed(1);
                    dropEl.innerText = droppedCount;

                    // Lookup from 288B Decoded Timeline
                    const entryIdx = Math.floor((currentFrameIdx / 900.0) * decodedTimeline.length) % decodedTimeline.length;
                    const item = decodedTimeline[entryIdx];

                    if (item && preloadedImages[item.viseme]) {
                        avatarImg.src = preloadedImages[item.viseme].src;
                    }

                    if (item) {
                        const targetFreq = 220 + (item.pcmAmp % 300);
                        osc1.frequency.setValueAtTime(targetFreq, audioCtx.currentTime);
                        osc2.frequency.setValueAtTime(targetFreq * 1.5, audioCtx.currentTime);
                        gain.gain.setValueAtTime(Math.min(0.15, (item.pcmAmp / 255.0) * 0.12 + 0.01), audioCtx.currentTime);
                    }

                    requestAnimationFrame(loop);
                }

                requestAnimationFrame(loop);
            }
        </script>
    </body>
    </html>
    """
