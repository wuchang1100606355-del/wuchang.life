odoo.define("wuchang_core.pos_extension", function (require) {
    "use strict"

    // 五常太極：V3 MIX EDLA 專屬客顯語音驅動
    let synth = window.speechSynthesis
    let voiceUnlocked = false

    // 1. 【破冰解鎖】綁定在店員(哥哥)點擊 POS 畫面的任何操作上
    document.body.addEventListener(
        "touchstart",
        function () {
            if (!voiceUnlocked) {
                // 播放一個無聲的空白語音，騙過 Android Chrome 解除靜音封印
                let unlockUtterance = new SpeechSynthesisUtterance("")
                synth.speak(unlockUtterance)
                voiceUnlocked = true
                console.log("🔓 V3 MIX 實體聲帶已解鎖！")
            }
        },
        { once: true }
    ) // 只執行一次

    // 2. 【正式發聲】當 4070 顯卡傳回文字時觸發
    function speakAIResponse(text) {
        if (synth) {
            let utterance = new SpeechSynthesisUtterance(text)

            // 針對 EDLA 內建的 Google TTS 引擎進行物理調校
            utterance.lang = "zh-TW"
            utterance.rate = 0.95
            utterance.pitch = 1.05
            utterance.volume = 1.0

            // 強制鎖定 Google 的台灣女聲 (如果有)
            let voices = synth.getVoices()
            let twVoice = voices.find((voice) => voice.name.includes("Google") && voice.lang === "zh-TW")
            if (twVoice) utterance.voice = twVoice

            console.log("🔊 V3 MIX 正在用 Google 聲帶播報社工回應...")
            synth.speak(utterance)
        }
    }

    window.speakAIResponse = speakAIResponse
})
