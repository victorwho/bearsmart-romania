# BearSmart Romania — Implementation Plan for AI Coding Agent

> **Purpose.** This document translates the findings from the *BearSmart Romania Strategic Dossier* (SWOT, UX Audit, Platform Strategy, Promote Localities) into a concrete, sequenced plan an AI coding agent can execute against the current repository.
>
> **Source of truth for code layout.**
> - Backend: `app/main.py`, `app/engine.py`, `app/models.py`, `app/bearsmart_mvp.py`
> - Frontend (static, no framework): `app/static/bearsmart/{index,localities,dashboard,ops,report,map,community}.{html,js}`, `shared.js`, `styles.css`
> - Design system: `DESIGN.md` (Rugged Editorial — Manrope + Public Sans, earth palette, no 1px lines)
> - Product reference: `data/bearsmart_romania_prd.md`, `data/bearsmart_romania_mvp_roadmap.md`
>
> **Rules the agent must follow throughout.**
> 1. Do not invent new colors, fonts, or components outside `DESIGN.md`.
> 2. Never use 1px solid borders for section boundaries — use background-tone shifts.
> 3. Every new public surface must be mobile-first and Romanian-default, English-optional.
> 4. Add tests for every new route/endpoint in `tests.py` using the existing testing style.
> 5. All public map renders MUST route through the geo-fuzz helper before returning coordinates.
> 6. Conventional commits, one PR per horizon below.

---

## 0. Shared foundations (prerequisite — land before Horizon 1)

These items unblock everything else. They are not user-visible but are referenced by every later task.

### 0.1 Session & role model

- **Where:** `app/main.py`, `app/models.py`, new `app/auth.py`.
- **Do:**
  - Add a real session layer (cookie-based, signed). Do not ship another round of features against the current role-dropdown hack.
  - Introduce roles: `public`, `resident`, `tourist`, `town_admin`, `moderator`, `reviewer`, `super_admin`.
  - Add middleware `require_role(*roles)`; return 403 JSON for API, redirect to `/login` for HTML.
  - Backfill existing API endpoints with role guards per the PRD permission matrix.
- **Test:** cross-role probe — for each endpoint, assert every non-permitted role receives 403.

### 0.2 Feature-flag module

- **Where:** new `app/flags.py`, surfaced via `/api/flags` and a `window.__FLAGS` bootstrap in `shared.js`.
- **Do:** simple env-backed flags `emergency_gate`, `geo_fuzz`, `trip_mode`, `town_pages_v2`, `admin_nudges`, `seasonal_campaigns`.
- **Why:** each fix below can be merged behind a flag and turned on per pilot town.

### 0.3 Event instrumentation

- **Where:** `app/telemetry.py`, `app/static/bearsmart/shared.js` (`track(event, props)`).
- **Do:** typed event catalog. At minimum: `alert_published`, `alert_opened`, `report_submitted`, `report_status_changed`, `checklist_item_completed`, `trip_subscription_created`, `town_page_viewed`, `cert_evidence_uploaded`.
- **Why:** the retention loop KPIs in the dossier ("28-day return," "alert CTR," "checklist completion by town") cannot be measured without this.

### 0.4 Geo-fuzz helper

- **Where:** `app/geo.py`.
- **Do:** `def public_point(lat, lng, report_type) -> (lat, lng, radius_m)` — snap to ~500m for sightings and attractant reports, drop coordinates entirely for livestock/apiary (privacy critical), return centre-of-town for anonymous submissions.
- **Why:** threat T5 is existential and the helper is referenced by W4, UX Audit card 4, and Horizon 1 tasks.

---

## Horizon 1 — Fix the front door (weeks 1–3)

**Addresses:** W1, W2, W5, UX Audit #1 (Map), UX Audit #4 (Report), Threats T1, T5.

### 1.1 Remove the public role switcher — W2, UX Audit #1

- **Files:** `app/static/bearsmart/index.html`, `shared.js`, `styles.css`.
- **Do:**
  - Delete `<label>Role<select id="roleSelect">…</select></label>` from the topbar.
  - Add a small `/login` page. Signed-out visitors only see Public surface.
  - Admin, moderator, reviewer UIs move behind `/workspace` (a separate layout, not panels inside the home screen).
  - Delete the Town Admin Console + Operations panels from `index.html`.
- **Acceptance:** a logged-out visitor never sees any role control. A logged-in `town_admin` lands on `/workspace` by default, not on the public map.

### 1.2 Collapse the 9-panel right column to 3 tabs — W1, UX Audit #1

