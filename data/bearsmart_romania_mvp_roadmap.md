# BearSmart Romania MVP Roadmap

## Purpose

This roadmap translates the PRD into a phased execution plan for launching `BearSmart Romania` as a town-centric civic web platform. The roadmap is optimized for:

- fastest path to a credible pilot launch
- early repeat-use value for residents and visitors
- operational usefulness for town halls
- a foundation that can scale to multiple Romanian towns

The roadmap assumes a phased rollout starting with a small group of pilot towns and expanding after the core product loops are proven.

## Product Strategy

The MVP should not try to launch every community feature at once. It should first prove one strong loop:

- a user selects a town
- the platform shows town-specific status, guidance, and alerts
- the user takes action through a checklist or report
- the town can respond and publish updates
- the platform shows visible progress and builds trust

That loop is the heart of the product. Everything else should support it.

## Prioritization Framework

### P0: Must Have for MVP

These are required for the first credible launch:

- town directory and town profile pages
- alert publishing and subscriptions
- user reporting with moderation
- personalized preparedness plans
- municipal certification workflow
- authentication and role-based access
- core admin and moderation tooling

### P1: High Value After MVP Core

- public town scorecards
- business bear-safe badges
- events and workshops
- richer map filters and hotspot views
- multilingual support beyond core Romanian defaults
- analytics dashboards for towns and national admins

### P2: Engagement and Growth Layer

- community stories and before/after case studies
- town-vs-town challenges
- school modules
- volunteer programs
- sponsor and partner showcases
- advanced personalization and campaign automation

## Recommended Pilot Scope

Launch first with `3 to 5 towns`, not nationally all at once.

Pilot town profile should include:

- one tourism-heavy town
- one residential town with recurring local conflict
- one town hall partner willing to actively use the admin portal
- at least one town with enough political support to pursue certification evidence submission

This gives enough variation to test whether the product works across different local contexts.

## Phase 0: Foundations and Validation

### Goal

Create the operational and technical base needed for a pilot without yet building every engagement feature.

### Priority

`P0`

### Deliverables

- finalize product scope for pilot
- define certification statuses and criterion model
- define report taxonomy and moderation rules
- define user roles and permission matrix
- define core town data model
- define alert severity model and expiry rules
- define privacy policy for public map data and geo-fuzzing
- create initial design system and UX patterns
- select stack and hosting architecture
- seed pilot-town content structure

### Key Decisions Locked in This Phase

- what counts as a certified town, in-progress town, and renewal-due town
- which report types are available at launch
- whether anonymous reports are allowed and under what limits
- what exact public information appears on a town page
- what minimum evidence is required for a town certification submission

### Exit Criteria

- product scope signed off for pilot
- core data model defined
- role model defined
- moderation and safety rules defined
- first-pass UX flows approved

## Phase 1: Core Platform and Town Experience

### Goal

Ship the public-facing product skeleton and make town pages the center of the experience.

### Priority

`P0`

### Features

- homepage with town search and pilot-town discovery
- certified towns directory
- town profile pages
- local contacts and policy blocks
- local rules and preparedness guidance blocks
- town status badge and renewal state
- public map with approved activity signals
- mobile-first responsive experience

### Why This Comes First

Without strong town pages, the platform is just another content site. This phase establishes the product's core identity and the main repeat-use destination.

### Dependencies

- finalized town data model
- CMS or content admin structure
- map and geospatial service decisions
- design system primitives

### Success Metrics

- users can find a town in under one minute
- each pilot town has a complete public profile
- users understand the difference between national content and town-specific content
- town pages are usable on mobile

## Phase 2: Alerts and Subscriptions

### Goal

Make the platform useful between visits and create a reason to come back.

### Priority

`P0`

### Features

- local alert creation by authorized town admins
- alert severity levels
- alert validity windows and expiry
- subscriptions by town
- optional short-term subscriptions for tourists
- email notifications
- web push support if feasible in MVP
- alert archive on each town page

