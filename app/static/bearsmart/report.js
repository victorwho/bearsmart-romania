const ReportPage = (() => {
  const {
    api,
    clearReportDraft,
    clearReportPoint,
    getCurrentTown,
    getReportDraft,
    getReportPoint,
    setCurrentTown,
    setReportDraft,
    setReportPoint,
    showToast,
    titleCase,
  } = window.BearSmart;

  const reportTypes = [
    { value: "sighting", label: "Bear Sighting", icon: "pets" },
    { value: "attractant_issue", label: "Attractant Issue", icon: "delete" },
    { value: "road_crossing", label: "Road Crossing", icon: "traffic" },
    { value: "livestock_incident", label: "Livestock Incident", icon: "agriculture" },
    { value: "apiary_incident", label: "Apiary Incident", icon: "hive" },
  ];

  const FUZZ_RADIUS_M = {
    sighting: 500,
    attractant_issue: 500,
    road_crossing: 300,
  };
  const STRIP_COORDINATE_TYPES = new Set(["livestock_incident", "apiary_incident"]);

  const state = {
    step: 1,
    townSlug: getCurrentTown(),
    town: null,
    map: null,
    marker: null,
    fuzzCircle: null,
    submittedReport: null,
    lookupAbortController: null,
    draft: {
      type: "sighting",
      latitude: null,
      longitude: null,
      location_label: "",
      location_autofilled: false,
      description: "",
      reporter_name: "",
      number_of_bears: "",
      behavior_observed: "",
      attractant_type: "",
      road_context: "",
      photo_name: "",
    },
  };

  function renderStep() {
    [1, 2, 3, 4].forEach((step) => {
      document.getElementById(`step${step}`).classList.toggle("hidden", state.step !== step);
      document.querySelector(`[data-step-bar="${step}"]`).classList.toggle("active", step <= state.step);
    });
    document.getElementById("stepLabel").textContent = `Step ${state.step} of 4`;
    document.getElementById("backStepButton").classList.toggle("hidden", state.step === 1 || !!state.submittedReport);
    document.getElementById("nextStepButton").textContent = state.step === 4 ? "Submit report" : "Next Step";
    document.getElementById("reportNav").classList.toggle("hidden", !!state.submittedReport);
    document.getElementById("confirmationState").classList.toggle("hidden", !state.submittedReport);
    if (state.step === 4) renderReview();
    renderDynamicFields();
  }

  function renderTypeGrid() {
    document.getElementById("reportTypeGrid").innerHTML = reportTypes.map((item) => `
      <button class="button report-type-card ${state.draft.type === item.value ? "active" : ""}" data-type="${item.value}" type="button">
        <span class="material-symbols-outlined report-type-icon" aria-hidden="true">${item.icon}</span>
        <span class="report-type-copy">
          <strong>${item.label}</strong>
        </span>
      </button>
    `).join("");
    document.querySelectorAll("[data-type]").forEach((button) => {
      button.addEventListener("click", () => {
        state.draft.type = button.dataset.type;
        persistDraft();
        renderTypeGrid();
        renderDynamicFields();
        if (state.draft.latitude && state.draft.longitude) {
          renderFuzzPreview(state.draft.latitude, state.draft.longitude);
        }
      });
    });
  }

  function renderDynamicFields() {
    document.getElementById("fieldNumberOfBears").classList.toggle("hidden", state.draft.type !== "sighting");
    document.getElementById("fieldBehaviorObserved").classList.toggle("hidden", !["sighting", "livestock_incident", "apiary_incident"].includes(state.draft.type));
    document.getElementById("fieldAttractantType").classList.toggle("hidden", state.draft.type !== "attractant_issue");
    document.getElementById("fieldRoadContext").classList.toggle("hidden", state.draft.type !== "road_crossing");
  }

  function renderSelectedCoordinates() {
    const label = state.draft.latitude && state.draft.longitude
      ? `${state.draft.latitude.toFixed(5)}, ${state.draft.longitude.toFixed(5)}`
      : "No point selected yet.";
    document.getElementById("selectedCoordinates").textContent = label;
    document.getElementById("selectedPointSummary").innerHTML = state.draft.latitude && state.draft.longitude
      ? `<strong>Selected point</strong><div class="section-copy">${label}</div><div class="field-help">${state.draft.location_label || "We’ll suggest a nearby place label automatically."}</div>`
      : "Point summary will appear here after you place a marker.";
  }

  function setLookupStatus(message) {
    document.getElementById("locationLookupStatus").textContent = message;
  }

  async function autoFillLocationLabel(lat, lng) {
    if (state.lookupAbortController) state.lookupAbortController.abort();
    state.lookupAbortController = new AbortController();
    setLookupStatus("Looking up a nearby place label…");

    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&zoom=17`,
        { signal: state.lookupAbortController.signal }
      );
      if (!response.ok) throw new Error("Lookup failed");
      const data = await response.json();
      const address = data.address || {};
      const suggestedLabel = [
        address.road,
        address.suburb || address.neighbourhood || address.village,
        address.city || address.town || address.municipality || state.town.name,
      ].filter(Boolean).slice(0, 2).join(", ");

      if (!suggestedLabel) {
        setLookupStatus("Couldn’t auto-fill a label. Add one manually.");
        renderSelectedCoordinates();
        return;
      }

      if (!state.draft.location_label || state.draft.location_autofilled) {
        state.draft.location_label = suggestedLabel;
        state.draft.location_autofilled = true;
        document.getElementById("reportLocation").value = suggestedLabel;
        persistDraft();
      }
      setLookupStatus("Place label suggested from the selected map point.");
      renderSelectedCoordinates();
    } catch (_error) {
      setLookupStatus("Couldn’t auto-fill a label. Add one manually.");
    }
  }

  function renderFuzzPreview(lat, lng) {
    const type = state.draft.type;
    const note = document.getElementById("fuzzPreviewNote");
    if (state.fuzzCircle) {
      state.map.removeLayer(state.fuzzCircle);
      state.fuzzCircle = null;
    }
    if (!note) return;
    if (STRIP_COORDINATE_TYPES.has(type)) {
      note.textContent = "Privacy: livestock and apiary locations are never published — only town-level aggregates appear on the public map.";
      return;
    }
    const radius = FUZZ_RADIUS_M[type] || 500;
    state.fuzzCircle = L.circle([lat, lng], {
      radius,
      className: "leaflet-bearsmart-fuzz",
      color: "#17341d",
      weight: 2,
      opacity: 0.6,
      fillColor: "#c8ecc9",
      fillOpacity: 0.3,
    }).addTo(state.map);
    note.textContent = `Your pin is published to the public as a ~${Math.round(radius)} m area so private homes are not identifiable.`;
  }

  function updateMarker(lat, lng) {
    state.draft.latitude = lat;
    state.draft.longitude = lng;
    setReportPoint({ lat, lng, town_slug: state.townSlug });
    persistDraft();
    renderSelectedCoordinates();
    if (state.marker) state.map.removeLayer(state.marker);
    state.marker = L.marker([lat, lng]).addTo(state.map);
    renderFuzzPreview(lat, lng);
    autoFillLocationLabel(lat, lng).catch(() => null);
  }

  function renderReview() {
    document.getElementById("reviewSummary").innerHTML = `
      <div class="list-card"><strong>Town</strong><div class="section-copy">${state.town.name}</div></div>
      <div class="list-card"><strong>Coordinates</strong><div class="section-copy">${state.draft.latitude?.toFixed(5) || "-"}, ${state.draft.longitude?.toFixed(5) || "-"}</div></div>
      <div class="list-card"><strong>Type</strong><div class="section-copy">${titleCase(state.draft.type)}</div></div>
      <div class="list-card"><strong>Location label</strong><div class="section-copy">${state.draft.location_label || "-"}</div></div>
      <div class="list-card"><strong>Description</strong><div class="section-copy">${state.draft.description || "-"}</div></div>
      <div class="list-card"><strong>Reporter</strong><div class="section-copy">${state.draft.reporter_name || "Anonymous community member"}</div></div>
    `;
  }

  function persistDraft() {
    setReportDraft({ ...state.draft, town_slug: state.townSlug });
  }

  function bindField(id, key) {
    const element = document.getElementById(id);
    element.value = state.draft[key] || "";
    element.addEventListener("input", () => {
      state.draft[key] = element.value;
      if (key === "location_label") {
        state.draft.location_autofilled = false;
        renderSelectedCoordinates();
      }
      persistDraft();
    });
  }

  function validateCurrentStep() {
    if (state.step === 1 && (!state.draft.latitude || !state.draft.longitude)) {
      showToast("Select a point on the map first.");
      return false;
    }
    if (state.step === 3 && (!state.draft.location_label || !state.draft.description)) {
      showToast("Add a location label and description.");
      return false;
    }
    return true;
  }

  async function submitReport() {
    const response = await api("/api/bearsmart/reports", {
      method: "POST",
      body: JSON.stringify({
        town_slug: state.townSlug,
        type: state.draft.type,
        location_label: state.draft.location_label,
        description: state.draft.description,
        reporter_name: state.draft.reporter_name || null,
        latitude: state.draft.latitude,
        longitude: state.draft.longitude,
        number_of_bears: state.draft.number_of_bears ? Number(state.draft.number_of_bears) : null,
        behavior_observed: state.draft.behavior_observed || null,
        attractant_type: state.draft.attractant_type || null,
        road_context: state.draft.road_context || null,
        photo_name: state.draft.photo_name || null,
      }),
    });
    state.submittedReport = response.report;
    if (window.BearSmart && typeof window.BearSmart.track === "function") {
      window.BearSmart.track("report_submitted", {
        town: state.townSlug,
        type: state.draft.type,
      });
    }
    clearReportDraft();
    clearReportPoint();
    document.getElementById("confirmationCopy").textContent =
      `${titleCase(response.report.type)} at ${response.report.location_label} was submitted for moderation. It will stay private until reviewed.`;
    renderStep();
  }

  async function initMap() {
    state.map = L.map("reportMap", { zoomControl: true }).setView([state.town.center.lat, state.town.center.lng], 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "&copy; OpenStreetMap contributors" }).addTo(state.map);
    L.polygon(
      [
        [state.town.bounds.lat_min, state.town.bounds.lng_min],
        [state.town.bounds.lat_min, state.town.bounds.lng_max],
        [state.town.bounds.lat_max, state.town.bounds.lng_max],
        [state.town.bounds.lat_max, state.town.bounds.lng_min],
      ],
      { color: state.town.certification_status === "certified" ? "#2e8b57" : "#c58b2a", weight: 2, fillOpacity: 0.18 }
    ).addTo(state.map);
    state.map.on("click", (event) => updateMarker(event.latlng.lat, event.latlng.lng));
    if (state.draft.latitude && state.draft.longitude) {
      updateMarker(state.draft.latitude, state.draft.longitude);
    }
  }

  async function init() {
    const townData = await api(`/api/bearsmart/towns/${state.townSlug}`);
    state.town = townData.town;
    setCurrentTown(state.townSlug);
    const savedPoint = getReportPoint();
    const savedDraft = getReportDraft();
    if (savedDraft && savedDraft.town_slug === state.townSlug) state.draft = { ...state.draft, ...savedDraft };
    if (savedPoint && savedPoint.town_slug === state.townSlug) {
      state.draft.latitude = savedPoint.lat;
      state.draft.longitude = savedPoint.lng;
    }
    renderTypeGrid();
    renderSelectedCoordinates();
    bindField("reportLocation", "location_label");
    bindField("reportDescription", "description");
    bindField("reportName", "reporter_name");
    bindField("numberOfBears", "number_of_bears");
    bindField("behaviorObserved", "behavior_observed");
    bindField("attractantType", "attractant_type");
    bindField("roadContext", "road_context");
    document.getElementById("photoMeta").textContent = state.draft.photo_name || "No photo selected.";
    document.getElementById("reportPhoto").addEventListener("change", (event) => {
      state.draft.photo_name = event.target.files?.[0]?.name || "";
      document.getElementById("photoMeta").textContent = state.draft.photo_name || "No photo selected.";
      persistDraft();
    });
    document.getElementById("useTownCenterButton").addEventListener("click", () => updateMarker(state.town.center.lat, state.town.center.lng));
    document.getElementById("useCurrentLocationButton").addEventListener("click", () => {
      const button = document.getElementById("useCurrentLocationButton");
      if (!navigator.geolocation) {
        showToast("Geolocation is not available in this browser.");
        return;
      }
      button.textContent = "Locating…";
      navigator.geolocation.getCurrentPosition(
        (position) => {
          button.textContent = "Use My Current Location";
          state.map.setView([position.coords.latitude, position.coords.longitude], 14);
          updateMarker(position.coords.latitude, position.coords.longitude);
        },
        () => {
          button.textContent = "Use My Current Location";
          showToast("Location permission was denied or unavailable.");
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    });
    document.getElementById("backStepButton").addEventListener("click", () => {
      state.step = Math.max(1, state.step - 1);
      renderStep();
    });
    document.getElementById("nextStepButton").addEventListener("click", async () => {
      if (!validateCurrentStep()) return;
      if (state.step < 4) {
        state.step += 1;
        renderStep();
        return;
      }
      await submitReport();
    });
    await initMap();
    renderStep();
  }

  return { init };
})();

ReportPage.init().catch((error) => window.BearSmart.showToast(error.message));
