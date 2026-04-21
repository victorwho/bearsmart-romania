from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

Retailer = Literal[
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

SkinType = Literal["Normal", "Uscat", "Gras", "Ten Mixt", "Sensibil"]
Need = Literal[
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


class HealthResponse(BaseModel):
    status: str
    product_count: int
    retailer_count: int
    retailer_link_count: int
    version: str


class RetailerListResponse(BaseModel):
    retailers: List[str]


class RetailerLinkResponse(BaseModel):
    retailer: str = Field(..., description="Canonical retailer name")
    mode: Literal["url", "in_store_only"] = Field(..., description="How purchase is handled")
    url: Optional[str] = Field(default=None, description="Direct purchase/search URL if available")
    cta_text: str = Field(..., description="Recommended call-to-action text for the GPT UI")
    source_label: Optional[str] = Field(default=None, description="Raw retailer label as seen in links.txt")
    notes: List[str] = Field(default_factory=list)


class RetailerLinkListResponse(BaseModel):
    count: int
    links: List[RetailerLinkResponse]


class ProductResponse(BaseModel):
    id_produs: str = Field(..., description="Internal stable product ID")
    nume_produs: str = Field(..., description="Exact product name from database")
    tip_produs: str
    needs: List[str]
    skin_types: List[str]
    retailer_disponibil: List[str]
    moment_utilizare: str
    hidratant: bool
    curatare: bool
    soare: bool
    are_retinol: bool
    nu_combina_cu: List[str]
    descriere: Optional[str] = None
    ingrediente: Optional[str] = None


class ProductSearchRequest(BaseModel):
    retailer: Optional[Retailer] = None
    skin_type: Optional[SkinType] = None
    need: Optional[Need] = None
    tip_produs: Optional[str] = None
    moment: Optional[Literal["AM", "PM"]] = None
    exact_name: Optional[str] = None
    exclude_retinol: bool = False
    include_ids_only: bool = False
    limit: int = Field(default=20, ge=1, le=100)


class ProductSearchResponse(BaseModel):
    count: int
    products: List[ProductResponse]


class SlotProduct(BaseModel):
    slot: Literal["Curatare", "Ochi", "Ser", "Produs problema", "Hidratare", "Soare"]
    phase: Literal["AM", "PM"]
    id_produs: str
    nume_produs: str
    tip_produs: str
    matched_need: Optional[str] = None
    notes: List[str] = Field(default_factory=list)


class PhaseRoutine(BaseModel):
    phase: Literal["AM", "PM"]
    products: List[SlotProduct] = Field(default_factory=list)
    missing_slots: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class RoutineScores(BaseModel):
    ten_tern: Optional[int] = Field(default=None, alias="Ten tern", ge=1, le=100)
    deshidratare: Optional[int] = Field(default=None, alias="Deshidratare", ge=1, le=100)
    acnee: Optional[int] = Field(default=None, alias="Acnee", ge=1, le=100)
    ten_neuniform: Optional[int] = Field(default=None, alias="Ten neuniform", ge=1, le=100)
    imperfectiuni: Optional[int] = Field(default=None, alias="Imperfectiuni", ge=1, le=100)
    riduri_linii_fine: Optional[int] = Field(
        default=None,
        alias="Riduri/linii fine",
        ge=1,
        le=100,
        description="Include this score whenever wrinkles are estimated. Values above 60 enable evening retinol selection.",
    )
    ochi_obositi_umflati: Optional[int] = Field(default=None, alias="Ochi obositi/umflati", ge=1, le=100)
    roseata: Optional[int] = Field(default=None, alias="Roseata", ge=1, le=100)
    pete_pigmentare: Optional[int] = Field(default=None, alias="Pete pigmentare", ge=1, le=100)

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        json_schema_extra={
            "description": (
                "Estimated severity scores from 1 to 100. Use the canonical Romanian keys exactly as listed here. "
                "Always include 'Riduri/linii fine' when you estimate wrinkles; values above 60 allow PM-only retinol."
            ),
            "examples": [
                {"Riduri/linii fine": 72, "Imperfectiuni": 61, "Ochi obositi/umflati": 34},
                {"Riduri/linii fine": 61},
            ],
        },
    )

    def as_score_map(self) -> Dict[str, int]:
        return self.model_dump(by_alias=True, exclude_none=True)


class RoutineRequest(BaseModel):
    retailer: Retailer = Field(..., description="Retailer chosen by the user.")
    skin_type: SkinType = Field(..., description="User skin type.")
    priority_need: Need = Field(..., description="Main concern selected by the user.")
    scores: RoutineScores = Field(
        default_factory=RoutineScores,
        description=(
            "Estimated concern scores from the selfie analysis. Always pass 'Riduri/linii fine' when wrinkles are estimated. "
            "If 'Riduri/linii fine' is above 60, the API can recommend PM-only retinol."
        ),
    )
    detected_needs: List[Need] = Field(default_factory=list, description="All detected concerns, if available.")
    eye_need: Optional[Literal["Ochi obositi/umflati", "Riduri/linii fine"]] = Field(
        default=None,
        description="Optional eye-area priority when relevant.",
    )
    allow_partial_routine: bool = Field(
        default=True,
        description="Set to true to allow partial routines when some slots cannot be filled.",
    )
    include_debug: bool = Field(default=False, description="Set to true only for internal debugging.")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "retailer": "Douglas",
                    "skin_type": "Normal",
                    "priority_need": "Imperfectiuni",
                    "scores": {"Riduri/linii fine": 72, "Imperfectiuni": 61},
                    "detected_needs": ["Imperfectiuni", "Riduri/linii fine"],
                    "allow_partial_routine": True,
                },
                {
                    "retailer": "Sephora",
                    "skin_type": "Ten Mixt",
                    "priority_need": "Riduri/linii fine",
                    "scores": {"Riduri/linii fine": 68},
                    "allow_partial_routine": True,
                },
            ]
        },
    )

    @model_validator(mode="after")
    def validate_scores(self) -> "RoutineRequest":
        for key, value in self.scores.as_score_map().items():
            if not 1 <= int(value) <= 100:
                raise ValueError(f"Score for {key} must be between 1 and 100.")
        return self


class RoutineResponse(BaseModel):
    status: Literal["ok", "no_products", "needs_other_retailer", "partial"]
    retailer: str
    priority_need: str
    skin_type: str
    morning_routine: Optional[PhaseRoutine] = None
    evening_routine: Optional[PhaseRoutine] = None
    products: List[SlotProduct] = Field(default_factory=list, description="Deprecated flat list for backward compatibility.")
    missing_slots: List[str] = Field(default_factory=list, description="Deprecated aggregate missing slots.")
    notes: List[str] = Field(default_factory=list, description="Deprecated aggregate notes.")
    alternative_retailers: List[str] = Field(default_factory=list)
    retailer_link: Optional[RetailerLinkResponse] = None
    alternative_retailer_links: List[RetailerLinkResponse] = Field(default_factory=list)
    retinol_disclaimer_required: bool = False
    retinol_disclaimer: Optional[str] = None
    feedback_cta_text: str = Field(
        default="Părerea ta contează! Spune-ne cum ți s-a părut experiența și ajută-ne să o facem și mai bună :apasă aici!"
    )
    debug: Optional[Dict[str, object]] = None
