window.__FLAGS = window.__FLAGS || {};

window.BearSmart = (() => {
  const storage = window.localStorage;

  function titleCase(value) {
    return String(value || "")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function api(path, options = {}) {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    return fetch(path, { credentials: "same-origin", ...options, headers }).then(async (response) => {
      if (!response.ok) {
        let detail = response.statusText || "Request failed.";
        try {
          const data = await response.json();
          detail = data.detail || detail;
        } catch (_error) {}
        throw new Error(detail);
      }
      return response.json();
    });
  }

  function loadFlags() {
    return fetch("/api/flags", { credentials: "same-origin" })
      .then((response) => (response.ok ? response.json() : {}))
      .then((flags) => {
        window.__FLAGS = flags || {};
        return window.__FLAGS;
      })
      .catch(() => window.__FLAGS);
  }

  function flagEnabled(name) {
    return Boolean(window.__FLAGS && window.__FLAGS[name]);
  }

  function track(name, props = {}) {
    try {
      const body = JSON.stringify({ name, props });
      if (navigator.sendBeacon) {
        navigator.sendBeacon(
          "/api/telemetry",
          new Blob([body], { type: "application/json" })
        );
        return;
      }
      fetch("/api/telemetry", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body,
      }).catch(() => {});
    } catch (_error) {
      /* telemetry must never throw */
    }
  }

  function getQuery(name) {
    return new URLSearchParams(window.location.search).get(name);
  }

  function setCurrentTown(slug) {
    storage.setItem("bearsmart-town", slug);
  }

  function getCurrentTown(fallback = "rasnov") {
    return getQuery("town") || storage.getItem("bearsmart-town") || fallback;
  }

  function setReportPoint(point) {
    storage.setItem("bearsmart-report-point", JSON.stringify(point));
  }

  function getReportPoint() {
    try {
      return JSON.parse(storage.getItem("bearsmart-report-point") || "null");
    } catch (_error) {
      return null;
    }
  }

  function clearReportPoint() {
    storage.removeItem("bearsmart-report-point");
  }

  function setReportDraft(draft) {
    storage.setItem("bearsmart-report-draft", JSON.stringify(draft));
  }

  function getReportDraft() {
    try {
      return JSON.parse(storage.getItem("bearsmart-report-draft") || "null");
    } catch (_error) {
      return null;
    }
  }

  function clearReportDraft() {
    storage.removeItem("bearsmart-report-draft");
  }

  function showToast(message) {
    let toast = document.getElementById("toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "toast";
      toast.className = "toast hidden";
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.remove("hidden");
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => toast.classList.add("hidden"), 2600);
  }

  function badgeClass(tier) {
    if (tier === "gold") return "badge badge-gold";
    if (tier === "silver") return "badge badge-silver";
    if (tier === "candidate") return "badge badge-candidate";
    return "badge badge-certified";
  }

  // Fire-and-forget: ensures every page has flags ready shortly after load.
  loadFlags();

  return {
    api,
    badgeClass,
    clearReportDraft,
    clearReportPoint,
    flagEnabled,
    getCurrentTown,
    getQuery,
    getReportDraft,
    getReportPoint,
    loadFlags,
    setCurrentTown,
    setReportDraft,
    setReportPoint,
    showToast,
    titleCase,
    track,
  };
})();
