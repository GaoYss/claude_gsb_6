"""危树排查接口。"""

from flask import Blueprint, request

from ..schemas import (
    validate_generate_task,
    validate_hazard_status,
    validate_hazard_tree,
    validate_reinspection,
)
from ..schemas.filters import hazard_filters
from ..services import HazardTreeService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("hazard_trees", __name__)


@bp.get("/hazard-trees")
def list_hazards():
    filters = hazard_filters(request.args)
    page, page_size = parse_page_args()
    query = HazardTreeService.list_hazards(filters, request.args)
    data = paginate(query, page, page_size, serializer=HazardTreeService.serialize_row)
    data["summary"] = HazardTreeService.status_summary()
    return ok(data)


@bp.post("/hazard-trees")
def create_hazard():
    payload = validate_hazard_tree(json_body())
    hazard = HazardTreeService.create(payload)
    return created(hazard.to_dict(detail=True), message="危树登记成功")


@bp.get("/hazard-trees/<int:hazard_id>")
def get_hazard(hazard_id):
    return ok(HazardTreeService.detail(hazard_id))


@bp.put("/hazard-trees/<int:hazard_id>")
def update_hazard(hazard_id):
    payload = validate_hazard_tree(json_body())
    hazard = HazardTreeService.update(hazard_id, payload)
    return ok(hazard.to_dict(detail=True), message="危树信息已更新")


@bp.patch("/hazard-trees/<int:hazard_id>/status")
def change_hazard_status(hazard_id):
    """处置状态流转：待处置 / 处置中 / 待复检（已闭环只能经复检合格到达）。"""

    payload = validate_hazard_status(json_body())
    hazard = HazardTreeService.change_status(hazard_id, payload)
    return ok(hazard.to_dict(detail=True), message="处置状态已更新")


@bp.post("/hazard-trees/<int:hazard_id>/generate-task")
def generate_task(hazard_id):
    """按危树登记信息生成排危任务。"""

    payload = validate_generate_task(json_body())
    hazard = HazardTreeService.generate_task(hazard_id, payload)
    return created(hazard.to_dict(detail=True), message="排危任务已生成")


@bp.post("/hazard-trees/<int:hazard_id>/reinspections")
def add_reinspection(hazard_id):
    """登记复检结论：合格即闭环，不合格退回处置中。"""

    payload = validate_reinspection(json_body())
    HazardTreeService.add_reinspection(hazard_id, payload)
    return created(HazardTreeService.detail(hazard_id), message="复检结论已登记")


@bp.delete("/hazard-trees/<int:hazard_id>")
def delete_hazard(hazard_id):
    result = HazardTreeService.delete(hazard_id)
    return ok(result, message="危树记录已删除")
