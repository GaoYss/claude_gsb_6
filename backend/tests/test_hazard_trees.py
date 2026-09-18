"""危树排查接口测试。"""

from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import HazardReinspection, MaintenanceTask


def hazard_payload(space_id, **overrides):
    payload = {
        "green_space_id": space_id,
        "tree_name": "香樟",
        "tree_count": 1,
        "location": "东侧园路口",
        "source": "patrol",
        "found_date": str(date.today() - timedelta(days=10)),
        "hazard_type": "topple",
        "risk_level": "high",
        "judgment_basis": "树干基部腐朽空洞，树体倾斜约 15°",
        "disposal_measure": "fell",
        "disposal_requirement": "尽快砍伐移除并补植",
        "dispose_deadline": str(date.today() + timedelta(days=7)),
        "inspector": "王海涛",
    }
    payload.update(overrides)
    return payload


@pytest.fixture()
def make_hazard(api, make_space):
    def _make(space=None, **overrides):
        space = space or make_space()
        payload = hazard_payload(space.id, **overrides)
        return api.data(api.post("/api/v1/hazard-trees", json=payload), 201)

    return _make


def test_create_validation(api, make_space):
    space = make_space()
    response = api.post("/api/v1/hazard-trees", json={"green_space_id": space.id})
    assert response.status_code == 422
    errors = response.get_json()["data"]
    assert "tree_name" in errors
    assert "hazard_type" in errors
    assert "risk_level" in errors
    assert "judgment_basis" in errors
    assert "disposal_measure" in errors

    response = api.post("/api/v1/hazard-trees", json=hazard_payload(9999))
    assert response.status_code == 422


def test_create_on_archived_space_is_blocked(api, make_space):
    space = make_space(status="archived")
    response = api.post("/api/v1/hazard-trees", json=hazard_payload(space.id))
    assert response.status_code == 409


def test_record_link_must_match_green_space(api, make_space, make_record):
    space, other_space = make_space(), make_space()
    record = make_record(space=other_space)
    response = api.post(
        "/api/v1/hazard-trees",
        json=hazard_payload(space.id, maintenance_record_id=record.id),
    )
    assert response.status_code == 422


def test_full_close_loop(api, make_hazard):
    hazard = make_hazard(risk_level="high")
    assert hazard["status"] == "pending"
    assert hazard["hazard_no"].startswith("HT-")

    # 生成排危任务：类型为危树排危，重大风险映射为紧急，危树转为处置中
    hazard = api.data(api.post(f"/api/v1/hazard-trees/{hazard['id']}/generate-task", json={}), 201)
    assert hazard["status"] == "in_progress"
    assert hazard["task"]["task_no"].startswith("MT-")
    task_id = hazard["task_id"]

    task = db.session.get(MaintenanceTask, task_id)
    assert task.task_type == "hazard"
    assert task.priority == "urgent"
    assert "判定依据" in task.description

    # 重复生成被拒绝
    response = api.post(f"/api/v1/hazard-trees/{hazard['id']}/generate-task", json={})
    assert response.status_code == 409

    # 处置完成 → 待复检
    hazard = api.data(
        api.patch(f"/api/v1/hazard-trees/{hazard['id']}/status", json={"status": "resolved"})
    )
    assert hazard["status"] == "resolved"

    # 复检合格 → 已闭环
    hazard = api.data(
        api.post(
            f"/api/v1/hazard-trees/{hazard['id']}/reinspections",
            json={"recheck_date": str(date.today()), "result": "passed", "inspector": "李建民"},
        ),
        201,
    )
    assert hazard["status"] == "closed"
    assert hazard["closed_at"]
    assert len(hazard["reinspections"]) == 1
    assert hazard["reinspections"][0]["result"] == "passed"

    # 已闭环不允许再变更状态或登记复检
    response = api.patch(f"/api/v1/hazard-trees/{hazard['id']}/status", json={"status": "pending"})
    assert response.status_code == 409
    response = api.post(
        f"/api/v1/hazard-trees/{hazard['id']}/reinspections",
        json={"recheck_date": str(date.today()), "result": "passed"},
    )
    assert response.status_code == 409


