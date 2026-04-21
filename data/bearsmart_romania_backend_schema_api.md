# BearSmart Romania P0 Backend Schema and API

## Purpose

This document derives the backend schema and API surface for the `P0` scope defined in the BearSmart Romania MVP roadmap.

It is intentionally limited to the first release-critical capabilities:

- town directory and town profile pages
- alerts and subscriptions
- reporting and moderation
- personalized preparedness plans
- municipal certification workflow
- authentication and role-based access
- public map support
- core analytics instrumentation

This specification assumes a backend stack of:

- `FastAPI`
- `PostgreSQL`
- `PostGIS`
- object storage for uploads
- async worker or queue for notifications and background processing

## Design Principles

- Use `UUID` primary keys for all major entities.
- Use `snake_case` for database columns and JSON fields.
- Prefer explicit lifecycle statuses over nullable-state inference.
- Keep public map data privacy-aware by default.
- Separate public read models from admin write workflows where needed.
- Version certification criteria to support future program evolution.
- Support both anonymous and authenticated reporting, with tighter controls on anonymous flows.

## P0 Domain Model

### Core Entities

- `users`
- `towns`
- `town_memberships`
- `town_contacts`
- `alerts`
- `alert_subscriptions`
- `reports`
- `report_media`
- `report_reviews`
- `preparedness_personas`
- `preparedness_task_templates`
- `user_plans`
- `user_plan_tasks`
- `certification_frameworks`
- `certification_criteria`
- `town_certifications`
- `town_certification_submissions`
- `submission_evidence`
- `audit_logs`
- `analytics_events`

## Recommended Enums

### User and access enums

- `user_role`
  - `resident`
  - `business_owner`
  - `town_admin`
  - `moderator`
  - `certification_reviewer`
  - `super_admin`

- `membership_role`
  - `town_admin`
  - `town_editor`
  - `town_alert_publisher`
  - `town_certification_manager`

### Town and certification enums

- `town_status`
  - `pilot`
  - `active`
  - `inactive`

- `certification_status`
  - `not_started`
  - `in_progress`
  - `submitted`
  - `under_review`
  - `certified`
  - `renewal_due`
  - `suspended`
  - `expired`
  - `rejected`

- `criterion_submission_status`
  - `not_started`
  - `draft`
  - `submitted`
  - `changes_requested`
  - `approved`
  - `rejected`

### Alerts and subscriptions enums

- `alert_type`
  - `bear_activity`
  - `attractant_warning`
  - `road_risk`
  - `seasonal_advisory`
  - `town_notice`

- `alert_severity`
  - `info`
  - `advisory`
  - `warning`
  - `critical`

- `alert_status`
  - `draft`
  - `scheduled`
  - `active`
  - `expired`
  - `cancelled`

- `subscription_channel`
  - `email`
  - `web_push`

### Reporting enums

- `report_type`
  - `sighting`
  - `attractant_issue`
  - `road_crossing`
  - `livestock_incident`
  - `apiary_incident`
  - `neighborhood_hazard`

- `report_status`
  - `submitted`
  - `under_review`
  - `published`
  - `closed`
  - `rejected`
  - `escalated`

- `verification_status`
  - `unverified`
  - `community_confirmed`
  - `officially_verified`

- `location_precision`
  - `exact_private`
  - `fuzzy_public`
  - `town_only`

- `review_action`
  - `approve`
  - `reject`
  - `redact`
  - `request_more_info`
  - `escalate`

### Plans enums

- `persona_type`
  - `resident`
  - `tourist`
  - `business_owner`
  - `school`
  - `beekeeper`
  - `farmer`

- `task_season`
  - `spring`
  - `summer`
  - `autumn`
  - `winter`
  - `all_year`

- `task_state`
  - `not_started`
  - `in_progress`
  - `completed`
  - `skipped`

## Database Schema

### 1. `users`

