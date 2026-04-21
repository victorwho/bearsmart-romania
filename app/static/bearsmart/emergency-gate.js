/* H1.3 — Emergency gate enforced before every report entry.

   References: IMPLEMENTATION_PLAN.md §1.3 and Threat T1.
   Dismissal is sticky for 30 minutes per session via sessionStorage.
*/
(() => {
  const STORAGE_KEY = "bearsmart-emergency-gate-dismissed-at";
  const STICKY_MS = 30 * 60 * 1000;
  const { flagEnabled, track } = window.BearSmart || {};

  function wasDismissedRecently() {
    try {
      const raw = window.sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return false;
      const ts = Number(raw);
      if (!Number.isFinite(ts)) return false;
      return Date.now() - ts < STICKY_MS;
    } catch (_error) {
      return false;
    }
  }

  function markDismissed() {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, String(Date.now()));
    } catch (_error) {
      /* ignore */
    }
  }

  function ensureGateElement() {
    let gate = document.getElementById("emergencyGate");
    if (gate) return gate;
    gate = document.createElement("div");
    gate.id = "emergencyGate";
    gate.className = "emergency-gate";
    gate.setAttribute("role", "dialog");
    gate.setAttribute("aria-modal", "true");
    gate.setAttribute("aria-labelledby", "emergencyGateTitle");
    gate.innerHTML = `
      <div class="emergency-gate-card">
        <p class="eyebrow">Safety first</p>
        <h2 id="emergencyGateTitle">Is anyone hurt or in immediate danger right now?</h2>
        <p class="section-copy">BearSmart is informational — it is not an emergency dispatcher. If someone is injured, cornered by a bear, or a crash just happened, call 112 before filing a report.</p>
        <div class="emergency-gate-actions">
          <a class="emergency-gate-call" href="tel:112" data-emergency="call">Yes — call 112</a>
          <button class="emergency-gate-continue" type="button" data-emergency="continue">No — continue report</button>
        </div>
      </div>
    `;
    document.body.appendChild(gate);
    gate.addEventListener("click", (event) => {
      const action = event.target?.dataset?.emergency;
      if (action === "continue") {
        event.preventDefault();
        dismiss(gate);
      } else if (action === "call") {
        // Let the tel: link work; still record it.
        if (typeof track === "function") track("emergency_gate_dismissed", { choice: "call" });
        markDismissed();
      }
    });
    return gate;
  }

  function dismiss(gate) {
    gate.classList.remove("open");
    markDismissed();
    if (typeof track === "function") track("emergency_gate_dismissed", { choice: "continue" });
    const pending = gate.dataset.pendingNav;
    if (pending) {
      gate.dataset.pendingNav = "";
      window.location.href = pending;
    }
    const callback = gate._resolve;
    if (typeof callback === "function") {
      gate._resolve = null;
      callback(true);
    }
  }

  function shouldRun() {
    // Respect feature flag; default on.
    if (typeof flagEnabled === "function" && window.__FLAGS && "emergency_gate" in window.__FLAGS) {
      return window.__FLAGS.emergency_gate !== false;
    }
    return true;
  }

  function showGate(pendingNav) {
    if (!shouldRun()) {
      if (pendingNav) window.location.href = pendingNav;
      return Promise.resolve(true);
    }
    if (wasDismissedRecently()) {
      if (pendingNav) window.location.href = pendingNav;
      return Promise.resolve(true);
    }
    const gate = ensureGateElement();
    if (pendingNav) gate.dataset.pendingNav = pendingNav;
    gate.classList.add("open");
    if (typeof track === "function") track("emergency_gate_shown", { path: window.location.pathname });
    return new Promise((resolve) => {
      gate._resolve = resolve;
    });
  }

  function interceptLinks() {
    document.addEventListener(
      "click",
      (event) => {
        const link = event.target?.closest?.("a[href]");
        if (!link) return;
        let href = link.getAttribute("href");
        if (!href) return;
        if (!href.startsWith("/bearsmart/report")) return;
        if (link.dataset.bypassEmergencyGate === "true") return;
        // Skip when already on the report page – the on-page gate takes over.
        if (window.location.pathname.startsWith("/bearsmart/report")) return;
        if (!shouldRun()) return;
        if (wasDismissedRecently()) return;
        event.preventDefault();
        showGate(href);
      },
      true
    );
  }

  function bootReportPage() {
    if (!window.location.pathname.startsWith("/bearsmart/report")) return;
    if (!shouldRun()) return;
    if (wasDismissedRecently()) return;
    showGate(null);
  }

  function init() {
    interceptLinks();
    bootReportPage();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.BearSmartEmergencyGate = { showGate, wasDismissedRecently };
})();
