from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["product_count"] >= 1
    assert data["retailer_link_count"] >= 1
    assert data["version"] == "1.3.0-public"


def test_exact_product():
    r = client.get("/products/RVX004")
    assert r.status_code == 200
    data = r.json()
    assert data["nume_produs"] == "Revox Just niacinamid daily moisturiser 30ml"


def test_list_retailer_links():
    r = client.get("/retailer-links")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert any(item["retailer"] == "Farmacia Tei" for item in data["links"])


def test_retailer_link_alias_normalization():
    r = client.get("/retailer-links/Farmacia%20Tei")
    assert r.status_code == 200
    data = r.json()
    assert data["retailer"] == "Farmacia Tei"
    assert data["url"] == "https://comenzi.farmaciatei.ro/brand/revox"


def test_openapi_gpt_schema_is_minimal():
    r = client.get("/openapi-gpt.json")
    assert r.status_code == 200
    data = r.json()
    assert set(data["paths"].keys()) == {
        "/retailer-links/{retailer}",
        "/products/{product_id}",
        "/routine/recommend",
    }
    assert "/health" not in data["paths"]
    assert data["servers"] == [{"url": "http://testserver"}]
    assert "RoutineRequest" in data["components"]["schemas"]
    assert "RoutineResponse" in data["components"]["schemas"]
    assert "RoutineScores" in data["components"]["schemas"]
    assert "PhaseRoutine" in data["components"]["schemas"]
    assert "RetailerLinkResponse" in data["components"]["schemas"]
    assert data["paths"]["/routine/recommend"]["post"]["x-openai-isConsequential"] is False


def test_openapi_gpt_schema_makes_wrinkle_score_explicit_for_action():
    r = client.get("/openapi-gpt.json")
    assert r.status_code == 200
    data = r.json()
    scores_schema = data["components"]["schemas"]["RoutineScores"]
    assert "Riduri/linii fine" in scores_schema["properties"]
    assert "above 60" in scores_schema["properties"]["Riduri/linii fine"]["description"]
    examples = scores_schema["examples"]
    assert any(example.get("Riduri/linii fine", 0) > 60 for example in examples)


def test_openapi_gpt_prefers_forwarded_headers():
    r = client.get(
        "/openapi-gpt.json",
        headers={
            "x-forwarded-proto": "https",
            "x-forwarded-host": "revox-api-q3d5yfy7ma-ew.a.run.app",
        },
    )
    assert r.status_code == 200
    assert r.json()["servers"] == [{"url": "https://revox-api-q3d5yfy7ma-ew.a.run.app"}]


def test_docs_disabled_by_default():
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404