Stores platform users. Authentication can be local or external, but the application should normalize to this table.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `email` | `citext unique` | nullable for invitation placeholders only |
| `full_name` | `text` | |
| `preferred_language` | `text` | default `ro` |
| `home_town_id` | `uuid fk -> towns.id` | nullable |
| `primary_role` | `user_role` | high-level role classification |
| `auth_provider` | `text` | e.g. `password`, `google`, `oidc` |
| `auth_provider_user_id` | `text` | nullable, indexed |
| `is_active` | `boolean` | default true |
| `email_verified_at` | `timestamptz` | nullable |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

Indexes:

- unique on `email`
- index on `home_town_id`
- index on `auth_provider, auth_provider_user_id`

### 2. `towns`

Primary public and operational entity.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `slug` | `text unique` | public routing key |
| `name` | `text` | |
| `county` | `text` | |
| `country_code` | `text` | default `RO` |
| `status` | `town_status` | |
| `certification_status` | `certification_status` | current public status shortcut |
| `hero_title` | `text` | nullable |
| `hero_summary` | `text` | nullable |
| `short_description` | `text` | nullable |
| `public_lat` | `numeric(9,6)` | town center |
| `public_lng` | `numeric(9,6)` | town center |
| `boundary_geom` | `geometry(MultiPolygon, 4326)` | nullable in earliest pilot |
| `map_default_zoom` | `int` | default 11 |
| `rules_summary` | `text` | short public safety summary |
| `waste_guidance` | `text` | nullable |
| `visitor_guidance` | `text` | nullable |
| `is_certified_public` | `boolean` | derived convenience field |
| `certification_issued_at` | `timestamptz` | nullable |
| `certification_expires_at` | `timestamptz` | nullable |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

Indexes:

- unique on `slug`
- GIST on `boundary_geom`
- index on `county`
- index on `certification_status`

### 3. `town_contacts`

Public contact blocks and emergency/non-emergency references.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `town_id` | `uuid fk -> towns.id` | |
| `contact_type` | `text` | e.g. `emergency`, `wildlife_manager`, `town_hall`, `visitor_info` |
| `label` | `text` | |
| `phone` | `text` | nullable |
| `email` | `text` | nullable |
| `url` | `text` | nullable |
| `display_order` | `int` | |
| `is_public` | `boolean` | default true |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

### 4. `town_memberships`

Town-scoped permissions.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `town_id` | `uuid fk -> towns.id` | |
| `user_id` | `uuid fk -> users.id` | |
| `role` | `membership_role` | |
| `is_active` | `boolean` | |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

Constraint:

- unique on `town_id, user_id, role`

### 5. `alerts`

Town-specific and optionally geotargeted alerts.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `town_id` | `uuid fk -> towns.id` | |
| `type` | `alert_type` | |
| `severity` | `alert_severity` | |
| `status` | `alert_status` | |
| `title` | `text` | |
| `message` | `text` | user-facing copy |
| `cta_label` | `text` | nullable |
| `cta_url` | `text` | nullable |
| `public_advice` | `text` | what the user should do |
| `starts_at` | `timestamptz` | |
| `ends_at` | `timestamptz` | nullable |
| `published_at` | `timestamptz` | nullable |
| `created_by_user_id` | `uuid fk -> users.id` | |
| `last_updated_by_user_id` | `uuid fk -> users.id` | |
| `coverage_geom` | `geometry(MultiPolygon, 4326)` | nullable for sub-town targeting |
| `source_note` | `text` | optional admin note |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

Indexes:

- index on `town_id, status`
- index on `starts_at, ends_at`
- GIST on `coverage_geom`

### 6. `alert_subscriptions`

