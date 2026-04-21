from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .flags import current_flags
from .geo import PublicPoint, public_point
from .telemetry import track

DemoRole = Literal["public", "resident", "town_admin", "moderator", "reviewer"]
AlertSeverity = Literal["info", "advisory", "warning", "critical"]
ReportType = Literal["sighting", "attractant_issue", "road_crossing", "livestock_incident", "apiary_incident"]
TaskState = Literal["not_started", "in_progress", "completed", "skipped"]
PersonaType = Literal["resident", "tourist", "business_owner", "school", "beekeeper", "farmer"]
CertificationStatus = Literal["in_progress", "submitted", "under_review", "certified", "renewal_due"]

MVP_DIR = Path(__file__).resolve().parent / "static" / "bearsmart"


class SubscriptionRequest(BaseModel):
    email: str = Field(..., min_length=5)
    is_temporary: bool = False


class ReportCreateRequest(BaseModel):
    town_slug: str
    type: ReportType
    description: str = Field(..., min_length=8)
    location_label: str = Field(..., min_length=3)
    reporter_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    number_of_bears: int | None = Field(default=None, ge=1, le=20)
    behavior_observed: str | None = None
    attractant_type: str | None = None
    road_context: str | None = None
    photo_name: str | None = None


class PlanCreateRequest(BaseModel):
    town_slug: str
    persona_type: PersonaType


class PlanTaskUpdateRequest(BaseModel):
    state: TaskState


class AlertCreateRequest(BaseModel):
    title: str = Field(..., min_length=5)
    message: str = Field(..., min_length=10)
    severity: AlertSeverity


class ReportReviewRequest(BaseModel):
    action: Literal["approve", "reject"]
    public_note: str | None = None


class CertificationDecisionRequest(BaseModel):
    status: CertificationStatus
    decision_notes: str = Field(..., min_length=8)


