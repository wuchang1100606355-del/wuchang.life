/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

const HANDOFF_CHANNEL = "wuchang_delivery_dispatch";
const HANDOFF_ENDPOINT = "/api/notification/broadcast";

const BackgroundService = {
    audio: new Audio("/wuchang_core/static/audio/alert.mp3"),
    isOnDuty: true,
    cooldownUntil: null,
    handoffPanels: new Map(),

    init(bus) {
        this.bus = bus;
        if (typeof this.bus.addChannel === "function") {
            this.bus.addChannel(HANDOFF_CHANNEL);
        }
        this.bus.addEventListener("notification", this._onNotification.bind(this));
        this._checkCooldown();
    },

    _onNotification({ detail: notifications }) {
        for (const notif of notifications) {
            if (notif.type === "wuchang_delivery_dispatch") {
                this._handleDispatch(notif.payload || {});
            }
        }
    },

    _handleDispatch(payload) {
        if (payload.action === "new_mission_alert") {
            this._showHandoff(payload);
        } else if (payload.action === "mission_taken") {
            this._setHandoffStatus(payload.receipt && payload.receipt.handoff_ref, "已由店員接手處理");
            this.audio.pause();
            this.audio.currentTime = 0;
        } else if (payload.action === "mission_resolved") {
            this._setHandoffStatus(payload.receipt && payload.receipt.handoff_ref, "店員已完成處理");
            this.audio.pause();
            this.audio.currentTime = 0;
        }
    },

    _showHandoff(payload) {
        const data = payload.data || {};
        const handoffRef = String(data.handoff_ref || "");
        if (!handoffRef || !this.isOnDuty || this._isCoolingDown()) {
            return;
        }
        this.audio.loop = true;
        this.audio.play().catch(() => {});
        if (Notification.permission === "granted") {
            new Notification("小J需要店內協助", { body: this._handoffLabel(data) });
        }
        if (this.handoffPanels.has(handoffRef)) {
            return;
        }
        const panel = document.createElement("section");
        panel.className = "o_wuchang_handoff_panel";
        panel.style.cssText = "position:fixed;right:20px;bottom:20px;z-index:2147483647;max-width:360px;padding:16px;background:#fff7e8;border:2px solid #c85f26;border-radius:12px;box-shadow:0 12px 30px rgba(0,0,0,.2);font:15px sans-serif;color:#3f2b22";
        const title = document.createElement("strong");
        title.textContent = "小J需要店內協助";
        const detail = document.createElement("p");
        detail.textContent = this._handoffLabel(data);
        const status = document.createElement("p");
        status.textContent = "等待店員明確確認";
        const acknowledge = document.createElement("button");
        acknowledge.type = "button";
        acknowledge.textContent = "我來處理";
        const resolve = document.createElement("button");
        resolve.type = "button";
        resolve.textContent = "處理完成";
        resolve.disabled = true;
        resolve.style.marginLeft = "8px";
        acknowledge.addEventListener("click", () => this._acknowledgeHandoff(handoffRef, acknowledge, resolve, status));
        resolve.addEventListener("click", () => this._resolveHandoff(handoffRef, resolve, status));
        panel.append(title, detail, status, acknowledge, resolve);
        document.body.appendChild(panel);
        this.handoffPanels.set(handoffRef, { panel, status });
    },

    _handoffLabel(data) {
        const table = data.table_ref ? `${data.table_ref} ` : "";
        return `${table}${data.problem_class || "GENERAL_SERVICE_ASSISTANCE"}`;
    },

    _post(action, payload) {
        const fetchFn = browser.fetch || window.fetch;
        return fetchFn(HANDOFF_ENDPOINT, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action, ...payload }),
        }).then((response) => response.json());
    },

    _acknowledgeHandoff(handoffRef, acknowledge, resolve, status) {
        acknowledge.disabled = true;
        status.textContent = "正在送出店員確認";
        this._post("human_acknowledge", { handoff_ref: handoffRef })
            .then((result) => {
                if (!result || result.state !== "HUMAN_REVIEW_ACKNOWLEDGED" || !result.receipt) {
                    throw new Error("acknowledgement_not_accepted");
                }
                status.textContent = "已確認接手，可在完成後回報結果";
                resolve.disabled = false;
            })
            .catch(() => {
                acknowledge.disabled = false;
                status.textContent = "確認未送達，請再試一次";
            });
    },

    _resolveHandoff(handoffRef, resolve, status) {
        resolve.disabled = true;
        status.textContent = "正在回報處理結果";
        this._post("human_resolution", {
            handoff_ref: handoffRef,
            result_class: "GENERAL_ASSISTANCE_RESOLVED",
            human_action_semantic: "STAFF_ASSISTANCE",
            human_response_semantic: "GENERAL_ASSISTANCE_PROVIDED",
        }).then((result) => {
            if (!result || result.state !== "HUMAN_REVIEW_RESOLVED" || !result.result_packet) {
                throw new Error("resolution_not_accepted");
            }
            status.textContent = "處理結果已形成候選封包";
            this.completeMission();
        }).catch(() => {
            resolve.disabled = false;
            status.textContent = "結果未送達，請確認後再試一次";
        });
    },

    _setHandoffStatus(handoffRef, message) {
        const entry = this.handoffPanels.get(String(handoffRef || ""));
        if (entry) {
            entry.status.textContent = message;
        }
    },

    _isCoolingDown() {
        return Boolean(this.cooldownUntil && new Date() < this.cooldownUntil);
    },

    _checkCooldown() {
        setInterval(() => {
            if (this.cooldownUntil && new Date() >= this.cooldownUntil) {
                this.cooldownUntil = null;
            }
        }, 60000);
    },

    toggleDuty(active) {
        this.isOnDuty = Boolean(active);
    },

    completeMission() {
        this.cooldownUntil = new Date(new Date().getTime() + 15 * 60000);
        this.audio.pause();
        this.audio.currentTime = 0;
    },
};

registry.category("services").add("wuchang_background_service", {
    dependencies: ["bus_service"],
    start(_env, { bus_service: busService }) {
        BackgroundService.init(busService);
        return BackgroundService;
    },
});

export default BackgroundService;
