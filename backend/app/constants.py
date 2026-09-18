"""业务字典。

集中维护各模块的枚举选项：模型层用于入库校验与展示文案，
接口层通过 /api/v1/meta/enums 下发给前端，避免前后端重复定义。
"""


class EnumGroup:
    """一组枚举选项：value 入库，label 用于展示。"""

    def __init__(self, name, options):
        self.name = name
        self.options = [{"value": value, "label": label} for value, label in options]
        self._labels = {value: label for value, label in options}

    @property
    def values(self):
        return list(self._labels)

    def label(self, value):
        return self._labels.get(value, value)

    def has(self, value):
        return value in self._labels

    def default(self):
        return self.options[0]["value"]

    def __contains__(self, value):
        return value in self._labels


# ---------------------------------------------------------------- 绿地台账
GREEN_SPACE_TYPE = EnumGroup("green_space_type", [
    ("park", "公园绿地"),
    ("street", "街头游园"),
    ("road", "道路绿地"),
    ("residential", "居住区绿地"),
    ("attached", "单位附属绿地"),
    ("other", "其他绿地"),
])

MAINTENANCE_GRADE = EnumGroup("maintenance_grade", [
    ("level1", "一级养护"),
    ("level2", "二级养护"),
    ("level3", "三级养护"),
])

GREEN_SPACE_STATUS = EnumGroup("green_space_status", [
    ("normal", "正常养护"),
    ("repairing", "整治提升中"),
    ("suspended", "暂停养护"),
    ("archived", "已归档"),
])

# ---------------------------------------------------------------- 养护任务
TASK_TYPE = EnumGroup("task_type", [
    ("prune", "修剪整形"),
    ("water", "浇灌排涝"),
    ("fertilize", "施肥"),
    ("pest", "病虫害防治"),
    ("weed", "除草松土"),
    ("clean", "保洁清扫"),
    ("replant", "补植补种"),
    ("winter", "防寒防冻"),
    ("hazard", "排危除险"),
    ("other", "其他养护"),
])

TASK_PRIORITY = EnumGroup("task_priority", [
    ("low", "低"),
    ("medium", "中"),
    ("high", "高"),
    ("urgent", "紧急"),
])

TASK_STATUS = EnumGroup("task_status", [
    ("pending", "待执行"),
    ("in_progress", "进行中"),
    ("completed", "已完成"),
    ("cancelled", "已取消"),
])

# ---------------------------------------------------------------- 养护记录
QUALITY_RESULT = EnumGroup("quality_result", [
    ("qualified", "合格"),
    ("pending", "待复检"),
    ("unqualified", "不合格"),
])

WEATHER = EnumGroup("weather", [
    ("sunny", "晴"),
    ("cloudy", "多云"),
    ("overcast", "阴"),
    ("rain", "雨"),
    ("snow", "雪"),
    ("windy", "大风"),
])

# ---------------------------------------------------------------- 绿植更换
PLANT_CATEGORY = EnumGroup("plant_category", [
    ("tree", "乔木"),
    ("shrub", "灌木"),
    ("flower", "草本花卉"),
    ("ground", "地被草坪"),
    ("vine", "藤本植物"),
    ("aquatic", "水生植物"),
])

REPLACEMENT_REASON = EnumGroup("replacement_reason", [
    ("dead", "枯死更换"),
    ("disease", "病虫害更换"),
    ("aging", "老化更新"),
    ("upgrade", "品种改造"),
    ("supplement", "补植补种"),
    ("design", "景观调整"),
])

OLD_PLANT_STATUS = EnumGroup("old_plant_status", [
    ("dead", "已枯死"),
    ("dying", "长势衰弱"),
    ("diseased", "感染病虫害"),
    ("aging", "老化退化"),
    ("normal", "长势正常"),
])

MEASURE_UNIT = EnumGroup("measure_unit", [
    ("plant", "株"),
    ("square_meter", "平方米"),
    ("pot", "盆"),
    ("clump", "丛"),
])

# ---------------------------------------------------------------- 危树排查
HAZARD_RISK_LEVEL = EnumGroup("hazard_risk_level", [
    ("major", "重大风险"),
    ("significant", "较大风险"),
    ("general", "一般风险"),
])

HAZARD_STATUS = EnumGroup("hazard_status", [
    ("pending", "待排危"),
    ("processing", "排危中"),
    ("recheck", "待复检"),
    ("closed", "已闭环"),
])

HAZARD_SOURCE = EnumGroup("hazard_source", [
    ("patrol", "日常巡查"),
    ("special", "专项排查"),
    ("report", "群众反映"),
    ("transfer", "上级交办"),
])

HAZARD_RISK_TYPE = EnumGroup("hazard_risk_type", [
    ("fall", "倒伏风险"),
    ("branch", "折枝风险"),
    ("lean", "树干明显倾斜"),
    ("decay", "树干腐朽中空"),
    ("root", "根系松动隆起"),
    ("deadwood", "大量枯枝枯死"),
    ("pest", "病虫害侵染"),
])

DISPOSAL_ACTION = EnumGroup("disposal_action", [
    ("support", "支撑加固"),
    ("cable", "拉索固定"),
    ("prune", "修剪截枝"),
    ("remove", "伐除清理"),
    ("transplant", "移栽"),
    ("monitor", "加密观测"),
    ("other", "其他措施"),
])

RECHECK_RESULT = EnumGroup("recheck_result", [
    ("passed", "复检合格"),
    ("failed", "复检不合格"),
])

# 前端下拉与文档共用的一份字典清单
ENUM_GROUPS = {
    "green_space_type": GREEN_SPACE_TYPE,
    "maintenance_grade": MAINTENANCE_GRADE,
    "green_space_status": GREEN_SPACE_STATUS,
    "task_type": TASK_TYPE,
    "task_priority": TASK_PRIORITY,
    "task_status": TASK_STATUS,
    "quality_result": QUALITY_RESULT,
    "weather": WEATHER,
    "plant_category": PLANT_CATEGORY,
    "replacement_reason": REPLACEMENT_REASON,
    "old_plant_status": OLD_PLANT_STATUS,
    "measure_unit": MEASURE_UNIT,
    "hazard_risk_level": HAZARD_RISK_LEVEL,
    "hazard_status": HAZARD_STATUS,
    "hazard_source": HAZARD_SOURCE,
    "hazard_risk_type": HAZARD_RISK_TYPE,
    "disposal_action": DISPOSAL_ACTION,
    "recheck_result": RECHECK_RESULT,
}


def all_enums():
    """返回全部字典，供前端下拉初始化。"""

    return {name: group.options for name, group in ENUM_GROUPS.items()}