- **Files:** `index.html`, `app.js`, `styles.css`.
- **Do:**
  - Replace the vertical stack with a mobile-first bottom sheet that has exactly three tabs: **Now**, **Plan**, **Report**.
    - *Now* = Town spotlight + Active alerts + Published reports (read loop).
    - *Plan* = Preparedness plan + Local contacts (action loop).
    - *Report* = Report CTA + How-it-works + Selected point (contribution loop).
  - Drive tab state from the URL hash (`#now|#plan|#report`) so deep-links work.
  - Existing panels migrate unchanged into the tab that owns them; styles stay in `styles.css` with no new tokens.
- **Acceptance:** the home page shows exactly one panel column at a time; DOM no longer contains `.panel.spotlight-panel` **and** admin/ops panels simultaneously.

### 1.3 Emergency gate on every report flow — W5, UX Audit #4, Pillar 1

- **Files:** `report.html`, `report.js`, `index.html` (FAB + dialog).
- **Do:**
  - Every entry to the report flow first renders a full-screen modal with one question: *"Is anyone hurt or in immediate danger right now?"* with two buttons: **Yes — call 112** (tel:112) and **No — continue report**.
  - The modal is dismissed-sticky for 30 minutes per session; after 30 min, re-show.
  - Update all CTAs (`#fabReportButton`, `#openReportDialogButton`, `report.html` entry) to route through the gate.
- **Acceptance:** e2e test "user clicks Report → sees emergency gate → chooses No → reaches the form."

### 1.4 Geo-fuzz preview inside the report dialog — W5, UX Audit #4, Threat T5

- **Files:** `report.js`, `app.js`, new CSS for the preview ring.
- **Do:**
  - When a point is placed, render a translucent circle of radius returned by `public_point()` and copy: *"Your pin is published to the public as a ~500 m area so private homes are not identifiable."*
  - Server `POST /api/reports` stores precise coordinates (for authorities) and exposes only fuzzed coordinates in `GET /api/reports`.
- **Acceptance:** API contract test: public report GET never returns `lat/lng` equal to the submitted values; it returns `public_lat`, `public_lng`, `public_radius_m`.

### 1.5 Moderation SLA surface — Threat T1

- **Files:** `app/main.py`, `ops.html`, `ops.js`.
- **Do:** moderation queue shows age-in-queue per item and colours red above the configured SLA (default 6h in-season, 24h off-season). `GET /api/moderation/stats` returns median + 90th percentile turn-around.
- **Acceptance:** ops queue renders an ISO timestamp + elapsed; reports older than SLA have the high-visibility badge.

---

## Horizon 2 — Localities as destinations (weeks 4–6)

**Addresses:** W3, O1, O2, O5, UX Audit #2 (Localities), Pillar 2 (promote localities).

### 2.1 Town page v2 — editorial destination layout

