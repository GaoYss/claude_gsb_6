"""危树排查业务逻辑。

危树登记后自动生成一张「排危除险」养护任务（maintenance_task），并按
「登记判定 → 排危处置 → 复检结论」驱动闭环：

1. 登记危树时按风险等级映射任务优先级（重大→紧急、较大→高、一般→中），
   处置期限写入任务计划日期；
2. 登记处置情况后危树进入「待复检」，排危任务同步进入「进行中」；
3. 复检合格后危树「已闭环」，排危任务完成；复检不合格退回「排危中」继续处置；
4. 未闭环（待排危/排危中/待复检）的危树在台账与看板单独计数。
"""

from datetime import timedelta

from sqlalchemy import case, func, or_

from ..constants import ENUM_GROUPS, HAZARD_RISK_LEVEL, HAZARD_RISK_TYPE, HAZARD_STATUS
from ..errors import ConflictError, ValidationError
from ..extensions import db
from ..models import GreenSpace, HazardousTree, MaintenanceRecord, MaintenanceTask
from ..models.hazardous_tree import OPEN_STATUSES
from ..models.maintenance_task import OPEN_STATUSES as TASK_OPEN_STATUSES
from ..models.mixins import utcnow
from ..utils.dates import today
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import daily_prefix

# 风险等级 → 排危任务优先级
RISK_PRIORITY = {
    "major": "urgent",
    "significant": "high",
    "general": "medium",
}

# 风险等级 → 处置期限（排查日后 N 天完成排危）
RISK_DEADLINE_DAYS = {
    "major": 1,
    "significant": 3,
    "general": 7,
}

# 列表排序时风险等级的轻重次序
RISK_ORDER = case(
    (HazardousTree.risk_level == "major", 0),
    (HazardousTree.risk_level == "significant", 1),
    (HazardousTree.risk_level == "general", 2),
)


# 列表默认：未闭环在前、风险高的在前、同级别排查日期新的在前
DEFAULT_ORDER = (
    case((HazardousTree.status == "closed", 1), else_=0),
    RISK_ORDER,
    HazardousTree.inspect_date.desc(),
)