Tracks user or email-based subscriptions.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `town_id` | `uuid fk -> towns.id` | |
| `user_id` | `uuid fk -> users.id` | nullable for guest subscriptions |
| `email` | `citext` | nullable if user-backed and email derived |
| `channel` | `subscription_channel` | |
| `is_temporary` | `boolean` | default false |
| `temporary_until` | `timestamptz` | nullable |
| `is_active` | `boolean` | |
| `confirmed_at` | `timestamptz` | nullable |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

Indexes:

- index on `town_id, is_active`
- index on `user_id`
- index on `email`

### 7. `reports`

Public contribution and moderation root entity.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `town_id` | `uuid fk -> towns.id` | derived from geometry or selected explicitly |
| `submitted_by_user_id` | `uuid fk -> users.id` | nullable for guest reports |
| `type` | `report_type` | |
| `status` | `report_status` | |
| `verification_status` | `verification_status` | default `unverified` |
| `title` | `text` | nullable; generated for some report types |
| `description` | `text` | |
| `occurred_at` | `timestamptz` | nullable |
| `submitted_at` | `timestamptz` | |
| `private_location_geom` | `geometry(Point, 4326)` | full-precision internal point |
| `public_location_geom` | `geometry(Point, 4326)` | geo-fuzzed point or null |
| `location_precision` | `location_precision` | |
| `location_label` | `text` | public-friendly area label |
| `is_anonymous` | `boolean` | |
| `submitter_email` | `citext` | nullable |
| `submitter_phone` | `text` | nullable |
| `source_context` | `text` | `web`, `admin_entered`, etc. |
| `is_sensitive` | `boolean` | default false |
| `public_summary` | `text` | nullable approved summary |
| `assigned_moderator_user_id` | `uuid fk -> users.id` | nullable |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

Indexes:

- index on `town_id, type`
- index on `status`
- index on `verification_status`
- GIST on `private_location_geom`
- GIST on `public_location_geom`

### 8. `report_media`

Attached evidence for reports.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `report_id` | `uuid fk -> reports.id` | |
| `storage_key` | `text` | object storage path |
| `mime_type` | `text` | |
| `width` | `int` | nullable |
| `height` | `int` | nullable |
| `is_public` | `boolean` | default false |
| `uploaded_by_user_id` | `uuid fk -> users.id` | nullable |
| `created_at` | `timestamptz` | |

### 9. `report_reviews`

Moderation and verification actions.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `report_id` | `uuid fk -> reports.id` | |
| `reviewed_by_user_id` | `uuid fk -> users.id` | |
| `action` | `review_action` | |
| `resulting_status` | `report_status` | |
| `resulting_verification_status` | `verification_status` | nullable |
| `internal_notes` | `text` | |
| `public_note` | `text` | nullable |
| `created_at` | `timestamptz` | |

Indexes:

- index on `report_id, created_at desc`

### 10. `preparedness_personas`

System-defined persona catalog.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `persona_type` | `persona_type unique` | |
| `label_ro` | `text` | |
| `label_en` | `text` | nullable |
| `description_ro` | `text` | |
| `is_active` | `boolean` | |

### 11. `preparedness_task_templates`

Reusable plan tasks for each persona and season.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `persona_id` | `uuid fk -> preparedness_personas.id` | |
| `town_id` | `uuid fk -> towns.id` | nullable for global tasks |
| `season` | `task_season` | |
| `title_ro` | `text` | |
| `description_ro` | `text` | |
| `priority_rank` | `int` | |
| `is_required` | `boolean` | |
| `is_active` | `boolean` | |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

Indexes:

- index on `persona_id, season`
- index on `town_id`

### 12. `user_plans`

Preparedness plans generated for users or guests.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `user_id` | `uuid fk -> users.id` | nullable for guest plans if allowed |
| `town_id` | `uuid fk -> towns.id` | |
| `persona_id` | `uuid fk -> preparedness_personas.id` | |
| `season` | `task_season` | |
| `completion_percent` | `int` | cached 0-100 |
| `is_active` | `boolean` | |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

Constraint:

- unique on `user_id, town_id, persona_id, season, is_active` where `is_active = true`

