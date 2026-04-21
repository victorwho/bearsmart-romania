# CHANGELOG

All notable product changes to BearSmart Romania. Entries reference findings
from `docs/IMPLEMENTATION_PLAN.md` and the strategic dossier.

## Unreleased — Horizon 0 + Horizon 1

### Horizon 0 — Foundations

- **Auth module** — signed-cookie sessions, role enum (`public`, `resident`,
  `tourist`, `town_admin`, `moderator`, `reviewer`, `super_admin`),
  `require_role(*roles)` dependency that returns 403 JSON for API callers
  and redirects HTML callers to `/login?next=`. Closes IMPLEMENTATION_PLAN §0.1.
- **Feature-flag module** — env-backed flags (`emergency_gate`, `geo_fuzz`,
  `trip_mode`, `town_pages_v2`, `admin_nudges`, `seasonal_campaigns`)
  exposed via `/api/flags` and bootstrapped onto `window.__FLAGS`.
  Closes IMPLEMENTATION_PLAN §0.2.
- **Telemetry module** — typed event catalog
  (`alert_published`, `alert_opened`, `report_submitted`,
  `report_status_changed`, `checklist_item_completed`,
  `trip_subscription_created`, `town_page_viewed`, `cert_evidence_uploaded`,
  plus platform events). Client helper `BearSmart.track(name, props)`
  posts to `/api/telemetry` via `sendBeacon` when available.
  Closes IMPLEMENTATION_PLAN §0.3.
- **Geo-fuzz helper** (`app/geo.py`) — `public_point(lat, lng, report_type)`
  snaps sightings/attractants to a ~500 m grid, road crossings to ~300 m,
  and strips coordinates entirely for `livestock_incident` /
  `apiary_incident` (returns town centre, `radius_m=None`). Every public
  read path routes reports through this helper. Closes IMPLEMENTATION_PLAN
  §0.4 and mitigates threat T5.

### Horizon 1 — Fix the front door

- **Remove role switcher + /login + /workspace** — removed the stale
  `index.html` prototype and its `app.js` (the role dropdown lived only
  there). Added `/login` (HTML form + POST), `/logout`, `/workspace` and
  `/workspace/ops`. `/bearsmart/ops` now 307-redirects to
  `/workspace/ops`, which itself requires `town_admin | moderator |
  reviewer | super_admin`. Closes IMPLEMENTATION_PLAN §1.1 / W2 / UX Audit #1.
- **3-tab Now / Plan / Report bottom sheet** — added a mobile-first
  bottom sheet to the public map home that surfaces alerts + published
  reports (Now), preparedness plan + local contacts (Plan) and the
  report CTA (Report). Tab state is driven by URL hash
  (`#now | #plan | #report`). Built with tonal shifts, no 1 px borders.
  Closes IMPLEMENTATION_PLAN §1.2 / W1 / UX Audit #1.
- **Emergency 112 gate** — every report entry is intercepted by a
  full-screen modal asking *"Is anyone hurt or in immediate danger right
  now?"* with **Yes — call 112** (`tel:112`) and **No — continue report**.
  Dismissal is session-sticky for 30 minutes. Gated by the
  `emergency_gate` flag. Closes IMPLEMENTATION_PLAN §1.3 / W5 / UX Audit #4.
- **Geo-fuzz preview ring** — the report flow renders a translucent
  circle at the fuzz radius when a pin is placed, with copy
  *"Your pin is published to the public as a ~500 m area so private homes
  are not identifiable."* Livestock / apiary types show a stronger
  privacy note and never render exact coordinates. Public `GET`
  endpoints (`/api/bearsmart/map`, `/api/bearsmart/towns/{slug}/reports`)
  expose `public_lat / public_lng / public_radius_m` and no longer leak
  submitted coordinates. Closes IMPLEMENTATION_PLAN §1.4 and threat T5.
- **Moderation SLA surface** — moderation queue items now carry
  `age_seconds` / `age_hours`; the ops UI renders colour-coded badges
  (calm / warn / over) against a 6 h in-season SLA. New
  `/api/bearsmart/moderation/stats` exposes median + p90 age and SLA
  breach counts. Closes IMPLEMENTATION_PLAN §1.5 / threat T1.

### Housekeeping

- Deleted dead prototype `app/static/bearsmart/index.html` and `app.js`.
- Added `emergency-gate.js` and `home-sheet.js` to the static bundle.
- `shared.js` now loads `/api/flags` once at boot, bootstraps
  `window.__FLAGS`, and exposes `BearSmart.track(...)`.
- Added 20+ tests covering auth, flags, telemetry, geo-fuzz, the emergency
  gate contract, the bottom-sheet markup, fuzzed public map output, SLA
  stats, and confirms no new `1px solid` borders in the Horizon blocks.
