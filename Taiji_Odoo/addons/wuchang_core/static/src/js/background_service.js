/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
// We use the web client's bus or a similar mechanism in modern Odoo.
// For Odoo 16+, we typically use the bus service.
// Assuming this module runs in the context where 'bus_service' is available.
// However, sticking to the user's provided structure as much as possible while adapting to ES6 modules.

const BackgroundService = {
    audio: new Audio('/wuchang_core/static/audio/alert.mp3'), // Updated path to match module name
    isOnDuty: false,
    cooldownUntil: null,

    init: function(bus) {
        // bus service instance passed from a setup function or component
        this.bus = bus;
        this.bus.addEventListener('notification', this._onNotification.bind(this));
        
        // 檢查冷卻狀態
        this._checkCooldown();
    },

    _onNotification: function({ detail: notifications }) {
        for (const notif of notifications) {
            if (notif.type === 'wuchang_delivery_dispatch') {
                this._handleDispatch(notif.payload);
            }
        }
    },

    _handleDispatch: function(payload) {
        if (payload.action === 'new_mission_alert') {
            if (this.isOnDuty && !this._isCoolingDown()) {
                // 1. 播放響鈴 (Loop)
                this.audio.loop = true;
                this.audio.play().catch(e => console.log('Audio error:', e));
                
                // 2. 顯示系統通知 (Native Push Notification)
                if (Notification.permission === "granted") {
                    new Notification(payload.data.title, { body: payload.data.body });
                }
                
                // 3. 顯示前端 UI 彈窗 (React/QWeb Update)
                // In a real scenario, we might use a reactive state or event bus to update the UI
                console.log('Incoming Mission:', payload.data);
            }
        } else if (payload.action === 'mission_taken') {
            // 任務已被搶走 (或自己搶到) -> 停止響鈴
            this.audio.pause();
            this.audio.currentTime = 0;
            console.log('Mission Taken');
        }
    },

    _isCoolingDown: function() {
        if (!this.cooldownUntil) return false;
        return new Date() < this.cooldownUntil;
    },

    _checkCooldown: function() {
        // 每分鐘檢查一次，若冷卻結束則恢復
        setInterval(() => {
            if (this.cooldownUntil && new Date() >= this.cooldownUntil) {
                this.cooldownUntil = null;
                console.log('Cooldown ended. Back to active duty.');
            }
        }, 60000);
    },

    toggleDuty: function(active) {
        this.isOnDuty = active;
        // 呼叫後端更新狀態 logic would go here
    },

    completeMission: function() {
        // 設定 15 分鐘冷卻
        this.cooldownUntil = new Date(new Date().getTime() + 15 * 60000);
        this.audio.pause();
    }
};

export default BackgroundService;