def test_search_retailer():
    r = client.post(
        "/products/search",
        json={
            "retailer": "Sephora",
            "skin_type": "Ten Mixt",
            "need": "Imperfectiuni",
            "limit": 5,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "products" in data
    assert data["count"] >= 1


def test_routine_response_contains_am_pm_structures():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Sephora",
            "skin_type": "Ten Mixt",
            "priority_need": "Imperfectiuni",
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in {"ok", "partial"}
    assert data["morning_routine"]["phase"] == "AM"
    assert data["evening_routine"]["phase"] == "PM"
    assert isinstance(data["morning_routine"]["products"], list)
    assert isinstance(data["evening_routine"]["products"], list)
    assert isinstance(data["products"], list)


def test_routine_includes_retailer_link_and_backward_compatible_products():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Sephora",
            "skin_type": "Ten Mixt",
            "priority_need": "Imperfectiuni",
            "scores": {"Acnee": 72, "Deshidratare": 18, "Riduri/linii fine": 24},
            "detected_needs": ["Imperfectiuni", "Acnee", "Ten neuniform"],
            "eye_need": "Ochi obositi/umflati",
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["retailer_link"]["retailer"] == "Sephora"
    assert data["retailer_link"]["url"] == "https://www.sephora.ro/branduri/de-la-a-la-z/revox/revox/"
    morning_cleanser = [item for item in data["morning_routine"]["products"] if item["slot"] == "Curatare"]
    evening_cleanser = [item for item in data["evening_routine"]["products"] if item["slot"] == "Curatare"]
    if morning_cleanser and evening_cleanser:
        assert morning_cleanser[0]["id_produs"] == evening_cleanser[0]["id_produs"]
        flat_cleanser_entries = [item for item in data["products"] if item["slot"] == "Curatare"]
        assert len(flat_cleanser_entries) == 2
        assert {item["phase"] for item in flat_cleanser_entries} == {"AM", "PM"}
    else:
        assert "Curatare" in data["morning_routine"]["missing_slots"]
        assert "Curatare" in data["evening_routine"]["missing_slots"]


def test_caffeine_eye_product_is_am_only():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Sephora",
            "skin_type": "Ten Mixt",
            "priority_need": "Imperfectiuni",
            "eye_need": "Ochi obositi/umflati",
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    morning_names = {item["nume_produs"] for item in data["morning_routine"]["products"]}
    evening_names = {item["nume_produs"] for item in data["evening_routine"]["products"]}
    assert "Revox Just caffeine 5% eye contour serum 30ml" in morning_names
    assert "Revox Just caffeine 5% eye contour serum 30ml" not in evening_names


def test_retinal_product_if_selected_is_pm_only():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Douglas",
            "skin_type": "Normal",
            "priority_need": "Riduri/linii fine",
            "scores": {"Riduri/linii fine": 70},
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    morning_names = {item["nume_produs"] for item in data["morning_routine"]["products"]}
    evening_names = {item["nume_produs"] for item in data["evening_routine"]["products"]}
    assert "Revox Just Retinal Serum 30ml" not in morning_names
    if "Revox Just Retinal Serum 30ml" in evening_names:
        assert True


def test_spf_is_only_am_and_pm_has_no_sun_slot():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Sephora",
            "skin_type": "Ten Mixt",
            "priority_need": "Imperfectiuni",
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert all(item["slot"] != "Soare" for item in data["evening_routine"]["products"])
    sun_entries = [item for item in data["products"] if item["slot"] == "Soare"]
    assert sun_entries
    assert all(item["phase"] == "AM" for item in sun_entries)


def test_wrinkle_score_above_60_can_force_retinol_even_if_priority_is_different():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Douglas",
            "skin_type": "Normal",
            "priority_need": "Imperfectiuni",
            "scores": {"Riduri/linii fine": 70},
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    morning_names = [item["nume_produs"] for item in data["morning_routine"]["products"]]
    evening_names = [item["nume_produs"] for item in data["evening_routine"]["products"]]
    assert any("retinol" in name.lower() or "retinal" in name.lower() for name in evening_names)
    assert all("retinol" not in name.lower() and "retinal" not in name.lower() for name in morning_names)


def test_priority_wrinkles_without_scores_does_not_trigger_retinol():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Douglas",
            "skin_type": "Normal",
            "priority_need": "Riduri/linii fine",
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    all_names = [item["nume_produs"] for item in data["products"]]
    assert all("retinol" not in name.lower() and "retinal" not in name.lower() for name in all_names)
    assert data["retinol_disclaimer_required"] is False


def test_priority_wrinkles_with_explicit_wrinkle_score_triggers_evening_retinol():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Douglas",
            "skin_type": "Normal",
            "priority_need": "Riduri/linii fine",
            "scores": {"Riduri/linii fine": 70},
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    morning_names = [item["nume_produs"] for item in data["morning_routine"]["products"]]
    evening_names = [item["nume_produs"] for item in data["evening_routine"]["products"]]
    assert any("retinol" in name.lower() or "retinal" in name.lower() for name in evening_names)
    assert all("retinol" not in name.lower() and "retinal" not in name.lower() for name in morning_names)


def test_wrinkle_score_above_60_adds_retinol_even_when_priority_is_not_wrinkles():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Douglas",
            "skin_type": "Normal",
            "priority_need": "Imperfectiuni",
            "scores": {"Riduri/linii fine": 61},
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    evening_names = [item["nume_produs"] for item in data["evening_routine"]["products"]]
    assert any("retinol" in name.lower() or "retinal" in name.lower() for name in evening_names)


def test_wrinkle_score_of_60_does_not_force_retinol():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Douglas",
            "skin_type": "Normal",
            "priority_need": "Imperfectiuni",
            "scores": {"Riduri/linii fine": 60},
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    all_names = [item["nume_produs"] for item in data["products"]]
    assert all("retinol" not in name.lower() and "retinal" not in name.lower() for name in all_names)
    assert data["retinol_disclaimer_required"] is False
    assert data["retinol_disclaimer"] is None


def test_wrinkle_score_above_60_keeps_retinol_out_of_morning_routine():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Douglas",
            "skin_type": "Normal",
            "priority_need": "Imperfectiuni",
            "scores": {"Riduri/linii fine": 70},
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    morning_names = [item["nume_produs"] for item in data["morning_routine"]["products"]]
    evening_names = [item["nume_produs"] for item in data["evening_routine"]["products"]]
    assert all("retinol" not in name.lower() and "retinal" not in name.lower() for name in morning_names)
    assert any("retinol" in name.lower() or "retinal" in name.lower() for name in evening_names)


def test_wrinkle_score_above_60_sets_retinol_disclaimer_when_retinol_is_selected():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Douglas",
            "skin_type": "Normal",
            "priority_need": "Imperfectiuni",
            "scores": {"Riduri/linii fine": 70},
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["retinol_disclaimer_required"] is True
    assert isinstance(data["retinol_disclaimer"], str)
    assert data["retinol_disclaimer"]


def test_database_backed_sephora_imperfections_routine_returns_expected_core_products():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Sephora",
            "skin_type": "Ten Mixt",
            "priority_need": "Imperfectiuni",
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    morning_by_slot = {item["slot"]: item["nume_produs"] for item in data["morning_routine"]["products"]}
    evening_by_slot = {item["slot"]: item["nume_produs"] for item in data["evening_routine"]["products"]}
    assert morning_by_slot["Curatare"] == "Revox Zitcare aha.bha.pha. face wash 250ml"
    assert evening_by_slot["Curatare"] == "Revox Zitcare aha.bha.pha. face wash 250ml"
    assert morning_by_slot["Ser"] == "Revox Just niacinamid daily moisturiser 30ml"
    assert evening_by_slot["Ser"] == "Revox Just niacinamid daily moisturiser 30ml"
    assert morning_by_slot["Soare"] == "Revox Just Daily sun shield uva+uvb filters spf 50+hyaluronic acid 30ml"
    assert "Soare" not in evening_by_slot


def test_database_backed_eye_need_prefers_caffeine_in_am_and_eye_fluid_in_pm():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Sephora",
            "skin_type": "Ten Mixt",
            "priority_need": "Imperfectiuni",
            "eye_need": "Ochi obositi/umflati",
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    morning_by_slot = {item["slot"]: item["nume_produs"] for item in data["morning_routine"]["products"]}
    evening_by_slot = {item["slot"]: item["nume_produs"] for item in data["evening_routine"]["products"]}
    assert morning_by_slot["Ochi"] == "Revox Just caffeine 5% eye contour serum 30ml"
    assert evening_by_slot["Ochi"] == "Revox Just eye care fluid 30ml"


def test_database_backed_wrinkle_score_61_uses_only_61_65_retinol_list():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Douglas",
            "skin_type": "Normal",
            "priority_need": "Imperfectiuni",
            "scores": {"Riduri/linii fine": 61},
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    evening_names = {item["nume_produs"] for item in data["evening_routine"]["products"]}
    assert "Revox Just retinol in squalane H2O - free solution age control 30ml" in evening_names
    assert "Revox Retinol Eye-Gel Anti-Wrinkle Concentrate 30ml" not in evening_names
    assert "Revox Retinol Daily Protection spf 20 50ml" not in evening_names
    assert "Revox Retinol Serum Unifying Regenerator 30ml" not in evening_names


def test_database_backed_wrinkle_score_70_uses_only_65_plus_retinol_list():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Douglas",
            "skin_type": "Normal",
            "priority_need": "Riduri/linii fine",
            "scores": {"Riduri/linii fine": 70},
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    evening_names = {item["nume_produs"] for item in data["evening_routine"]["products"]}
    assert "Revox Retinol Eye-Gel Anti-Wrinkle Concentrate 30ml" in evening_names
    assert "Revox Retinol Daily Protection spf 20 50ml" in evening_names
    assert "Revox Just retinol in squalane H2O - free solution age control 30ml" not in evening_names
    assert "Revox Just retinol toner 250ml" not in evening_names


def test_database_backed_nu_combina_cu_removes_conflicting_cleanser_when_retinol_forced():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Douglas",
            "skin_type": "Normal",
            "priority_need": "Imperfectiuni",
            "scores": {"Riduri/linii fine": 61},
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    morning_slots = {item["slot"] for item in data["morning_routine"]["products"]}
    evening_slots = {item["slot"] for item in data["evening_routine"]["products"]}
    assert "Curatare" not in morning_slots
    assert "Curatare" not in evening_slots
    assert "Curatare" in data["morning_routine"]["missing_slots"]
    assert "Curatare" in data["evening_routine"]["missing_slots"]
    assert any("Revox Zitcare aha.bha.pha. face wash 250ml" in note for note in data["notes"])


def test_edge_unknown_product_returns_404():
    r = client.get("/products/DOES-NOT-EXIST")
    assert r.status_code == 404
    assert "Unknown product ID" in r.json()["detail"]


def test_edge_invalid_score_above_100_returns_422():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Douglas",
            "skin_type": "Normal",
            "priority_need": "Imperfectiuni",
            "scores": {"Riduri/linii fine": 101},
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 422


def test_edge_extra_request_field_is_rejected():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Douglas",
            "skin_type": "Normal",
            "priority_need": "Imperfectiuni",
            "allow_partial_routine": True,
            "unexpected_field": "not allowed",
        },
    )
    assert r.status_code == 422