class HazardousTreeService(BaseService):
    """危树排查：登记建单、处置复检流转与闭环统计。"""

    model = HazardousTree
    label = "危树"
    code_field = "tree_no"
    code_width = 3

    SORTABLE = {
        "inspect_date": HazardousTree.inspect_date,
        "tree_no": HazardousTree.tree_no,
        "created_at": HazardousTree.created_at,
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

        inspect_date = payload.get("inspect_date", instance.inspect_date)
        if inspect_date and space.established_date and inspect_date < space.established_date:
            raise ValidationError(
                "登记失败",
                details={"inspect_date": f"排查日期不能早于该绿地建成日期 {space.established_date}"},
            )

    @classmethod
    def prepare_update(cls, instance, payload):
        if instance.status == "closed":
            raise ConflictError("该危树已闭环，判定信息不可再修改，如需变更请先联系管理员")
        setattr(instance, "_previous_risk_level", instance.risk_level)
        cls.prepare_instance(instance, payload)

    # ------------------------------------------------------------ 自动建单
    @classmethod
    def after_create(cls, instance, payload):
        """登记危树即生成一张「排危除险」养护任务。"""

        from .maintenance_task_service import MaintenanceTaskService

        deadline_days = RISK_DEADLINE_DAYS.get(instance.risk_level, 7)
        task = MaintenanceTask(
            task_no=MaintenanceTaskService.generate_code(),
            green_space_id=instance.green_space_id,
            title=f"排危除险：{instance.tree_name}",
            task_type="hazard",
            plan_date=instance.inspect_date + timedelta(days=deadline_days),
            priority=RISK_PRIORITY.get(instance.risk_level, "medium"),
            executor=None,
            status="pending",
            description=(
                f"由危树排查单 {instance.tree_no} 自动生成。\n"
                f"风险类型：{HAZARD_RISK_TYPE.label(instance.risk_type)}；"
                f"风险等级：{HAZARD_RISK_LEVEL.label(instance.risk_level)}。\n"
                f"判定依据：{instance.basis}\n处置要求：{instance.requirement}"
            ),
        )
        db.session.add(task)
        db.session.flush()
        instance.maintenance_task_id = task.id

    @classmethod
    def after_update(cls, instance, payload):
        """风险等级或树名变更时同步排危任务（任务仍开放时）。"""

        task = instance.task
        if task is None or task.status not in TASK_OPEN_STATUSES:
            return
        if "risk_level" in payload:
            task.priority = RISK_PRIORITY.get(instance.risk_level, "medium")
        task.title = f"排危除险：{instance.tree_name}"

    # ------------------------------------------------------------ 处置 / 复检
    @classmethod
    def register_disposal(cls, obj_id, payload):
        """登记处置情况：待排危/排危中 → 待复检。"""

        tree = cls.get(obj_id)
        if tree.status == "closed":
            raise ConflictError("该危树已闭环，不能再登记处置情况")
        tree.disposal_action = payload["disposal_action"]
        tree.disposal_date = payload.get("disposal_date") or today()
        tree.disposer = payload.get("disposer")
        tree.disposal_note = payload.get("disposal_note")
        tree.status = "recheck"
        if tree.task is not None and tree.task.status == "pending":
            tree.task.status = "in_progress"
            tree.task.completed_at = None
        db.session.commit()
        return tree

    @classmethod
    def register_recheck(cls, obj_id, payload):
        """登记复检结论：合格闭环，不合格退回排危中。"""

        tree = cls.get(obj_id)
        if tree.status != "recheck":
            raise ConflictError("仅「待复检」的危树可以登记复检结论，请先登记处置情况")

        result = payload["recheck_result"]
        tree.recheck_result = result
        tree.recheck_date = payload.get("recheck_date") or today()
        tree.rechecker = payload.get("rechecker")
        tree.recheck_note = payload.get("recheck_note")

        if result == "passed":
            cls._complete_linked_task(tree)
            tree.status = "closed"
        else:
            tree.status = "processing"
            if tree.task is not None:
                tree.task.status = "in_progress"
                tree.task.completed_at = None
        db.session.commit()
        return tree

    @staticmethod
    def _complete_linked_task(tree):
        """复检合格后完成排危任务；任务下存在不合格养护记录时暂不闭环。"""

        task = tree.task
        if task is None or task.status not in TASK_OPEN_STATUSES:
            return
        unqualified = (
            db.session.query(func.count(MaintenanceRecord.id))
            .filter(
                MaintenanceRecord.task_id == task.id,
                MaintenanceRecord.quality_result == "unqualified",
            )
            .scalar()
            or 0
        )
        if unqualified:
            raise ConflictError(
                f"排危任务 {task.task_no} 存在 {unqualified} 条不合格养护记录，"
                "请整改复检合格后再提交危树复检结论"
            )
        task.status = "completed"
        task.completed_at = utcnow()

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("green_space_id"):
            query = query.filter(HazardousTree.green_space_id == filters["green_space_id"])
        if filters.get("maintenance_task_id"):
            query = query.filter(
                HazardousTree.maintenance_task_id == filters["maintenance_task_id"]
            )
        if filters.get("status"):
            query = query.filter(HazardousTree.status == filters["status"])
        if filters.get("risk_level"):
            query = query.filter(HazardousTree.risk_level == filters["risk_level"])
        if filters.get("risk_type"):
            query = query.filter(HazardousTree.risk_type == filters["risk_type"])
        if filters.get("source"):
            query = query.filter(HazardousTree.source == filters["source"])
        if filters.get("date_from"):
            query = query.filter(HazardousTree.inspect_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(HazardousTree.inspect_date <= filters["date_to"])
        if filters.get("open"):
            query = query.filter(HazardousTree.status.in_(OPEN_STATUSES))
        if filters.get("overdue"):
            query = query.join(
                MaintenanceTask,
                HazardousTree.maintenance_task_id == MaintenanceTask.id,
            ).filter(
                HazardousTree.status.in_(OPEN_STATUSES),
                MaintenanceTask.status.in_(TASK_OPEN_STATUSES),
                MaintenanceTask.plan_date < today(),
            )
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    HazardousTree.tree_no.like(like),
                    HazardousTree.tree_name.like(like),
                    HazardousTree.location.like(like),
                    HazardousTree.inspector.like(like),
                )
            )
        return query

    @classmethod
    def list_hazards(cls, filters, args):
        query = cls._apply_filters(db.session.query(HazardousTree), filters)
        order = parse_sort(args, cls.SORTABLE, DEFAULT_ORDER)
        return query.order_by(*order) if isinstance(order, tuple) else query.order_by(order)

    @classmethod
    def detail(cls, obj_id):
        tree = cls.get(obj_id)
        data = tree.to_dict(detail=True)
        if tree.task is not None:
            from .maintenance_task_service import MaintenanceTaskService

            data["task_detail"] = MaintenanceTaskService.detail(tree.maintenance_task_id)
        else:
            data["task_detail"] = None
        return data

    # ------------------------------------------------------------ 删除
    @classmethod
    def delete(cls, obj_id):
        """删除危树：排危任务无养护记录时一并删除，已有作业记录则保留任务履历。"""

        tree = cls.get(obj_id)
        task = tree.task
        detached_task = False
        if task is not None:
            record_count = (
                db.session.query(func.count(MaintenanceRecord.id))
                .filter(MaintenanceRecord.task_id == task.id)
                .scalar()
                or 0
            )
            if record_count:
                # 保留排危任务与养护履历，仅解除与危树的关联
                tree.maintenance_task_id = None
                db.session.flush()
                detached_task = True
            else:
                db.session.delete(task)
        db.session.delete(tree)
        db.session.commit()
        return {"kept_task": detached_task}

    # ------------------------------------------------------------ 汇总
    @classmethod
    def summary(cls, filters=None):
        """按状态、未闭环风险等级与逾期计数。"""

        filters = filters or {}
        base = cls._apply_filters(db.session.query(HazardousTree), filters)

        status_rows = (
            base.with_entities(HazardousTree.status, func.count(HazardousTree.id))
            .group_by(HazardousTree.status)
            .all()
        )
        by_status = {code: 0 for code in HAZARD_STATUS.values}
        for status, count in status_rows:
            by_status[status] = count

        open_rows = (
            db.session.query(HazardousTree.risk_level, func.count(HazardousTree.id))
            .filter(HazardousTree.status.in_(OPEN_STATUSES))
            .group_by(HazardousTree.risk_level)
            .all()
        )
        open_by_level = {code: 0 for code in ENUM_GROUPS["hazard_risk_level"].values}
        for level, count in open_rows:
            open_by_level[level] = count

        overdue = (
            db.session.query(func.count(HazardousTree.id))
            .join(MaintenanceTask, HazardousTree.maintenance_task_id == MaintenanceTask.id)
            .filter(
                HazardousTree.status.in_(OPEN_STATUSES),
                MaintenanceTask.status.in_(TASK_OPEN_STATUSES),
                MaintenanceTask.plan_date < today(),
            )
            .scalar()
            or 0
        )

        return {
            "total": sum(by_status.values()),
            "by_status": by_status,
            "open_count": sum(by_status[code] for code in OPEN_STATUSES),
            "closed_count": by_status["closed"],
            "open_by_level": open_by_level,
            "overdue_count": overdue,
        }

    @classmethod
    def open_alerts(cls, limit=10):
        """看板提醒：未闭环危树，按风险等级与处置期限升序。"""

        rows = (
            db.session.query(HazardousTree)
            .outerjoin(MaintenanceTask, HazardousTree.maintenance_task_id == MaintenanceTask.id)
            .filter(HazardousTree.status.in_(OPEN_STATUSES))
            .order_by(
                RISK_ORDER,
                MaintenanceTask.plan_date.is_(None),
                MaintenanceTask.plan_date.asc(),
                HazardousTree.inspect_date.desc(),
            )
            .limit(limit)
            .all()
        )
        return [item.to_dict() for item in rows]

    @classmethod
    def space_open_count(cls, space_id):
        return (
            db.session.query(func.count(HazardousTree.id))
            .filter(
                HazardousTree.green_space_id == space_id,
                HazardousTree.status.in_(OPEN_STATUSES),
            )
            .scalar()
            or 0
        )
