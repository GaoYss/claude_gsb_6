<template>
  <el-drawer :model-value="visible" size="680px"
             :title="detail.tree_no ? `危树排查单 · ${detail.tree_no}` : '危树详情'"
             @update:model-value="close">
    <div v-loading="loading" class="drawer-body">
      <div class="drawer-head">
        <div>
          <span class="tree-name">{{ detail.tree_name }}</span>
          <EnumTag class="head-tag" group="hazard_status" :value="detail.status"
                   :label="detail.status_label" />
        </div>
        <div class="head-sub">
          <EnumTag group="hazard_risk_level" :value="detail.risk_level" :label="detail.risk_level_label" />
          <EnumTag group="hazard_risk_type" :value="detail.risk_type" :label="detail.risk_type_label" />
          <EnumTag group="hazard_source" :value="detail.source" :label="detail.source_label" />
        </div>
      </div>

      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="所属绿地" :span="2">
          {{ detail.green_space ? `${detail.green_space.code} ${detail.green_space.name}` : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="具体位置" :span="2">{{ detail.location || '-' }}</el-descriptions-item>
        <el-descriptions-item label="排查日期">{{ formatDate(detail.inspect_date) }}</el-descriptions-item>
        <el-descriptions-item label="排查人">{{ detail.inspector || '-' }}</el-descriptions-item>
        <el-descriptions-item label="判定依据" :span="2">{{ detail.basis }}</el-descriptions-item>
        <el-descriptions-item label="处置要求" :span="2">{{ detail.requirement }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ detail.remark || '-' }}</el-descriptions-item>
      </el-descriptions>

      <div class="panel-title">排危任务</div>
      <div v-if="detail.task" class="task-card">
        <div class="task-card__main">
          <span class="task-no">{{ detail.task.task_no }}</span>
          <span>{{ detail.task.title }}</span>
          <EnumTag group="task_status" :value="detail.task.status" />
        </div>
        <el-button link type="primary" @click="goTask">查看任务执行进度</el-button>
      </div>
      <el-empty v-else description="排危任务已被删除，仅保留危树单" :image-size="60" />

      <div class="panel-title">处置与复检</div>
      <el-timeline>
        <el-timeline-item :timestamp="formatDate(detail.inspect_date)" placement="top" type="primary">
          <el-card shadow="never">
            <h4>判定登记</h4>
            <p>{{ detail.source_label }}发现，{{ detail.risk_level_label }}（{{ detail.risk_type_label }}）</p>
            <p class="muted">{{ detail.basis }}</p>
          </el-card>
        </el-timeline-item>
        <el-timeline-item v-if="detail.disposal_date" :timestamp="formatDate(detail.disposal_date)"
                          placement="top" type="warning">
          <el-card shadow="never">
            <h4>排危处置 · {{ detail.disposal_action_label }}</h4>
            <p class="muted">负责人：{{ detail.disposer || '-' }}</p>
            <p class="muted">{{ detail.disposal_note || '未填写处置说明' }}</p>
          </el-card>
        </el-timeline-item>
        <el-timeline-item v-if="detail.recheck_date" :timestamp="formatDate(detail.recheck_date)"
                          placement="top" :type="detail.recheck_result === 'passed' ? 'success' : 'danger'">
          <el-card shadow="never">
            <h4>
              复检结论
              <EnumTag group="recheck_result" :value="detail.recheck_result"
                       :label="detail.recheck_result_label" />
            </h4>
            <p class="muted">复检人：{{ detail.rechecker || '-' }}</p>
            <p class="muted">{{ detail.recheck_note || '未填写复检说明' }}</p>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </div>

    <template #footer>
      <el-button @click="close">关闭</el-button>
      <el-button v-if="detail.status === 'pending' || detail.status === 'processing'" type="warning"
                 @click="openAction('disposal')">登记处置情况</el-button>
      <el-button v-if="detail.status === 'recheck'" type="primary" @click="openAction('recheck')">
        登记复检结论
      </el-button>
    </template>

    <HazardActionDialog ref="actionDialog" @saved="onSaved" />
  </el-drawer>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { hazardousTreeApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import { formatDate } from '@/utils/format'

import HazardActionDialog from './HazardActionDialog.vue'

const emit = defineEmits(['updated'])
const router = useRouter()

const visible = ref(false)
const loading = ref(false)
const detail = ref({})
const currentId = ref(null)
const actionDialog = ref(null)

async function open(id) {
  currentId.value = id
  visible.value = true
  await load()
}

async function load() {
  if (!currentId.value) return
  loading.value = true
  try {
    detail.value = await hazardousTreeApi.detail(currentId.value)
  } finally {
    loading.value = false
  }
}

function openAction(mode) {
  actionDialog.value?.open(mode, currentId.value)
}

async function onSaved() {
  await load()
  emit('updated')
}

function goTask() {
  if (detail.value.green_space?.id) {
    router.push({ name: 'task-list', query: { green_space_id: detail.value.green_space.id } })
    close()
  }
}

function close() {
  visible.value = false
}

defineExpose({ open })
</script>

<style scoped>
.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.drawer-head .tree-name {
  font-size: 16px;
  font-weight: 600;
  margin-right: 8px;
}

.head-tag {
  margin-right: 0;
}

.head-sub {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.panel-title {
  font-weight: 600;
  margin-top: 4px;
}

.task-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid var(--gs-border);
  border-radius: 8px;
  padding: 10px 14px;
  background: #fafbfc;
}

.task-card__main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.task-no {
  color: #909399;
  font-size: 13px;
}

h4 {
  margin: 0 0 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

p {
  margin: 4px 0;
  line-height: 1.5;
}

.muted {
  color: #909399;
  font-size: 13px;
}
</style>
