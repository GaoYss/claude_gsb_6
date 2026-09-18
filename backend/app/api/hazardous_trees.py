"""危树排查接口。"""

from flask import Blueprint, request

from ..schemas import (
    hazard_filters,
    validate_disposal,
    validate_hazardous_tree,
    validate_recheck,
)
from ..services import HazardousTreeService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("hazardous_trees", __name__)


@bp.get("/hazardous-trees")
def list_hazardous_trees():
    filters = hazard_filters(request.args)
    page, page_size = parse_page_args()
    query = HazardousTreeService.list_hazards(filters, request.args)
    data = paginate(query, page, page_size)
    data["summary"] = HazardousTreeService.summary()
    return ok(data)


@bp.post("/hazardous-trees")
def create_hazardous_tree():
    payload = validate_hazardous_tree(json_body())
    tree = HazardousTreeService.create(payload)
    return created(tree.to_dict(detail=True), message="危树登记成功，已生成排危任务")


@bp.get("/hazardous-trees/<int:tree_id>")
def get_hazardous_tree(tree_id):
    return ok(HazardousTreeService.detail(tree_id))


@bp.put("/hazardous-trees/<int:tree_id>")
def update_hazardous_tree(tree_id):
    payload = validate_hazardous_tree(json_body())
    tree = HazardousTreeService.update(tree_id, payload)
    return ok(tree.to_dict(detail=True), message="危树信息已更新")


@bp.patch("/hazardous-trees/<int:tree_id>/disposal")
def register_disposal(tree_id):
    """登记处置情况：危树进入待复检。"""

    payload = validate_disposal(json_body())
    tree = HazardousTreeService.register_disposal(tree_id, payload)
    return ok(tree.to_dict(detail=True), message="处置情况已登记，等待复检")


@bp.patch("/hazardous-trees/<int:tree_id>/recheck")
def register_recheck(tree_id):
    """登记复检结论：合格闭环，不合格退回排危中。"""

    payload = validate_recheck(json_body())
    tree = HazardousTreeService.register_recheck(tree_id, payload)
    message = "复检合格，危树已闭环" if payload["recheck_result"] == "passed" else "复检不合格，已退回排危中"
    return ok(tree.to_dict(detail=True), message=message)


@bp.delete("/hazardous-trees/<int:tree_id>")
def delete_hazardous_tree(tree_id):
    result = HazardousTreeService.delete(tree_id)
    message = "危树已删除"
    if result["kept_task"]:
        message = "危树已删除，排危任务及养护记录予以保留"
    return ok(result, message=message)