### Why This Comes Early

Alerts are one of the strongest retention loops. They make the platform feel live and relevant.

### Dependencies

- authentication and role permissions
- notification infrastructure
- alert model and admin UI

### Success Metrics

- town admins can publish alerts without engineering help
- users can subscribe in under two minutes
- expired alerts no longer appear as active
- alert CTR and return visits show repeat-use behavior

## Phase 3: Reporting and Moderation

### Goal

Create a trusted public contribution loop without turning the platform into an unsafe rumor board.

### Priority

`P0`

### Features

- public reporting flow
- report types: sighting, attractant issue, road crossing, livestock/apiary issue, neighborhood hazard
- optional image upload
- moderation queue
- report status model: unverified, community-confirmed, officially verified
- geo-fuzzed public display
- resident submission tracking for signed-in users
- emergency guidance on every report flow

### Why This Is Core

Reporting is the first meaningful UGC engine and the main way to convert passive readers into participants.

### Dependencies

- moderation rules
- auth and anonymous submission rules
- storage for media
- map display logic

### Success Metrics

- reports can be submitted from mobile in the field
- moderators can review reports efficiently
- unsafe or sensitive data is not shown publicly
- users receive clear confirmation and status updates

## Phase 4: Personalized Preparedness Plans

### Goal

Turn the platform from an alert-and-report tool into an action platform.

### Priority

`P0`

### Features

- persona selection
- local context-aware checklists
- progress tracking
- seasonal tasks
- saved plan per user
- quick-start plans for guests without full account setup if feasible

### Initial Personas

- resident
- tourist / visitor
- business owner
- school / educator
- beekeeper
- farmer / livestock owner

### Why This Is MVP-Critical

Preparedness plans make the platform behavior-changing, not merely informative. They also create repeat visits and progress loops.

### Dependencies

- structured task library
- user profile model
- town-specific rules and content

### Success Metrics

- users can generate a plan in under three minutes
- users understand what to do next after completing onboarding
- checklist completion correlates with repeat sessions

## Phase 5: Municipal Certification Workflow

### Goal

Provide real operational value to town halls and establish the platform's institutional differentiator.

### Priority

`P0`

### Features

- town admin portal
- certification criteria checklist
- evidence upload per criterion
- reviewer comments
- status changes and audit trail
- issue, renewal, suspension, and expiry workflow
- public certification badge on town page

### Why This Is Essential

This is what makes the platform national infrastructure for BearSmart towns rather than just a public consumer app.

### Dependencies

- admin roles
- document storage
- criterion versioning model
- reviewer workflow

### Success Metrics

- a pilot town can complete a certification submission end-to-end
- reviewers can assess evidence without ad hoc tools
- certification state updates appear correctly on public town pages

## Phase 6: Pilot Launch and Operational Hardening

### Goal

Launch with a controlled group of towns and improve the product based on real usage.

### Priority

`P0`

### Features and Tasks

- pilot onboarding for town admins
- moderation operations handbook
- support workflows for false reports and content corrections
- instrumentation and analytics dashboards
- bug fixing and UX refinements
- content QA across all pilot towns
- launch communications

### Success Metrics

- at least one town actively publishes alerts
- at least one town submits certification evidence
- residents submit reports and return to check outcomes
- tourist visitors can use the product without training
- moderation turnaround stays within agreed SLA

## Phase 7: Post-MVP Expansion

### Goal

Increase engagement, public visibility, and municipal value after the core workflows are stable.

### Priority

`P1`

### Features

- public town scorecards
- bear-safe business directory and badges
- events and workshops calendar
- hotspot heatmaps and richer filters
- county-level and national analytics views
- English and possibly other tourist-facing language support

### Why This Is Not Phase 1

These features are valuable, but they depend on the core town, alert, reporting, and certification systems already being trusted and used.

## Phase 8: Community and Network Effects

### Goal

Make the platform socially sticky and self-reinforcing.

