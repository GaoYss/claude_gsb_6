"""危树排查模型。"""

from ..constants import (
    DISPOSAL_ACTION,
    HAZARD_RISK_LEVEL,
    HAZARD_RISK_TYPE,
    HAZARD_SOURCE,
    HAZARD_STATUS,
    RECHECK_RESULT,
)
from ..extensions import db
from ..utils.dates import format_date, format_datetime
from .mixins import TimestampMixin

# 未闭环状态：待排危 / 排危中 / 待复检
OPEN_STATUSES = ("pending", "processing", "recheck")
CLOSED_STATUS = "closed"


class HazardousTree(TimestampMixin, db.Model):
    """危树排查登记：判定存在倒伏、折枝风险的树木及其排危闭环跟踪。"""

    __tablename__ = "hazardous_tree"

    id = db.Column(db.Integer, primary_key=True)
    tree_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    green_space_id = db.Column(
        db.Integer, db.ForeignKey("green_space.id", ondelete="CASCADE"), nullable=False, index=True
    )
    maintenance_task_id = db.Column(
        db.Integer,
        db.ForeignKey("maintenance_task.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    tree_name = db.Column(db.String(96), nullable=False, index=True)
    location = db.Column(db.String(128))
    risk_type = db.Column(db.String(32), nullable=False, index=True)
    risk_level = db.Column(db.String(16), nullable=False, index=True)
    source = db.Column(db.String(16), nullable=False, default="patrol", index=True)
    inspect_date = db.Column(db.Date, nullable=False, index=True)
    inspector = db.Column(db.String(64))
    basis = db.Column(db.Text, nullable=False)
    requirement = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    disposal_action = db.Column(db.String(32))
    disposal_note = db.Column(db.Text)
    disposer = db.Column(db.String(64))
    disposal_date = db.Column(db.Date)
    recheck_result = db.Column(db.String(16))
    recheck_note = db.Column(db.Text)
    rechecker = db.Column(db.String(64))
    recheck_date = db.Column(db.Date)
    remark = db.Column(db.Text)

    green_space = db.relationship("GreenSpace", back_populates="hazardous_trees", lazy="joined")
    task = db.relationship("MaintenanceTask", foreign_keys=[maintenance_task_id], lazy="joined")

    @property
    def is_closed(self):
        return self.status == CLOSED_STATUS

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "tree_no": self.tree_no,
            "green_space_id": self.green_space_id,
            "green_space": self.green_space.to_brief() if self.green_space else None,
            "maintenance_task_id": self.maintenance_task_id,
            "task": (
                {
                    "id": self.task.id,
                    "task_no": self.task.task_no,
                    "title": self.task.title,
                    "status": self.task.status,
                    "plan_date": format_date(self.task.plan_date),
                    "is_overdue": self.task.is_overdue,
                }
                if self.task
                else None
            ),
            "tree_name": self.tree_name,
            "location": self.location,
            "risk_type": self.risk_type,
            "risk_type_label": HAZARD_RISK_TYPE.label(self.risk_type),
            "risk_level": self.risk_level,
            "risk_level_label": HAZARD_RISK_LEVEL.label(self.risk_level),
            "source": self.source,
            "source_label": HAZARD_SOURCE.label(self.source),
            "inspect_date": format_date(self.inspect_date),
            "inspector": self.inspector,
            "basis": self.basis,
            "requirement": self.requirement,
            "status": self.status,
            "status_label": HAZARD_STATUS.label(self.status),
            "is_closed": self.is_closed,
            "disposal_action": self.disposal_action,
            "disposal_action_label": (
                DISPOSAL_ACTION.label(self.disposal_action) if self.disposal_action else None
            ),
            "disposal_date": format_date(self.disposal_date),
            "disposer": self.disposer,
            "recheck_result": self.recheck_result,
            "recheck_result_label": (
                RECHECK_RESULT.label(self.recheck_result) if self.recheck_result else None
            ),
            "recheck_date": format_date(self.recheck_date),
            "rechecker": self.rechecker,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["disposal_note"] = self.disposal_note
            data["recheck_note"] = self.recheck_note
            data["remark"] = self.remark
        return data
