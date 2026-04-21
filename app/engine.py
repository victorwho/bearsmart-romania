
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from fastapi import HTTPException

from .models import (
    PhaseRoutine,
    ProductResponse,
    ProductSearchRequest,
    ProductSearchResponse,
    RetailerLinkListResponse,
    RetailerLinkResponse,
    RoutineRequest,
    RoutineResponse,
    SlotProduct,
)

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "database13_retaileri_moment2_IDProdus_NuCombinaCu_IDs.json"
LINKS_PATH = Path(__file__).resolve().parents[1] / "data" / "retailer_links.json"

RETAILERS: List[str] = [
    "DM",
    "Farmacia Tei",
    "Bebe Tei",
    "eMag",
    "Dr. Max",
    "Douglas",
    "Sephora",
    "Marionnaud",
    "Kaufland",
    "Auchan",
    "Carrefour",
]

SUPPORTED_NEEDS = [
    "Ten tern",
    "Deshidratare",
    "Acnee",
    "Ten neuniform",
    "Imperfectiuni",
    "Riduri/linii fine",
    "Ochi obositi/umflati",
    "Roseata",
    "Pete pigmentare",
]

SLOT_ORDER = ["Curatare", "Ochi", "Ser", "Produs problema", "Hidratare", "Soare"]
PHASE_SLOT_ORDER = {
    "AM": ["Curatare", "Ochi", "Ser", "Produs problema", "Hidratare", "Soare"],
    "PM": ["Curatare", "Ochi", "Ser", "Produs problema", "Hidratare"],
}

RETINOL_DISCLAIMER = (
    "Produsele cu retinol nu se introduc direct în utilizare zilnică, mai ales dacă nu ai mai folosit "
    "retinoizi anterior. Pentru o adaptare corectă a pielii, începe cu 2- 3 aplicări pe săptămână, în seri "
    "neconsecutive, timp de 2 săptămâni. În săptămânile următoare, frecvența poate fi crescută treptat "
    "(de exemplu o seară da, una nu), în funcție de toleranța pielii. În perioada utilizării retinolului, "
    "aplicarea zilnică, dimineața, a unui produs cu protecție solară este esențială."
)

RETINOL_SCORE_THRESHOLD = 60

RETINOL_ALLOWED_61_65 = {
    "Revox Just retinol toner 250ml",
    "Revox Just retinol in squalane H2O - free solution age control 30ml",
}

RETINOL_ALLOWED_65_PLUS = {
    "Revox Retinol Eye-Gel Anti-Wrinkle Concentrate 30ml",
    "Revox Retinol Daily Protection spf 20 50ml",
    "Revox Retinol Serum Unifying Regenerator 30ml",
}

NEED_ALIASES = {
    "deshidratre": "Deshidratare",
    "imperfectiuni: acnee": "Imperfectiuni",
    "pori dilatati": "Imperfectiuni",
}

SKIN_ALIASES = {
    "mixt": "Ten Mixt",
    "ten mixt": "Ten Mixt",
    "gras": "Gras",
    "uscat": "Uscat",
    "sensibil": "Sensibil",
    "normal": "Normal",
}

TIP_ALIAS = {
    "revox sun": "Revox Sun",
    "face serum": "Face serum",
    "face cream": "Face cream",
    "cleanser": "Cleanser",
    "eye care": "Eye care",
    "exfoliator": "Exfoliator",
    "toner": "Toner",
    "toner exfoliator": "Toner Exfoliator",
    "lip care": "Lip care",
    "face mask": "Face mask",
}

RETAILER_ALIASES = {
    "tei": "Farmacia Tei",
    "farmacia tei": "Farmacia Tei",
    "bebetei": "Bebe Tei",
    "bebe tei": "Bebe Tei",
    "marrionnaud": "Marionnaud",
    "marionnaud": "Marionnaud",
    "dm": "DM",
    "emag": "eMag",
    "dr. max": "Dr. Max",
    "douglas": "Douglas",
    "sephora": "Sephora",
    "kaufland": "Kaufland",
    "auchan": "Auchan",
    "carrefour": "Carrefour",
}


@dataclass
class PhaseState:
    phase: str
    selected: Dict[str, dict] = field(default_factory=dict)
    missing_slots: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    selection_order: List[Tuple[int, str]] = field(default_factory=list)

    def assign(self, slot: str, product: dict, sequence_id: int) -> None:
        self.selected[slot] = product
        self.selection_order = [(seq, existing_slot) for seq, existing_slot in self.selection_order if existing_slot != slot]
        self.selection_order.append((sequence_id, slot))
        self.remove_missing(slot)

    def remove(self, slot: str) -> Optional[dict]:
        removed = self.selected.pop(slot, None)
        self.selection_order = [(seq, existing_slot) for seq, existing_slot in self.selection_order if existing_slot != slot]
        return removed

    def mark_missing(self, slot: str) -> None:
        if slot not in self.missing_slots:
            self.missing_slots.append(slot)

    def remove_missing(self, slot: str) -> None:
        self.missing_slots = [value for value in self.missing_slots if value != slot]


def _split_semicolon_text(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in re.split(r"\s*;\s*", value) if part and part.strip()]


def _normalize_need(value: str) -> str:
    v = value.strip()
    return NEED_ALIASES.get(v.lower(), v)


def _parse_needs(value: Optional[str]) -> List[str]:
    items = []
    for item in _split_semicolon_text(value):
        normalized = _normalize_need(item)
        if normalized and normalized not in items:
            items.append(normalized)
    return items