### Priority

`P2`

### Features

- community stories
- before-and-after showcases
- neighborhood or town challenges
- volunteer signups
- school participation modules
- campaign automation for seasonal outreach

### Why This Comes Later

UGC and engagement features work best when the platform already has trust, moderation quality, and municipal participation.

## Suggested Build Order by Workstream

### Workstream A: Platform Core

1. auth and roles
2. town model
3. content model
4. admin shell
5. analytics plumbing

### Workstream B: Public Experience

1. homepage
2. towns directory
3. town page
4. mobile optimization
5. public map

### Workstream C: Operational Utilities

1. alerts
2. subscriptions
3. notifications
4. report moderation
5. certification portal

### Workstream D: Behavior Change Tools

1. persona model
2. task library
3. plan generation
4. progress tracking
5. seasonal reminder logic

## Release Plan

### Release 0: Internal Alpha

Scope:

- static pilot-town data
- internal admin access
- early town page prototypes
- no public reporting yet

Purpose:

- validate data model and IA
- validate admin workflows
- test map and location privacy rules

### Release 1: Pilot Beta

Scope:

- public town pages
- alerts
- reporting with moderation
- preparedness plans
- town admin portal

Purpose:

- prove repeat-use value
- prove town-hall operational usefulness
- validate moderation load and user comprehension

### Release 2: Public MVP

Scope:

- refined pilot flows
- certification review workflow
- improved analytics
- stronger onboarding and subscriptions

Purpose:

- support public launch narrative
- onboard additional towns
- establish credible BearSmart certification visibility

## Priority Matrix

| Capability | Priority | Reason |
| --- | --- | --- |
| Town directory and town pages | P0 | Core product identity |
| Alerts and subscriptions | P0 | Strong repeat-use loop |
| Reporting and moderation | P0 | Core participation and trust loop |
| Preparedness plans | P0 | Converts information into action |
| Municipal certification workflow | P0 | Institutional differentiator |
| Auth and role permissions | P0 | Required for operations and trust |
| Public map | P0 | Central UI for local relevance |
| Analytics instrumentation | P0 | Needed to evaluate pilot |
| Business badges | P1 | Valuable but not launch-critical |
| Events and workshops | P1 | Good for local engagement |
| Town scorecards | P1 | Strong motivator after baseline data exists |
| Multilingual expansion | P1 | Important for tourism, can phase |
| Community stories | P2 | Better after trust and moderation mature |
| Challenges and gamification | P2 | Retention enhancer, not core utility |
| School modules | P2 | Important expansion area, not MVP blocker |

## Team Recommendation

If capacity is limited, organize around these module groups:

- `Platform Core`: auth, permissions, users, towns, content
- `Civic Operations`: alerts, moderation, certification, admin dashboards
- `Public Experience`: homepage, town pages, maps, subscriptions
- `Preparedness Engine`: personas, tasks, plans, reminders

This keeps the MVP focused on deep modules instead of scattered page-by-page development.

## Key Risks

- trying to launch too many engagement features before core trust systems are stable
- weak moderation causing misinformation or unsafe map behavior
- treating certification as static content instead of an operational workflow
- insufficient town admin participation during pilot
- poor mobile UX reducing field usage
- unclear difference between emergency response and informational reporting

## MVP Success Criteria

The MVP is successful if:

- users repeatedly return to town pages and alerts
- at least a subset of residents complete preparedness actions
- town admins can operate their local profile and alerts without product team intervention
- report submissions are moderated safely and efficiently
- at least one town completes a certification workflow end-to-end
- pilot towns want to remain on the platform and additional towns want to join

## Recommended Immediate Next Steps

1. Convert this roadmap into implementation epics.
2. Define the exact MVP data model for towns, alerts, reports, plans, and certifications.
3. Design the three critical flows first: town page, alert subscription, and report submission.
4. Choose pilot towns and validate real operational partners.
5. Lock the moderation and privacy model before building public maps.

