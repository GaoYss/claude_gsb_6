"""危树排查校验规则。"""

from ..constants import (
    DISPOSAL_MEASURE,
    HAZARD_RISK_LEVEL,
    HAZARD_SOURCE,
    HAZARD_STATUS,
    HAZARD_TYPE,
    RECHECK_RESULT,
)
from .common import PayloadValidator


def validate_hazard_tree(payload):
    return (
        PayloadValidator(payload)
        .string("hazard_no", "危树编号", max_length=32)
        .integer("green_space_id", "所属绿地", required=True, min_value=1)
        .integer("maintenance_record_id", "来源巡查记录", min_value=1)
        .string("tree_name", "树种名称", required=True, max_length=64)
        .integer("tree_count", "危树株数", default=1, min_value=1, max_value=9999)
        .string("location", "具体位置", max_length=255)
        .enum("source", "排查来源", group=HAZARD_SOURCE, default="patrol")
        .date("found_date", "发现日期", required=True)
        .enum("hazard_type", "风险类型", group=HAZARD_TYPE, required=True)
        .enum("risk_level", "风险等级", group=HAZARD_RISK_LEVEL, required=True)
        .text("judgment_basis", "判定依据", required=True, max_length=2000)
        .enum("disposal_measure", "处置措施", group=DISPOSAL_MEASURE, required=True)
        .text("disposal_requirement", "处置要求", max_length=2000)
        .date("dispose_deadline", "处置时限")
        .string("inspector", "排查人", max_length=64)
        .enum("status", "处置状态", group=HAZARD_STATUS, default="pending")
        .text("remark", "备注", max_length=2000)
        .done()
    )


def validate_hazard_status(payload):
    """危树状态流转：只允许变更状态与备注。"""

    return (
        PayloadValidator(payload)
        .enum("status", "处置状态", group=HAZARD_STATUS, required=True)
        .text("remark", "备注", max_length=2000)
        .done()
    )


def validate_reinspection(payload):
    """复检登记：结论决定危树是否闭环。"""

    return (
        PayloadValidator(payload)
        .date("recheck_date", "复检日期", required=True)
        .enum("result", "复检结论", group=RECHECK_RESULT, required=True)
        .string("inspector", "复检人", max_length=64)
        .text("note", "复检意见", max_length=2000)
        .done()
    )


def validate_generate_task(payload):
    """生成排危任务：计划日期与执行班组可覆盖默认值。"""

    return (
        PayloadValidator(payload)
        .date("plan_date", "计划处置日期")
        .string("executor", "执行班组/负责人", max_length=64)
        .done()
    )