### 13. `user_plan_tasks`

Concrete task instances copied from templates.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `plan_id` | `uuid fk -> user_plans.id` | |
| `template_id` | `uuid fk -> preparedness_task_templates.id` | nullable to allow future custom tasks |
| `title_ro` | `text` | denormalized snapshot |
| `description_ro` | `text` | denormalized snapshot |
| `priority_rank` | `int` | |
| `state` | `task_state` | |
| `completed_at` | `timestamptz` | nullable |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

Indexes:

- index on `plan_id, state`

### 14. `certification_frameworks`

Versioned certification frameworks.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `version_code` | `text unique` | e.g. `RO-2026-v1` |
| `label` | `text` | |
| `description` | `text` | nullable |
| `is_active` | `boolean` | |
| `effective_from` | `date` | |
| `effective_to` | `date` | nullable |
| `created_at` | `timestamptz` | |

### 15. `certification_criteria`

Framework criteria definition.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `framework_id` | `uuid fk -> certification_frameworks.id` | |
| `code` | `text` | e.g. `WASTE-01` |
| `label_ro` | `text` | |
| `description_ro` | `text` | |
| `sort_order` | `int` | |
| `is_required` | `boolean` | |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

Constraint:

- unique on `framework_id, code`

### 16. `town_certifications`

Town-level certification state.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `town_id` | `uuid fk -> towns.id` | |
| `framework_id` | `uuid fk -> certification_frameworks.id` | |
| `status` | `certification_status` | |
| `issued_at` | `timestamptz` | nullable |
| `expires_at` | `timestamptz` | nullable |
| `submitted_at` | `timestamptz` | nullable |
| `review_started_at` | `timestamptz` | nullable |
| `reviewed_by_user_id` | `uuid fk -> users.id` | nullable |
| `decision_notes` | `text` | nullable |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

Constraint:

- unique on `town_id, framework_id`

### 17. `town_certification_submissions`

Criterion-by-criterion workflow state.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `town_certification_id` | `uuid fk -> town_certifications.id` | |
| `criterion_id` | `uuid fk -> certification_criteria.id` | |
| `status` | `criterion_submission_status` | |
| `submitted_by_user_id` | `uuid fk -> users.id` | nullable |
| `reviewed_by_user_id` | `uuid fk -> users.id` | nullable |
| `town_notes` | `text` | nullable |
| `reviewer_notes` | `text` | nullable |
| `submitted_at` | `timestamptz` | nullable |
| `reviewed_at` | `timestamptz` | nullable |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

Constraint:

- unique on `town_certification_id, criterion_id`

### 18. `submission_evidence`

Evidence attachments per criterion submission.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `submission_id` | `uuid fk -> town_certification_submissions.id` | |
| `storage_key` | `text` | |
| `file_name` | `text` | |
| `mime_type` | `text` | |
| `uploaded_by_user_id` | `uuid fk -> users.id` | |
| `created_at` | `timestamptz` | |

### 19. `audit_logs`

Cross-cutting admin action history.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `actor_user_id` | `uuid fk -> users.id` | nullable for system actions |
| `entity_type` | `text` | e.g. `alert`, `report`, `town_certification` |
| `entity_id` | `uuid` | |
| `action` | `text` | |
| `metadata` | `jsonb` | |
| `created_at` | `timestamptz` | |

Indexes:

- index on `entity_type, entity_id`
- index on `actor_user_id`

### 20. `analytics_events`

