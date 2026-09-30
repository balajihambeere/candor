from domains.returns.catalog import evaluate_case
from packages.candor.decide import decide
from packages.candor.models import Verdict


def test_reema_case_denied_with_two_reasons():
    record = decide(
        "defect_claim",
        {"days_since_delivery": 9, "defect_confidence": 0.61},
        evaluate_case,
    )
    assert record.verdict is Verdict.DENIED
    assert len(record.reasons) == 2
    assert {r.rule_id for r in record.failing_reasons} == {
        "WINDOW-STANDARD-01",
        "DEFECT-EXCEPTION-02",
    }


def test_kochi_case_denied_with_one_failing_reason():
    record = decide(
        "footwear",
        {"days_since_delivery": 6, "wear_confidence": 0.94},
        evaluate_case,
    )
    assert record.verdict is Verdict.DENIED
    assert len(record.reasons) == 2
    assert [r.rule_id for r in record.failing_reasons] == ["FOOTWEAR-EXCEPTION-03"]


def test_clean_case_approved():
    record = decide(
        "defect_claim",
        {"days_since_delivery": 3, "defect_confidence": 0.95},
        evaluate_case,
    )
    assert record.verdict is Verdict.APPROVED
    assert record.failing_reasons == []


def test_indore_final_sale_denied():
    record = decide(
        "final_sale",
        {"days_since_delivery": 3, "is_final_sale": True},
        evaluate_case,
    )
    assert record.verdict is Verdict.DENIED
    assert [r.rule_id for r in record.failing_reasons] == ["FINAL-SALE-EXCLUSION"]
