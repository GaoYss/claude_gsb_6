<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑危树信息 · ${form.tree_no}` : '危树排查登记'"
             width="780px" top="6vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
      <el-alert type="warning" :closable="false" show-icon class="form-alert"
                title="对巡查或专项排查中判定存在倒伏、折枝风险的树木进行登记，保存后将自动生成排危任务并跟踪处置与复检。" />
      <el-form-item label="所属绿地" prop="green_space_id" :error="fieldErrors.green_space_id">
        <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset" placeholder="请选择绿地" />
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="树木名称/编号" prop="tree_name" :error="fieldErrors.tree_name">
            <el-input v-model="form.tree_name" placeholder="如：香樟（行道第 12 株）" maxlength="96" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="具体位置" :error="fieldErrors.location">
            <el-input v-model="form.location" placeholder="如：北门游步道东侧" maxlength="128" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="风险类型" prop="risk_type" :error="fieldErrors.risk_type">
            <el-select v-model="form.risk_type" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in riskTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="风险等级" prop="risk_level" :error="fieldErrors.risk_level">
            <el-radio-group v-model="form.risk_level">
              <el-radio-button v-for="item in riskLevelOptions" :key="item.value" :value="item.value">
                {{ item.label }}
              </el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="判定来源" :error="fieldErrors.source">
            <el-select v-model="form.source" style="width: 100%">
              <el-option v-for="item in sourceOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="排查日期" prop="inspect_date" :error="fieldErrors.inspect_date">
            <el-date-picker v-model="form.inspect_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择排查日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="排查人" :error="fieldErrors.inspector">
            <el-input v-model="form.inspector" placeholder="排查/判定人" maxlength="64" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="判定依据" prop="basis" :error="fieldErrors.basis">
        <el-input v-model="form.basis" type="textarea" :rows="3" maxlength="2000" show-word-limit
                  placeholder="倾斜角度、腐朽/折枝部位、根部状况、现场照片描述等判定事实" />
      </el-form-item>
      <el-form-item label="处置要求" prop="requirement" :error="fieldErrors.requirement">
        <el-input v-model="form.requirement" type="textarea" :rows="3" maxlength="2000" show-word-limit
                  placeholder="明确处置措施、时限与现场管控要求，如：24 小时内支撑加固或伐除" />
      </el-form-item>
      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000" />
      </el-form-item>
      <div class="form-hint">
        保存后自动生成「排危除险」养护任务：重大风险 24 小时内、较大风险 3 日内、一般风险 7 日内完成，优先级随风险等级确定。
      </div>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存并生成排危任务</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { hazardousTreeApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { today } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: riskTypeOptions } = useEnumOptions('hazard_risk_type')
const { options: riskLevelOptions } = useEnumOptions('hazard_risk_level')
const { options: sourceOptions } = useEnumOptions('hazard_source')

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
  tree_name: [{ required: true, message: '请输入树木名称/编号', trigger: 'blur' }],
  risk_type: [{ required: true, message: '请选择风险类型', trigger: 'change' }],
  risk_level: [{ required: true, message: '请选择风险等级', trigger: 'change' }],
  inspect_date: [{ required: true, message: '请选择排查日期', trigger: 'change' }],
  basis: [{ required: true, message: '请填写判定依据', trigger: 'blur' }],
  requirement: [{ required: true, message: '请填写处置要求', trigger: 'blur' }],
}

function emptyForm() {
  return {
    tree_no: '',
    green_space_id: null,
    tree_name: '',
    location: '',
    risk_type: 'fall',
    risk_level: 'significant',
    source: 'patrol',
    inspect_date: today(),
    inspector: '',
    basis: '',
    requirement: '',
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
  if (!payload.tree_no) delete payload.tree_no
  try {
    if (isEdit.value) {
      await hazardousTreeApi.update(editingId.value, payload)
      ElMessage.success('危树信息已更新')
    } else {
      await hazardousTreeApi.create(payload)
      ElMessage.success('危树登记成功，已生成排危任务')
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

<style scoped>
.form-alert {
  margin-bottom: 16px;
}
</style>