def _parse_skin_types(value: Optional[str]) -> List[str]:
    if not value:
        return []
    raw_items = [part.strip() for part in re.split(r"\s*,\s*", value) if part.strip()]
    normalized: List[str] = []
    for item in raw_items:
        candidate = SKIN_ALIASES.get(item.lower(), item)
        if candidate not in normalized:
            normalized.append(candidate)
    return normalized


def _normalize_text(value: Optional[str]) -> str:
    lowered = str(value or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", lowered)
    without_diacritics = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_diacritics).strip()


def _normalize_moment(value: Optional[str]) -> str:
    return _normalize_text(value)


def _contains_caffeine(text: str) -> bool:
    normalized = _normalize_text(text)
    return any(token in normalized for token in ("caffeine", "cafeina", "cofeina", "cafeine"))


def _is_yes(value: Optional[str]) -> bool:
    return str(value).strip().lower() == "da"


def get_allowed_phases(product: dict) -> Set[str]:
    if product.get("soare_bool"):
        return {"AM"}
    if product.get("contains_caffeine"):
        return {"AM"}
    if product.get("retinol_bool"):
        return {"PM"}
    if product.get("doar_seara_bool"):
        return {"PM"}

    moment = _normalize_moment(product.get("moment_raw"))
    if moment == "dimineata":
        return {"AM"}
    if moment == "seara":
        return {"PM"}
    if moment == "dimineata si seara":
        return {"AM", "PM"}
    return set()


def _canonicalize_retailer(value: str) -> str:
    if value in RETAILERS:
        return value
    normalized = str(value).strip().lower()
    return RETAILER_ALIASES.get(normalized, value)


