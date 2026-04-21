const DashboardPage = (() => {
  const { api, getCurrentTown, setCurrentTown, showToast, titleCase } = window.BearSmart;
  const state = { townSlug: getCurrentTown(), plan: null };

  const profileMeta = {
    resident: {
      title: "Resident",
      short: "For homes, shared streets, and everyday routines.",
      body: "Practical everyday actions for homes, shared streets, and neighborhood routines.",
      audience: "people living near bear activity year-round",
      icon: "home",
    },
    tourist: {
      title: "Tourist",
      short: "For lodging stays, day trips, and trailheads.",
      body: "Quick guidance for lodging, day trips, and hiking near town edges.",
      audience: "visitors staying briefly in bear country",
      icon: "hiking",
    },
    business_owner: {
      title: "Business Owner",
      short: "For guesthouses, restaurants, and visitor spaces.",
      body: "Operational guidance for hospitality, food service, and visitor-facing spaces.",
      audience: "businesses handling guest food or waste",
      icon: "storefront",
    },
    school: {
      title: "School",
      short: "For staff routines, families, and student safety.",
      body: "Simple safety guidance for staff, families, and school routines.",
      audience: "teachers, staff, and school families",
      icon: "school",
    },
    beekeeper: {
      title: "Beekeeper",
      short: "For apiaries, fencing, and hive checks.",
      body: "Focused actions for apiaries, fencing, and repeated movement near hives.",
      audience: "people managing hives or honey storage",
      icon: "pest_control",
    },
    farmer: {
      title: "Farmer",
      short: "For feed areas, farmyards, and perimeter routines.",
      body: "Checklist guidance for feed areas, farmyards, and perimeter routines.",
      audience: "people working around livestock, feed, or barns",
      icon: "agriculture",
    },
  };

  const categoryThemes = {
    Home: "At Home",
    Property: "At Home",
    Community: "Shared Spaces",
    Planning: "Before You Go",
    Lodging: "Before You Go",
    Outdoors: "Outdoors",
    Operations: "Operations",
    Staff: "Operations",
    Documentation: "Operations",
    Campus: "School Grounds",
    Families: "School Grounds",
    Apiary: "Working Land",
    Monitoring: "Working Land",
    Coordination: "Working Land",
    Farmyard: "Working Land",
    Perimeter: "Working Land",
    Reporting: "Working Land",
  };

  function renderProfileCards(selectedPersona) {
    document.getElementById("profileCardGrid").innerHTML = Object.entries(profileMeta).map(([key, profile]) => `
      <button class="profile-card ${key === selectedPersona ? "active" : ""}" type="button" data-persona="${key}">
        <div class="profile-card-top">
          <span class="material-symbols-outlined profile-card-icon" aria-hidden="true">${profile.icon}</span>
          <p class="eyebrow">Profile</p>
        </div>
        <strong>${profile.title}</strong>
        <p class="section-copy">${profile.short}</p>
        <p class="profile-card-audience">Best for ${profile.audience}.</p>
      </button>
    `).join("");

    document.querySelectorAll("[data-persona]").forEach((button) => {
      button.addEventListener("click", () => {
        const persona = button.dataset.persona;
        createPlan(persona, { scrollToRecommendations: true }).catch((error) => showToast(error.message));
      });
    });
  }

  function themeForCategory(category) {
    return categoryThemes[category] || "Essential Steps";
  }

  function generalizeTaskDetails(details) {
    return String(details || "").replace(/\s+In\s+[A-ZĂÂÎȘȚ][^.]+before marking it complete\.\s*$/u, "").trim();
  }

  function renderTask(task, open = false) {
    return `
      <details class="recommendation-card ${task.state === "completed" ? "completed" : ""}" ${open ? "open" : ""}>
        <summary class="recommendation-summary">
          <div class="recommendation-copy">
            <div class="recommendation-meta">
              <span class="eyebrow">${task.category}</span>
              <span class="recommendation-state">${titleCase(task.state)}</span>
            </div>
            <strong>${task.title}</strong>
            <p class="section-copy">${task.summary}</p>
          </div>
        </summary>
        <div class="recommendation-detail">
          <p class="section-copy">${generalizeTaskDetails(task.details)}</p>
          <div class="action-grid two">
            <button class="button button-primary" type="button" data-task-id="${task.id}" data-state="${task.state}">
              ${task.state === "completed" ? "Mark as in progress" : "Mark complete"}
            </button>
            <button class="button button-secondary" type="button" data-expand-close="${task.id}">
              Close details
            </button>
          </div>
        </div>
      </details>
    `;
  }

  function renderChecklist(plan) {
    state.plan = plan;
    document.getElementById("completionLabel").textContent = `${plan.completion_percent}%`;
    document.getElementById("recommendationHeading").textContent = `${titleCase(plan.persona_type.replace("_", " "))} checklist`;

    const grouped = plan.tasks.reduce((accumulator, task) => {
      const theme = themeForCategory(task.category);
      if (!accumulator[theme]) accumulator[theme] = [];
      accumulator[theme].push(task);
      return accumulator;
    }, {});

    let firstTask = true;
    document.getElementById("checklistList").innerHTML = Object.entries(grouped).map(([theme, tasks]) => `
      <section class="recommendation-group">
        <div class="recommendation-group-head">
          <p class="section-kicker">${theme}</p>
        </div>
        <div class="recommendation-group-list">
          ${tasks.map((task) => {
            const markup = renderTask(task, firstTask);
            firstTask = false;
            return markup;
          }).join("")}
        </div>
      </section>
    `).join("");

    document.querySelectorAll("[data-task-id]").forEach((button) => {
      button.addEventListener("click", async () => {
        const nextState = button.dataset.state === "completed" ? "in_progress" : "completed";
        const response = await api(`/api/bearsmart/plans/${state.plan.id}/tasks/${button.dataset.taskId}`, {
          method: "PATCH",
          body: JSON.stringify({ state: nextState }),
        });
        renderChecklist(response.plan);
      });
    });

    document.querySelectorAll("[data-expand-close]").forEach((button) => {
      button.addEventListener("click", () => {
        button.closest("details")?.removeAttribute("open");
      });
    });
  }

  async function createPlan(persona = state.plan?.persona_type || "resident", options = {}) {
    const { scrollToRecommendations = false } = options;
    document.getElementById("selectedProfileTitle").textContent = profileMeta[persona].title;
    document.getElementById("selectedProfileCopy").textContent = profileMeta[persona].body;
    renderProfileCards(persona);
    const response = await api("/api/bearsmart/plans", {
      method: "POST",
      body: JSON.stringify({ town_slug: state.townSlug, persona_type: persona }),
    });
    document.getElementById("recommendationCount").textContent = response.plan.tasks.length;
    renderChecklist(response.plan);
    if (scrollToRecommendations) {
      document.getElementById("recommendationFocus").scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function bindActions() {
    document.getElementById("printGuideButton").addEventListener("click", () => window.print());
  }

  async function init() {
    setCurrentTown(state.townSlug);
    document.getElementById("dashboardIntroCopy").textContent =
      "Choose a profile to see the most relevant BearSmart actions for your situation. Open any recommendation to see the practical detail behind it.";
    bindActions();
    createPlan().catch((error) => showToast(error.message));
  }

  return { init };
})();

DashboardPage.init().catch((error) => window.BearSmart.showToast(error.message));
