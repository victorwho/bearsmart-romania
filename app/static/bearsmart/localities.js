const Localities = (() => {
  const { api, badgeClass, setCurrentTown, titleCase } = window.BearSmart;
  let towns = [];
  let sortKey = "score";
  let countyFilter = "all";
  let regionFilter = "all";

  function filteredAndSortedTowns() {
    return [...towns]
      .filter((town) => (countyFilter === "all" ? true : town.county === countyFilter))
      .filter((town) => (regionFilter === "all" ? true : town.region === regionFilter))
      .sort((a, b) => {
        if (sortKey === "region") return a.region.localeCompare(b.region);
        return b.safety_score - a.safety_score;
      });
  }

  function renderCards() {
    const grid = document.getElementById("localitiesGrid");
    const ordered = filteredAndSortedTowns();
    if (!ordered.length) {
      grid.innerHTML = `
        <article class="content-card empty-directory-state">
          <h3 class="section-title">No localities match these filters.</h3>
          <p class="section-copy">Try a broader county or region selection.</p>
        </article>
      `;
      return;
    }

    const cards = ordered.map((town) => `
      <article class="locality-card calm-locality-card">
        <img src="${town.hero_image}" alt="${town.name}">
        <div class="locality-card-body">
          <div class="locality-card-head">
            <div class="locality-card-copy">
              <span class="${badgeClass(town.certification_tier)}">${titleCase(town.certification_tier)} certified</span>
              <h3 class="section-title locality-card-title">${town.name}</h3>
              <p class="section-copy">${town.county} · ${town.region}</p>
              <p class="section-copy">${town.tagline}</p>
            </div>
            <div class="locality-score-pill">
              <span class="eyebrow">BearSmart Score</span>
              <strong>${town.safety_score}</strong>
            </div>
          </div>
          <ul class="measure-list">
            ${town.highlights.slice(0, 2).map((item) => `<li><span class="accent-bar"></span><span>${item}</span></li>`).join("")}
          </ul>
          <div class="locality-meta-row">
            <span class="status-chip">${town.activity_level} activity</span>
          </div>
          <div class="action-grid single-action">
            <a class="button button-secondary" data-map-town="${town.slug}" href="/bearsmart/map?town=${town.slug}">View Map</a>
          </div>
        </div>
      </article>
    `);

    const ctaCard = `
      <article class="cta-card">
        <div>
          <p class="eyebrow" style="color:rgba(255,255,255,0.78);">Grow the network</p>
          <h3 class="section-title" style="color:#fff;">Nominate your locality</h3>
          <p class="section-copy" style="color:rgba(255,255,255,0.78);">Help your town begin its BearSmart certification journey with resident reporting, attractant control, and coordinated education.</p>
        </div>
        <a class="button button-secondary" href="/bearsmart/map">Nominate locality</a>
      </article>
    `;

    grid.innerHTML = [...cards, ctaCard].join("");
    document.querySelectorAll("[data-map-town]").forEach((link) => {
      link.addEventListener("click", () => setCurrentTown(link.dataset.mapTown));
    });
  }

  function renderImpact(impact) {
    document.getElementById("impactNote").textContent = impact.note;
    document.getElementById("impactCommunityCount").textContent = impact.community_count;
    document.getElementById("impactAcres").textContent = impact.acres_protected;
    document.getElementById("trendLabel").textContent = impact.trend_label;
    const latest = impact.trend_values[impact.trend_values.length - 1];
    const previous = impact.trend_values[impact.trend_values.length - 2];
    const change = latest - previous;
    const direction = change <= 0 ? "Down" : "Up";
    document.getElementById("impactTrend").textContent = `${direction} ${Math.abs(change)} vs last year`;
  }

  function populateFilters() {
    const countySelect = document.getElementById("countyFilter");
    const regionSelect = document.getElementById("regionFilter");
    const counties = [...new Set(towns.map((town) => town.county))].sort();
    const regions = [...new Set(towns.map((town) => town.region))].sort();

    countySelect.innerHTML = [`<option value="all">All counties</option>`, ...counties.map((value) => `<option value="${value}">${value}</option>`)].join("");
    regionSelect.innerHTML = [`<option value="all">All regions</option>`, ...regions.map((value) => `<option value="${value}">${value}</option>`)].join("");
    countySelect.value = countyFilter;
    regionSelect.value = regionFilter;
  }

  function bindSort() {
    document.querySelectorAll("[data-sort]").forEach((button) => {
      button.addEventListener("click", () => {
        sortKey = button.dataset.sort;
        document.querySelectorAll("[data-sort]").forEach((item) => item.classList.toggle("active", item === button));
        renderCards();
      });
    });
  }

  function bindFilters() {
    document.getElementById("countyFilter").addEventListener("change", (event) => {
      countyFilter = event.target.value;
      renderCards();
    });

    document.getElementById("regionFilter").addEventListener("change", (event) => {
      regionFilter = event.target.value;
      renderCards();
    });
  }

  async function init() {
    const [townData, impact] = await Promise.all([api("/api/bearsmart/towns"), api("/api/bearsmart/network-impact")]);
    towns = townData.items;
    populateFilters();
    renderCards();
    renderImpact(impact);
    bindSort();
    bindFilters();
  }

  return { init };
})();

Localities.init().catch((error) => window.BearSmart.showToast(error.message));