Minimal event ingestion for MVP measurement.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid pk` | |
| `user_id` | `uuid fk -> users.id` | nullable |
| `town_id` | `uuid fk -> towns.id` | nullable |
| `session_id` | `text` | nullable |
| `event_name` | `text` | |
| `properties` | `jsonb` | |
| `occurred_at` | `timestamptz` | |

Indexes:

- index on `event_name, occurred_at`
- index on `town_id, occurred_at`

## Key Relationships

- one `town` has many `alerts`, `contacts`, `reports`, `memberships`, and `user_plans`
- one `user` can belong to many towns through `town_memberships`
- one `report` has many `report_media` and `report_reviews`
- one `framework` has many `criteria`
- one `town_certification` belongs to one `town` and one `framework`
- one `town_certification` has many `town_certification_submissions`
- one `user_plan` has many `user_plan_tasks`

## Public API Design

Base path:

- `/api/v1`

Authentication:

- Bearer token for authenticated endpoints
- anonymous allowed only for selected reporting and guest subscription flows

Response conventions:

- use top-level resource objects for single fetches
- use paginated collection envelopes for lists
- use RFC7807-style error shape or a consistent custom error object

Recommended error shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The submitted payload is invalid.",
    "details": [
      {
        "field": "town_id",
        "issue": "required"
      }
    ]
  }
}
```

## Auth and Session Endpoints

### `POST /api/v1/auth/register`

Creates a resident or business-owner account.

Request:

```json
{
  "email": "user@example.com",
  "password": "strong-password",
  "full_name": "Ana Popescu",
  "preferred_language": "ro",
  "home_town_slug": "sinaia"
}
```

Response:

```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "Ana Popescu",
    "preferred_language": "ro",
    "primary_role": "resident"
  },
  "access_token": "jwt-or-session-token"
}
```

### `POST /api/v1/auth/login`

### `POST /api/v1/auth/logout`

### `GET /api/v1/me`

Returns current user plus roles and town memberships.

## Town Endpoints

### `GET /api/v1/towns`

Public directory.

Query params:

- `county`
- `certification_status`
- `q`
- `page`
- `page_size`

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "sinaia",
      "name": "Sinaia",
      "county": "Prahova",
      "certification_status": "certified",
      "short_description": "Mountain town with active BearSmart program.",
      "public_lat": 45.35,
      "public_lng": 25.55
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

### `GET /api/v1/towns/{town_slug}`

Public town profile payload for the main town page.

Includes:

- town core data
- contacts
- active alerts summary
- current certification snapshot
- top preparedness cards
- recent public reports summary

### `GET /api/v1/towns/{town_slug}/map`

Public map data.

Query params:

- `layers=alerts,reports`
- `report_type`
- `since`

Returns only public-safe geometries and metadata.

### `GET /api/v1/towns/{town_slug}/contacts`

### `GET /api/v1/towns/{town_slug}/alerts`

Public alert list for that town.

### `GET /api/v1/towns/{town_slug}/reports`

Public published reports only.

Query params:

- `type`
- `verification_status`
- `page`

### `GET /api/v1/towns/{town_slug}/preparedness-preview`

Public preview for available persona-based plans.

## Alert Subscription Endpoints

### `POST /api/v1/towns/{town_slug}/subscriptions`

Creates a town alert subscription.

Request:

```json
{
  "channel": "email",
  "email": "visitor@example.com",
  "is_temporary": true,
  "temporary_until": "2026-08-25T18:00:00Z"
}
```

Notes:

- signed-in users may omit `email`
- anonymous email subscriptions should use double opt-in

### `DELETE /api/v1/subscriptions/{subscription_id}`

### `GET /api/v1/me/subscriptions`

## Report Submission Endpoints

### `POST /api/v1/reports`

Creates a public report.

Request:

```json
{
  "town_slug": "sinaia",
  "type": "sighting",
  "description": "Bear seen near lower cable car parking area.",
  "occurred_at": "2026-08-20T06:20:00Z",
  "latitude": 45.3571,
  "longitude": 25.5474,
  "location_precision": "fuzzy_public",
  "submitter_email": "ana@example.com",
  "is_anonymous": false
}
```

Response:

