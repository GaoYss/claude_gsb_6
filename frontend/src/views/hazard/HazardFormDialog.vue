<template>
  <el-dialog :model-value="visible" :title="isEdit ? `编辑危树 · ${form.hazard_no}` : '登记危树'"
             width="760px" top="6vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="所属绿地" prop="green_space_id" :error="fieldErrors.green_space_id">
            <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset" placeholder="请选择绿地" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="来源巡查记录" :error="fieldErrors.maintenance_record_id">
            <RecordSelect v-model="form.maintenance_record_id" :green-space-id="form.green_space_id"
                          placeholder="可关联巡查记录（选填）" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="树种名称" prop="tree_name" :error="fieldErrors.tree_name">
            <el-input v-model="form.tree_name" placeholder="如：香樟" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="危树株数" :error="fieldErrors.tree_count">
            <el-input-number v-model="form.tree_count" :min="1" :max="9999" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="具体位置" :error="fieldErrors.location">
            <el-input v-model="form.location" placeholder="如：东侧园路口" maxlength="255" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="排查来源" :error="fieldErrors.source">
            <el-select v-model="form.source" style="width: 100%">
              <el-option v-for="item in sourceOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="发现日期" prop="found_date" :error="fieldErrors.found_date">
            <el-date-picker v-model="form.found_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择发现日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="排查人" :error="fieldErrors.inspector">
            <el-input v-model="form.inspector" placeholder="排查责任人" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="风险类型" prop="hazard_type" :error="fieldErrors.hazard_type">
            <el-select v-model="form.hazard_type" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="风险等级" prop="risk_level" :error="fieldErrors.risk_level">
            <el-select v-model="form.risk_level" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in riskOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="判定依据" prop="judgment_basis" :error="fieldErrors.judgment_basis">
        <el-input v-model="form.judgment_basis" type="textarea" :rows="3" maxlength="2000"
                  placeholder="树体状况、腐朽/倾斜/枯枝等具体表现与测量数据" />
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="处置措施" prop="disposal_measure" :error="fieldErrors.disposal_measure">
            <el-select v-model="form.disposal_measure" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in measureOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="处置时限" :error="fieldErrors.dispose_deadline">
            <el-date-picker v-model="form.dispose_deadline" type="date" value-format="YYYY-MM-DD"
                            placeholder="要求完成处置的期限" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="处置要求" :error="fieldErrors.disposal_requirement">
        <el-input v-model="form.disposal_requirement" type="textarea" :rows="2" maxlength="2000"
                  placeholder="处置作业的具体要求、安全注意事项等" />
      </el-form-item>
      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000" />
      </el-form-item>
      <div class="form-hint">
        危树编号由系统按日自动生成；登记后可在详情中生成排危任务，处置完成后登记复检结论，复检合格即闭环。
      </div>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { hazardTreeApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import RecordSelect from '@/components/common/RecordSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { today } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: sourceOptions } = useEnumOptions('hazard_source')
const { options: typeOptions } = useEnumOptions('hazard_type')
const { options: riskOptions } = useEnumOptions('hazard_risk_level')
const { options: measureOptions } = useEnumOptions('disposal_measure')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const spacePreset = ref(null)
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const rules = {
  green_space_id: [{ required: true, message: '请选择所属绿地', trigger: 'change' }],
  tree_name: [{ required: true, message: '请输入树种名称', trigger: 'blur' }],
  found_date: [{ required: true, message: '请选择发现日期', trigger: 'change' }],
  hazard_type: [{ required: true, message: '请选择风险类型', trigger: 'change' }],
  risk_level: [{ required: true, message: '请选择风险等级', trigger: 'change' }],
  judgment_basis: [{ required: true, message: '请填写判定依据', trigger: 'blur' }],
  disposal_measure: [{ required: true, message: '请选择处置措施', trigger: 'change' }],
}

function emptyForm() {
  return {
    hazard_no: '',
    green_space_id: null,
    maintenance_record_id: null,
    tree_name: '',
    tree_count: 1,
    location: '',
    source: 'patrol',
    found_date: today(),
    hazard_type: 'topple',
    risk_level: 'medium',
    judgment_basis: '',
    disposal_measure: 'prune',
    disposal_requirement: '',
    dispose_deadline: '',
    inspector: '',
    remark: '',
  }
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  spacePreset.value = null
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    form.green_space_id = row.green_space_id
    spacePreset.value = row.green_space || null
  }
  visible.value = true
}

function close() {
  visible.value = false
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  fieldErrors.value = {}
  const payload = { ...form }
  if (!payload.hazard_no) delete payload.hazard_no
  if (!payload.maintenance_record_id) delete payload.maintenance_record_id
  if (!payload.dispose_deadline) delete payload.dispose_deadline
  try {
    if (isEdit.value) {
      await hazardTreeApi.update(editingId.value, payload)
      ElMessage.success('危树信息已更新')
    } else {
      await hazardTreeApi.create(payload)
      ElMessage.success('危树登记成功')
    }
    emit('saved')
    close()
  } catch (error) {
    fieldErrors.value = error?.details || {}
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>
