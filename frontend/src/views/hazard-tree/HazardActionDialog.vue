<template>
  <el-dialog :model-value="visible" :title="title" width="640px" top="10vh"
             destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
      <el-form-item v-if="mode === 'disposal'" label="处置措施" prop="disposal_action"
                    :error="fieldErrors.disposal_action">
        <el-select v-model="form.disposal_action" placeholder="请选择实际采取的处置措施" style="width: 100%">
          <el-option v-for="item in actionOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-row :gutter="16">
        <el-col v-if="mode === 'disposal'" :span="12">
          <el-form-item label="处置日期" prop="disposal_date" :error="fieldErrors.disposal_date">
            <el-date-picker v-model="form.disposal_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择处置日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col v-if="mode === 'disposal'" :span="12">
          <el-form-item label="处置班组" :error="fieldErrors.disposer">
            <el-input v-model="form.disposer" placeholder="如：应急排危班" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col v-if="mode === 'recheck'" :span="12">
          <el-form-item label="复检结论" prop="recheck_result" :error="fieldErrors.recheck_result">
            <el-radio-group v-model="form.recheck_result">
              <el-radio-button v-for="item in resultOptions" :key="item.value" :value="item.value">
                {{ item.label }}
              </el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-col>
        <el-col v-if="mode === 'recheck'" :span="12">
          <el-form-item label="复检日期" prop="recheck_date" :error="fieldErrors.recheck_date">
            <el-date-picker v-model="form.recheck_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择复检日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col v-if="mode === 'recheck'" :span="12">
          <el-form-item label="复检人" :error="fieldErrors.rechecker">
            <el-input v-model="form.rechecker" placeholder="复检负责人" maxlength="64" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item v-if="mode === 'disposal'" label="处置情况" :error="fieldErrors.disposal_note">
        <el-input v-model="form.disposal_note" type="textarea" :rows="3" maxlength="2000"
                  placeholder="现场支撑/截枝/伐除等处置完成情况，材料与清运情况" />
      </el-form-item>
      <el-form-item v-if="mode === 'recheck'" label="复检说明" :error="fieldErrors.recheck_note">
        <el-input v-model="form.recheck_note" type="textarea" :rows="3" maxlength="2000"
                  :placeholder="form.recheck_result === 'failed'
                    ? '复检不合格：说明仍存在的风险与再次处置要求'
                    : '复检合格：说明树体稳定、隐患消除情况'" />
      </el-form-item>
      <el-alert v-if="mode === 'recheck' && form.recheck_result === 'failed'" type="error" :closable="false"
                show-icon title="复检不合格将退回「排危中」，需再次处置后重新提交复检。" />
      <el-alert v-if="mode === 'recheck' && form.recheck_result === 'passed'" type="success" :closable="false"
                show-icon title="复检合格后危树将标记「已闭环」，排危任务同步完成。" />
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">
        {{ mode === 'disposal' ? '提交处置情况' : '提交复检结论' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { hazardousTreeApi } from '@/api'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { today } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: actionOptions } = useEnumOptions('disposal_action')
const { options: resultOptions } = useEnumOptions('recheck_result')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const mode = ref('disposal')
const currentId = ref(null)
const fieldErrors = ref({})
const form = reactive({})

const title = computed(() => (mode.value === 'disposal' ? '登记排危处置情况' : '登记复检结论'))

const rules = computed(() =>
  mode.value === 'disposal'
    ? { disposal_action: [{ required: true, message: '请选择处置措施', trigger: 'change' }] }
    : { recheck_result: [{ required: true, message: '请选择复检结论', trigger: 'change' }] },
)

function open(nextMode, id) {
  mode.value = nextMode
  currentId.value = id
  fieldErrors.value = {}
  Object.keys(form).forEach((key) => delete form[key])
  if (nextMode === 'disposal') {
    Object.assign(form, {
      disposal_action: 'support',
      disposal_date: today(),
      disposer: '',
      disposal_note: '',
    })
  } else {
    Object.assign(form, {
      recheck_result: 'passed',
      recheck_date: today(),
      rechecker: '',
      recheck_note: '',
    })
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
  try {
    if (mode.value === 'disposal') {
      await hazardousTreeApi.registerDisposal(currentId.value, { ...form })
      ElMessage.success('处置情况已登记，危树进入待复检')
    } else {
      await hazardousTreeApi.registerRecheck(currentId.value, { ...form })
      ElMessage.success(
        form.recheck_result === 'passed' ? '复检合格，危树已闭环' : '复检不合格，已退回排危中',
      )
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