```json
{
  "report": {
    "id": "uuid",
    "status": "submitted",
    "verification_status": "unverified",
    "town_slug": "sinaia",
    "type": "sighting",
    "submitted_at": "2026-08-20T06:25:00Z"
  }
}
```

Behavior:

- if lat/lng falls outside supplied town boundary, backend should reject or reassign based on validated geospatial logic
- exact coordinates stay private
- public geometry is derived by privacy rules

### `POST /api/v1/reports/{report_id}/media`

Creates an upload target or registers uploaded media.

### `GET /api/v1/me/reports`

Returns submitter-visible reports and statuses.

### `GET /api/v1/reports/{report_id}`

Authenticated submitter view or admin/moderator view depending on permissions.

## Preparedness Plan Endpoints

### `GET /api/v1/personas`

Public list of supported personas.

### `POST /api/v1/plans`

Creates or refreshes a preparedness plan.

Request:

```json
{
  "town_slug": "zarnesti",
  "persona_type": "resident",
  "season": "autumn"
}
```

Response:

```json
{
  "plan": {
    "id": "uuid",
    "town_slug": "zarnesti",
    "persona_type": "resident",
    "season": "autumn",
    "completion_percent": 0,
    "tasks": [
      {
        "id": "uuid",
        "title_ro": "Secure all garbage before evening.",
        "description_ro": "Store waste in a bear-resistant container or locked structure.",
        "state": "not_started",
        "priority_rank": 1
      }
    ]
  }
}
```

### `GET /api/v1/me/plans`

### `GET /api/v1/plans/{plan_id}`

### `PATCH /api/v1/plans/{plan_id}/tasks/{task_id}`

Request:

```json
{
  "state": "completed"
}
```

## Town Admin Endpoints

All endpoints in this section require town-scoped membership or elevated admin roles.

### `PATCH /api/v1/admin/towns/{town_id}`

Update public town profile fields.

### `POST /api/v1/admin/towns/{town_id}/alerts`

Create alert.

### `PATCH /api/v1/admin/alerts/{alert_id}`

Update draft or active alert.

### `POST /api/v1/admin/alerts/{alert_id}/publish`

Transitions alert to `active` if valid.

### `POST /api/v1/admin/alerts/{alert_id}/expire`

### `GET /api/v1/admin/towns/{town_id}/reports`

Town-scoped report queue view.

### `GET /api/v1/admin/towns/{town_id}/dashboard`

P0 dashboard summary:

- active alerts count
- submitted reports count
- published reports count
- subscription count
- certification progress count

## Moderation Endpoints

Requires `moderator` or stronger role.

### `GET /api/v1/moderation/reports`

Queue filters:

- `status`
- `type`
- `town_id`
- `verification_status`

### `POST /api/v1/moderation/reports/{report_id}/review`

Request:

```json
{
  "action": "approve",
  "resulting_status": "published",
  "resulting_verification_status": "community_confirmed",
  "public_note": "Location generalized before publication.",
  "internal_notes": "Matches two related submissions from same morning."
}
```

Backend effects:

- append `report_reviews` row
- update `reports.status`
- update `reports.verification_status`
- update `reports.public_summary` if needed
- emit audit event

### `POST /api/v1/moderation/reports/{report_id}/assign`

Assign moderator.

## Certification Endpoints

### `GET /api/v1/admin/towns/{town_id}/certification`

Returns current framework, town certification state, and per-criterion progress.

### `POST /api/v1/admin/towns/{town_id}/certification/start`

Creates or activates `town_certifications` for the current active framework.

### `PATCH /api/v1/admin/towns/{town_id}/certification/submissions/{submission_id}`

Update draft notes for a criterion submission.

### `POST /api/v1/admin/certification/submissions/{submission_id}/evidence`

Register evidence upload.

### `POST /api/v1/admin/towns/{town_id}/certification/submit`

Transitions overall town certification from `in_progress` to `submitted` if all required criteria are ready.

### `GET /api/v1/reviewer/certifications`