class BearSmartDemoStore:
    def __init__(self) -> None:
        self._seed()

    def _seed(self) -> None:
        now = datetime.now(timezone.utc)
        self.towns = {
            "rasnov": {
                "id": "town-rasnov",
                "slug": "rasnov",
                "name": "Rasnov",
                "county": "Brasov",
                "region": "Brasov mountain corridor",
                "locality_profile": "Tourism-heavy historic foothill town",
                "tagline": "Historic mountain town pairing tourism with stronger neighborhood bear-safety systems.",
                "certification_status": "certified",
                "certification_tier": "gold",
                "safety_score": 96,
                "activity_level": "Low",
                "issued_at": (now - timedelta(days=120)).isoformat(),
                "expires_at": (now + timedelta(days=245)).isoformat(),
                "hero_summary": "A certified BearSmart town focused on waste control, tourism messaging, and fast local alerting.",
                "hero_image": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1200&q=80",
                "center": {"lat": 45.593, "lng": 25.463},
                "bounds": {"lat_min": 45.54, "lat_max": 45.64, "lng_min": 25.39, "lng_max": 25.54},
                "rules_summary": [
                    "Do not leave residential garbage outside overnight.",
                    "Use secure storage for guesthouse and restaurant food waste.",
                    "Report repeat attractant issues through the platform.",
                ],
                "safety_measures": [
                    "Mandatory bear-safe waste handling in hospitality zones",
                    "Trail-edge visitor messaging during peak season",
                    "Fast local alert escalation for repeat corridor sightings",
                ],
                "highlights": [
                    "Mandatory bear-safe waste handling in hospitality zones",
                    "Seasonal visitor messaging around trails and lodging edges",
                    "Fast alert escalation for repeat guesthouse corridor sightings",
                ],
                "news_items": [
                    {
                        "title": "Guesthouse bin retrofit complete",
                        "body": "Three hospitality clusters now use secure late-evening waste storage.",
                        "timestamp": "2d ago",
                    },
                    {
                        "title": "Workshop scheduled for foothill residents",
                        "body": "Town hall and wildlife office are hosting a practical attractant-reduction session.",
                        "timestamp": "3h ago",
                    },
                ],
                "assessment_cta": {
                    "title": "Need a property assessment?",
                    "body": "A local ranger volunteer can help identify fruit tree, compost, and waste attractants around your property.",
                    "primary_action": "Schedule Visit",
                    "secondary_action": "Download PDF Guide",
                },
                "contacts": [
                    {"label": "Emergency", "value": "112"},
                    {"label": "Local wildlife office", "value": "+40 268 555 210"},
                    {"label": "Town hall BearSmart desk", "value": "bearsmart@rasnov.ro"},
                ],
            },
            "sfantul-gheorghe": {
                "id": "town-sfantul-gheorghe",
                "slug": "sfantul-gheorghe",
                "name": "Sfantul Gheorghe",
                "county": "Covasna",
                "region": "Covasna regional corridor",
                "locality_profile": "Regional civic hub with neighborhood-first coordination",
                "tagline": "Regional town coordinating certified attractant control and public education.",
                "certification_status": "certified",
                "certification_tier": "silver",
                "safety_score": 91,
                "activity_level": "Moderate",
                "issued_at": (now - timedelta(days=45)).isoformat(),
                "expires_at": (now + timedelta(days=320)).isoformat(),
                "hero_summary": "A certified BearSmart town using town-hall coordination, education, and neighborhood reporting to reduce conflict.",
                "hero_image": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
                "center": {"lat": 45.866, "lng": 25.787},
                "bounds": {"lat_min": 45.81, "lat_max": 45.91, "lng_min": 25.72, "lng_max": 25.86},
                "rules_summary": [
                    "Keep household and market-area waste locked until pickup.",
                    "Do not feed wildlife from vehicles, yards, or balconies.",
                    "Use temporary subscriptions during seasonal bear activity peaks.",
                ],
                "safety_measures": [
                    "Neighborhood attractant reduction drive",
                    "Market district waste lockups",
                    "Resident reporting and alert workflow",
                ],
                "highlights": [
                    "Town hall-led neighborhood attractant reduction",
                    "Public education coordinated with local community channels",
                    "Certified reporting and alert workflow for residents",
                ],
                "news_items": [
                    {
                        "title": "Neighborhood briefing this evening",
                        "body": "Local coordinators are reviewing best practices for shared bins and balconies.",
                        "timestamp": "Tonight",
                    },
                    {
                        "title": "Market district inspection completed",
                        "body": "Overflow issues were resolved after a coordinated waste pickup run.",
                        "timestamp": "1d ago",
                    },
                ],
                "assessment_cta": {
                    "title": "Book a neighborhood walkthrough",
                    "body": "Town coordinators can review shared waste areas and common attractant hotspots with residents.",
                    "primary_action": "Request Walkthrough",
                    "secondary_action": "Download Checklist",
                },
                "contacts": [
                    {"label": "Emergency", "value": "112"},
                    {"label": "County wildlife office", "value": "+40 267 555 144"},
                    {"label": "Town hall", "value": "contact@sfantulgheorghe.ro"},
                ],
            },
            "busteni": {
                "id": "town-busteni",
                "slug": "busteni",
                "name": "Busteni",
                "county": "Prahova",
                "region": "Prahova valley edge",
                "locality_profile": "Residential and visitor corridor still building full certification",
                "tagline": "Residential and visitor town with road and edge-of-forest conflict risk.",
                "certification_status": "in_progress",
                "certification_tier": "candidate",
                "safety_score": 78,
                "activity_level": "Elevated",
                "issued_at": None,
                "expires_at": None,
                "hero_summary": "A town building its first certification submission around reporting, roadside risk reduction, and community education.",
                "hero_image": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1200&q=80",
                "center": {"lat": 45.414, "lng": 25.534},
                "bounds": {"lat_min": 45.36, "lat_max": 45.47, "lng_min": 25.47, "lng_max": 25.60},
                "rules_summary": [
                    "Harvest fruit promptly in season.",
                    "Do not store pet food or grilling grease outdoors.",
                    "Use the reporting tool for repeated roadside crossings.",
                ],
                "safety_measures": [
                    "Roadside crossing monitoring",
                    "Candidate certification evidence package",
                    "Visitor-facing safety messaging in progress",
                ],
                "highlights": [
                    "Roadside crossing monitoring on the northern approach",
                    "Active community education campaign under development",
                    "Candidate locality building first certification evidence package",
                ],
                "news_items": [
                    {
                        "title": "Northern approach alert refreshed",
                        "body": "Drivers are being warned about evening crossings near the forest edge.",
                        "timestamp": "4h ago",
                    },
                    {
                        "title": "School awareness session drafted",
                        "body": "Teachers and parents will receive a practical safety guide before the spring break period.",
                        "timestamp": "1d ago",
                    },
                ],
                "assessment_cta": {
                    "title": "Start your home readiness check",
                    "body": "Busteni is still building certification evidence, and resident property updates can directly reduce conflict risk.",
                    "primary_action": "Start Assessment",
                    "secondary_action": "Get Home Guide",
                },
                "contacts": [
                    {"label": "Emergency", "value": "112"},
                    {"label": "County wildlife manager", "value": "+40 244 555 501"},
                    {"label": "Town hall", "value": "office@busteni.ro"},
                ],
            },
        }
        self.alerts = [
            {
                "id": "alert-r-1",
                "town_slug": "rasnov",
                "title": "Evening waste lockdown advisory",
                "message": "Multiple food-conditioned bear reports were logged near guesthouses. Secure bins before dusk.",
                "severity": "warning",
                "status": "active",
                "starts_at": (now - timedelta(hours=6)).isoformat(),
                "ends_at": (now + timedelta(days=2)).isoformat(),
            },
            {
                "id": "alert-sg-1",
                "town_slug": "sfantul-gheorghe",
                "title": "Neighborhood attractant reminder",
                "message": "Residents should secure bins and avoid storing pet food outside during evening hours.",
                "severity": "advisory",
                "status": "active",
                "starts_at": (now - timedelta(hours=12)).isoformat(),
                "ends_at": (now + timedelta(days=4)).isoformat(),
            },
            {
                "id": "alert-b-1",
                "town_slug": "busteni",
                "title": "Road crossing hotspot near forest edge",
                "message": "Drivers should reduce speed after sunset on the northern approach road.",
                "severity": "warning",
                "status": "active",
                "starts_at": (now - timedelta(days=1)).isoformat(),
                "ends_at": (now + timedelta(days=1)).isoformat(),
            },
        ]
        self.reports = [
            {
                "id": "report-r-1",
                "town_slug": "rasnov",
                "type": "sighting",
                "description": "Bear sighted near a row of guesthouses after bins were left outside.",
                "location_label": "Guesthouse lane, south edge",
                "status": "published",
                "verification_status": "community_confirmed",
                "reporter_name": "Local resident",
                "lat": 45.548,
                "lng": 25.429,
                "created_at": (now - timedelta(hours=7)).isoformat(),
                "public_note": "Location generalized for public display.",
                "details": {"number_of_bears": 1, "behavior_observed": "Moving between guesthouse bins"},
            },
            {
                "id": "report-r-2",
                "town_slug": "rasnov",
                "type": "road_crossing",
                "description": "Bear crossed the foothill road just before sunrise near the upper switchback.",
                "location_label": "Foothill switchback",
                "status": "published",
                "verification_status": "officially_verified",
                "reporter_name": "Town ranger",
                "lat": 45.616,
                "lng": 25.507,
                "created_at": (now - timedelta(days=1, hours=2)).isoformat(),
                "public_note": "Confirmed by local wildlife office.",
                "details": {"road_context": "Low light, forest edge approach"},
            },
            {
                "id": "report-sg-1",
                "town_slug": "sfantul-gheorghe",
                "type": "attractant_issue",
                "description": "Overflowing waste enclosure beside a neighborhood market block.",
                "location_label": "Market district edge",
                "status": "submitted",
                "verification_status": "unverified",
                "reporter_name": "Community member",
                "lat": 45.858,
                "lng": 25.779,
                "created_at": (now - timedelta(hours=2)).isoformat(),
                "public_note": None,
                "details": {"attractant_type": "Overflowing communal waste enclosure"},
            },
            {
                "id": "report-sg-2",
                "town_slug": "sfantul-gheorghe",
                "type": "sighting",
                "description": "Single bear moving along a drainage edge before dusk.",
                "location_label": "North drainage corridor",
                "status": "published",
                "verification_status": "community_confirmed",
                "reporter_name": "Resident",
                "lat": 45.883,
                "lng": 25.744,
                "created_at": (now - timedelta(hours=10)).isoformat(),
                "public_note": "Generalized to reduce exact location sharing.",
                "details": {"number_of_bears": 1, "behavior_observed": "Passing through"},
            },
            {
                "id": "report-b-1",
                "town_slug": "busteni",
                "type": "road_crossing",
                "description": "Bear crossed at roadside just after dark. Drivers were braking hard.",
                "location_label": "Northern approach road",
                "status": "published",
                "verification_status": "officially_verified",
                "reporter_name": "Town ranger",
                "lat": 45.432,
                "lng": 25.521,
                "created_at": (now - timedelta(days=1, hours=4)).isoformat(),
                "public_note": "Verified by local authority.",
                "details": {"road_context": "Night driving, low visibility curve"},
            },
        ]
        self.subscriptions = [{"id": "sub-1", "town_slug": "rasnov", "email": "pilot@bearsmart.ro", "is_temporary": False}]
        self.plan_templates = {
            "resident": [
                {
                    "title": "Secure garbage before dusk",
                    "summary": "Keep waste containers latched and only place them out at the approved time.",
                    "details": "Even one evening of exposed waste can teach a bear to revisit the same street. Check lids, shared bin areas, and pickup timing with neighbors so attractants do not build up overnight.",
                    "category": "Home",
                },
                {
                    "title": "Clear food scents around the property",
                    "summary": "Remove outdoor pet food, bird seed, and barbecue residue that can pull bears toward homes.",
                    "details": "Focus on small scent sources people often forget: feeding bowls, grease trays, storage sheds, outdoor fridges, and compost areas. A clean perimeter reduces repeat visits and lowers conflict risk for the whole block.",
                    "category": "Property",
                },
                {
                    "title": "Coordinate with your street",
                    "summary": "Talk with neighbors about shared attractants and repeat problem spots.",
                    "details": "Bear-smart streets work best when everyone follows the same rhythm. If one home leaves fruit, food, or waste exposed, the whole corridor becomes more attractive and harder to manage.",
                    "category": "Community",
                },
            ],
            "tourist": [
                {
                    "title": "Start with local alerts",
                    "summary": "Check the latest activity in your destination town before setting out.",
                    "details": "Alerts can change the best route, timing, or trailhead for the day. A quick check helps you avoid recent hotspots and gives you current local guidance instead of generic advice.",
                    "category": "Planning",
                },
                {
                    "title": "Store food inside secure lodging",
                    "summary": "Keep all food and scented items inside, not on balconies, cars, or outdoor tables.",
                    "details": "Visitors often create conflict unintentionally by leaving coolers, snacks, or garbage outside overnight. Lodging edges and parking areas are some of the first places bears learn to investigate.",
                    "category": "Lodging",
                },
                {
                    "title": "Know your local contacts before hiking",
                    "summary": "Save emergency and wildlife numbers before you head into forest-edge areas.",
                    "details": "If you have a sighting or unsafe encounter, you should not be searching for numbers after the fact. Keep local contacts accessible and tell someone your route when leaving town.",
                    "category": "Outdoors",
                },
            ],
            "business_owner": [
                {
                    "title": "Audit waste storage and pickup timing",
                    "summary": "Check that bins, grease, and back-of-house waste stay secure through the evening period.",
                    "details": "Hospitality and food businesses create strong scent trails when collection timing slips. Review container integrity, overflow handling, and late-night cleanup so wildlife does not associate the site with easy calories.",
                    "category": "Operations",
                },
                {
                    "title": "Train staff on guest messaging",
                    "summary": "Make sure every team member can give simple, consistent BearSmart advice.",
                    "details": "Guests often ask front-desk or service staff what is safe. Short scripts about waste, parking, food storage, and reporting reduce mixed messages and help the town keep a consistent safety culture.",
                    "category": "Staff",
                },
                {
                    "title": "Track fixes for certification readiness",
                    "summary": "Document what was changed and when so you can support town-wide certification efforts.",
                    "details": "Simple evidence like bin upgrades, signage, and training logs helps local coordinators show progress. It also makes recurring issues easier to review after the season ends.",
                    "category": "Documentation",
                },
            ],
            "school": [
                {
                    "title": "Share age-appropriate safety guidance",
                    "summary": "Keep staff and students aligned on simple, repeatable bear-safety rules.",
                    "details": "Children need short, memorable instructions, while staff need slightly deeper response guidance. Use the same language across classrooms, recess supervisors, and parent communication.",
                    "category": "Staff",
                },
                {
                    "title": "Review outdoor supervision practices",
                    "summary": "Check arrival, dismissal, recess, and edge-of-property routines.",
                    "details": "Most school risk comes from routine transitions, not special events. Confirm supervision coverage, waste handling, and how staff escalate sightings during the day.",
                    "category": "Campus",
                },
                {
                    "title": "Plan a family awareness moment",
                    "summary": "Send one clear seasonal guide to families before high-activity periods.",
                    "details": "Parents reinforce school safety when they know what to watch for at home, on walking routes, and around shared waste areas. One short seasonal message goes a long way.",
                    "category": "Families",
                },
            ],
            "beekeeper": [
                {
                    "title": "Inspect fencing and power",
                    "summary": "Check grounding, voltage, and weak points before activity increases.",
                    "details": "A fence that looks intact can still fail if grounding, vegetation, or battery condition is off. Quick regular checks are cheaper and more effective than reacting after a breach.",
                    "category": "Apiary",
                },
                {
                    "title": "Log repeated movement near hives",
                    "summary": "Track timing, direction, and any signs of repeated animal interest around the site.",
                    "details": "A simple record helps you spot patterns and show escalation to local coordinators if the same corridor is used again and again.",
                    "category": "Monitoring",
                },
                {
                    "title": "Report hotspots early",
                    "summary": "Share repeated pressure points with the town before damage escalates.",
                    "details": "If several beekeepers or nearby residents are noticing the same movement corridor, early reporting can shape alerts and support before a major incident occurs.",
                    "category": "Coordination",
                },
            ],
            "farmer": [
                {
                    "title": "Secure feed and waste areas",
                    "summary": "Reduce strong scent sources around storage, feeding, and disposal zones.",
                    "details": "Feed rooms, carcass areas, and waste piles can create repeat attraction if they are not managed consistently. Focus on the places that hold smell longest, not just the places you see most often.",
                    "category": "Farmyard",
                },
                {
                    "title": "Review overnight controls",
                    "summary": "Check gates, lighting, fencing, and storage routines before dusk.",
                    "details": "Even small gaps in a nightly routine can train wildlife to revisit a working property. Build a close-down pattern that can be repeated even on busy days.",
                    "category": "Perimeter",
                },
                {
                    "title": "Document repeated incidents",
                    "summary": "Keep notes on recurring movement, pressure points, and near misses.",
                    "details": "Detailed reporting helps local coordinators understand whether activity is isolated or part of a broader corridor pattern affecting multiple properties.",
                    "category": "Reporting",
                },
            ],
        }
        self.plans: dict[str, dict] = {}
        self.certifications = {
            "rasnov": {
                "town_slug": "rasnov",
                "framework_version": "RO-2026-v1",
                "status": "certified",
                "decision_notes": "Pilot town met required municipal criteria and maintains active alerts.",
                "criteria": [
                    {"code": "WASTE-01", "label": "Bear-resistant waste handling", "status": "approved"},
                    {"code": "EDU-01", "label": "Resident education program", "status": "approved"},
                    {"code": "ALERT-01", "label": "Operational alert workflow", "status": "approved"},
                ],
            },
            "sfantul-gheorghe": {
                "town_slug": "sfantul-gheorghe",
                "framework_version": "RO-2026-v1",
                "status": "certified",
                "decision_notes": "Town completed required attractant control, public education, and alert workflow criteria.",
                "criteria": [
                    {"code": "WASTE-01", "label": "Bear-resistant waste handling", "status": "approved"},
                    {"code": "EDU-01", "label": "Resident education program", "status": "approved"},
                    {"code": "ALERT-01", "label": "Operational alert workflow", "status": "approved"},
                ],
            },
            "busteni": {
                "town_slug": "busteni",
                "framework_version": "RO-2026-v1",
                "status": "in_progress",
                "decision_notes": "Town is building its first certification package around road safety and attractant reduction.",
                "criteria": [
                    {"code": "WASTE-01", "label": "Bear-resistant waste handling", "status": "draft"},
                    {"code": "EDU-01", "label": "Resident education program", "status": "submitted"},
                    {"code": "ALERT-01", "label": "Operational alert workflow", "status": "draft"},
                ],
            },
        }
        self.network_impact = {
            "community_count": 3,
            "acres_protected": "186K",
            "trend_label": "Conflict incidents trend",
            "trend_years": ["2022", "2023", "2024", "2025", "2026"],
            "trend_values": [92, 81, 66, 53, 41],
            "note": "Pilot localities with coordinated waste control and alert workflows are showing a steady reduction in reported conflict incidents.",
        }
        self.community_feed = {
            "pinned_alert": {
                "title": "Pinned: Elevated roadside crossings near Busteni",
                "body": "Drivers should slow down after sunset on the northern approach. Residents are asked to report repeated movement along the forest edge.",
                "primary_action": "View Map Location",
                "secondary_action": "Safety Protocols",
            },
            "posts": [
                {
                    "id": "post-1",
                    "author": "Marcus Toma",
                    "role": "Certified Ranger",
                    "time_ago": "2h ago",
                    "title": "Electric fencing check for orchard edge properties",
                    "body": "We tested several orchard-edge fence lines this morning. Anything below the recommended voltage needs immediate maintenance before fruit season peaks.",
                    "image": "https://images.unsplash.com/photo-1501004318641-b39e6451bec6?auto=format&fit=crop&w=1200&q=80",
                    "likes": 24,
                    "comments": 8,
                },
                {
                    "id": "post-2",
                    "author": "Sarah Ionescu",
                    "role": "Resident",
                    "time_ago": "5h ago",
                    "title": "Berry season is starting earlier than expected",
                    "body": "It looks like food pressure is shifting activity closer to town earlier this year. Keep bird feeders down and shared bins locked through the weekend.",
                    "location_label": "Silver Creek corridor",
                },
            ],
            "heroes": [
                {"name": "Erik Chen", "achievement": "12 sightings verified", "points": 2450},
                {"name": "Aisha Okafor", "achievement": "8 safety workshops", "points": 1920},
                {"name": "Lucas Bennett", "achievement": "Trail cleanup lead", "points": 1100},
            ],
            "workshops": [
                {
                    "title": "Bear Spray 101: Inert Practice",
                    "schedule": "Saturday, Apr 12 • 10:00",
                    "details": "Learn wind allowance, safe draw technique, and range with inert training cans.",
                    "availability": "12 spots left",
                },
                {
                    "title": "Electric Fence Maintenance",
                    "schedule": "Wednesday, Apr 16 • 18:30",
                    "details": "Check grounding, voltage, and seasonal maintenance for orchard and apiary fences.",
                    "availability": "Online session",
                },
            ],
            "cta": {
                "title": "Be a wilderness hero",
                "body": "Join local patrols, event crews, and awareness campaigns that help keep residents and bears safer.",
                "action": "Apply Now",
            },
        }

    def _town_or_404(self, town_slug: str) -> dict:
        town = self.towns.get(town_slug)
        if not town:
            raise HTTPException(status_code=404, detail="Town not found.")
        return town

    def _active_alerts(self, town_slug: str) -> list[dict]:
        return [deepcopy(a) for a in self.alerts if a["town_slug"] == town_slug and a["status"] == "active"]

    def _apply_geo_fuzz(self, report: dict) -> dict:
        """Attach fuzzed public_lat/public_lng/public_radius_m to a report.

        Threat T5 mitigation: precise coordinates are kept server-side for
        authorities but never leaked by public-facing readers.
        """
        if not current_flags().is_enabled("geo_fuzz"):
            # Preserve the original behaviour while the flag is disabled so
            # operators can toggle off in dev; public routes still set the
            # radius to ``None`` so clients always see the new contract.
            report["public_lat"] = report.get("lat")
            report["public_lng"] = report.get("lng")
            report["public_radius_m"] = None
            return report
        town = self.towns.get(report["town_slug"])
        center = (town["center"]["lat"], town["center"]["lng"]) if town else None
        fuzzed: PublicPoint = public_point(
            report.get("lat"),
            report.get("lng"),
            report["type"],
            town_center=center,
            jitter_seed=hash(report["id"]) & 0xFFFFFF,
        )
        report["public_lat"] = fuzzed.lat
        report["public_lng"] = fuzzed.lng
        report["public_radius_m"] = fuzzed.radius_m
        if fuzzed.stripped or fuzzed.radius_m is None and report["type"] in {"livestock_incident", "apiary_incident"}:
            report["lat"] = None
            report["lng"] = None
        else:
            # Precise coords are for authorities only. Strip before returning.
            report["lat"] = fuzzed.lat
            report["lng"] = fuzzed.lng
        return report

    def _published_reports(self, town_slug: str) -> list[dict]:
        return [
            self._apply_geo_fuzz(deepcopy(r))
            for r in self.reports
            if r["town_slug"] == town_slug and r["status"] == "published"
        ]

    def _criteria_summary(self, town_slug: str) -> str:
        certification = self.certifications[town_slug]
        approved = len([item for item in certification["criteria"] if item["status"] == "approved"])
        return f"{approved}/{len(certification['criteria'])}"

    def list_towns(self) -> list[dict]:
        items = []
        for town in self.towns.values():
            items.append(
                {
                    "id": town["id"],
                    "slug": town["slug"],
                    "name": town["name"],
                    "county": town["county"],
                    "region": town["region"],
                    "locality_profile": town["locality_profile"],
                    "tagline": town["tagline"],
                    "hero_summary": town["hero_summary"],
                    "hero_image": town["hero_image"],
                    "highlights": town["highlights"],
                    "activity_level": town["activity_level"],
                    "safety_measures": town["safety_measures"],
                    "certification_status": town["certification_status"],
                    "certification_tier": town["certification_tier"],
                    "safety_score": town["safety_score"],
                    "active_alert_count": sum(
                        1 for alert in self.alerts if alert["town_slug"] == town["slug"] and alert["status"] == "active"
                    ),
                    "published_report_count": sum(
                        1 for report in self.reports if report["town_slug"] == town["slug"] and report["status"] == "published"
                    ),
                    "subscriber_count": sum(1 for sub in self.subscriptions if sub["town_slug"] == town["slug"]),
                }
            )
        return items

    def get_town(self, town_slug: str) -> dict:
        town = deepcopy(self._town_or_404(town_slug))
        alerts = self._active_alerts(town_slug)
        reports = self._published_reports(town_slug)
        certification = deepcopy(self.certifications[town_slug])
        return {
            "town": town,
            "alerts": alerts,
            "reports": reports,
            "certification": certification,
            "stats": {
                "active_alert_count": len(alerts),
                "public_report_count": len(reports),
                "subscriber_count": sum(1 for sub in self.subscriptions if sub["town_slug"] == town_slug),
                "criteria_summary": self._criteria_summary(town_slug),
            },
        }

    def get_map(self, town_slug: str) -> dict:
        town = self._town_or_404(town_slug)
        features = []
        for report in self.reports:
            if report["town_slug"] != town_slug or report["status"] != "published":
                continue
            fuzzed = self._apply_geo_fuzz(deepcopy(report))
            features.append(
                {
                    "id": fuzzed["id"],
                    "kind": fuzzed["type"],
                    "label": fuzzed["location_label"],
                    "lat": fuzzed["public_lat"],
                    "lng": fuzzed["public_lng"],
                    "public_lat": fuzzed["public_lat"],
                    "public_lng": fuzzed["public_lng"],
                    "public_radius_m": fuzzed["public_radius_m"],
                    "description": fuzzed["description"],
                    "verification_status": fuzzed["verification_status"],
                    "town_slug": fuzzed["town_slug"],
                    "public_note": fuzzed["public_note"],
                    "details": fuzzed.get("details", {}),
                }
            )
        return {"town_slug": town_slug, "center": town["center"], "bounds": town["bounds"], "features": features}

    def get_map_overview(self) -> dict:
        towns = []
        for town in self.towns.values():
            bounds = town["bounds"]
            polygon = [
                [bounds["lat_min"], bounds["lng_min"]],
                [bounds["lat_min"], bounds["lng_max"]],
                [bounds["lat_max"], bounds["lng_max"]],
                [bounds["lat_max"], bounds["lng_min"]],
            ]
            towns.append(
                {
                    "id": town["id"],
                    "slug": town["slug"],
                    "name": town["name"],
                    "county": town["county"],
                    "hero_image": town["hero_image"],
                    "safety_score": town["safety_score"],
                    "activity_level": town["activity_level"],
                    "certification_status": town["certification_status"],
                    "certification_tier": town["certification_tier"],
                    "center": town["center"],
                    "polygon": polygon,
                    "zone_color": "#2e8b57" if town["certification_status"] == "certified" else "#c58b2a",
                }
            )
        reports = []
        for report in self.reports:
            if report["status"] != "published":
                continue
            fuzzed = self._apply_geo_fuzz(deepcopy(report))
            reports.append(
                {
                    "id": fuzzed["id"],
                    "town_slug": fuzzed["town_slug"],
                    "type": fuzzed["type"],
                    "description": fuzzed["description"],
                    "location_label": fuzzed["location_label"],
                    "verification_status": fuzzed["verification_status"],
                    "lat": fuzzed["public_lat"],
                    "lng": fuzzed["public_lng"],
                    "public_lat": fuzzed["public_lat"],
                    "public_lng": fuzzed["public_lng"],
                    "public_radius_m": fuzzed["public_radius_m"],
                    "created_at": fuzzed["created_at"],
                    "public_note": fuzzed["public_note"],
                    "details": fuzzed.get("details", {}),
                }
            )
        return {"towns": towns, "reports": reports}

    def get_network_impact(self) -> dict:
        return deepcopy(self.network_impact)

    def get_community_feed(self) -> dict:
        return deepcopy(self.community_feed)

    def get_public_dashboard(self, town_slug: str) -> dict:
        town = deepcopy(self._town_or_404(town_slug))
        alerts = self._active_alerts(town_slug)
        reports = self._published_reports(town_slug)
        status_label = "Green / Low"
        status_note = "No sightings in the last 48 hours."
        if town["activity_level"] == "Moderate":
            status_label = "Amber / Moderate"
            status_note = "Monitor evening attractants and shared waste areas."
        if town["activity_level"] == "Elevated":
            status_label = "Orange / Elevated"
            status_note = "Recent activity means residents should review routes and home readiness."
        return {
            "town": town,
            "status": {"label": status_label, "note": status_note, "activity_level": town["activity_level"]},
            "news_items": deepcopy(town["news_items"]),
            "assessment_cta": deepcopy(town["assessment_cta"]),
            "stats": {
                "active_alerts": len(alerts),
                "sightings_7d": len(reports),
                "safety_level": town["activity_level"],
            },
            "nearby_reports": reports,
        }

    def create_subscription(self, town_slug: str, payload: SubscriptionRequest) -> dict:
        self._town_or_404(town_slug)
        item = {"id": str(uuid4()), "town_slug": town_slug, "email": payload.email, "is_temporary": payload.is_temporary}
        self.subscriptions.append(item)
        return item

    def create_report(self, payload: ReportCreateRequest) -> dict:
        town = self._town_or_404(payload.town_slug)
        lat = payload.latitude if payload.latitude is not None else town["center"]["lat"] + 0.01
        lng = payload.longitude if payload.longitude is not None else town["center"]["lng"] + 0.01
        report = {
            "id": str(uuid4()),
            "town_slug": payload.town_slug,
            "type": payload.type,
            "description": payload.description,
            "location_label": payload.location_label,
            "status": "submitted",
            "verification_status": "unverified",
            "reporter_name": payload.reporter_name or "Community member",
            "lat": lat,
            "lng": lng,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "public_note": None,
            "details": {
                "number_of_bears": payload.number_of_bears,
                "behavior_observed": payload.behavior_observed,
                "attractant_type": payload.attractant_type,
                "road_context": payload.road_context,
                "photo_name": payload.photo_name,
            },
        }
        self.reports.insert(0, report)
        return report

    def list_public_reports(self, town_slug: str) -> list[dict]:
        self._town_or_404(town_slug)
        return self._published_reports(town_slug)

    def list_moderation_queue(self) -> list[dict]:
        now = datetime.now(timezone.utc)
        items: list[dict] = []
        for report in self.reports:
            if report["status"] not in {"submitted", "under_review"}:
                continue
            item = deepcopy(report)
            try:
                created_at = datetime.fromisoformat(item["created_at"])
            except ValueError:
                items.append(item)
                continue
            age = max(0.0, (now - created_at).total_seconds())
            item["age_seconds"] = age
            item["age_hours"] = round(age / 3600.0, 2)
            items.append(item)
        return items

    def moderation_stats(self) -> dict:
        """Return median + p90 age-in-queue plus SLA breach breakdown."""
        queue = self.list_moderation_queue()
        ages = sorted(item.get("age_seconds", 0.0) for item in queue)
        sla_in_season = 6 * 3600
        sla_off_season = 24 * 3600

        def _percentile(values: list[float], pct: float) -> float:
            if not values:
                return 0.0
            if len(values) == 1:
                return values[0]
            idx = max(0, min(len(values) - 1, int(round((pct / 100.0) * (len(values) - 1)))))
            return values[idx]

        return {
            "queue_size": len(queue),
            "median_age_seconds": _percentile(ages, 50),
            "p90_age_seconds": _percentile(ages, 90),
            "sla_in_season_seconds": sla_in_season,
            "sla_off_season_seconds": sla_off_season,
            "over_sla_in_season": sum(1 for a in ages if a > sla_in_season),
            "over_sla_off_season": sum(1 for a in ages if a > sla_off_season),
        }

    def review_report(self, report_id: str, payload: ReportReviewRequest) -> dict:
        for report in self.reports:
            if report["id"] == report_id:
                if payload.action == "approve":
                    report["status"] = "published"
                    report["verification_status"] = "community_confirmed"
                    report["public_note"] = payload.public_note or "Published after moderation review."
                else:
                    report["status"] = "rejected"
                    report["public_note"] = payload.public_note or "Rejected after moderation review."
                track(
                    "moderation_decision_made",
                    report_id=report_id,
                    action=payload.action,
                    town_slug=report["town_slug"],
                )
                return deepcopy(report)
        raise HTTPException(status_code=404, detail="Report not found.")

    def create_plan(self, payload: PlanCreateRequest) -> dict:
        town = self._town_or_404(payload.town_slug)
        plan_id = str(uuid4())
        template_items = self.plan_templates[payload.persona_type]
        plan = {
            "id": plan_id,
            "town_slug": payload.town_slug,
            "persona_type": payload.persona_type,
            "completion_percent": 0,
            "tasks": [
                {
                    "id": str(uuid4()),
                    "title": item["title"],
                    "summary": item["summary"],
                    "details": f"{item['details']} In {town['name']}, align this with local guidance and current alerts before marking it complete.",
                    "category": item["category"],
                    "state": "not_started",
                }
                for item in template_items
            ],
        }
        self.plans[plan_id] = plan
        return deepcopy(plan)

    def update_plan_task(self, plan_id: str, task_id: str, payload: PlanTaskUpdateRequest) -> dict:
        plan = self.plans.get(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found.")
        for task in plan["tasks"]:
            if task["id"] == task_id:
                task["state"] = payload.state
                break
        else:
            raise HTTPException(status_code=404, detail="Task not found.")
        completed = sum(1 for task in plan["tasks"] if task["state"] == "completed")
        plan["completion_percent"] = round((completed / len(plan["tasks"])) * 100)
        return deepcopy(plan)

    def get_admin_dashboard(self, town_slug: str) -> dict:
        self._town_or_404(town_slug)
        town_reports = [r for r in self.reports if r["town_slug"] == town_slug]
        certification = self.certifications[town_slug]
        return {
            "town_slug": town_slug,
            "metrics": {
                "active_alerts": sum(1 for alert in self.alerts if alert["town_slug"] == town_slug and alert["status"] == "active"),
                "submitted_reports": sum(1 for report in town_reports if report["status"] == "submitted"),
                "published_reports": sum(1 for report in town_reports if report["status"] == "published"),
                "subscribers": sum(1 for sub in self.subscriptions if sub["town_slug"] == town_slug),
                "approved_criteria": sum(1 for item in certification["criteria"] if item["status"] == "approved"),
                "total_criteria": len(certification["criteria"]),
            },
        }

    def create_alert(self, town_slug: str, payload: AlertCreateRequest) -> dict:
        self._town_or_404(town_slug)
        alert = {
            "id": str(uuid4()),
            "town_slug": town_slug,
            "title": payload.title,
            "message": payload.message,
            "severity": payload.severity,
            "status": "active",
            "starts_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        }
        self.alerts.insert(0, alert)
        return deepcopy(alert)

    def get_certification(self, town_slug: str) -> dict:
        self._town_or_404(town_slug)
        return deepcopy(self.certifications[town_slug])

    def review_certification(self, town_slug: str, payload: CertificationDecisionRequest) -> dict:
        self._town_or_404(town_slug)
        cert = self.certifications[town_slug]
        cert["status"] = payload.status
        cert["decision_notes"] = payload.decision_notes
        self.towns[town_slug]["certification_status"] = payload.status
        if payload.status == "certified":
            self.towns[town_slug]["issued_at"] = datetime.now(timezone.utc).isoformat()
            self.towns[town_slug]["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        return deepcopy(cert)


store = BearSmartDemoStore()
router = APIRouter(prefix="/api/bearsmart", tags=["bearsmart-mvp"])


def _role_from_headers(x_demo_role: str | None) -> DemoRole:
    role = (x_demo_role or "public").strip().lower()
    if role not in {"public", "resident", "town_admin", "moderator", "reviewer"}:
        raise HTTPException(status_code=400, detail="Invalid demo role.")
    return role  # type: ignore[return-value]


def _require_role(role: DemoRole, allowed: set[DemoRole]) -> None:
    if role not in allowed:
        raise HTTPException(status_code=403, detail="This demo action is not available for the current role.")


@router.get("/session")
def get_demo_session(x_demo_role: str | None = Header(default=None)) -> dict:
    role = _role_from_headers(x_demo_role)
    return {"role": role, "available_roles": ["public", "resident", "town_admin", "moderator", "reviewer"]}


@router.get("/towns")
def list_towns() -> dict:
    return {"items": store.list_towns()}


@router.get("/map")
def get_map_overview() -> dict:
    return store.get_map_overview()


@router.get("/network-impact")
def get_network_impact() -> dict:
    return store.get_network_impact()


@router.get("/community")
def get_community_feed() -> dict:
    return store.get_community_feed()


@router.get("/dashboard/{town_slug}")
def get_dashboard_data(town_slug: str) -> dict:
    return store.get_public_dashboard(town_slug)


@router.get("/towns/{town_slug}")
def get_town(town_slug: str) -> dict:
    return store.get_town(town_slug)


@router.get("/towns/{town_slug}/map")
def get_town_map(town_slug: str) -> dict:
    return store.get_map(town_slug)


@router.get("/towns/{town_slug}/reports")
def get_town_reports(town_slug: str) -> dict:
    return {"items": store.list_public_reports(town_slug)}


@router.post("/towns/{town_slug}/subscriptions")
def subscribe_to_town(town_slug: str, payload: SubscriptionRequest) -> dict:
    return {"subscription": store.create_subscription(town_slug, payload), "message": "Subscription saved for demo preview."}


@router.post("/reports")
def create_report(payload: ReportCreateRequest) -> dict:
    return {"report": store.create_report(payload), "message": "Report submitted and sent to moderation."}


@router.get("/moderation/reports")
def moderation_reports(x_demo_role: str | None = Header(default=None)) -> dict:
    role = _role_from_headers(x_demo_role)
    _require_role(role, {"moderator"})
    return {"items": store.list_moderation_queue()}


@router.get("/moderation/stats")
def moderation_stats(x_demo_role: str | None = Header(default=None)) -> dict:
    role = _role_from_headers(x_demo_role)
    _require_role(role, {"moderator"})
    return store.moderation_stats()


@router.post("/moderation/reports/{report_id}/review")
def moderation_review(report_id: str, payload: ReportReviewRequest, x_demo_role: str | None = Header(default=None)) -> dict:
    role = _role_from_headers(x_demo_role)
    _require_role(role, {"moderator"})
    return {"report": store.review_report(report_id, payload)}


@router.post("/plans")
def create_plan(payload: PlanCreateRequest) -> dict:
    return {"plan": store.create_plan(payload)}


@router.patch("/plans/{plan_id}/tasks/{task_id}")
def update_plan_task(plan_id: str, task_id: str, payload: PlanTaskUpdateRequest) -> dict:
    return {"plan": store.update_plan_task(plan_id, task_id, payload)}


@router.get("/admin/towns/{town_slug}/dashboard")
def get_admin_dashboard(town_slug: str, x_demo_role: str | None = Header(default=None)) -> dict:
    role = _role_from_headers(x_demo_role)
    _require_role(role, {"town_admin"})
    return store.get_admin_dashboard(town_slug)


@router.post("/admin/towns/{town_slug}/alerts")
def create_admin_alert(town_slug: str, payload: AlertCreateRequest, x_demo_role: str | None = Header(default=None)) -> dict:
    role = _role_from_headers(x_demo_role)
    _require_role(role, {"town_admin"})
    return {"alert": store.create_alert(town_slug, payload)}


@router.get("/reviewer/towns/{town_slug}/certification")
def get_certification(town_slug: str, x_demo_role: str | None = Header(default=None)) -> dict:
    role = _role_from_headers(x_demo_role)
    _require_role(role, {"reviewer", "town_admin"})
    return store.get_certification(town_slug)


@router.post("/reviewer/towns/{town_slug}/certification/decision")
def certification_decision(
    town_slug: str,
    payload: CertificationDecisionRequest,
    x_demo_role: str | None = Header(default=None),
) -> dict:
    role = _role_from_headers(x_demo_role)
    _require_role(role, {"reviewer"})
    return {"certification": store.review_certification(town_slug, payload)}


def bearsmart_index() -> FileResponse:
    return FileResponse(MVP_DIR / "map.html")


def bearsmart_map_index() -> FileResponse:
    return FileResponse(MVP_DIR / "map.html")


def bearsmart_localities_index() -> FileResponse:
    return FileResponse(MVP_DIR / "localities.html")


def bearsmart_dashboard_index() -> FileResponse:
    return FileResponse(MVP_DIR / "dashboard.html")


def bearsmart_report_index() -> FileResponse:
    return FileResponse(MVP_DIR / "report.html")


def bearsmart_community_index() -> FileResponse:
    return FileResponse(MVP_DIR / "community.html")


def bearsmart_ops_index() -> FileResponse:
    return FileResponse(MVP_DIR / "ops.html")
