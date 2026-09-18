"""危树排查模块测试。

覆盖：登记自动建单、风险等级映射、处置/复检流转闭环、复检不合格返工、
删除保护、列表过滤与汇总、看板与绿地台账计数、演示数据自洽。
"""

from datetime import date, timedelta


def hazard_payload(space_id, **overrides):
    payload = {
        "green_space_id": space_id,
        "tree_name": "倾斜香樟",
        "location": "北门行道第 3 株",
        "risk_type": "fall",
        "risk_level": "major",
        "source": "patrol",
        "inspect_date": "2026-03-10",
        "inspector": "王海涛",
        "basis": "雨后树干倾斜 20°，根部土壤开裂隆起。",
        "requirement": "24 小时内支撑或伐除。",
    }
    payload.update(overrides)
    return payload


def test_register_hazard_auto_creates_task(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/hazardous-trees", hazard_payload(space.id)), 201)
    assert data["tree_no"] == f"HT-{date.today():%Y%m%d}-001"
    assert data["status"] == "pending"
    assert data["is_closed"] is False
    assert data["risk_level_label"] == "重大风险"

    # 自动生成排危任务：类型、优先级、计划日期（重大风险 +1 天）与双向关联
    task = data["task"]
    assert task["status"] == "pending"
    assert data["maintenance_task_id"] == task["id"]
    full = api.data(api.get(f"/api/v1/hazardous-trees/{data['id']}"))
    assert full["task_detail"]["task_type"] == "hazard"
    assert full["task_detail"]["priority"] == "urgent"
    # 重大风险处置期限为排查日后 1 天
    assert full["task_detail"]["plan_date"] == "2026-03-11"
    assert full["task_detail"]["green_space"]["id"] == space.id


def test_risk_level_priority_and_deadline_mapping(api, make_space):
    space = make_space()
    inspect = date(2026, 3, 10)

    major = api.data(api.post(
        "/api/v1/hazardous-trees",
        hazard_payload(space.id, tree_name="重大危树", risk_level="major", inspect_date="2026-03-10"),
    ), 201)
    significant = api.data(api.post(
        "/api/v1/hazardous-trees",
        hazard_payload(space.id, tree_name="较大危树", risk_level="significant",
                       inspect_date="2026-03-10"),
    ), 201)
    general = api.data(api.post(
        "/api/v1/hazardous-trees",
        hazard_payload(space.id, tree_name="一般危树", risk_level="general",
                       inspect_date="2026-03-10"),
    ), 201)

    assert major["task"]["id"] != significant["task"]["id"]
    assert api.data(api.get(f"/api/v1/hazardous-trees/{major['id']}"))["task_detail"]["priority"] == "urgent"
    assert api.data(api.get(f"/api/v1/hazardous-trees/{significant['id']}"))["task_detail"]["priority"] == "high"
    assert api.data(api.get(f"/api/v1/hazardous-trees/{general['id']}"))["task_detail"]["plan_date"] == "2026-03-17"
    assert inspect  # 排查日期供后续场景复用


def test_disposal_moves_to_recheck(api, make_hazard):
    tree = make_hazard(risk_level="general")
    data = api.data(api.patch(f"/api/v1/hazardous-trees/{tree.id}/disposal", {
        "disposal_action": "support",
        "disposal_date": "2026-03-11",
        "disposer": "应急排危班",
        "disposal_note": "已架设三角支撑。",
    }))
    assert data["status"] == "recheck"
    assert data["disposal_action_label"] == "支撑加固"
    assert data["disposal_note"] == "已架设三角支撑。"
    # 排危任务随之进入进行中
    assert data["task"]["status"] == "in_progress"


def test_recheck_passed_closes_hazard_and_completes_task(api, make_hazard):
    tree = make_hazard(risk_level="general")
    api.data(api.patch(f"/api/v1/hazardous-trees/{tree.id}/disposal",
                       {"disposal_action": "support"}))
    data = api.data(api.patch(f"/api/v1/hazardous-trees/{tree.id}/recheck", {
        "recheck_result": "passed",
        "recheck_date": "2026-03-14",
        "rechecker": "李建民",
        "recheck_note": "支撑牢固，树体稳定。",
    }))
    assert data["status"] == "closed"
    assert data["is_closed"] is True
    assert data["recheck_result_label"] == "复检合格"
    assert data["task"]["status"] == "completed"


def test_recheck_failed_returns_to_processing(api, make_hazard):
    tree = make_hazard(risk_level="general")
    api.data(api.patch(f"/api/v1/hazardous-trees/{tree.id}/disposal",
                       {"disposal_action": "prune"}))
    data = api.data(api.patch(f"/api/v1/hazardous-trees/{tree.id}/recheck", {
        "recheck_result": "failed",
        "recheck_note": "支撑松动，需重新加固。",
    }))
    assert data["status"] == "processing"
    assert data["is_closed"] is False
    assert data["task"]["status"] == "in_progress"

    # 再次处置并复检合格后闭环
    api.data(api.patch(f"/api/v1/hazardous-trees/{tree.id}/disposal",
                       {"disposal_action": "support"}))
    data = api.data(api.patch(f"/api/v1/hazardous-trees/{tree.id}/recheck",
                              {"recheck_result": "passed"}))
    assert data["status"] == "closed"
    assert data["task"]["status"] == "completed"


def test_recheck_blocked_before_disposal(api, make_hazard):
    tree = make_hazard()
    response = api.patch(f"/api/v1/hazardous-trees/{tree.id}/recheck",
                         {"recheck_result": "passed"})
    assert response.status_code == 409
    assert "待复检" in response.get_json()["message"]


def test_disposal_rejected_after_closed(api, make_hazard):
    tree = make_hazard(risk_level="general")
    api.data(api.patch(f"/api/v1/hazardous-trees/{tree.id}/disposal",
                       {"disposal_action": "support"}))
    api.data(api.patch(f"/api/v1/hazardous-trees/{tree.id}/recheck",
                       {"recheck_result": "passed"}))
    response = api.patch(f"/api/v1/hazardous-trees/{tree.id}/disposal",
                         {"disposal_action": "remove"})
    assert response.status_code == 409


def test_closed_hazard_cannot_be_edited(api, make_hazard):
    tree = make_hazard(risk_level="general")
    api.data(api.patch(f"/api/v1/hazardous-trees/{tree.id}/disposal",
                       {"disposal_action": "support"}))
    api.data(api.patch(f"/api/v1/hazardous-trees/{tree.id}/recheck",
                       {"recheck_result": "passed"}))
    response = api.put(f"/api/v1/hazardous-trees/{tree.id}",
                       hazard_payload(tree.green_space_id, basis="改一下依据"))
    assert response.status_code == 409
    assert "闭环" in response.get_json()["message"]


def test_unqualified_task_record_blocks_hazard_closure(app, api, make_hazard, make_record):
    from app.extensions import db
    from app.models import MaintenanceTask

    tree = make_hazard(risk_level="general")
    task = db.session.get(MaintenanceTask, tree.maintenance_task_id)
    make_record(task=task, quality_result="unqualified")

    api.data(api.patch(f"/api/v1/hazardous-trees/{tree.id}/disposal",
                       {"disposal_action": "support"}))
    response = api.patch(f"/api/v1/hazardous-trees/{tree.id}/recheck",
                         {"recheck_result": "passed"})
    assert response.status_code == 409
    assert "不合格养护记录" in response.get_json()["message"]


def test_register_validates_fields_and_green_space(api):
    response = api.post("/api/v1/hazardous-trees", {"tree_name": "只有名字"})
    assert response.status_code == 422
    body = response.get_json()["data"]
    assert {"green_space_id", "risk_type", "risk_level", "inspect_date",
            "basis", "requirement"} <= set(body)

    space_payload = hazard_payload(999)
    response = api.post("/api/v1/hazardous-trees", space_payload)
    assert response.status_code == 422
    assert response.get_json()["data"]["green_space_id"] == "所选绿地不存在"


def test_archived_space_rejects_hazard(api, make_space):
    space = make_space(status="archived")
    response = api.post("/api/v1/hazardous-trees", hazard_payload(space.id))
    assert response.status_code == 409


def test_list_filters_and_summary(api, make_space, make_hazard):
    space = make_space()
    make_hazard(space=space, risk_level="major")
    general = make_hazard(space=space, risk_level="general")
    make_hazard(risk_level="significant")  # 另一处绿地

    listing = api.data(api.get("/api/v1/hazardous-trees", green_space_id=space.id))
    assert listing["meta"]["total"] == 2

    major_only = api.data(api.get("/api/v1/hazardous-trees", risk_level="major"))
    assert major_only["meta"]["total"] == 1
    assert major_only["items"][0]["risk_level"] == "major"

    open_list = api.data(api.get("/api/v1/hazardous-trees", open="true"))
    assert open_list["meta"]["total"] == 3

    # 闭环后不再计入未闭环
    api.data(api.patch(f"/api/v1/hazardous-trees/{general.id}/disposal",
                       {"disposal_action": "support"}))
    api.data(api.patch(f"/api/v1/hazardous-trees/{general.id}/recheck",
                       {"recheck_result": "passed"}))
    after = api.data(api.get("/api/v1/hazardous-trees", open="true"))
    assert after["meta"]["total"] == 2

    summary = after["summary"]
    assert summary["total"] == 3
    assert summary["closed_count"] == 1
    assert summary["open_count"] == 2
    assert summary["by_status"]["closed"] == 1
    assert summary["open_by_level"]["general"] == 0


def test_overdue_filter_uses_task_deadline(api, make_hazard):
    # 重大风险 1 天期限，排查日为 5 天前 → 已逾期
    overdue_tree = make_hazard(risk_level="major", inspect_date=date.today() - timedelta(days=5))
    # 一般风险 7 天期限，排查日为昨天 → 未逾期
    fresh_tree = make_hazard(risk_level="general", inspect_date=date.today() - timedelta(days=1))

    overdue = api.data(api.get("/api/v1/hazardous-trees", overdue="true"))
    ids = {item["id"] for item in overdue["items"]}
    assert ids == {overdue_tree.id}
    assert fresh_tree.id not in ids


def test_delete_hazard_with_task_records_keeps_task(app, api, make_hazard, make_record):
    from app.extensions import db
    from app.models import MaintenanceTask

    tree = make_hazard()
    task_id = tree.maintenance_task_id
    task = db.session.get(MaintenanceTask, task_id)
    make_record(task=task, quality_result="qualified")

    result = api.data(api.delete(f"/api/v1/hazardous-trees/{tree.id}"))
    assert result == {"kept_task": True}
    # 排危任务仍可查到
    task_page = api.data(api.get("/api/v1/maintenance-tasks"))
    assert any(item["id"] == task_id for item in task_page["items"])


def test_delete_hazard_without_records_removes_task(api, make_hazard):
    tree = make_hazard()
    task_id = tree.maintenance_task_id
    api.data(api.delete(f"/api/v1/hazardous-trees/{tree.id}"))
    assert api.get(f"/api/v1/maintenance-tasks/{task_id}").status_code == 404


def test_delete_task_detaches_hazard(api, make_hazard):
    tree = make_hazard()
    # 无养护记录，任务可直接删除，危树解除关联但保留
    result = api.data(api.delete(f"/api/v1/maintenance-tasks/{tree.maintenance_task_id}"))
    assert result["detached_hazardous_trees"] == 1

    detail = api.data(api.get(f"/api/v1/hazardous-trees/{tree.id}"))
    assert detail["maintenance_task_id"] is None
    assert detail["task"] is None
    assert detail["task_detail"] is None


def test_green_space_profile_counts_open_hazards(api, make_space, make_hazard):
    space = make_space()
    make_hazard(space=space, risk_level="major")
    closed = make_hazard(space=space, risk_level="general")
    api.data(api.patch(f"/api/v1/hazardous-trees/{closed.id}/disposal",
                       {"disposal_action": "monitor"}))
    api.data(api.patch(f"/api/v1/hazardous-trees/{closed.id}/recheck",
                       {"recheck_result": "passed"}))

    profile = api.data(api.get(f"/api/v1/green-spaces/{space.id}/profile"))
    assert profile["statistics"]["hazard_total"] == 2
    assert profile["statistics"]["open_hazard_count"] == 1
    assert len(profile["recent_hazardous_trees"]) == 2


def test_green_space_list_shows_open_hazard_count(api, make_space, make_hazard):
    space = make_space()
    make_hazard(space=space, risk_level="major")

    listing = api.data(api.get("/api/v1/green-spaces"))
    row = next(item for item in listing["items"] if item["id"] == space.id)
    assert row["statistics"]["open_hazard_count"] == 1


def test_dashboard_overview_counts_hazards(api, make_hazard):
    make_hazard(risk_level="major")
    make_hazard(risk_level="significant")

    overview = api.data(api.get("/api/v1/statistics/overview"))
    assert overview["hazard"]["total"] == 2
    assert overview["hazard"]["open_count"] == 2
    assert overview["hazard"]["major_open_count"] == 1
    assert overview["hazard"]["closed_count"] == 0

    dashboard = api.data(api.get("/api/v1/statistics/dashboard"))
    assert {item["risk_level"] for item in dashboard["hazard_alerts"]} <= {
        "major", "significant", "general",
    }
    assert len(dashboard["hazard_alerts"]) == 2


def test_archived_space_delete_counts_hazard(api, make_hazard):
    tree = make_hazard()
    space_id = tree.green_space_id
    response = api.delete(f"/api/v1/green-spaces/{space_id}")
    assert response.status_code == 409
    assert response.get_json()["data"]["hazardous_tree"] == 1
    api.data(api.delete(f"/api/v1/green-spaces/{space_id}", force="true"))
    assert api.get(f"/api/v1/hazardous-trees/{tree.id}").status_code == 404
