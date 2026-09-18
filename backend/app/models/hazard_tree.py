"""危树排查模型。"""

from ..constants import (
    DISPOSAL_MEASURE,
    HAZARD_RISK_LEVEL,
    HAZARD_SOURCE,
    HAZARD_STATUS,
    HAZARD_TYPE,
    RECHECK_RESULT,
    TASK_STATUS,
)
from ..extensions import db
from ..utils.dates import format_date, format_datetime
from .mixins import TimestampMixin

# 未闭环状态：待处置、处置中、待复检
OPEN_STATUSES = ("pending", "in_progress", "resolved")


class HazardTree(TimestampMixin, db.Model):
    """危树登记：巡查或专项排查中判定存在倒伏、折枝风险的树木。"""

    __tablename__ = "hazard_tree"

    id = db.Column(db.Integer, primary_key=True)
    hazard_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    green_space_id = db.Column(
        db.Integer, db.ForeignKey("green_space.id", ondelete="CASCADE"), nullable=False, index=True
    )
    maintenance_record_id = db.Column(
        db.Integer,
        db.ForeignKey("maintenance_record.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("maintenance_task.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tree_name = db.Column(db.String(64), nullable=False)
    tree_count = db.Column(db.Integer, nullable=False, default=1)
    location = db.Column(db.String(255))
    source = db.Column(db.String(16), nullable=False, default="patrol", index=True)
    found_date = db.Column(db.Date, nullable=False, index=True)
    hazard_type = db.Column(db.String(16), nullable=False, index=True)
    risk_level = db.Column(db.String(16), nullable=False, index=True)
    judgment_basis = db.Column(db.Text, nullable=False)
    disposal_measure = db.Column(db.String(16), nullable=False)
    disposal_requirement = db.Column(db.Text)
    dispose_deadline = db.Column(db.Date)
    inspector = db.Column(db.String(64))
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    closed_at = db.Column(db.DateTime)
    remark = db.Column(db.Text)

    green_space = db.relationship("GreenSpace", back_populates="hazard_trees", lazy="joined")
    maintenance_record = db.relationship("MaintenanceRecord", lazy="joined")
    task = db.relationship("MaintenanceTask", lazy="joined")
    reinspections = db.relationship(
        "HazardReinspection",
        back_populates="hazard_tree",
        cascade="all, delete-orphan",
        order_by="HazardReinspection.recheck_date.desc(), HazardReinspection.id.desc()",
    )

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "hazard_no": self.hazard_no,
            "green_space_id": self.green_space_id,
            "green_space": self.green_space.to_brief() if self.green_space else None,
            "maintenance_record_id": self.maintenance_record_id,
            "task_id": self.task_id,
            "task": (
                {
                    "id": self.task.id,
                    "task_no": self.task.task_no,
                    "title": self.task.title,
                    "status": self.task.status,
                    "status_label": TASK_STATUS.label(self.task.status),
                }
                if self.task
                else None
            ),
            "tree_name": self.tree_name,
            "tree_count": self.tree_count,
            "location": self.location,
            "source": self.source,
            "source_label": HAZARD_SOURCE.label(self.source),
            "found_date": format_date(self.found_date),
            "hazard_type": self.hazard_type,
            "hazard_type_label": HAZARD_TYPE.label(self.hazard_type),
            "risk_level": self.risk_level,
            "risk_level_label": HAZARD_RISK_LEVEL.label(self.risk_level),
            "disposal_measure": self.disposal_measure,
            "disposal_measure_label": DISPOSAL_MEASURE.label(self.disposal_measure),
            "dispose_deadline": format_date(self.dispose_deadline),
            "inspector": self.inspector,
            "status": self.status,
            "status_label": HAZARD_STATUS.label(self.status),
            "closed_at": format_datetime(self.closed_at),
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["judgment_basis"] = self.judgment_basis
            data["disposal_requirement"] = self.disposal_requirement
            data["remark"] = self.remark
            data["reinspections"] = [item.to_dict() for item in self.reinspections]
        return data


class HazardReinspection(TimestampMixin, db.Model):
    """危树复检记录：处置完成后的复检结论，合格即闭环。"""

    __tablename__ = "hazard_reinspection"

    id = db.Column(db.Integer, primary_key=True)
    hazard_tree_id = db.Column(
        db.Integer, db.ForeignKey("hazard_tree.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recheck_date = db.Column(db.Date, nullable=False)
    result = db.Column(db.String(16), nullable=False)
    inspector = db.Column(db.String(64))
    note = db.Column(db.Text)

    hazard_tree = db.relationship("HazardTree", back_populates="reinspections")

    def to_dict(self):
        return {
            "id": self.id,
            "hazard_tree_id": self.hazard_tree_id,
            "recheck_date": format_date(self.recheck_date),
            "result": self.result,
            "result_label": RECHECK_RESULT.label(self.result),
            "inspector": self.inspector,
            "note": self.note,
            "created_at": format_datetime(self.created_at),
        }
