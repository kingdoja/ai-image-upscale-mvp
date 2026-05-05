from app.schemas import ResultRead


def test_result_read_accepts_legacy_material_guard_results():
    result = ResultRead(
        id="res_legacy",
        type="material_guard",
        url="/storage/results/res_legacy.png",
        thumbnail_url="/storage/thumbnails/res_legacy.png",
        model_name="material_guard",
        model_version="legacy",
        quality_score=0.8,
        risk_level="low",
    )

    assert result.type == "material_guard"
