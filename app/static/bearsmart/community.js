const Community = (() => {
  const { api } = window.BearSmart;

  function renderPinnedAlert(pinned) {
    document.getElementById("pinnedAlert").innerHTML = `
      <p class="eyebrow">Pinned alert</p>
      <h3 class="section-title community-alert-title">${pinned.title}</h3>
      <p class="section-copy community-alert-copy">${pinned.body}</p>
      <div class="action-grid single-action">
        <a class="button button-secondary" href="/bearsmart/map">${pinned.primary_action}</a>
        <a class="button button-ghost" href="/bearsmart/dashboard">${pinned.secondary_action}</a>
      </div>
    `;
  }

  function renderPosts(posts) {
    document.getElementById("feedPosts").innerHTML = posts.map((post) => `
      <article class="post-card calm-post-card">
        <div class="feed-meta">
          <div class="avatar-pill">${post.author.split(" ").map((word) => word[0]).join("").slice(0, 2)}</div>
          <div>
            <strong>${post.author}</strong>
            <div class="section-copy">${post.role} · ${post.time_ago}</div>
          </div>
        </div>
        <div>
          <h3 class="section-title community-post-title">${post.title}</h3>
          <p class="section-copy">${post.body}</p>
        </div>
        ${post.image ? `<img class="post-image community-post-image" src="${post.image}" alt="${post.title}">` : ""}
        <div class="community-post-footer">
          <span>${post.likes || 0} people found this useful</span>
          <span>${post.comments || 0} discussion notes</span>
        </div>
      </article>
    `).join("");
  }

  function renderHeroes(heroes) {
    document.getElementById("heroesList").innerHTML = `
      <div>
        <p class="eyebrow">Community Heroes</p>
        <div class="list-stack">
          ${heroes.slice(0, 3).map((hero, index) => `
            <div class="hero-row calm-row">
              <div class="community-rank">${index + 1}</div>
              <div style="flex:1;">
                <strong>${hero.name}</strong>
                <div class="section-copy">${hero.achievement}</div>
              </div>
              <strong>${hero.points}</strong>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  function renderWorkshops(workshops) {
    document.getElementById("workshopsList").innerHTML = `
      <div>
        <p class="eyebrow">Upcoming Workshops</p>
        <div class="list-stack">
          ${workshops.slice(0, 2).map((workshop) => `
            <div class="surface-card calm-workshop-card">
              <p class="eyebrow">${workshop.schedule}</p>
              <strong>${workshop.title}</strong>
              <div class="section-copy">${workshop.details}</div>
              <div class="community-post-footer">
                <span>${workshop.availability}</span>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  function renderCta(cta) {
    document.getElementById("communityCta").innerHTML = `
      <div>
        <p class="eyebrow" style="color:rgba(255,255,255,0.78);">Get involved</p>
        <h3 class="section-title" style="color:#fff;">${cta.title}</h3>
        <p class="section-copy" style="color:rgba(255,255,255,0.78);">${cta.body}</p>
      </div>
      <button class="button button-secondary" type="button">${cta.action}</button>
    `;
  }

  async function init() {
    const data = await api("/api/bearsmart/community");
    renderPinnedAlert(data.pinned_alert);
    renderPosts(data.posts);
    renderHeroes(data.heroes);
    renderWorkshops(data.workshops);
    renderCta(data.cta);
  }

  return { init };
})();

Community.init().catch((error) => window.BearSmart.showToast(error.message));