class RevoxEngine:
    def __init__(self) -> None:
        self.products = self._load_products()
        self.products_by_id = {product["IDProdus"]: product for product in self.products}
        self.retailers = list(RETAILERS)
        self.retailer_links = self._load_retailer_links()
        self.product_count = len(self.products)

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_products() -> Tuple[dict, ...]:
        with DATA_PATH.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        normalized = []
        for item in raw:
            product = {
                **item,
                "needs_list": _parse_needs(item.get("NevoiPiele")),
                "skin_types_list": _parse_skin_types(item.get("TipPiele")),
                "retailers_list": list(item.get("RetaileriDisponibili") or []),
                "moment_raw": item.get("Moment utilizare", ""),
                "doar_seara_bool": _is_yes(item.get("Doar seara")),
                "tip_produs_norm": TIP_ALIAS.get(str(item.get("TipProdus", "")).strip().lower(), item.get("TipProdus", "")),
                "hidratare_bool": _is_yes(item.get("Hidratare")),
                "curatare_bool": _is_yes(item.get("Curatare")),
                "soare_bool": _is_yes(item.get("Soare")),
                "retinol_bool": _is_yes(item.get("Are Retinol")),
            }
            product["contains_caffeine"] = _contains_caffeine(
                f"{item.get('NumeProdus', '')} {item.get('Ingrediente', '')} {item.get('Descriere', '')}"
            )
            allowed_phases = get_allowed_phases(product)
            product["allowed_phases"] = tuple(sorted(allowed_phases))
            product["phase_warning"] = (
                f"Produsul '{product['NumeProdus']}' nu are un 'Moment utilizare' recunoscut pentru regulile AM/PM."
                if not allowed_phases
                else None
            )
            normalized.append(product)
        return tuple(normalized)

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_retailer_links() -> Dict[str, dict]:
        if not LINKS_PATH.exists():
            return {}
        with LINKS_PATH.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        mapping: Dict[str, dict] = {}
        for entry in raw:
            retailer = _canonicalize_retailer(entry.get("retailer", ""))
            if retailer:
                mapping[retailer] = {
                    "retailer": retailer,
                    "mode": entry.get("mode", "url"),
                    "url": entry.get("url"),
                    "cta_text": entry.get("cta_text") or (
                        "Gaseste produsele in toate magazinele Kaufland."
                        if retailer == "Kaufland"
                        else "Pentru a cumpăra rutina Revox recomandată, apasă aici!"
                    ),
                    "source_label": entry.get("source_label"),
                    "notes": list(entry.get("notes") or []),
                }
        return mapping

    def get_retailer_link(self, retailer: str) -> RetailerLinkResponse:
        canonical = _canonicalize_retailer(retailer)
        payload = self.retailer_links.get(canonical)
        if not payload:
            raise HTTPException(status_code=404, detail=f"No retailer link configured for: {retailer}")
        return RetailerLinkResponse(**payload)

    def list_retailer_links(self) -> RetailerLinkListResponse:
        ordered = [RetailerLinkResponse(**self.retailer_links[r]) for r in RETAILERS if r in self.retailer_links]
        return RetailerLinkListResponse(count=len(ordered), links=ordered)

    def _available_for_retailer(self, product: dict, retailer: str) -> bool:
        if retailer in product["retailers_list"]:
            return True
        return _is_yes(product.get(retailer))

    def _skin_type_matches(self, product: dict, skin_type: str) -> bool:
        supported = product["skin_types_list"]
        if not supported:
            return True
        return skin_type in supported

    def _compatible_phase(self, product: dict, phase: str) -> bool:
        return phase in set(product.get("allowed_phases") or ())

    def _to_response(self, product: dict) -> ProductResponse:
        return ProductResponse(
            id_produs=product["IDProdus"],
            nume_produs=product["NumeProdus"],
            tip_produs=product["tip_produs_norm"],
            needs=product["needs_list"],
            skin_types=product["skin_types_list"],
            retailer_disponibil=product["retailers_list"],
            moment_utilizare=product["moment_raw"],
            hidratant=product["hidratare_bool"],
            curatare=product["curatare_bool"],
            soare=product["soare_bool"],
            are_retinol=product["retinol_bool"],
            nu_combina_cu=list(product.get("NuCombinaCu") or []),
            descriere=product.get("Descriere"),
            ingrediente=product.get("Ingrediente"),
        )

    def get_product_response(self, product_id: str) -> ProductResponse:
        product = self.products_by_id.get(product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Unknown product ID: {product_id}")
        return self._to_response(product)

    def search_products(self, payload: ProductSearchRequest) -> ProductSearchResponse:
        results = []
        tip_requested = None
        if payload.tip_produs:
            tip_requested = TIP_ALIAS.get(payload.tip_produs.strip().lower(), payload.tip_produs.strip())

        for product in self.products:
            if payload.exact_name and product["NumeProdus"] != payload.exact_name:
                continue
            if payload.retailer and not self._available_for_retailer(product, payload.retailer):
                continue
            if payload.skin_type and not self._skin_type_matches(product, payload.skin_type):
                continue
            if payload.need and payload.need not in product["needs_list"]:
                continue
            if tip_requested and product["tip_produs_norm"] != tip_requested:
                continue
            if payload.moment and not self._compatible_phase(product, payload.moment):
                continue
            if payload.exclude_retinol and product["retinol_bool"]:
                continue
            results.append(product)

        results = results[: payload.limit]
        return ProductSearchResponse(
            count=len(results),
            products=[self._to_response(product) for product in results],
        )

    def recommend_routine(self, payload: RoutineRequest) -> RoutineResponse:
        allowed_products = [
            product
            for product in self.products
            if self._available_for_retailer(product, payload.retailer)
            and self._skin_type_matches(product, payload.skin_type)
        ]
        retailer_link = self.retailer_links.get(payload.retailer)
        retailer_link_response = RetailerLinkResponse(**retailer_link) if retailer_link else None

        if not allowed_products:
            morning = self._empty_phase_state("AM", notes=["Nu exista produse eligibile pentru rutina de dimineata."])
            evening = self._empty_phase_state("PM", notes=["Nu exista produse eligibile pentru rutina de seara."])
            return self._build_routine_response(
                payload=payload,
                status="no_products",
                morning=morning,
                evening=evening,
                notes=[f"Nu exista produse disponibile la retailerul {payload.retailer} pentru tipul de piele selectat."],
                retailer_link=retailer_link_response,
                debug=self._debug_blob(payload, allowed_products, morning, evening) if payload.include_debug else None,
            )

        retinol_allowed, retinol_notes, alt_retailers = self._retinol_policy(payload, allowed_products)
        alt_links = self._alternative_link_responses(alt_retailers)

        if self._wrinkle_score(payload) > RETINOL_SCORE_THRESHOLD and not retinol_allowed:
            morning = self._empty_phase_state("AM", notes=["Nu exista selectie valida pentru rutina de dimineata."])
            evening = self._empty_phase_state("PM", notes=["Nu exista selectie valida pentru rutina de seara."])
            return self._build_routine_response(
                payload=payload,
                status="needs_other_retailer",
                morning=morning,
                evening=evening,
                notes=retinol_notes or [f"Nu exista un retinol permis la retailerul {payload.retailer} pentru regulile actuale."],
                alternative_retailers=alt_retailers,
                retailer_link=retailer_link_response,
                alternative_retailer_links=alt_links,
                debug=self._debug_blob(payload, allowed_products, morning, evening) if payload.include_debug else None,
            )

        morning = PhaseState(phase="AM")
        evening = PhaseState(phase="PM")
        notes: List[str] = list(retinol_notes)
        sequence = 0

        cleanser = self._pick_best_cleanser(allowed_products, payload, morning, evening, retinol_allowed)
        if cleanser is None:
            self._mark_missing(morning, "Curatare")
            self._mark_missing(evening, "Curatare")
            morning.notes.append("Nu exista un cleanser eligibil pentru ambele faze.")
            evening.notes.append("Nu exista un cleanser eligibil pentru ambele faze.")
        else:
            sequence = self._assign_product(morning, "Curatare", cleanser, sequence)
            sequence = self._assign_product(evening, "Curatare", cleanser, sequence)

        for phase_state in (morning, evening):
            for slot in PHASE_SLOT_ORDER[phase_state.phase]:
                if slot == "Curatare":
                    continue
                if slot == "Produs problema" and self._phase_already_covers_need(phase_state, payload):
                    phase_state.notes.append(
                        f"Nevoia prioritara '{payload.priority_need}' este deja acoperita in rutina de {self._phase_label(phase_state.phase)}."
                    )
                    continue
                product = self._pick_slot_product(
                    allowed_products=allowed_products,
                    payload=payload,
                    phase_state=phase_state,
                    morning=morning,
                    evening=evening,
                    allow_retinol=retinol_allowed,
                    slot=slot,
                )
                if product is None:
                    self._mark_missing(phase_state, slot)
                    continue
                sequence = self._assign_product(phase_state, slot, product, sequence)

        sequence, retinol_notes = self._ensure_evening_retinol(
            payload=payload,
            allowed_products=allowed_products,
            morning=morning,
            evening=evening,
            allow_retinol=retinol_allowed,
            next_sequence=sequence,
        )
        notes.extend(retinol_notes)

        sequence, conflict_notes = self._resolve_day_conflicts(
            payload=payload,
            allowed_products=allowed_products,
            morning=morning,
            evening=evening,
            allow_retinol=retinol_allowed,
            next_sequence=sequence,
        )
        notes.extend(conflict_notes)

        sequence, retinol_notes = self._ensure_evening_retinol(
            payload=payload,
            allowed_products=allowed_products,
            morning=morning,
            evening=evening,
            allow_retinol=retinol_allowed,
            next_sequence=sequence,
        )
        notes.extend(retinol_notes)

        sequence, conflict_notes = self._resolve_day_conflicts(
            payload=payload,
            allowed_products=allowed_products,
            morning=morning,
            evening=evening,
            allow_retinol=retinol_allowed,
            next_sequence=sequence,
        )
        notes.extend(conflict_notes)

        has_missing = bool(morning.missing_slots or evening.missing_slots)
        status = "ok"
        if not payload.allow_partial_routine and has_missing:
            status = "no_products"
            if not notes:
                notes.append("Nu a putut fi construita o rutina completa cu regulile actuale.")
        elif has_missing:
            status = "partial"

        return self._build_routine_response(
            payload=payload,
            status=status,
            morning=morning,
            evening=evening,
            notes=notes,
            alternative_retailers=alt_retailers if status != "ok" else [],
            retailer_link=retailer_link_response,
            alternative_retailer_links=alt_links if status != "ok" else [],
            debug=self._debug_blob(payload, allowed_products, morning, evening) if payload.include_debug else None,
        )

    def _alternative_link_responses(self, retailers: List[str]) -> List[RetailerLinkResponse]:
        results = []
        for retailer in retailers:
            payload = self.retailer_links.get(retailer)
            if payload:
                results.append(RetailerLinkResponse(**payload))
        return results

    def _debug_blob(
        self,
        payload: RoutineRequest,
        allowed_products: List[dict],
        morning: PhaseState,
        evening: PhaseState,
    ) -> Dict[str, object]:
        phase_warnings = [product["phase_warning"] for product in allowed_products if product.get("phase_warning")]
        return {
            "retailer": payload.retailer,
            "skin_type": payload.skin_type,
            "priority_need": payload.priority_need,
            "allowed_product_ids": [p["IDProdus"] for p in allowed_products],
            "wrinkle_score": self._wrinkle_score(payload),
            "retailer_link_found": payload.retailer in self.retailer_links,
            "phase_warnings": phase_warnings,
            "morning_selected_ids": [product["IDProdus"] for product in morning.selected.values()],
            "evening_selected_ids": [product["IDProdus"] for product in evening.selected.values()],
        }

    def _wrinkle_score(self, payload: RoutineRequest) -> int:
        keys = ["Riduri/linii fine", "riduri", "wrinkles"]
        score_map = payload.scores.as_score_map()
        for key in keys:
            if key in score_map:
                return int(score_map[key])
        return 0

    def _retinol_policy(self, payload: RoutineRequest, allowed_products: List[dict]) -> Tuple[Set[str], List[str], List[str]]:
        notes: List[str] = []
        alternative_retailers: List[str] = []

        wrinkle_score = self._wrinkle_score(payload)
        if wrinkle_score <= RETINOL_SCORE_THRESHOLD:
            notes.append("Retinol exclus: scorul pentru riduri/linii fine nu depaseste 60.")
            return set(), notes, []

        if payload.priority_need == "Riduri/linii fine":
            notes.append("Retinol activ: nevoia prioritara este riduri/linii fine si scorul depaseste 60.")
        else:
            notes.append("Retinol activ: scorul pentru riduri/linii fine depaseste 60.")

        if wrinkle_score <= 65:
            allowed_names = set(RETINOL_ALLOWED_61_65)
            notes.append("Retinol limitat la lista 61-65 conform regulilor.")
        else:
            allowed_names = set(RETINOL_ALLOWED_65_PLUS)
            notes.append("Retinol limitat la lista >65 conform regulilor.")

        allowed_ids = {p["IDProdus"] for p in allowed_products if p["NumeProdus"] in allowed_names}
        if not allowed_ids:
            alternative_retailers = self._retinol_alternative_retailers(allowed_names)
            notes.append("Niciun retinol permis nu este disponibil la retailerul selectat.")
        return allowed_ids, notes, alternative_retailers

    def _retinol_alternative_retailers(self, allowed_names: Set[str]) -> List[str]:
        counter = defaultdict(int)
        for product in self.products:
            if product["NumeProdus"] in allowed_names:
                for retailer in RETAILERS:
                    if self._available_for_retailer(product, retailer):
                        counter[retailer] += 1
        ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
        return [name for name, _ in ranked[:3]]

    def _is_allowed_by_retinol_policy(self, product: dict, payload: RoutineRequest, allow_retinol_ids: Set[str]) -> bool:
        if not product["retinol_bool"]:
            return True
        if self._wrinkle_score(payload) <= RETINOL_SCORE_THRESHOLD:
            return False
        return product["IDProdus"] in allow_retinol_ids

    def _compatible_with_selected(self, candidate: dict, selected: Dict[str, dict]) -> bool:
        candidate_id = candidate["IDProdus"]
        candidate_conflicts = set(candidate.get("NuCombinaCu") or [])
        for selected_product in selected.values():
            selected_id = selected_product["IDProdus"]
            if candidate_id == selected_id:
                continue
            selected_conflicts = set(selected_product.get("NuCombinaCu") or [])
            if candidate_id in selected_conflicts or selected_id in candidate_conflicts:
                return False
        return True

    def _score_product(self, product: dict, payload: RoutineRequest, slot: str, phase: str = "AM") -> int:
        score = 0

        if payload.priority_need in product["needs_list"]:
            score += 60
        score += len(set(payload.detected_needs).intersection(set(product["needs_list"]))) * 8

        if self._skin_type_matches(product, payload.skin_type):
            score += 20

        if slot == "Curatare" and product["curatare_bool"]:
            score += 60
        if slot == "Ochi" and product["tip_produs_norm"] == "Eye care":
            score += 60
        if slot == "Ser" and product["tip_produs_norm"] == "Face serum":
            score += 50
        if slot == "Produs problema" and payload.priority_need in product["needs_list"]:
            score += 70
            if product["tip_produs_norm"] in {"Exfoliator", "Toner Exfoliator", "Face cream", "Eye care"}:
                score += 10
        if slot == "Hidratare" and product["hidratare_bool"]:
            score += 60
        if slot == "Soare" and product["soare_bool"]:
            score += 70

        if product["contains_caffeine"] and slot == "Ochi":
            score += 10
            if phase == "AM" and payload.eye_need == "Ochi obositi/umflati":
                score += 30

        if slot == "Ochi" and payload.eye_need == "Ochi obositi/umflati" and "Ochi obositi/umflati" in product["needs_list"]:
            score += 30
        if slot == "Ochi" and payload.eye_need == "Riduri/linii fine" and "Riduri/linii fine" in product["needs_list"]:
            score += 20

        if product["retinol_bool"]:
            if self._wrinkle_score(payload) > RETINOL_SCORE_THRESHOLD:
                score += 120
                if phase == "PM":
                    score += 30
                if slot in {"Ser", "Ochi", "Produs problema"}:
                    score += 20
            else:
                score -= 100

        return score

    def _pick_best(
        self,
        products: Sequence[dict],
        slot: str,
        payload: RoutineRequest,
        extra_filter,
        phase: str,
        selected: Dict[str, dict],
        allow_retinol: Set[str],
    ) -> Optional[dict]:
        candidates = []
        selected_ids = {p["IDProdus"] for p in selected.values()}
        for product in products:
            if product["IDProdus"] in selected_ids:
                continue
            if not extra_filter(product):
                continue
            if not self._compatible_phase(product, phase):
                continue
            if not self._is_allowed_by_retinol_policy(product, payload, allow_retinol):
                continue
            if not self._compatible_with_selected(product, selected):
                continue
            candidates.append((self._score_product(product, payload, slot), product))
        candidates.sort(key=lambda item: (-item[0], item[1]["NumeProdus"]))
        return candidates[0][1] if candidates else None

    def _pick_best_eye(
        self,
        products: Sequence[dict],
        payload: RoutineRequest,
        selected: Dict[str, dict],
        allow_retinol: Set[str],
    ) -> Optional[dict]:
        candidates = []
        wrinkle_score = self._wrinkle_score(payload)
        selected_ids = {p["IDProdus"] for p in selected.values()}

        for product in products:
            if product["IDProdus"] in selected_ids:
                continue
            if product["tip_produs_norm"] != "Eye care":
                continue
            if not self._compatible_phase(product, "AM"):
                continue
            if not self._is_allowed_by_retinol_policy(product, payload, allow_retinol):
                continue
            if not self._compatible_with_selected(product, selected):
                continue

            score = self._score_product(product, payload, "Ochi")
            if payload.eye_need == "Ochi obositi/umflati" and "Ochi obositi/umflati" in product["needs_list"]:
                score += 30
            if payload.eye_need == "Riduri/linii fine" and "Riduri/linii fine" in product["needs_list"]:
                score += 20
            if payload.eye_need == "Ochi obositi/umflati" and wrinkle_score <= RETINOL_SCORE_THRESHOLD and product["retinol_bool"]:
                score -= 100
            if product["contains_caffeine"] and payload.eye_need == "Ochi obositi/umflati":
                score += 30
            candidates.append((score, product))

        candidates.sort(key=lambda item: (-item[0], item[1]["NumeProdus"]))
        return candidates[0][1] if candidates else None

    def _pick_best_problem_product(
        self,
        products: Sequence[dict],
        payload: RoutineRequest,
        selected: Dict[str, dict],
        allow_retinol: Set[str],
    ) -> Optional[dict]:
        candidates = []
        selected_ids = {p["IDProdus"] for p in selected.values()}
        for product in products:
            if product["IDProdus"] in selected_ids:
                continue
            if payload.priority_need not in product["needs_list"]:
                continue
            if not self._is_allowed_by_retinol_policy(product, payload, allow_retinol):
                continue
            if not self._compatible_with_selected(product, selected):
                continue
            penalty = 0
            if "Ser" in selected and product["tip_produs_norm"] == "Face serum":
                penalty -= 25
            score = self._score_product(product, payload, "Produs problema") + penalty
            candidates.append((score, product))
        candidates.sort(key=lambda item: (-item[0], item[1]["NumeProdus"]))
        return candidates[0][1] if candidates else None

    def _add_or_missing(
        self,
        slot: str,
        product: Optional[dict],
        selected: Dict[str, dict],
        selected_order: List[str],
        missing_slots: List[str],
    ) -> None:
        if product is None:
            missing_slots.append(slot)
            return
        selected[slot] = product
        selected_order.append(slot)

    def _resolve_conflicts(self, selected: Dict[str, dict], selected_order: List[str]) -> Tuple[Dict[str, dict], List[str]]:
        notes: List[str] = []
        final_selected = dict(selected)

        for idx, slot_a in enumerate(list(selected_order)):
            product_a = final_selected.get(slot_a)
            if not product_a:
                continue
            for slot_b in list(selected_order)[idx + 1 :]:
                product_b = final_selected.get(slot_b)
                if not product_b:
                    continue
                a_id = product_a["IDProdus"]
                b_id = product_b["IDProdus"]
                if b_id in set(product_a.get("NuCombinaCu") or []) or a_id in set(product_b.get("NuCombinaCu") or []):
                    removed = final_selected.pop(slot_b)
                    notes.append(
                        f"Produsul '{removed['NumeProdus']}' a fost eliminat din slotul '{slot_b}' deoarece intra in conflict cu un produs deja selectat."
                    )
        return final_selected, notes

    def _has_retinol(self, selected: Dict[str, dict]) -> bool:
        return any(product["retinol_bool"] for product in selected.values())

    def _build_slot_products(self, selected: Dict[str, dict], payload: RoutineRequest) -> List[SlotProduct]:
        ordered = []
        for slot in SLOT_ORDER:
            product = selected.get(slot)
            if not product:
                continue
            if slot == "Curatare":
                phase = "AM/PM"
            elif slot == "Soare":
                phase = "AM"
            elif product["contains_caffeine"]:
                phase = "AM"
            elif product["moment_raw"] == "Seara":
                phase = "PM"
            elif product["moment_raw"] == "Dimineata":
                phase = "AM"
            else:
                phase = "AM/PM"
            notes = []
            if product["contains_caffeine"]:
                notes.append("Cafeina: recomandat doar dimineata.")
            if payload.priority_need in product["needs_list"]:
                notes.append(f"Acopera nevoia prioritara: {payload.priority_need}.")
            ordered.append(
                SlotProduct(
                    slot=slot,
                    phase=phase,
                    id_produs=product["IDProdus"],
                    nume_produs=product["NumeProdus"],
                    tip_produs=product["tip_produs_norm"],
                    matched_need=payload.priority_need if payload.priority_need in product["needs_list"] else None,
                    notes=notes,
                )
            )
        return ordered

    def _phase_label(self, phase: str) -> str:
        return "dimineata" if phase == "AM" else "seara"

    def _mark_missing(self, phase_state: PhaseState, slot: str) -> None:
        if slot in PHASE_SLOT_ORDER[phase_state.phase]:
            phase_state.mark_missing(slot)

    def _empty_phase_state(self, phase: str, notes: Optional[List[str]] = None) -> PhaseState:
        phase_state = PhaseState(phase=phase, notes=list(notes or []))
        for slot in PHASE_SLOT_ORDER[phase]:
            phase_state.mark_missing(slot)
        return phase_state

    def _assign_product(self, phase_state: PhaseState, slot: str, product: dict, sequence: int) -> int:
        next_sequence = sequence + 1
        phase_state.assign(slot, product, next_sequence)
        return next_sequence

    def _phase_already_covers_need(self, phase_state: PhaseState, payload: RoutineRequest) -> bool:
        return any(payload.priority_need in product["needs_list"] for product in phase_state.selected.values())

    def _combined_selected(
        self,
        morning: PhaseState,
        evening: PhaseState,
        exclude: Optional[Tuple[str, str]] = None,
    ) -> Dict[str, dict]:
        combined: Dict[str, dict] = {}
        for phase_state in (morning, evening):
            for slot, product in phase_state.selected.items():
                if exclude and exclude == (phase_state.phase, slot):
                    continue
                combined[f"{phase_state.phase}:{slot}"] = product
        return combined

    def _same_phase_selected_ids(self, phase_state: PhaseState, exclude_slot: Optional[str] = None) -> Set[str]:
        selected_ids = set()
        for slot, product in phase_state.selected.items():
            if slot == exclude_slot:
                continue
            selected_ids.add(product["IDProdus"])
        return selected_ids

    def _pick_best_cleanser(
        self,
        products: Sequence[dict],
        payload: RoutineRequest,
        morning: PhaseState,
        evening: PhaseState,
        allow_retinol: Set[str],
    ) -> Optional[dict]:
        candidates = []
        combined = self._combined_selected(morning, evening)
        for product in products:
            if not (product["curatare_bool"] and product["tip_produs_norm"] == "Cleanser"):
                continue
            if not {"AM", "PM"}.issubset(set(product.get("allowed_phases") or ())):
                continue
            if not self._is_allowed_by_retinol_policy(product, payload, allow_retinol):
                continue
            if not self._compatible_with_selected(product, combined):
                continue
            score = self._score_product(product, payload, "Curatare", "AM") + self._score_product(product, payload, "Curatare", "PM")
            candidates.append((score, product))
        candidates.sort(key=lambda item: (-item[0], item[1]["NumeProdus"]))
        return candidates[0][1] if candidates else None

    def _matches_slot(self, slot: str, product: dict, payload: RoutineRequest) -> bool:
        if slot == "Curatare":
            return product["curatare_bool"] and product["tip_produs_norm"] == "Cleanser"
        if slot == "Ochi":
            return product["tip_produs_norm"] == "Eye care"
        if slot == "Ser":
            return product["tip_produs_norm"] == "Face serum"
        if slot == "Produs problema":
            return payload.priority_need in product["needs_list"]
        if slot == "Hidratare":
            return product["hidratare_bool"]
        if slot == "Soare":
            return product["soare_bool"]
        return False

    def _pick_slot_product(
        self,
        allowed_products: Sequence[dict],
        payload: RoutineRequest,
        phase_state: PhaseState,
        morning: PhaseState,
        evening: PhaseState,
        allow_retinol: Set[str],
        slot: str,
        exclude_slot: Optional[str] = None,
    ) -> Optional[dict]:
        candidates = []
        combined = self._combined_selected(morning, evening, exclude=(phase_state.phase, exclude_slot) if exclude_slot else None)
        same_phase_ids = self._same_phase_selected_ids(phase_state, exclude_slot=exclude_slot)

        for product in allowed_products:
            if product["IDProdus"] in same_phase_ids:
                continue
            if not self._compatible_phase(product, phase_state.phase):
                continue
            if not self._is_allowed_by_retinol_policy(product, payload, allow_retinol):
                continue
            if not self._compatible_with_selected(product, combined):
                continue
            if not self._matches_slot(slot, product, payload):
                continue
            score = self._score_product(product, payload, slot, phase_state.phase)
            if slot == "Produs problema" and "Ser" in phase_state.selected and product["tip_produs_norm"] == "Face serum":
                score -= 25
            candidates.append((score, product))

        candidates.sort(key=lambda item: (-item[0], item[1]["NumeProdus"]))
        return candidates[0][1] if candidates else None

    def _ensure_evening_retinol(
        self,
        payload: RoutineRequest,
        allowed_products: Sequence[dict],
        morning: PhaseState,
        evening: PhaseState,
        allow_retinol: Set[str],
        next_sequence: int,
    ) -> Tuple[int, List[str]]:
        notes: List[str] = []
        if self._wrinkle_score(payload) <= RETINOL_SCORE_THRESHOLD:
            return next_sequence, notes
        if any(product["retinol_bool"] for product in evening.selected.values()):
            return next_sequence, notes

        retinol_products = [product for product in allowed_products if product["retinol_bool"]]
        for slot in ["Ser", "Ochi", "Produs problema", "Hidratare"]:
            candidate = self._pick_forced_evening_retinol_candidate(
                slot=slot,
                payload=payload,
                evening=evening,
                allow_retinol=allow_retinol,
                retinol_products=retinol_products,
            )
            if candidate is None:
                continue

            replaced = evening.selected.get(slot)
            if replaced:
                evening.remove(slot)
            conflict_notes = self._remove_conflicts_for_forced_retinol(candidate, morning, evening, excluded_evening_slot=slot)
            next_sequence = self._assign_product(evening, slot, candidate, next_sequence)
            evening.remove_missing(slot)
            notes.extend(conflict_notes)
            if replaced:
                notes.append(
                    f"Retinolul a fost inclus in rutina de seara deoarece scorul pentru riduri depaseste 60, inlocuind produsul '{replaced['NumeProdus']}' din slotul '{slot}'."
                )
            else:
                notes.append(
                    f"Retinolul a fost inclus in rutina de seara deoarece scorul pentru riduri depaseste 60, pe slotul '{slot}'."
                )
            return next_sequence, notes

        return next_sequence, notes

    def _pick_forced_evening_retinol_candidate(
        self,
        slot: str,
        payload: RoutineRequest,
        evening: PhaseState,
        allow_retinol: Set[str],
        retinol_products: Sequence[dict],
    ) -> Optional[dict]:
        candidates = []
        same_phase_ids = self._same_phase_selected_ids(evening, exclude_slot=slot)
        for product in retinol_products:
            if product["IDProdus"] in same_phase_ids:
                continue
            if not self._compatible_phase(product, "PM"):
                continue
            if not self._is_allowed_by_retinol_policy(product, payload, allow_retinol):
                continue
            if not self._matches_slot(slot, product, payload):
                continue
            candidates.append((self._score_product(product, payload, slot, "PM"), product))
        candidates.sort(key=lambda item: (-item[0], item[1]["NumeProdus"]))
        return candidates[0][1] if candidates else None

    def _remove_conflicts_for_forced_retinol(
        self,
        candidate: dict,
        morning: PhaseState,
        evening: PhaseState,
        excluded_evening_slot: str,
    ) -> List[str]:
        notes: List[str] = []
        candidate_id = candidate["IDProdus"]
        candidate_conflicts = set(candidate.get("NuCombinaCu") or [])
        for phase_state in (morning, evening):
            for slot, selected_product in list(phase_state.selected.items()):
                if phase_state.phase == "PM" and slot == excluded_evening_slot:
                    continue
                selected_id = selected_product["IDProdus"]
                if selected_id == candidate_id:
                    continue
                selected_conflicts = set(selected_product.get("NuCombinaCu") or [])
                if candidate_id in selected_conflicts or selected_id in candidate_conflicts:
                    phase_state.remove(slot)
                    self._mark_missing(phase_state, slot)
                    notes.append(
                        f"Produsul '{selected_product['NumeProdus']}' a fost eliminat din rutina de {self._phase_label(phase_state.phase)} pentru a face loc retinolului permis de scorul ridurilor."
                    )
        return notes

    def _current_selection_entries(self, morning: PhaseState, evening: PhaseState) -> List[Tuple[int, str, str, dict]]:
        entries: List[Tuple[int, str, str, dict]] = []
        for phase_state in (morning, evening):
            for sequence_id, slot in phase_state.selection_order:
                product = phase_state.selected.get(slot)
                if product:
                    entries.append((sequence_id, phase_state.phase, slot, product))
        return sorted(entries, key=lambda item: item[0])

    def _find_conflict(self, morning: PhaseState, evening: PhaseState) -> Optional[Tuple[Tuple[int, str, str, dict], Tuple[int, str, str, dict]]]:
        entries = self._current_selection_entries(morning, evening)
        for idx, earlier in enumerate(entries):
            earlier_product = earlier[3]
            earlier_id = earlier_product["IDProdus"]
            earlier_conflicts = set(earlier_product.get("NuCombinaCu") or [])
            for later in entries[idx + 1 :]:
                later_product = later[3]
                later_id = later_product["IDProdus"]
                if earlier_id == later_id:
                    continue
                later_conflicts = set(later_product.get("NuCombinaCu") or [])
                if later_id in earlier_conflicts or earlier_id in later_conflicts:
                    return earlier, later
        return None

    def _resolve_day_conflicts(
        self,
        payload: RoutineRequest,
        allowed_products: Sequence[dict],
        morning: PhaseState,
        evening: PhaseState,
        allow_retinol: Set[str],
        next_sequence: int,
    ) -> Tuple[int, List[str]]:
        notes: List[str] = []
        while True:
            conflict = self._find_conflict(morning, evening)
            if conflict is None:
                return next_sequence, notes
            _, later = conflict
            _, phase, slot, removed_product = later
            phase_state = morning if phase == "AM" else evening

            if slot == "Curatare":
                morning.remove("Curatare")
                evening.remove("Curatare")
                replacement = self._pick_best_cleanser(allowed_products, payload, morning, evening, allow_retinol)
                if replacement is None:
                    self._mark_missing(morning, "Curatare")
                    self._mark_missing(evening, "Curatare")
                    notes.append("Cleanserul a fost eliminat din cauza unei incompatibilitati zilnice si nu exista un inlocuitor valid pentru ambele faze.")
                else:
                    next_sequence = self._assign_product(morning, "Curatare", replacement, next_sequence)
                    next_sequence = self._assign_product(evening, "Curatare", replacement, next_sequence)
                    notes.append(f"Cleanserul '{removed_product['NumeProdus']}' a fost inlocuit pentru a respecta regulile NuCombinaCu pe intreaga zi.")
                continue

            phase_state.remove(slot)
            if slot == "Produs problema" and self._phase_already_covers_need(phase_state, payload):
                notes.append(
                    f"Produsul '{removed_product['NumeProdus']}' a fost eliminat din slotul '{slot}' in rutina de {self._phase_label(phase)} deoarece nevoia prioritara este deja acoperita."
                )
                continue

            replacement = self._pick_slot_product(
                allowed_products=allowed_products,
                payload=payload,
                phase_state=phase_state,
                morning=morning,
                evening=evening,
                allow_retinol=allow_retinol,
                slot=slot,
                exclude_slot=slot,
            )
            if replacement is not None:
                next_sequence = self._assign_product(phase_state, slot, replacement, next_sequence)
                notes.append(
                    f"Produsul '{removed_product['NumeProdus']}' a fost inlocuit in slotul '{slot}' din rutina de {self._phase_label(phase)} pentru a respecta regulile NuCombinaCu."
                )
            else:
                self._mark_missing(phase_state, slot)
                notes.append(
                    f"Produsul '{removed_product['NumeProdus']}' a fost eliminat din slotul '{slot}' din rutina de {self._phase_label(phase)} si nu exista un inlocuitor compatibil."
                )

    def _slot_product(self, slot: str, phase: str, product: dict, payload: RoutineRequest) -> SlotProduct:
        notes: List[str] = []
        if product["contains_caffeine"]:
            notes.append("Cafeina: recomandat doar dimineata.")
        if product["soare_bool"]:
            notes.append("Protectia solara este inclusa doar in rutina de dimineata.")
        if payload.priority_need in product["needs_list"]:
            notes.append(f"Acopera nevoia prioritara: {payload.priority_need}.")
        return SlotProduct(
            slot=slot,
            phase=phase,
            id_produs=product["IDProdus"],
            nume_produs=product["NumeProdus"],
            tip_produs=product["tip_produs_norm"],
            matched_need=payload.priority_need if payload.priority_need in product["needs_list"] else None,
            notes=notes,
        )

    def _build_phase_routine(self, phase_state: PhaseState, payload: RoutineRequest) -> PhaseRoutine:
        products: List[SlotProduct] = []
        for slot in PHASE_SLOT_ORDER[phase_state.phase]:
            product = phase_state.selected.get(slot)
            if product:
                products.append(self._slot_product(slot, phase_state.phase, product, payload))
        return PhaseRoutine(
            phase=phase_state.phase,
            products=products,
            missing_slots=list(phase_state.missing_slots),
            notes=list(phase_state.notes),
        )

    def _aggregate_missing_slots(self, morning: PhaseRoutine, evening: PhaseRoutine) -> List[str]:
        ordered: List[str] = []
        for slot in morning.missing_slots + evening.missing_slots:
            if slot not in ordered:
                ordered.append(slot)
        return ordered

    def _aggregate_notes(self, global_notes: List[str], morning: PhaseRoutine, evening: PhaseRoutine) -> List[str]:
        aggregated = list(global_notes)
        aggregated.extend(f"AM: {note}" for note in morning.notes)
        aggregated.extend(f"PM: {note}" for note in evening.notes)
        return aggregated

    def _has_retinol_in_day(self, morning: PhaseState, evening: PhaseState) -> bool:
        return any(product["retinol_bool"] for product in [*morning.selected.values(), *evening.selected.values()])

    def _build_routine_response(
        self,
        payload: RoutineRequest,
        status: str,
        morning: PhaseState,
        evening: PhaseState,
        notes: List[str],
        alternative_retailers: Optional[List[str]] = None,
        retailer_link: Optional[RetailerLinkResponse] = None,
        alternative_retailer_links: Optional[List[RetailerLinkResponse]] = None,
        debug: Optional[Dict[str, object]] = None,
    ) -> RoutineResponse:
        morning_routine = self._build_phase_routine(morning, payload)
        evening_routine = self._build_phase_routine(evening, payload)
        flat_products = list(morning_routine.products) + list(evening_routine.products)
        has_retinol = self._has_retinol_in_day(morning, evening)
        return RoutineResponse(
            status=status,
            retailer=payload.retailer,
            priority_need=payload.priority_need,
            skin_type=payload.skin_type,
            morning_routine=morning_routine,
            evening_routine=evening_routine,
            products=flat_products,
            missing_slots=self._aggregate_missing_slots(morning_routine, evening_routine),
            notes=self._aggregate_notes(notes, morning_routine, evening_routine),
            alternative_retailers=list(alternative_retailers or []),
            retailer_link=retailer_link,
            alternative_retailer_links=list(alternative_retailer_links or []),
            retinol_disclaimer_required=has_retinol,
            retinol_disclaimer=RETINOL_DISCLAIMER if has_retinol else None,
            debug=debug,
        )