Reviewer queue.

### `POST /api/v1/reviewer/certifications/{town_certification_id}/decision`

Request:

```json
{
  "status": "certified",
  "decision_notes": "Pilot criteria met for 2026 framework.",
  "expires_at": "2027-12-31T23:59:59Z"
}
```

### `POST /api/v1/reviewer/submissions/{submission_id}/decision`

Per-criterion approval or change request.

## Analytics Endpoints

### `POST /api/v1/analytics/events`

Accepts front-end event ingestion for MVP metrics.

Allowed event examples:

- `town_page_viewed`
- `alert_subscribed`
- `report_submitted`
- `plan_created`
- `plan_task_completed`
- `certification_started`

### `GET /api/v1/admin/analytics/overview`

Admin-only rollup for:

- active towns
- certified towns
- alert subscriptions
- submitted reports
- published reports
- plan creation count

## Suggested Pydantic Models

These are the minimum response families worth modeling explicitly in a FastAPI codebase:

- `UserResponse`
- `CurrentSessionResponse`
- `TownListItem`
- `TownDetailResponse`
- `TownMapResponse`
- `AlertResponse`
- `AlertListResponse`
- `SubscriptionRequest`
- `SubscriptionResponse`
- `ReportCreateRequest`
- `ReportResponse`
- `ReportListResponse`
- `ReportReviewRequest`
- `PreparednessPersonaResponse`
- `PlanCreateRequest`
- `PlanResponse`
- `PlanTaskResponse`
- `CertificationSummaryResponse`
- `CriterionSubmissionResponse`
- `ReviewerDecisionRequest`
- `PaginatedResponse[T]`
- `ErrorResponse`

## Permission Rules

### Public

- can list towns
- can view town pages
- can view public alerts
- can view published public reports
- can create limited report submissions
- can create email-based alert subscriptions

### Authenticated Resident

- everything public can do
- can manage own subscriptions
- can see own submitted reports
- can create and update own preparedness plans

### Town Admin

- can update assigned town public data
- can create and publish alerts for assigned town
- can see town-scoped reports
- can manage town certification submissions

### Moderator

- can review reports across towns
- can redact or reject unsafe content
- can publish moderated reports

### Certification Reviewer

- can review town certification submissions
- can issue decision states

### Super Admin

- global read/write across all entities
- can manage frameworks and criteria
- can override certification and moderation decisions

## Core Business Rules

1. A public report can never expose exact wildlife coordinates directly.
2. An alert must have a start time and a valid town.
3. An active alert with an `ends_at` in the past must automatically become `expired`.
4. Only town admins with the proper membership role can publish alerts for a town.
5. Town certification can only be marked `submitted` when all required criteria are at least in submitted-ready state.
6. A reviewer decision on a town certification updates both `town_certifications` and the public certification snapshot on `towns`.
7. A user can have multiple plans, but only one active plan per town, persona, and season.
8. Anonymous report submissions must be rate-limited and may require stricter moderation before publication.
9. Public map endpoints must only use `public_location_geom`.
10. Every moderation and certification decision must write to `audit_logs`.

## Background Jobs

P0 should include these backend jobs:

- expire alerts when `ends_at` passes
- send subscription notifications for newly published alerts
- recompute `user_plans.completion_percent` when task states change
- derive `reports.public_location_geom` from privacy rules
- sync `towns.certification_status` from latest certification decision

## Recommended First Implementation Order

1. `users`, `towns`, `town_memberships`, auth/session endpoints
2. public town endpoints
3. alerts + subscriptions
4. reports + moderation
5. preparedness plans
6. certification workflow
7. analytics ingestion and admin summaries

## Suggested Next Artifact

The best next step after this document is to turn it into one of:

- PostgreSQL migration SQL for the P0 tables
- FastAPI `models.py` and route module skeletons
- OpenAPI YAML for the first public and admin endpoints

