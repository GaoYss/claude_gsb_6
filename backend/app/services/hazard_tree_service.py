"""危树排查业务逻辑。"""

from sqlalchemy import func, or_

from ..constants import DISPOSAL_MEASURE, ENUM_GROUPS
from ..errors import ConflictError, ValidationError
from ..extensions import db
from ..models import GreenSpace, HazardReinspection, HazardTree, MaintenanceRecord
from ..models.hazard_tree import OPEN_STATUSES
from ..models.mixins import utcnow
from ..utils.dates import today
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import daily_prefix
from .maintenance_task_service import MaintenanceTaskService

# 风险等级 → 排危任务优先级
RISK_TO_PRIORITY = {"low": "medium", "medium": "high", "high": "urgent"}


class HazardTreeService(BaseService):
    """危树登记：排查建档、排危任务生成、处置流转与复检闭环。"""

    model = HazardTree
    label = "危树"
    code_field = "hazard_no"
    code_width = 3

    SORTABLE = {
        "found_date": HazardTree.found_date,
        "dispose_deadline": HazardTree.dispose_deadline,
        "hazard_no": HazardTree.hazard_no,
        "created_at": HazardTree.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return daily_prefix("HT")

    # ------------------------------------------------------------ 校验
    @classmethod
    def prepare_instance(cls, instance, payload):
        green_space_id = payload.get("green_space_id", instance.green_space_id)
        space = db.session.get(GreenSpace, green_space_id) if green_space_id else None
        if space is None:
            raise ValidationError("登记失败", details={"green_space_id": "所选绿地不存在"})
        if space.status == "archived":
            raise ConflictError(f"绿地「{space.name}」已归档，不能再登记危树")

        record_id = payload.get("maintenance_record_id", instance.maintenance_record_id)
        if record_id:
            record = db.session.get(MaintenanceRecord, record_id)
            if record is None:
                raise ValidationError(
                    "登记失败", details={"maintenance_record_id": "所选巡查记录不存在"}
                )
            if record.green_space_id != green_space_id:
                raise ValidationError(
                    "登记失败",
                    details={"maintenance_record_id": "巡查记录与危树必须属于同一绿地"},
                )

    @classmethod
    def apply_derived(cls, instance):
        """闭环时间与状态保持一致：闭环即写入时间，撤销闭环即清空。"""

        if instance.status == "closed":
            if instance.closed_at is None:
                instance.closed_at = utcnow()
        else:
            instance.closed_at = None

    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("green_space_id"):
            query = query.filter(HazardTree.green_space_id == filters["green_space_id"])
        if filters.get("status"):
            query = query.filter(HazardTree.status == filters["status"])
        if filters.get("risk_level"):
            query = query.filter(HazardTree.risk_level == filters["risk_level"])
        if filters.get("hazard_type"):
            query = query.filter(HazardTree.hazard_type == filters["hazard_type"])
        if filters.get("source"):
            query = query.filter(HazardTree.source == filters["source"])
        if filters.get("date_from"):
            query = query.filter(HazardTree.found_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(HazardTree.found_date <= filters["date_to"])
        if filters.get("open_only"):
            query = query.filter(HazardTree.status.in_(OPEN_STATUSES))
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    HazardTree.hazard_no.like(like),
                    HazardTree.tree_name.like(like),
                    HazardTree.location.like(like),
                    HazardTree.inspector.like(like),
                    HazardTree.judgment_basis.like(like),
                )
            )
        return query

    # ------------------------------------------------------------ 查询
    @classmethod
    def list_hazards(cls, filters, args):
        query = db.session.query(HazardTree)
        query = cls._apply_filters(query, filters)
        query = query.order_by(parse_sort(args, cls.SORTABLE, HazardTree.found_date.desc()))
        return query

    @classmethod
    def serialize_row(cls, hazard):
        return hazard.to_dict()

    @classmethod
    def detail(cls, obj_id):
        return cls.get(obj_id).to_dict(detail=True)

    @classmethod
    def status_summary(cls):
        rows = (
            db.session.query(HazardTree.status, func.count(HazardTree.id))
            .group_by(HazardTree.status)
            .all()
        )
        summary = {code: 0 for code in ENUM_GROUPS["hazard_status"].values}
        for status, count in rows:
            summary[status] = count
        summary["open_count"] = sum(summary.get(code, 0) for code in OPEN_STATUSES)
        return summary

    # ------------------------------------------------------------ 状态流转
    @classmethod
    def change_status(cls, obj_id, payload):
        """手动流转处置状态。

        规则：「已闭环」只能由复检合格自动到达，不允许手动设置；
        已闭环的危树不允许再手动变更状态。
        """

        hazard = cls.get(obj_id)
        status = payload["status"]
        if status == "closed":
            raise ValidationError(
                "「已闭环」需登记复检且结论合格后才能到达，不能手动设置",
                details={"status": "请通过复检登记完成闭环"},
            )
        if hazard.status == "closed":
            raise ConflictError("该危树已闭环，不能再变更处置状态")
        if payload.get("remark") is not None:
            hazard.remark = payload["remark"]
        hazard.status = status
        hazard.closed_at = None
        db.session.commit()
        return hazard

    # ------------------------------------------------------------ 排危任务
    @classmethod
    def generate_task(cls, obj_id, payload):
        """按危树登记信息生成排危任务，并联动处置状态。"""

        hazard = cls.get(obj_id)
        if hazard.task_id:
            raise ConflictError("该危树已生成排危任务，请勿重复生成")
        if hazard.status == "closed":
            raise ConflictError("该危树已闭环，无需再生成排危任务")

        measure_label = DISPOSAL_MEASURE.label(hazard.disposal_measure)
        description_parts = [
            f"【风险类型】{hazard.hazard_type and ENUM_GROUPS['hazard_type'].label(hazard.hazard_type)}"
            f"，风险等级：{ENUM_GROUPS['hazard_risk_level'].label(hazard.risk_level)}",
            f"【判定依据】{hazard.judgment_basis}",
            f"【处置措施】{measure_label}",
        ]
        if hazard.disposal_requirement:
            description_parts.append(f"【处置要求】{hazard.disposal_requirement}")

        task = MaintenanceTaskService.create({
            "green_space_id": hazard.green_space_id,
            "title": f"危树排危：{hazard.tree_name}（{hazard.hazard_no}）",
            "task_type": "hazard",
            "plan_date": payload.get("plan_date") or hazard.dispose_deadline or today(),
            "priority": RISK_TO_PRIORITY.get(hazard.risk_level, "high"),
            "executor": payload.get("executor"),
            "description": "\n".join(description_parts),
        })
        hazard.task_id = task.id
        if hazard.status == "pending":
            hazard.status = "in_progress"
        db.session.commit()
        return hazard

    # ------------------------------------------------------------ 复检闭环
    @classmethod
    def add_reinspection(cls, obj_id, payload):
        """登记复检结论：合格即闭环，不合格退回处置中。"""

        hazard = cls.get(obj_id)
        if hazard.status != "resolved":
            raise ConflictError("仅「待复检」状态的危树可登记复检结论，请先将处置状态转为待复检")

        item = HazardReinspection(hazard_tree_id=hazard.id, **payload)
        db.session.add(item)
        if payload["result"] == "passed":
            hazard.status = "closed"
            hazard.closed_at = utcnow()
        else:
            hazard.status = "in_progress"
            hazard.closed_at = None
        db.session.commit()
        return item

    # ------------------------------------------------------------ 删除
    @classmethod
    def delete(cls, obj_id):
        hazard = cls.get(obj_id)
        # 复检记录随危树级联删除；已生成的排危任务保留为普通养护任务
        had_task = bool(hazard.task_id)
        db.session.delete(hazard)
        db.session.commit()
        return {"detached_task": had_task}