def test_edge_include_debug_returns_internal_selection_summary():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Douglas",
            "skin_type": "Normal",
            "priority_need": "Imperfectiuni",
            "scores": {"Riduri/linii fine": 61},
            "allow_partial_routine": True,
            "include_debug": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["debug"]["retailer"] == "Douglas"
    assert data["debug"]["skin_type"] == "Normal"
    assert data["debug"]["priority_need"] == "Imperfectiuni"
    assert data["debug"]["wrinkle_score"] == 61
    assert data["debug"]["retailer_link_found"] is True
    assert isinstance(data["debug"]["allowed_product_ids"], list)
    assert isinstance(data["debug"]["morning_selected_ids"], list)
    assert isinstance(data["debug"]["evening_selected_ids"], list)


def test_edge_allow_partial_false_turns_partial_routine_into_no_products():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Douglas",
            "skin_type": "Normal",
            "priority_need": "Imperfectiuni",
            "scores": {"Riduri/linii fine": 61},
            "allow_partial_routine": False,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "no_products"
    assert "Curatare" in data["missing_slots"]


def test_edge_missing_retailer_retinol_returns_needs_other_retailer_with_links():
    r = client.post(
        "/routine/recommend",
        json={
            "retailer": "Marionnaud",
            "skin_type": "Normal",
            "priority_need": "Imperfectiuni",
            "scores": {"Riduri/linii fine": 61},
            "allow_partial_routine": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "needs_other_retailer"
    assert data["alternative_retailers"][:3] == ["Auchan", "Bebe Tei", "DM"]
    assert [item["retailer"] for item in data["alternative_retailer_links"][:3]] == ["Auchan", "Bebe Tei", "DM"]
    assert all(slot in data["missing_slots"] for slot in ["Curatare", "Ochi", "Ser", "Produs problema", "Hidratare"])


def test_privacy_policy():
    r = client.get("/privacy-policy")
    assert r.status_code == 200
    assert "Privacy Policy" in r.text


def test_root_exposes_bearsmart_mvp_link():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["bearsmart_mvp"] == "/bearsmart"


def test_bearsmart_mvp_page_loads():
    r = client.get("/bearsmart")
    assert r.status_code == 200
    assert "BearSmart Romania | Interactive Map" in r.text
    assert "/logo/bearsmart-logo-light.svg" in r.text
    assert "Tap anywhere to report a sighting" in r.text
    assert "BearSmart Localities" in r.text
    assert "Bear Safety Guides" in r.text
    assert ">Community<" not in r.text
    assert "Report Sighting" in r.text
    assert "Emergency" in r.text


def test_bearsmart_map_alias_page_loads():
    r = client.get("/bearsmart/map")
    assert r.status_code == 200
    assert "Tap anywhere to report a sighting" in r.text
    assert "centerLocationButton" in r.text
    assert "Center on my location" in r.text
    assert "mapTownSelect" in r.text
    assert "mapFilterToggle" in r.text
    assert "legendToggleButton" in r.text
    assert "Current town" not in r.text
    assert "All zones" not in r.text
    assert "Safety Dashboard" not in r.text
    assert "Report Here" not in r.text
    assert "Focus town" not in r.text
    assert "/bearsmart-static/map.js" in r.text


def test_bearsmart_map_script_uses_geolocation_centering_not_report_redirect():
    r = client.get("/bearsmart-static/map.js")
    assert r.status_code == 200
    assert "centerOnUserLocation" in r.text
    assert "centerLocationButton" in r.text
    assert "Your location" in r.text
    assert "mapTownSelect" in r.text
    assert "clusterReports" in r.text
    assert "mapFilterDrawer" in r.text


def test_bearsmart_localities_page_loads():
    r = client.get("/bearsmart/localities")
    assert r.status_code == 200
    assert "Certified Localities" in r.text
    assert "/logo/bearsmart-logo-light.svg" in r.text
    assert "Network Impact" in r.text
    assert "trendChart" not in r.text
    assert "countyFilter" in r.text
    assert "regionFilter" in r.text
    assert "/bearsmart-static/localities.js" in r.text


def test_bearsmart_dashboard_page_loads():
    r = client.get("/bearsmart/dashboard")
    assert r.status_code == 200
    assert "Bear Safety Guides" in r.text
    assert "Choose your profile" in r.text
    assert "profileCardGrid" in r.text
    assert "Personalized Recommendations" in r.text
    assert "Quick advice for common situations" not in r.text
    assert "Who to call locally" not in r.text
    assert "Loading locality" not in r.text
    assert "printGuideButton" in r.text
    assert "Local Context" not in r.text
    assert "Latest Local Notes" not in r.text
    assert "/bearsmart-static/dashboard.js" in r.text


def test_bearsmart_report_page_loads():
    r = client.get("/bearsmart/report")
    assert r.status_code == 200
    assert "Report a Sighting" in r.text
    assert "Step 1 of 4" in r.text
    assert "selectedPointSummary" in r.text
    assert "locationLookupStatus" in r.text
    assert "/bearsmart-static/report.js" in r.text


def test_bearsmart_community_route_redirects_out_of_public_nav():
    r = client.get("/bearsmart/community", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "/bearsmart"


def test_bearsmart_hidden_community_page_loads():
    r = client.get("/bearsmart/community-hidden")
    assert r.status_code == 200
    assert "Community Feed" in r.text
    assert "Community at a glance" in r.text
    assert "See how residents, volunteers, and local coordinators" in r.text
    assert "/bearsmart-static/community.js" in r.text


def test_bearsmart_ops_page_redirects_to_workspace():
    # H1.1: public /bearsmart/ops moved behind /workspace.
    r = client.get("/bearsmart/ops", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"].startswith("/workspace/ops")


def test_workspace_ops_requires_auth_via_html_redirect():
    r = client.get("/workspace/ops", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/login?next=/workspace/ops")


def test_workspace_ops_renders_for_authenticated_moderator():
    login = client.post(
        "/login",
        data={"email": "mod@bearsmart.ro", "role": "moderator", "next": "/workspace/ops"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    # TestClient.session persists cookies across calls.
    r = client.get("/workspace/ops")
    assert r.status_code == 200
    assert "Operations Console" in r.text
    client.cookies.clear()


def test_bearsmart_logo_asset_is_served():
    r = client.get("/logo/bearsmart-logo-light.svg")
    assert r.status_code == 200
    assert "<svg" in r.text


def test_bearsmart_towns_endpoint_returns_seed_data():
    r = client.get("/api/bearsmart/towns")
    assert r.status_code == 200
    data = r.json()
    assert any(item["slug"] == "rasnov" for item in data["items"])
    assert any(item["slug"] == "sfantul-gheorghe" for item in data["items"])


def test_bearsmart_map_endpoint_returns_zones_and_reports():
    r = client.get("/api/bearsmart/map")
    assert r.status_code == 200
    data = r.json()
    rasnov = next(item for item in data["towns"] if item["slug"] == "rasnov")
    assert rasnov["zone_color"] == "#2e8b57"
    assert len(rasnov["polygon"]) == 4
    assert rasnov["hero_image"].startswith("https://")
    assert any(report["town_slug"] == "rasnov" for report in data["reports"])


def test_bearsmart_network_impact_endpoint_returns_trend_data():
    r = client.get("/api/bearsmart/network-impact")
    assert r.status_code == 200
    data = r.json()
    assert data["community_count"] == 3
    assert len(data["trend_years"]) == len(data["trend_values"])


def test_bearsmart_community_endpoint_returns_feed_data():
    r = client.get("/api/bearsmart/community")
    assert r.status_code == 200
    data = r.json()
    assert "pinned_alert" in data
    assert len(data["posts"]) >= 1
    assert len(data["heroes"]) >= 1
    assert len(data["workshops"]) >= 1


def test_bearsmart_dashboard_endpoint_returns_public_dashboard_data():
    r = client.get("/api/bearsmart/dashboard/rasnov")
    assert r.status_code == 200
    data = r.json()
    assert data["town"]["slug"] == "rasnov"
    assert "status" in data
    assert "news_items" in data
    assert "assessment_cta" in data


def test_bearsmart_report_submission_creates_submitted_item():
    r = client.post(
        "/api/bearsmart/reports",
        json={
            "town_slug": "rasnov",
            "type": "sighting",
            "description": "Bear observed near a guesthouse waste enclosure.",
            "location_label": "South guesthouse lane",
            "reporter_name": "Test User",
            "latitude": 45.592,
            "longitude": 25.461,
            "number_of_bears": 2,
            "behavior_observed": "Crossing road then moving into brush",
            "photo_name": "bear.jpg",
        },
    )
    assert r.status_code == 200
    data = r.json()["report"]
    assert data["town_slug"] == "rasnov"
    assert data["status"] == "submitted"
    assert data["verification_status"] == "unverified"
    assert data["lat"] == 45.592
    assert data["lng"] == 25.461
    assert data["details"]["number_of_bears"] == 2
    assert data["details"]["behavior_observed"] == "Crossing road then moving into brush"
    assert data["details"]["photo_name"] == "bear.jpg"


def test_bearsmart_moderation_requires_role_header():
    r = client.get("/api/bearsmart/moderation/reports")
    assert r.status_code == 403


def test_bearsmart_admin_can_create_alert():
    r = client.post(
        "/api/bearsmart/admin/towns/rasnov/alerts",
        headers={"X-Demo-Role": "town_admin"},
        json={
            "title": "Night bin patrol",
            "message": "Teams should verify all communal bins are locked before midnight.",
            "severity": "warning",
        },
    )
    assert r.status_code == 200
    data = r.json()["alert"]
    assert data["town_slug"] == "rasnov"
    assert data["severity"] == "warning"


def test_bearsmart_plan_generation_and_task_update():
    created = client.post(
        "/api/bearsmart/plans",
        json={"town_slug": "busteni", "persona_type": "resident"},
    )
    assert created.status_code == 200
    plan = created.json()["plan"]
    task_id = plan["tasks"][0]["id"]
    assert plan["tasks"][0]["summary"]
    assert plan["tasks"][0]["details"]
    assert plan["tasks"][0]["category"]

    updated = client.patch(
        f"/api/bearsmart/plans/{plan['id']}/tasks/{task_id}",
        json={"state": "completed"},
    )
    assert updated.status_code == 200
    data = updated.json()["plan"]
    assert data["completion_percent"] > 0
    assert any(task["state"] == "completed" for task in data["tasks"])


# ---------------------------------------------------------------------------
# Horizon 0 — foundations (auth, flags, telemetry, geo-fuzz)
# ---------------------------------------------------------------------------


def test_auth_encode_decode_round_trips():
    from app.auth import Session, decode_session, encode_session

    session = Session(role="moderator", email="mod@example.com", town_slug="rasnov")
    token = encode_session(session)
    decoded = decode_session(token)
    assert decoded == session


def test_auth_decode_rejects_tampered_token():
    from app.auth import Session, decode_session, encode_session

    token = encode_session(Session(role="moderator"))
    assert decode_session(token + "x") is None
    assert decode_session("totally.bogus") is None


def test_flags_api_returns_known_flags():
    r = client.get("/api/flags")
    assert r.status_code == 200
    flags = r.json()
    for name in ("emergency_gate", "geo_fuzz", "trip_mode", "town_pages_v2",
                 "admin_nudges", "seasonal_campaigns"):
        assert name in flags


def test_telemetry_post_records_event_and_super_admin_reads_recent():
    from app.telemetry import reset_for_tests

    reset_for_tests()
    r = client.post(
        "/api/telemetry",
        json={"name": "town_page_viewed", "props": {"tab": "plan", "town": "rasnov"}},
    )
    assert r.status_code == 200
    assert r.json()["recorded"] is True

    # Unauthenticated fetch of recent events is forbidden (API path → 403).
    denied = client.get("/api/telemetry/recent", follow_redirects=False)
    assert denied.status_code == 403

    # Super admin login then read.
    login = client.post(
        "/login",
        data={"email": "root@bearsmart.ro", "role": "super_admin", "next": "/api/telemetry/recent"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    ok = client.get("/api/telemetry/recent")
    assert ok.status_code == 200
    events = ok.json()["items"]
    assert any(e["name"] == "town_page_viewed" for e in events)
    client.cookies.clear()


def test_geo_fuzz_strips_livestock_and_apiary_coordinates():
    from app.geo import public_point

    for report_type in ("livestock_incident", "apiary_incident"):
        point = public_point(45.59, 25.46, report_type, town_center=(45.5, 25.5))
        # Coordinates resolve to town centre, not the original farm.
        assert point.lat == 45.5
        assert point.lng == 25.5
        assert point.radius_m is None
        assert point.stripped is True


def test_geo_fuzz_snaps_sighting_to_500m_grid():
    from app.geo import haversine_m, public_point

    lat, lng = 45.593, 25.463
    point = public_point(lat, lng, "sighting")
    assert point.radius_m == 500.0
    assert point.lat is not None and point.lng is not None
    # Fuzzed point never further than ~1.5× the radius (jitter + snap bound).
    distance = haversine_m(lat, lng, point.lat, point.lng)
    assert distance <= 750.0


# ---------------------------------------------------------------------------
# Horizon 1 — front-door fixes
# ---------------------------------------------------------------------------


def test_login_form_renders_next_param():
    r = client.get("/login?next=/workspace/ops")
    assert r.status_code == 200
    assert "/workspace/ops" in r.text
    assert "Sign in to BearSmart" in r.text


def test_login_rejects_bad_payload():
    r = client.post(
        "/login",
        data={"email": "", "role": "not_a_role", "next": "/workspace"},
        follow_redirects=False,
    )
    assert r.status_code == 400


def test_api_session_reflects_cookie_and_demo_header():
    client.cookies.clear()
    anon = client.get("/api/session").json()
    assert anon["role"] == "public"
    assert anon["authenticated"] is False

    demo = client.get("/api/session", headers={"X-Demo-Role": "moderator"}).json()
    assert demo["role"] == "moderator"
    assert demo["authenticated"] is False

    client.post(
        "/login",
        data={"email": "admin@bearsmart.ro", "role": "town_admin", "next": "/"},
        follow_redirects=False,
    )
    authed = client.get("/api/session").json()
    assert authed["role"] == "town_admin"
    assert authed["authenticated"] is True
    client.cookies.clear()


def test_require_role_returns_403_for_api_requests():
    # Super admin endpoint; anonymous API caller must get 403, not a redirect.
    r = client.get(
        "/api/telemetry/recent",
        headers={"Accept": "application/json"},
        follow_redirects=False,
    )
    assert r.status_code == 403


def test_map_js_includes_home_sheet_and_emergency_gate_scripts():
    r = client.get("/bearsmart/map")
    assert r.status_code == 200
    assert "/bearsmart-static/emergency-gate.js" in r.text
    assert "/bearsmart-static/home-sheet.js" in r.text
    assert 'data-tab="now"' in r.text
    assert 'data-tab="plan"' in r.text
    assert 'data-tab="report"' in r.text
    # Confirms the 9-panel column is gone (dead index.html/app.js removed).
    assert "roleSelect" not in r.text


def test_report_page_embeds_fuzz_preview_and_emergency_gate():
    r = client.get("/bearsmart/report")
    assert r.status_code == 200
    assert "fuzzPreviewNote" in r.text
    assert "/bearsmart-static/emergency-gate.js" in r.text


def test_emergency_gate_script_contains_112_contract():
    r = client.get("/bearsmart-static/emergency-gate.js")
    assert r.status_code == 200
    assert 'tel:112' in r.text
    assert "emergency_gate_shown" in r.text
    assert "STICKY_MS" in r.text


def test_public_map_endpoint_never_returns_submitted_sighting_coords():
    # Seed a sighting with precise coordinates.
    submit = client.post(
        "/api/bearsmart/reports",
        json={
            "town_slug": "rasnov",
            "type": "sighting",
            "description": "Precise sighting used for privacy guarantee test.",
            "location_label": "Guesthouse lane",
            "latitude": 45.5931,
            "longitude": 25.4634,
        },
    )
    assert submit.status_code == 200
    report_id = submit.json()["report"]["id"]

    # Approve so it's published to the public map.
    client.post(
        f"/api/bearsmart/moderation/reports/{report_id}/review",
        headers={"X-Demo-Role": "moderator"},
        json={"action": "approve"},
    )

    public = client.get("/api/bearsmart/map").json()
    match = next((r for r in public["reports"] if r["id"] == report_id), None)
    assert match is not None
    from app.geo import haversine_m

    assert match["public_radius_m"] == 500.0
    assert match["public_lat"] is not None
    assert match["public_lng"] is not None
    distance = haversine_m(45.5931, 25.4634, match["public_lat"], match["public_lng"])
    assert distance > 10.0  # point moved, coordinates no longer identical


def test_public_map_strips_livestock_incident_coordinates():
    submit = client.post(
        "/api/bearsmart/reports",
        json={
            "town_slug": "rasnov",
            "type": "livestock_incident",
            "description": "Livestock pressure — precise coords must not leak.",
            "location_label": "Foothill farm",
            "latitude": 45.6010,
            "longitude": 25.4720,
        },
    )
    assert submit.status_code == 200
    report_id = submit.json()["report"]["id"]
    client.post(
        f"/api/bearsmart/moderation/reports/{report_id}/review",
        headers={"X-Demo-Role": "moderator"},
        json={"action": "approve"},
    )
    public = client.get("/api/bearsmart/map").json()
    match = next((r for r in public["reports"] if r["id"] == report_id), None)
    assert match is not None
    # Livestock reports must never expose a radius and must not leak the
    # submitted coordinates.
    assert match["public_radius_m"] is None
    assert match["public_lat"] != 45.6010
    assert match["public_lng"] != 25.4720


def test_moderation_stats_endpoint_returns_sla_breakdown():
    stats = client.get(
        "/api/bearsmart/moderation/stats",
        headers={"X-Demo-Role": "moderator"},
    )
    assert stats.status_code == 200
    data = stats.json()
    assert "median_age_seconds" in data
    assert "p90_age_seconds" in data
    assert data["sla_in_season_seconds"] == 6 * 3600
    assert data["sla_off_season_seconds"] == 24 * 3600
    assert "over_sla_in_season" in data


def test_moderation_queue_items_expose_age_fields():
    queue = client.get(
        "/api/bearsmart/moderation/reports",
        headers={"X-Demo-Role": "moderator"},
    )
    assert queue.status_code == 200
    items = queue.json()["items"]
    assert items, "expected at least one moderation item from seeded data"
    for item in items:
        assert "age_seconds" in item
        assert "age_hours" in item
        assert item["age_seconds"] >= 0


def test_styles_css_does_not_introduce_decorative_1px_borders_in_new_blocks():
    # Definition-of-done: /grep "1px solid" against the H0/H1 additions must
    # not find any inside the new bottom-sheet / gate / SLA blocks.
    with open(
        "app/static/bearsmart/styles.css", "r", encoding="utf-8"
    ) as handle:
        css = handle.read()
    start = css.find("H1.2 — Now / Plan / Report bottom sheet")
    assert start > 0, "H1.2 block missing"
    snippet = css[start:]
    assert "1px solid" not in snippet