def test_failed_recheck_returns_to_in_progress(api, make_hazard):
    hazard = make_hazard()
    api.data(api.post(f"/api/v1/hazard-trees/{hazard['id']}/generate-task", json={}), 201)
    api.data(api.patch(f"/api/v1/hazard-trees/{hazard['id']}/status", json={"status": "resolved"}))

    hazard = api.data(
        api.post(
            f"/api/v1/hazard-trees/{hazard['id']}/reinspections",
            json={"recheck_date": str(date.today()), "result": "failed", "note": "支撑仍松动"},
        ),
        201,
    )
    assert hazard["status"] == "in_progress"
    assert hazard["closed_at"] is None


def test_manual_closed_is_rejected(api, make_hazard):
    hazard = make_hazard()
    response = api.patch(f"/api/v1/hazard-trees/{hazard['id']}/status", json={"status": "closed"})
    assert response.status_code == 422


def test_recheck_requires_resolved_status(api, make_hazard):
    hazard = make_hazard()
    response = api.post(
        f"/api/v1/hazard-trees/{hazard['id']}/reinspections",
        json={"recheck_date": str(date.today()), "result": "passed"},
    )
    assert response.status_code == 409


def test_open_hazard_counting(api, make_space, make_hazard):
    space = make_space()
    open_one = make_hazard(space=space, risk_level="high")
    closed_one = make_hazard(space=space, risk_level="low")
    make_hazard(risk_level="medium")  # 其他绿地的危树不计入本绿地台账

    # 闭环其中一株
    hazard_id = closed_one["id"]
    api.data(api.post(f"/api/v1/hazard-trees/{hazard_id}/generate-task", json={}), 201)
    api.data(api.patch(f"/api/v1/hazard-trees/{hazard_id}/status", json={"status": "resolved"}))
    api.data(
        api.post(
            f"/api/v1/hazard-trees/{hazard_id}/reinspections",
            json={"recheck_date": str(date.today()), "result": "passed"},
        ),
        201,
    )

    # 台账列表与详情单独计数未闭环危树
    spaces = api.data(api.get("/api/v1/green-spaces"))
    row = next(item for item in spaces["items"] if item["id"] == space.id)
    assert row["statistics"]["open_hazard_count"] == 1

    detail = api.data(api.get(f"/api/v1/green-spaces/{space.id}/profile"))
    assert detail["statistics"]["open_hazard_count"] == 1
    assert detail["statistics"]["hazard_status"]["closed"] == 1
    assert len(detail["recent_hazards"]) == 2

    # 看板总览与未闭环清单
    overview = api.data(api.get("/api/v1/statistics/overview"))
    assert overview["hazard"]["open_count"] == 2  # 本绿地 1 株 + 其他绿地 1 株
    assert overview["hazard"]["high_open_count"] == 1
    assert overview["hazard"]["by_status"]["closed"] == 1

    dashboard = api.data(api.get("/api/v1/statistics/dashboard"))
    open_ids = {item["id"] for item in dashboard["open_hazards"]}
    assert open_one["id"] in open_ids
    assert closed_one["id"] not in open_ids

    # 列表仅看未闭环
    data = api.data(api.get("/api/v1/hazard-trees", open_only="true"))
    assert data["summary"]["open_count"] == 2
    assert all(item["status"] != "closed" for item in data["items"])


def test_delete_keeps_generated_task(api, make_hazard):
    hazard = make_hazard()
    hazard = api.data(api.post(f"/api/v1/hazard-trees/{hazard['id']}/generate-task", json={}), 201)
    api.data(api.patch(f"/api/v1/hazard-trees/{hazard['id']}/status", json={"status": "resolved"}))
    api.data(
        api.post(
            f"/api/v1/hazard-trees/{hazard['id']}/reinspections",
            json={"recheck_date": str(date.today()), "result": "failed"},
        ),
        201,
    )
    task_id = hazard["task_id"]

    api.data(api.delete(f"/api/v1/hazard-trees/{hazard['id']}"))
    assert api.get(f"/api/v1/hazard-trees/{hazard['id']}").status_code == 404
    # 复检记录级联删除，排危任务保留
    assert db.session.query(HazardReinspection).count() == 0
    assert db.session.get(MaintenanceTask, task_id) is not None
