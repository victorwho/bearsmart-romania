const OpsPage = (() => {
  const { api, showToast, titleCase } = window.BearSmart;
  let towns = [];

  function currentTown() {
    return document.getElementById("opsTownSelect").value;
  }

  async function loadTowns() {
    const response = await api("/api/bearsmart/towns");
    towns = response.items;
    document.getElementById("opsTownSelect").innerHTML = towns.map((town) => `<option value="${town.slug}">${town.name}</option>`).join("");
  }

  async function loadAdmin() {
    const response = await api(`/api/bearsmart/admin/towns/${currentTown()}/dashboard`, { headers: { "X-Demo-Role": "town_admin" } });
    document.getElementById("opsMetrics").innerHTML = Object.entries(response.metrics).map(([label, value]) => `
      <div class="stat-card"><span class="eyebrow">${titleCase(label)}</span><strong>${value}</strong></div>
    `).join("");
  }

  const IN_SEASON_SLA_SECONDS = 6 * 3600;

  function formatAge(seconds) {
    if (!Number.isFinite(seconds)) return "Age unknown";
    if (seconds < 60) return "Under a minute";
    if (seconds < 3600) return `${Math.round(seconds / 60)} min in queue`;
    if (seconds < 48 * 3600) return `${(seconds / 3600).toFixed(1)} h in queue`;
    return `${Math.round(seconds / 3600)} h in queue`;
  }

  function slaBadgeClass(seconds) {
    if (!Number.isFinite(seconds)) return "sla-badge";
    if (seconds > IN_SEASON_SLA_SECONDS) return "sla-badge over";
    if (seconds > IN_SEASON_SLA_SECONDS * 0.75) return "sla-badge warn";
    return "sla-badge";
  }

  function renderStats(stats) {
    const el = document.getElementById("opsModerationStats");
    if (!el) return;
    el.innerHTML = `
      <div class="sla-stat"><strong>${stats.queue_size}</strong><span>In queue</span></div>
      <div class="sla-stat"><strong>${formatAge(stats.median_age_seconds)}</strong><span>Median age</span></div>
      <div class="sla-stat"><strong>${formatAge(stats.p90_age_seconds)}</strong><span>P90 age</span></div>
      <div class="sla-stat"><strong>${stats.over_sla_in_season}</strong><span>Over 6h SLA</span></div>
    `;
  }

  async function loadModeration() {
    const [queue, stats] = await Promise.all([
      api("/api/bearsmart/moderation/reports", { headers: { "X-Demo-Role": "moderator" } }),
      api("/api/bearsmart/moderation/stats", { headers: { "X-Demo-Role": "moderator" } }),
    ]);
    renderStats(stats);
    document.getElementById("opsModerationList").innerHTML = queue.items.map((item) => {
      const ageSeconds = Number(item.age_seconds) || 0;
      const badgeClass = slaBadgeClass(ageSeconds);
      const createdIso = item.created_at || "";
      return `
      <div class="surface-card">
        <div class="list-stack">
          <span class="${badgeClass}">${formatAge(ageSeconds)}</span>
          <strong>${titleCase(item.type)}</strong>
          <div class="section-copy">${item.location_label}</div>
          <div class="section-copy">${item.description}</div>
          <div class="field-help">Submitted ${createdIso}</div>
        </div>
        <div class="action-grid two">
          <button class="button button-primary" data-review="${item.id}" data-action="approve" type="button">Approve</button>
          <button class="button button-secondary" data-review="${item.id}" data-action="reject" type="button">Reject</button>
        </div>
      </div>
    `;
    }).join("") || `<div class="surface-card">No items waiting for moderation.</div>`;
    document.querySelectorAll("[data-review]").forEach((button) => {
      button.addEventListener("click", async () => {
        await api(`/api/bearsmart/moderation/reports/${button.dataset.review}/review`, {
          method: "POST",
          headers: { "X-Demo-Role": "moderator" },
          body: JSON.stringify({ action: button.dataset.action, public_note: `Report ${button.dataset.action}d in demo.` }),
        });
        showToast(`Report ${button.dataset.action}d.`);
        loadModeration();
      });
    });
  }

  async function loadCertification() {
    const certification = await api(`/api/bearsmart/reviewer/towns/${currentTown()}/certification`, { headers: { "X-Demo-Role": "reviewer" } });
    document.getElementById("opsCertificationCard").innerHTML = `
      <div class="surface-card">
        <strong>${titleCase(certification.status)}</strong>
        <div class="section-copy">${certification.decision_notes}</div>
      </div>
      ${certification.criteria.map((item) => `
        <div class="surface-card">
          <strong>${item.code}</strong>
          <div class="section-copy">${item.label}</div>
          <div class="eyebrow">${titleCase(item.status)}</div>
        </div>
      `).join("")}
    `;
  }

  async function init() {
    await loadTowns();
    await Promise.all([loadAdmin(), loadModeration(), loadCertification()]);
    document.getElementById("opsTownSelect").addEventListener("change", () => Promise.all([loadAdmin(), loadCertification()]).catch((error) => showToast(error.message)));
    document.getElementById("opsPublishAlert").addEventListener("click", async () => {
      await api(`/api/bearsmart/admin/towns/${currentTown()}/alerts`, {
        method: "POST",
        headers: { "X-Demo-Role": "town_admin" },
        body: JSON.stringify({
          title: document.getElementById("opsAlertTitle").value,
          severity: document.getElementById("opsAlertSeverity").value,
          message: document.getElementById("opsAlertMessage").value,
        }),
      });
      showToast("Alert published.");
      loadAdmin();
    });
    document.getElementById("opsSaveDecision").addEventListener("click", async () => {
      await api(`/api/bearsmart/reviewer/towns/${currentTown()}/certification/decision`, {
        method: "POST",
        headers: { "X-Demo-Role": "reviewer" },
        body: JSON.stringify({
          status: document.getElementById("opsCertDecision").value,
          decision_notes: document.getElementById("opsCertNotes").value || "Decision saved in demo ops console.",
        }),
      });
      showToast("Certification decision saved.");
      loadCertification();
    });
  }

  return { init };
})();

OpsPage.init().catch((error) => window.BearSmart.showToast(error.message));
