/** @odoo-module **/

export const SUITE_SETTING = Object.freeze({
  key: "liaoguo.ui.selected_suite.company_3.pos_unresolved",
  companyId: 1,
  posConfigId: 2,
  branchRef: "merchant_ref:shangpin-liaoguo-cafe-chongxin-hq",
});

export const ROLES = Object.freeze(["staff_pos", "online_ordering", "in_store_self_service"]);

export const SUITES = Object.freeze({
  a: Object.freeze({
    name: "靛藍科技",
    aliases: Object.freeze(["a", "靛藍科技", "曜石靛藍", "蔚藍智能"]),
    tokens: Object.freeze({
      bg: "#f3f6fd", surface: "#ffffff", surface2: "#eef3fc", line: "#dbe4f2",
      ink: "#18284a", muted: "#64718b", accent: "#445fe7", accent2: "#293da8",
      focus: "#9eacf8", chip: "#edf2ff",
      hero: "linear-gradient(120deg,#e5eeff,#f4f7ff 58%,#eaf0ff)",
    }),
  }),
  b: Object.freeze({
    name: "暖米咖啡",
    aliases: Object.freeze(["b", "暖米咖啡", "暖米醇香"]),
    tokens: Object.freeze({
      bg: "#f7f3ec", surface: "#fffdf9", surface2: "#efe8de", line: "#e6dcd0",
      ink: "#332c2a", muted: "#817267", accent: "#805a43", accent2: "#5b3c2c",
      focus: "#b99582", chip: "#f3e9db",
      hero: "linear-gradient(125deg,#efe2d0,#fffaf1 65%,#e5d3be)",
    }),
  }),
  c: Object.freeze({
    name: "墨韻典藏",
    aliases: Object.freeze(["c", "墨韻典藏", "墨藍雅韻"]),
    tokens: Object.freeze({
      bg: "#eeeae3", surface: "#fffcf5", surface2: "#e9e2d4", line: "#d8cebb",
      ink: "#193039", muted: "#72766e", accent: "#174451", accent2: "#0b2b33",
      focus: "#ae966b", chip: "#e5ede7",
      hero: "linear-gradient(122deg,#d5e0d9,#f6f1e7 70%,#e7ddc8)",
    }),
  }),
});

export function normalizeSuite(value) {
  const normalized = String(value ?? "").trim();
  const matches = Object.entries(SUITES).filter(([, suite]) => suite.aliases.includes(normalized));
  if (matches.length !== 1) return { state: "HOLD_UNKNOWN_OR_AMBIGUOUS_SUITE", suiteId: null };
  return { state: "PASS_SUITE_RESOLVED", suiteId: matches[0][0], name: matches[0][1].name };
}

export function resolveSuiteForStore({ companyId, posConfigId, settingKey, settingValue }) {
  if (Number(companyId) !== SUITE_SETTING.companyId || Number(posConfigId) !== SUITE_SETTING.posConfigId) {
    return { state: "HOLD_OUTSIDE_CHONGXIN_HQ_SCOPE", suiteId: null };
  }
  if (settingKey !== SUITE_SETTING.key) {
    return { state: "HOLD_SUITE_SETTING_KEY_MISMATCH", suiteId: null };
  }
  return normalizeSuite(settingValue);
}

export function resolveSurface({ suiteValue, role }) {
  const suite = normalizeSuite(suiteValue);
  if (suite.state !== "PASS_SUITE_RESOLVED") return suite;
  if (!ROLES.includes(role)) return { state: "HOLD_UNKNOWN_CORE_ROLE", suiteId: suite.suiteId };
  return {
    state: "PASS_CORE_SURFACE_RESOLVED",
    id: `${SUITES[suite.suiteId].name}.${role}`,
    suiteId: suite.suiteId,
    suiteName: SUITES[suite.suiteId].name,
    role,
    tokens: SUITES[suite.suiteId].tokens,
  };
}

export function cssVariables(suiteId) {
  const suite = SUITES[suiteId];
  if (!suite) throw new Error("UNKNOWN_SUITE");
  const t = suite.tokens;
  return {
    "--bg": t.bg, "--surface": t.surface, "--surface2": t.surface2,
    "--surface-alt": t.surface2, "--line": t.line, "--ink": t.ink,
    "--muted": t.muted, "--accent": t.accent, "--accent2": t.accent2,
    "--primary": t.accent, "--focus": t.focus, "--chip": t.chip,
    "--selected-bg": t.chip, "--hero": t.hero, "--hero-bg": t.hero,
  };
}
