"""危树排查校验规则。"""

from ..constants import (
    DISPOSAL_ACTION,
    HAZARD_RISK_LEVEL,
    HAZARD_RISK_TYPE,
    HAZARD_SOURCE,
    RECHECK_RESULT,
)
from .common import PayloadValidator


def validate_hazardous_tree(payload):
    return (
        PayloadValidator(payload)
        .string("tree_no", "危树编号", max_length=32)
        .integer("green_space_id", "所属绿地", required=True, min_value=1)
        .string("tree_name", "树木名称/编号", required=True, max_length=96)
        .string("location", "具体位置", max_length=128)
        .enum("risk_type", "风险类型", group=HAZARD_RISK_TYPE, required=True)
        .enum("risk_level", "风险等级", group=HAZARD_RISK_LEVEL, required=True)
        .enum("source", "判定来源", group=HAZARD_SOURCE, default="patrol")
        .date("inspect_date", "排查日期", required=True)
        .string("inspector", "排查人", max_length=64)
        .text("basis", "判定依据", required=True, max_length=2000)
        .text("requirement", "处置要求", required=True, max_length=2000)
        .text("remark", "备注", max_length=2000)
        .done()
    )


def validate_disposal(payload):
    """处置登记：记录处置措施与处置结果，危树随之进入待复检。"""

    return (
        PayloadValidator(payload)
        .enum("disposal_action", "处置措施", group=DISPOSAL_ACTION, required=True)
        .date("disposal_date", "处置日期")
        .string("disposer", "处置负责人/班组", max_length=64)
        .text("disposal_note", "处置情况说明", max_length=2000)
        .done()
    )


def validate_recheck(payload):
    """复检登记：复检合格闭环，不合格退回排危中。"""

    return (
        PayloadValidator(payload)
        .enum("recheck_result", "复检结论", group=RECHECK_RESULT, required=True)
        .date("recheck_date", "复检日期")
        .string("rechecker", "复检人", max_length=64)
        .text("recheck_note", "复检说明", max_length=2000)
        .done()
    )
