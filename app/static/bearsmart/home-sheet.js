(() => {
  const { api, getCurrentTown, titleCase, track } = window.BearSmart;

  const VALID_TABS = ["now", "plan", "report"];

  function currentHashTab() {
    const raw = (window.location.hash || "").replace("#", "").toLowerCase();
    return VALID_TABS.includes(raw) ? raw : "now";
  }

  function activateTab(name) {
    const target = VALID_TABS.includes(name) ? name : "now";
    const sheet = document.getElementById("homeSheet");
    if (!sheet) return;
    sheet.dataset.activeTab = target;
    document.querySelectorAll(".home-sheet-tab").forEach((btn) => {
      const isActive = btn.dataset.tab === target;
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-selected", isActive ? "true" : "false");
    });
    document.querySelectorAll(".home-sheet-panel").forEach((panel) => {
      const isActive = panel.id === `tab${titleCase(target).replace(/\s/g, "")}`;
      panel.classList.toggle("active", isActive);
      panel.hidden = !isActive;
    });
    if (target !== "now") {
      track("town_page_viewed", { tab: target, town: getCurrentTown() });
    }
  }

  function bindTabs() {
    document.querySelectorAll(".home-sheet-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        const next = btn.dataset.tab;
        const hash = btn.dataset.hash || `#${next}`;
        if (window.location.hash !== hash) {
          history.replaceState(null, "", hash);
        }
        activateTab(next);
      });
    });
    window.addEventListener("hashchange", () => activateTab(currentHashTab()));
    const toggle = document.getElementById("homeSheetToggle");
    if (toggle) {
      toggle.addEventListener("click", () => {
        const sheet = document.getElementById("homeSheet");
        const expanded = sheet.classList.toggle("collapsed");
        toggle.setAttribute("aria-expanded", expanded ? "false" : "true");
      });
    }
  }

  function renderNow(townData) {
    const nameEl = document.getElementById("nowTownName");
    if (nameEl) {
      nameEl.textContent = townData.town?.name || "This town";
    }
    const alertList = document.getElementById("nowAlertList");
    if (alertList) {
      const alerts = townData.alerts || [];
      alertList.innerHTML = alerts.length
        ? alerts
            .map(
              (a) => `
              <div class="list-card">
                <span class="eyebrow">${titleCase(a.severity || "info")}</span>
                <strong>${a.title}</strong>
                <div class="section-copy">${a.message}</div>
              </div>`
            )
            .join("")
        : `<div class="list-card"><strong>No active alerts.</strong><div class="section-copy">We'll surface urgent local context here as soon as it's published.</div></div>`;
    }
    const reportList = document.getElementById("nowReportList");
    if (reportList) {
      const reports = (townData.reports || []).slice(0, 5);
      reportList.innerHTML = reports.length
        ? reports
            .map(
              (r) => `
              <div class="list-card">
                <span class="eyebrow">${titleCase(r.type)}</span>
                <strong>${r.location_label || "Location"}</strong>
                <div class="section-copy">${r.description || ""}</div>
              </div>`
            )
            .join("")
        : `<div class="list-card"><strong>No published reports yet.</strong></div>`;
    }
    const contacts = document.getElementById("planContactsList");
    if (contacts) {
      const rows = townData.town?.contacts || [];
      contacts.innerHTML = rows.length
        ? rows
            .map(
              (c) => `<div class="list-card"><strong>${c.label}</strong><div class="section-copy">${c.value}</div></div>`
            )
            .join("")
        : `<div class="list-card"><strong>No contacts configured yet.</strong></div>`;
    }
  }

  async function hydrate() {
    try {
      const town = getCurrentTown();
      const data = await api(`/api/bearsmart/towns/${town}`);
      renderNow(data);
    } catch (_error) {
      /* silent: panel will show placeholders */
    }
  }

  function init() {
    if (!document.getElementById("homeSheet")) return;
    bindTabs();
    activateTab(currentHashTab());
    hydrate();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
