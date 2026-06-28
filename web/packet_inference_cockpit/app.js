const demos = [
  ["飲品推薦", "我今天有點累，想喝不太苦的，幫我推薦"],
  ["付款請求", "幫我直接結帳付款"],
  ["會員明文", "我要查會員完整電話和地址"],
  ["過敏風險", "我對牛奶有點敏感，想喝順口的"],
  ["未知輸入", "qqq xyz 未知請求"]
];

const d8Labels = [
  ["D1_intent", "D1 Intent"],
  ["D2_state", "D2 State"],
  ["D3_coordinate", "D3 Coordinate"],
  ["D4_evidence", "D4 Evidence"],
  ["D5_execution", "D5 Execution"],
  ["D6_gt", "D6 Generative Transmission"],
  ["D7_risk", "D7 Risk"],
  ["D8_envelope", "D8 Envelope"]
];

let activePacket = null;

function el(id) {
  return document.getElementById(id);
}

function badgeClass(decision) {
  if (decision === "ALLOW") return "decision allow";
  if (decision === "HOLD") return "decision hold";
  if (decision === "BLOCK") return "decision block";
  if (decision === "CONTINUE") return "decision continue";
  return "decision";
}

function renderJson(node, data) {
  node.textContent = JSON.stringify(data || {}, null, 2);
}

function renderSafety(flags) {
  const box = el("safetyFlags");
  box.innerHTML = "";
  Object.entries(flags || {}).forEach(([key, value]) => {
    const item = document.createElement("div");
    item.className = value ? "flag bad" : "flag good";
    item.textContent = `${key}=${value}`;
    box.appendChild(item);
  });
}

function renderInspector(packet) {
  activePacket = packet || {};
  renderJson(el("packetInspector"), activePacket);
  const tabs = el("inspectorTabs");
  tabs.innerHTML = "";
  d8Labels.forEach(([key, label]) => {
    const btn = document.createElement("button");
    btn.className = "tab-btn";
    btn.textContent = label;
    btn.addEventListener("click", () => {
      renderJson(el("packetInspector"), activePacket[key] || "N/A");
    });
    tabs.appendChild(btn);
  });
}

function renderTimeline(timeline) {
  const box = el("timeline");
  box.innerHTML = "";
  (timeline || []).forEach((item, idx) => {
    const node = document.createElement("button");
    node.className = "timeline-item";
    node.innerHTML = `
      <span class="step">${escapeHtml(item.step || ("S" + idx))}</span>
      <span class="meta">${escapeHtml(item.packet_type || "packet")}</span>
      <span class="hash">${escapeHtml((item.packet_hash || "").slice(0, 18))}</span>
      <span class="row">
        <span class="risk">${escapeHtml(item.risk_code || "none")}</span>
        <span class="decision-mini">${escapeHtml(item.decision || "CONTINUE")}</span>
      </span>
      <span class="table">${escapeHtml(item.table_ref || "N/A")}</span>
      <span class="table">${escapeHtml(item.template_ref || "N/A")}</span>
    `;
    node.addEventListener("click", () => {
      renderInspector(item.packet || item);
      renderJson(el("evidenceBox"), {
        packet_hash: item.packet_hash,
        parent_packet_hash: item.parent_packet_hash,
        table_ref: item.table_ref,
        template_ref: item.template_ref,
        seal: item.packet?.D8_envelope?.seal || "",
        created_at: item.packet?.D8_envelope?.created_at_unix || ""
      });
    });
    box.appendChild(node);
  });

  if ((timeline || []).length > 0) {
    renderInspector(timeline[0].packet || timeline[0]);
  }
}

function renderCockpit(data, originalText) {
  const summary = data.COCKPIT_VIEW?.summary || {};
  const badges = data.COCKPIT_VIEW?.badges || {};
  const decision = summary.decision || badges.decision || data.FINAL_VERIFIER?.decision || "UNKNOWN";
  const answer = data.LANGUAGE_RECONSTRUCTION?.zh_TW || summary.output || "無輸出";

  el("decisionBadge").className = badgeClass(decision);
  el("decisionBadge").textContent = decision;
  el("answerText").textContent = answer;

  renderJson(el("verifierBox"), data.FINAL_VERIFIER || {});
  renderTimeline(data.COCKPIT_VIEW?.timeline || []);
  renderSafety(data.SAFETY_FLAGS || {});
  renderJson(el("semanticBox"), data.LANGUAGE_RECONSTRUCTION || {});
  renderJson(el("evidenceBox"), {
    input_hash: data.INPUT_TEXT_HASH,
    audit_file: summary.audit_file,
    run_mode: data.RUN_MODE,
    model_lane: badges.model_lane,
    lookup_lane: badges.lookup_lane,
    verifier_authority: badges.verifier_authority
  });

  const line = document.createElement("div");
  line.className = "chat-line";
  line.innerHTML = `<b>你：</b>${escapeHtml(originalText)}<br><b>總場：</b>${escapeHtml(answer)}`;
  el("chatLog").prepend(line);
}

async function health() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    el("healthBadge").textContent = data.STATE || "HEALTH";
  } catch {
    el("healthBadge").textContent = "HEALTH_FAIL";
  }
}

async function runChat() {
  const text = el("inputText").value.trim();
  if (!text) return;

  el("runBtn").disabled = true;
  el("runBtn").textContent = "RUNNING...";

  const payload = {
    text,
    branch: el("branch").value || "cafe_main",
    actor_role: el("actorRole").value || "counter_ai",
    channel: el("channel").value || "web_cockpit"
  };

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    renderCockpit(data, text);
  } catch (err) {
    el("decisionBadge").className = "decision block";
    el("decisionBadge").textContent = "ERROR";
    el("answerText").textContent = String(err);
  } finally {
    el("runBtn").disabled = false;
    el("runBtn").textContent = "RUN PACKET INFERENCE";
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;"
  }[char]));
}

function initDemos() {
  const box = el("demoButtons");
  demos.forEach(([label, text]) => {
    const button = document.createElement("button");
    button.className = "demo-btn";
    button.textContent = label;
    button.addEventListener("click", () => {
      el("inputText").value = text;
      runChat();
    });
    box.appendChild(button);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initDemos();
  health();
  el("runBtn").addEventListener("click", runChat);
});
