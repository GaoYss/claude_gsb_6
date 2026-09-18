<template>
  <el-drawer :model-value="visible" size="660px"
             :title="detail.hazard_no ? `危树 · ${detail.hazard_no}` : '危树详情'"
             @update:model-value="close">
    <div v-loading="loading" class="drawer-body">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="树种" :span="1">
          {{ detail.tree_name }}<span v-if="detail.tree_count > 1"> × {{ detail.tree_count }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="处置状态">
          <EnumTag group="hazard_status" :value="detail.status" :label="detail.status_label" />
        </el-descriptions-item>
        <el-descriptions-item label="所属绿地" :span="2">
          {{ detail.green_space ? `${detail.green_space.code} ${detail.green_space.name}` : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="具体位置">{{ detail.location || '-' }}</el-descriptions-item>
        <el-descriptions-item label="排查来源">
          <EnumTag group="hazard_source" :value="detail.source" :label="detail.source_label" />
        </el-descriptions-item>
        <el-descriptions-item label="风险类型">
          <EnumTag group="hazard_type" :value="detail.hazard_type" :label="detail.hazard_type_label" />
        </el-descriptions-item>
        <el-descriptions-item label="风险等级">
          <EnumTag group="hazard_risk_level" :value="detail.risk_level" :label="detail.risk_level_label" />
        </el-descriptions-item>
        <el-descriptions-item label="发现日期">{{ formatDate(detail.found_date) }}</el-descriptions-item>
        <el-descriptions-item label="处置时限">{{ formatDate(detail.dispose_deadline) }}</el-descriptions-item>
        <el-descriptions-item label="排查人">{{ detail.inspector || '-' }}</el-descriptions-item>
        <el-descriptions-item label="闭环时间">{{ formatDateTime(detail.closed_at) }}</el-descriptions-item>
        <el-descriptions-item label="判定依据" :span="2">{{ detail.judgment_basis || '-' }}</el-descriptions-item>
        <el-descriptions-item label="处置措施">
          <EnumTag group="disposal_measure" :value="detail.disposal_measure" :label="detail.disposal_measure_label" />
        </el-descriptions-item>
        <el-descriptions-item label="处置要求" :span="2">{{ detail.disposal_requirement || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ detail.remark || '-' }}</el-descriptions-item>
      </el-descriptions>

      <div class="panel-section">
        <div class="table-toolbar">
          <span class="panel-title">排危任务</span>
          <el-button v-if="!detail.task && detail.status !== 'closed'" type="primary" size="small"
                     @click="taskDialogVisible = true">生成排危任务</el-button>
        </div>
        <template v-if="detail.task">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="任务编号">{{ detail.task.task_no }}</el-descriptions-item>
            <el-descriptions-item label="任务状态">
              <EnumTag group="task_status" :value="detail.task.status" :label="detail.task.status_label" />
            </el-descriptions-item>
            <el-descriptions-item label="任务名称" :span="2">{{ detail.task.title }}</el-descriptions-item>
          </el-descriptions>
        </template>
        <el-alert v-else type="info" :closable="false"
                  title="尚未生成排危任务，生成后将在「养护任务」中跟踪处置进度" />
      </div>

      <div v-if="detail.status !== 'closed'" class="panel-section">
        <div class="table-toolbar"><span class="panel-title">处置流转</span></div>
        <div class="flow-actions">
          <el-button v-if="detail.status === 'pending'" type="warning" @click="changeStatus('in_progress')">
            开始处置
          </el-button>
          <el-button v-if="detail.status === 'in_progress'" type="primary" @click="changeStatus('resolved')">
            处置完成，待复检
          </el-button>
          <el-button v-if="detail.status === 'resolved'" type="success" @click="recheckVisible = !recheckVisible">
            登记复检结论
          </el-button>
          <span class="flow-hint">{{ flowHint }}</span>
        </div>
        <el-form v-if="recheckVisible && detail.status === 'resolved'" :model="recheckForm"
                 label-width="90px" class="recheck-form">
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="复检日期" required>
                <el-date-picker v-model="recheckForm.recheck_date" type="date" value-format="YYYY-MM-DD"
                                style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="复检人">
                <el-input v-model="recheckForm.inspector" maxlength="64" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="复检结论" required>
            <el-radio-group v-model="recheckForm.result">
              <el-radio-button value="passed">复检合格（闭环）</el-radio-button>
              <el-radio-button value="failed">不合格（退回处置）</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="复检意见">
            <el-input v-model="recheckForm.note" type="textarea" :rows="2" maxlength="2000" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="submitting" @click="submitRecheck">提交复检结论</el-button>
          </el-form-item>
        </el-form>
      </div>

      <div class="panel-section">
        <div class="table-toolbar"><span class="panel-title">复检记录</span></div>
        <el-table :data="detail.reinspections || []" size="small" border empty-text="暂无复检记录">
          <el-table-column prop="recheck_date" label="复检日期" width="105" />
          <el-table-column label="结论" width="110">
            <template #default="{ row }">
              <EnumTag group="recheck_result" :value="row.result" :label="row.result_label" />
            </template>
          </el-table-column>
          <el-table-column prop="inspector" label="复检人" width="100">
            <template #default="{ row }">{{ row.inspector || '-' }}</template>
          </el-table-column>
          <el-table-column prop="note" label="复检意见" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">{{ row.note || '-' }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <template #footer>
      <el-button @click="close">关闭</el-button>
    </template>

    <el-dialog v-model="taskDialogVisible" title="生成排危任务" width="440px" append-to-body destroy-on-close>
      <el-form :model="taskForm" label-width="100px">
        <el-form-item label="计划日期">
          <el-date-picker v-model="taskForm.plan_date" type="date" value-format="YYYY-MM-DD"
                          :placeholder="detail.dispose_deadline ? `默认取处置时限 ${detail.dispose_deadline}` : '选择计划处置日期'"
                          style="width: 100%" />
        </el-form-item>
        <el-form-item label="执行班组">
          <el-input v-model="taskForm.executor" placeholder="如：绿化一班" maxlength="64" />
        </el-form-item>
        <div class="form-hint">
          将按危树登记信息生成「危树排危」类型养护任务，风险等级越高任务优先级越高；生成后危树转为「处置中」。
        </div>
      </el-form>
      <template #footer>
        <el-button @click="taskDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="generateTask">生成</el-button>
      </template>
    </el-dialog>
  </el-drawer>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { hazardTreeApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import { formatDate, formatDateTime, today } from '@/utils/format'

const emit = defineEmits(['updated'])

const visible = ref(false)
const loading = ref(false)
const submitting = ref(false)
const detail = ref({})
const currentId = ref(null)
const taskDialogVisible = ref(false)
const recheckVisible = ref(false)

const taskForm = reactive({ plan_date: '', executor: '' })
const recheckForm = reactive({ recheck_date: today(), result: 'passed', inspector: '', note: '' })

const flowHint = computed(() => {
  const hints = {
    pending: '生成排危任务或手动开始处置',
    in_progress: '处置作业完成后转为「待复检」',
    resolved: '复检合格即闭环；不合格将退回「处置中」',
  }
  return hints[detail.value.status] || ''
})

async function open(id) {
  currentId.value = id
  visible.value = true
  recheckVisible.value = false
  await load()
}

async function load() {
  if (!currentId.value) return
  loading.value = true
  try {
    detail.value = await hazardTreeApi.detail(currentId.value)
  } finally {
    loading.value = false
  }
}

function close() {
  visible.value = false
}

async function changeStatus(status) {
  try {
    await hazardTreeApi.changeStatus(currentId.value, { status })
    ElMessage.success('处置状态已更新')
    await load()
    emit('updated')
  } catch {
    // 冲突提示由请求层统一处理
  }
}

async function generateTask() {
  submitting.value = true
  try {
    const payload = {}
    if (taskForm.plan_date) payload.plan_date = taskForm.plan_date
    if (taskForm.executor) payload.executor = taskForm.executor
    await hazardTreeApi.generateTask(currentId.value, payload)
    ElMessage.success('排危任务已生成')
    taskDialogVisible.value = false
    await load()
    emit('updated')
  } catch {
    // 已生成过等冲突提示由请求层统一处理
  } finally {
    submitting.value = false
  }
}

async function submitRecheck() {
  if (!recheckForm.recheck_date) {
    ElMessage.warning('请选择复检日期')
    return
  }
  submitting.value = true
  try {
    await hazardTreeApi.addReinspection(currentId.value, { ...recheckForm })
    ElMessage.success(recheckForm.result === 'passed' ? '复检合格，危树已闭环' : '复检不合格，已退回处置中')
    recheckVisible.value = false
    recheckForm.note = ''
    await load()
    emit('updated')
  } catch {
    // 状态不满足等提示由请求层统一处理
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-title {
  font-weight: 600;
}

.flow-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.flow-hint {
  color: #909399;
  font-size: 12px;
}

.recheck-form {
  margin-top: 12px;
  padding: 12px 12px 0;
  background: var(--gs-bg);
  border-radius: 6px;
}

.form-hint {
  color: #909399;
  font-size: 12px;
  line-height: 1.6;
}
</style>
