const MapPage = (() => {
  const { api, getCurrentTown, setCurrentTown, setReportPoint, showToast, titleCase } = window.BearSmart;
  const reportFilterLabels = {
    all: "All reports",
    sighting: "Sightings",
    road_crossing: "Road crossings",
    attractant_issue: "Attractants",
  };

  const state = {
    townSlug: getCurrentTown(),
    map: null,
    overview: null,
    townData: null,
    zoneLayers: [],
    markerLayers: [],
    userLocation: null,
    userMarker: null,
    locationRequestInFlight: null,
    reportFilter: "all",
    legendExpanded: window.innerWidth > 860,
    statusTimer: null,
  };

  function formatReportTime(value) {
    try {
      return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(value));
    } catch (_error) {
      return "Recent report";
    }
  }

  function verificationLabel(value) {
    if (value === "officially_verified") return "Officially verified";
    if (value === "community_confirmed") return "Community confirmed";
    return "Unverified";
  }

  function reportTypeLabel(value) {
    if (value === "road_crossing") return "Road crossing";
    if (value === "attractant_issue") return "Attractant issue";
    if (value === "livestock_incident") return "Livestock incident";
    if (value === "apiary_incident") return "Apiary incident";
    return titleCase(value);
  }

  function popupMarkup(report) {
    const details = [];
    if (report.details?.number_of_bears) details.push(`${report.details.number_of_bears} bear(s)`);
    if (report.details?.behavior_observed) details.push(report.details.behavior_observed);
    if (report.details?.road_context) details.push(report.details.road_context);
    if (report.details?.attractant_type) details.push(report.details.attractant_type);

    return `
      <div class="map-popup">
        <p class="section-kicker">${reportTypeLabel(report.type)}</p>
        <strong>${report.location_label}</strong>
        <p class="section-copy">${report.description}</p>
        <p class="popup-meta">${formatReportTime(report.created_at)} · ${verificationLabel(report.verification_status)}</p>
        ${details.length ? `<p class="popup-meta">${details[0]}</p>` : ""}
      </div>
    `;
  }

  function clearLayers() {
    state.zoneLayers.forEach((layer) => state.map.removeLayer(layer));
    state.markerLayers.forEach((layer) => state.map.removeLayer(layer));
    state.zoneLayers = [];
    state.markerLayers = [];
  }

  function focusTown() {
    const town = state.overview?.towns.find((item) => item.slug === state.townSlug);
    if (town && state.map) state.map.fitBounds(town.polygon, { padding: [24, 24] });
  }

  function renderUserMarker() {
    if (!state.map || !state.userLocation) return;
    if (state.userMarker) state.map.removeLayer(state.userMarker);
    state.userMarker = L.circleMarker([state.userLocation.lat, state.userLocation.lng], {
      radius: 9,
      color: "#17341d",
      weight: 3,
      fillColor: "#c8ecc9",
      fillOpacity: 1,
    }).bindPopup("Your location").addTo(state.map);
  }

  function setLocationStatus(message, persist = false) {
    const chip = document.getElementById("mapStatusChip");
    chip.textContent = message;
    chip.classList.remove("hidden");
    if (state.statusTimer) window.clearTimeout(state.statusTimer);
    if (!persist) {
      state.statusTimer = window.setTimeout(() => chip.classList.add("hidden"), 2200);
    }
  }

  async function resolveUserLocation() {
    if (state.userLocation) return state.userLocation;
    if (state.locationRequestInFlight) return state.locationRequestInFlight;
    if (!navigator.geolocation) throw new Error("Geolocation is not available in this browser.");
    state.locationRequestInFlight = new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const location = { lat: position.coords.latitude, lng: position.coords.longitude };
          state.userLocation = location;
          state.locationRequestInFlight = null;
          resolve(location);
        },
        () => {
          state.locationRequestInFlight = null;
          reject(new Error("Location permission was denied or unavailable."));
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    });
    return state.locationRequestInFlight;
  }

  async function centerOnUserLocation({ notifyOnFailure = false, automatic = false } = {}) {
    try {
      setLocationStatus("Locating you…", true);
      const location = await resolveUserLocation();
      state.map.setView([location.lat, location.lng], 12);
      renderUserMarker();
      setLocationStatus("Centered on your location");
      return true;
    } catch (error) {
      setLocationStatus(
        automatic ? "Location unavailable. Showing selected locality." : "Location denied. Showing selected locality."
      );
      if (notifyOnFailure) showToast(error.message);
      return false;
    }
  }

  function goToReport(point, townSlug = state.townSlug) {
    setReportPoint({ ...point, town_slug: townSlug });
    setCurrentTown(townSlug);
    window.location.href = `/bearsmart/report?town=${townSlug}`;
  }

  function filteredReports() {
    return state.overview.reports.filter((report) => {
      if (state.reportFilter === "all") return true;
      return report.type === state.reportFilter;
    });
  }

  function addIndividualMarker(report) {
    const marker = L.circleMarker([report.lat, report.lng], {
      radius: report.town_slug === state.townSlug ? 7 : 5,
      color: "#ffffff",
      weight: 2,
      fillColor: "#805533",
      fillOpacity: 1,
    })
      .bindPopup(popupMarkup(report))
      .on("click", () => {
        if (report.town_slug !== state.townSlug) {
          state.townSlug = report.town_slug;
          setCurrentTown(report.town_slug);
          document.getElementById("mapTownSelect").value = report.town_slug;
          refresh({ preferUserLocation: false });
        }
      })
      .addTo(state.map);
    state.markerLayers.push(marker);
  }

  function clusterReports(reports) {
    const zoom = state.map.getZoom();
    if (zoom > 10) {
      reports.forEach(addIndividualMarker);
      return;
    }

    const buckets = new Map();
    reports.forEach((report) => {
      const projected = state.map.project([report.lat, report.lng], zoom);
      const key = `${Math.floor(projected.x / 60)}:${Math.floor(projected.y / 60)}`;
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(report);
    });

    [...buckets.values()].forEach((bucket) => {
      if (bucket.length === 1) {
        addIndividualMarker(bucket[0]);
        return;
      }

      const average = bucket.reduce(
        (acc, report) => ({ lat: acc.lat + report.lat, lng: acc.lng + report.lng }),
        { lat: 0, lng: 0 }
      );
      const lat = average.lat / bucket.length;
      const lng = average.lng / bucket.length;
      const cluster = L.marker([lat, lng], {
        icon: L.divIcon({
          className: "cluster-marker",
          html: `<span>${bucket.length}</span>`,
          iconSize: [42, 42],
        }),
      })
        .bindPopup(`<strong>${bucket.length} nearby reports</strong><br>Zoom in for individual details.`)
        .on("click", () => {
          const bounds = L.latLngBounds(bucket.map((report) => [report.lat, report.lng]));
          state.map.fitBounds(bounds, { padding: [36, 36], maxZoom: 13 });
        })
        .addTo(state.map);
      state.markerLayers.push(cluster);
    });
  }

  function renderMap() {
    clearLayers();
    state.overview.towns.forEach((town) => {
      const polygon = L.polygon(town.polygon, {
        color: town.zone_color,
        weight: town.slug === state.townSlug ? 3 : 2,
        fillColor: town.zone_color,
        fillOpacity: town.slug === state.townSlug ? 0.26 : 0.16,
      })
        .bindPopup(`<strong>${town.name}</strong><br>${titleCase(town.certification_status)} zone`)
        .on("click", (event) => goToReport({ lat: event.latlng.lat, lng: event.latlng.lng }, town.slug))
        .addTo(state.map);
      state.zoneLayers.push(polygon);
    });

    clusterReports(filteredReports());
  }

  function populateTownSelector() {
    const select = document.getElementById("mapTownSelect");
    select.innerHTML = state.overview.towns
      .map((town) => `<option value="${town.slug}">${town.name}</option>`)
      .join("");
    select.value = state.townSlug;
  }

  function renderLegendState() {
    document.getElementById("legendCard").classList.toggle("collapsed", !state.legendExpanded);
  }

  function renderContext() {
    const { town, alerts } = state.townData;
    document.getElementById("mapTownChip").textContent = `${town.name} · ${titleCase(town.certification_status)}`;
    document.getElementById("alertTicker").textContent = alerts[0]?.title || `Live context for ${town.name}`;
  }

  function renderFilterState() {
    document.querySelectorAll("[data-report-filter]").forEach((button) => {
      button.classList.toggle("active", button.dataset.reportFilter === state.reportFilter);
    });
  }

  async function refresh({ preferUserLocation = true } = {}) {
    const [overview, townData] = await Promise.all([api("/api/bearsmart/map"), api(`/api/bearsmart/towns/${state.townSlug}`)]);
    state.overview = overview;
    state.townData = townData;
    populateTownSelector();
    renderMap();
    renderContext();
    renderFilterState();
    if (preferUserLocation) {
      const centeredOnUser = await centerOnUserLocation({ automatic: true });
      if (!centeredOnUser) focusTown();
      return;
    }
    focusTown();
  }

  function bindControls() {
    document.getElementById("centerLocationButton").addEventListener("click", () => {
      centerOnUserLocation({ notifyOnFailure: true }).catch(() => null);
    });

    document.getElementById("mapTownSelect").addEventListener("change", async (event) => {
      state.townSlug = event.target.value;
      setCurrentTown(state.townSlug);
      await refresh({ preferUserLocation: false });
    });

    document.getElementById("mapFilterToggle").addEventListener("click", () => {
      document.getElementById("mapFilterDrawer").classList.toggle("hidden");
    });

    document.querySelectorAll("[data-report-filter]").forEach((button) => {
      button.addEventListener("click", () => {
        state.reportFilter = button.dataset.reportFilter;
        renderFilterState();
        renderMap();
        document.getElementById("mapFilterDrawer").classList.add("hidden");
      });
    });

    document.getElementById("legendToggleButton").addEventListener("click", () => {
      state.legendExpanded = !state.legendExpanded;
      renderLegendState();
    });
  }

  async function init() {
    state.map = L.map("map", { zoomControl: true }).setView([45.67, 25.55], 8);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "&copy; OpenStreetMap contributors" }).addTo(state.map);
    state.map.on("click", (event) => goToReport({ lat: event.latlng.lat, lng: event.latlng.lng }));
    state.map.on("zoomend", () => renderMap());
    bindControls();
    renderLegendState();
    await refresh();
  }

  return { init };
})();

MapPage.init().catch((error) => window.BearSmart.showToast(error.message));