- **Files:** new `app/static/bearsmart/town.html`, `town.js`. Replace `localities.html` per-town links so each card routes to `/town/<slug>`.
- **Layout sections (in order):**
  1. **Hero** — full-bleed image, town name, county, population, one-line pitch, certification pill, live alert strip.
  2. **Seasonal mood** — current-season text block ("Spring: mothers with cubs emerging on south-facing slopes") pulled from `content_objects` keyed by town + season.
  3. **Resident / admin quote** — a single quote, name, role.
  4. **What to do this weekend** — compact 3-line summary for tourists (US #36).
  5. **Bear-safe businesses** — badge directory grid (see 2.3).
  6. **Live activity** — last 5 public reports (fuzzed) + upcoming events.
  7. **Progress scorecard** — households bear-proofed, businesses certified, 12-month incident trend sparkline.
  8. **Local rules & contacts** — existing content, restyled.
- **Data model additions:** `towns.hero_image_url`, `towns.pitch_ro`, `towns.pitch_en`, `towns.seasonal_notes: {spring,summer,autumn,winter}`, `towns.featured_quote`.
- **Acceptance:** `/town/zarnesti` renders all 8 sections on mobile without horizontal scroll; Lighthouse performance ≥ 85 on 4G throttled.

### 2.2 National pride map (replaces the filterable table) — O1, W3

- **Files:** `localities.html`, `localities.js`.
- **Do:**
  - Primary surface becomes a Romania SVG/canvas map with pins coloured by certification state (certified / renewal-due / in-progress / new).
  - Secondary surface is the existing grid, demoted to below the fold.
  - County mini-legend on the right (pilot counties first: Brașov, Prahova, Harghita, Covasna, Argeș).
- **Acceptance:** tapping a pin pushes `/town/<slug>`. Filter chips update pin visibility without a reload.

### 2.3 Bear-safe business badge — O5, Pillar 2

- **Files:** `app/models.py` (new `businesses` + `business_evidence` tables), `app/main.py` (`/api/businesses/*`), new `workspace/businesses.html` admin UI.
- **Do:**
  - Business self-apply form; evidence upload per checklist criterion; moderator review reuses the existing moderation queue.
  - Public directory block on every town page (section 5 above).
  - Each approved business gets: profile page, printable window-sticker PDF endpoint (`/badge/<business_id>.pdf`), backlink HTML snippet.
- **Acceptance:** a business can submit → be reviewed → appear on its town page end-to-end in tests.

### 2.4 "Plan a visit" trip mode — O3, US #7, US #36

- **Files:** new `trip.html`, `trip.js`; subscription model gains `kind = permanent | trip`, `expires_at`, `target_town_id`.
- **Do:**
  - On every town page: a pinned CTA "Plan a visit this weekend" → single-page form: dates + email → creates a trip subscription (auto-expires 3 days after end date) + generates a tourist prep checklist + a "pocket guide" HTML the user can bookmark offline.
  - No account required; trip subscriptions are email-keyed.
- **Acceptance:** submitting the form results in (a) a row in `subscriptions` with `kind='trip'`, (b) a confirmation email stub, (c) a rendered pocket-guide URL with the trip's context.

---

## Horizon 3 — Return loops (weeks 7–9)

**Addresses:** Pillar 3 (design for return), Threats T2, T4, UX Audit #3 (Dashboard), UX Audit #4 status pings.

### 3.1 Admin workspace — compose first, analyse second — UX Audit #3

- **Files:** new `workspace/index.html`, move existing `dashboard.html` behind `/workspace/analytics`.
- **Do:**
  - Landing surface on admin login: an **alert composer** (title, severity, validity window, body) and a **to-do list** (reports awaiting public comment, cert criteria due, businesses in review).
  - Analytics/charts move to a second tab.
  - Weekly digest email to each town admin: "this week — N new reports, M alerts expired, cert renewal in X days, peer benchmark."
- **Acceptance:** time-to-publish an alert from login is ≤ 3 interactions.

### 3.2 Report status pings — UX Audit #4

- **Files:** `app/models.py` (reports gain `status_history: [{status, at, actor_id}]`), `app/main.py`, email templates.
- **Do:**
  - Authenticated reporters get emails + in-app indicators when status changes through `unverified → community-confirmed → officially verified`.
  - Add a public `status` badge on every report card.
  - "My reports" page for signed-in residents.
- **Acceptance:** changing a report's status via the moderation API triggers a stored event and an email stub.

### 3.3 Seasonal campaign engine — Threat T4, Pillar 3

- **Files:** new `app/campaigns.py`, `content/campaigns/*.yml`.
- **Do:**
  - YAML-defined campaigns (spring emergence, berry season, hyperphagia, winter denning) with a `trigger_window`, `target_audience`, per-town placeholder copy and a primary CTA.
  - Cron-like scheduler publishes them as town alerts (opt-in per town) + banner on the home map.
- **Acceptance:** a campaign scheduled for `2026-04-15..2026-05-15` appears on all opted-in town pages during that window, disappears after.

### 3.4 Preparedness streaks + household graduation — Pillar 3

- **Files:** `app/engine.py` (existing plan engine), `app.js` (Plan tab).
- **Do:**
  - Checklists persist per user + per season. Completing ≥ 80 % in a season advances the household from `new → prepared → mentor`.
  - Mentor households receive a per-season prompt to share a story (fed into the community story pipeline).
- **Acceptance:** progression test — simulate 4 seasons of checklist completions; user record graduates through all three states.

### 3.5 Neighbour verification — Pillar 3

- **Files:** `report.html` detail view, `app/main.py`.
- **Do:** authenticated residents of the same town can confirm a report. At 3 independent confirms, status auto-advances to `community-confirmed`. Throttled (one confirm per user per report; rate-limited per user).
- **Acceptance:** API test; UI shows confirm count and the "3 neighbours confirm" badge.

---

## Horizon 4 — Public launch & distribution (weeks 10–12)

**Addresses:** O2, O4, Pillar 2 distribution, platform appeal.

### 4.1 Public scorecards — O2

- **Files:** `/town/<slug>/scorecard` (sub-route), `app/metrics.py`.
- **Do:** publish per-town quarterly metrics: households on plan, businesses certified, report volume, median moderation time, cert progress %. All derived from events registered in 0.3.
- **Acceptance:** scorecard pages are static-generated quarterly and pinned to the town page hero.

### 4.2 Embeddable town-status widget — Pillar 2

- **Files:** new `widget/town.html` (iframe-friendly), `widget.js`.
- **Do:** a narrow (320×180) card showing town name, cert state, current alert, last-updated; one-line `<script src="/widget/town.js?slug=zarnesti">` embed.
- **Acceptance:** embedded in a throwaway HTML page, widget renders and updates when a new alert is published.

### 4.3 Auto-generated "State of BearSmart" PDF — Pillar 2, O4

- **Files:** `app/reports_pdf.py` (WeasyPrint or similar), template in `templates/state_of_bearsmart.html`.
- **Do:** quarterly PDF per town — hero image, cert state, stats, three resident quotes, alerts sent, reports resolved. Download endpoint `/town/<slug>/press-kit.pdf`.
- **Acceptance:** a generated PDF for a seeded town renders on page-1 without broken images.

### 4.4 Retention dashboard — Pillar 3 instrumentation, dossier KPI band

- **Files:** `workspace/retention.html` (super-admin only).
- **Do:** surface the four dossier KPIs — 28-day return, median moderation turn-around, active-alerts-per-town-per-week, first-checklist completion rate — filterable per pilot town.
- **Acceptance:** dashboard reads exclusively from the event log; no ad-hoc SQL.

### 4.5 Bilingual plumbing — W4-adjacent, public-launch blocker

- **Files:** `i18n/` dir, `ro.json`, `en.json`; `shared.js` helper `t(key)`; every static template migrates strings.
- **Do:** default Romanian; English toggle in the footer; trip-mode + town pages are bilingual on day 1.
- **Acceptance:** setting `?lang=en` switches every static string on home, town pages, trip form, and the report flow.

---

## Threat-specific hardening (runs in parallel, not a separate horizon)

| Threat | Mitigation | File(s) | Acceptance |
|---|---|---|---|
| T1 — misinformation | Moderation SLA surface (1.5) + neighbour verification (3.5) + status pings (3.2) | `ops.js`, `app/main.py` | reports are never shown public without passing moderation or the 3-confirm threshold |
| T2 — low admin engagement | Weekly admin digests + composer-first workspace (3.1) | `workspace/*`, `app/campaigns.py` | digest email sent every Monday; open rate tracked |
| T3 — agency territorialism | "Informational, not dispatch" disclaimer on every emergency surface; read-only feed endpoints for authorities (`/api/feeds/authority.json`) | `app/main.py`, footer component | endpoint returns unfuzzed data only to IP-allowlisted authority clients |
| T4 — seasonality collapse | Seasonal campaign engine (3.3) + preparedness streaks (3.4) | `app/campaigns.py`, `app/engine.py` | winter surface still shows campaign + household graduation prompts |
| T5 — privacy exposure | Geo-fuzz (0.4) + geo-fuzz preview (1.4) + no coordinates for livestock/apiary (0.4) | `app/geo.py`, `report.js` | automated test: no public endpoint returns a point closer than 400m to its source for sighting/attractant, and returns no point at all for livestock/apiary |

---

## Definition of done per PR

Every PR merged by the agent must:

1. Update or add tests in `tests.py` covering the behaviour described under **Acceptance**.
2. Emit at least one event through `app/telemetry.py` if the task affects a KPI in the dossier.
3. Pass a `grep -n "1px solid" app/static/bearsmart/styles.css` check — no new 1px borders introduced (design system rule).
4. Stay behind its feature flag (from 0.2) until the horizon's demo review.
5. Add a one-line entry to `CHANGELOG.md` linking back to the dossier finding it closes (e.g. *"Closes W2 / UX Audit #1"*).

---

## Execution order summary

```
Horizon 0 — foundations     (prerequisite)
  0.1 auth       0.2 flags       0.3 telemetry       0.4 geo-fuzz
Horizon 1 — fix the front door
  1.1 role switcher out → 1.2 three-tab sheet → 1.3 emergency gate → 1.4 geo-fuzz preview → 1.5 moderation SLA
Horizon 2 — localities as destinations
  2.1 town page v2 → 2.2 pride map → 2.3 business badges → 2.4 trip mode
Horizon 3 — return loops
  3.1 admin workspace → 3.2 status pings → 3.3 campaigns → 3.4 streaks → 3.5 neighbour verify
Horizon 4 — public launch
  4.1 scorecards → 4.2 widget → 4.3 PDF press kits → 4.4 retention dashboard → 4.5 i18n
```

Every horizon is shippable on its own. If the agent has to stop early, the furthest-back completed horizon is a coherent release.
