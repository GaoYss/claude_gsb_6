<template>
  <div class="page">
    <PageHeader title="危树排查" description="独立入口：登记倒伏、折枝风险树木，自动生成排危任务并跟踪处置与复检闭环">
      <template #actions>
        <el-button type="danger" :icon="'WarningFilled'" @click="formDialog.open()">危树排查登记</el-button>
      </template>
    </PageHeader>

    <div class="stat-grid">
      <StatCard label="未闭环危树" :value="formatNumber(summary?.open_count ?? 0)" unit="株"
                :hint="`待排危 ${summary?.by_status?.pending ?? 0}、排危中 ${summary?.by_status?.processing ?? 0}、待复检 ${summary?.by_status?.recheck ?? 0}`"
                :tone="(summary?.open_count ?? 0) ? 'danger' : 'default'" icon="WarningFilled" />
      <StatCard label="其中重大风险" :value="formatNumber(summary?.open_by_level?.major ?? 0)" unit="株"
                hint="重大风险须 24 小时内完成排危" tone="warning" icon="AlarmClock" />
      <StatCard label="超期未闭环" :value="formatNumber(summary?.overdue_count ?? 0)" unit="株"
                hint="超过排危任务处置期限仍未闭环"
                :tone="(summary?.overdue_count ?? 0) ? 'danger' : 'default'" icon="Timer" />
      <StatCard label="已闭环" :value="formatNumber(summary?.closed_count ?? 0)" unit="株"
                :hint="`累计登记 ${formatNumber(summary?.total ?? 0)} 株，复检合格后闭环`"
                tone="info" icon="CircleCheck" />
    </div>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="危树编号 / 树名 / 位置 / 排查人" clearable
                  :prefix-icon="'Search'" style="width: 240px"
                  @keyup.enter="search" @clear="search" />
        <div style="width: 220px">
          <GreenSpaceSelect v-model="filters.green_space_id" placeholder="按绿地筛选"
                            @update:model-value="search" />
        </div>
        <el-select v-model="filters.status" placeholder="闭环状态" clearable @change="search">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.risk_level" placeholder="风险等级" clearable @change="search">
          <el-option v-for="item in levelOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.risk_type" placeholder="风险类型" clearable @change="search">
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="排查日期起" end-placeholder="排查日期止" @change="onDateChange" />
        <el-checkbox v-model="filters.open" label="仅看未闭环" border @change="search" />
        <el-checkbox v-model="filters.overdue" label="超期未闭环" border @change="search" />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="resetFilters">重置</el-button>
      </div>
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 株危树，未闭环
          <strong class="danger-text">{{ summary?.open_count ?? 0 }}</strong> 株
          （重大 <strong class="danger-text">{{ summary?.open_by_level?.major ?? 0 }}</strong>、
          较大 <strong class="warning-text">{{ summary?.open_by_level?.significant ?? 0 }}</strong>、
          一般 {{ summary?.open_by_level?.general ?? 0 }}），已闭环 {{ summary?.closed_count ?? 0 }} 株
        </span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe
                :row-class-name="rowClassName">
        <el-table-column label="危树编号 / 树木" min-width="210" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="cell-main">{{ row.tree_name }}</div>
            <div class="cell-sub">{{ row.tree_no }}</div>
          </template>
        </el-table-column>
        <el-table-column label="所属绿地 / 位置" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <div>{{ row.green_space?.name || '-' }}</div>
            <div class="cell-sub">{{ row.location || '未填写具体位置' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="风险" width="150">
          <template #default="{ row }">
            <div class="risk-cell">
              <EnumTag group="hazard_risk_level" :value="row.risk_level" :label="row.risk_level_label" />
              <EnumTag group="hazard_risk_type" :value="row.risk_type" :label="row.risk_type_label" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="排查" width="130">
          <template #default="{ row }">
            <div>{{ row.inspect_date }}</div>
            <div class="cell-sub">{{ row.source_label }}{{ row.inspector ? ` · ${row.inspector}` : '' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="排危期限" width="120">
          <template #default="{ row }">
            <template v-if="row.task">
              <div>{{ row.task.plan_date }}</div>
              <el-tag v-if="!row.is_closed && row.task.is_overdue" type="danger" size="small" effect="plain">
                已超期
              </el-tag>
              <span v-else-if="!row.is_closed" class="cell-sub">处置中</span>
            </template>
            <span v-else class="cell-sub">任务已删除</span>
          </template>
        </el-table-column>
        <el-table-column label="处置 / 复检" width="170">
          <template #default="{ row }">
            <div class="cell-sub">
              处置：{{ row.disposal_date ? row.disposal_action_label : '未处置' }}
            </div>
            <div class="cell-sub">
              复检：
              <EnumTag v-if="row.recheck_result" group="recheck_result" :value="row.recheck_result"
                       :label="row.recheck_result_label" />
              <span v-else>未复检</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="闭环状态" width="100">
          <template #default="{ row }">
            <EnumTag group="hazard_status" :value="row.status" :label="row.status_label" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="drawer.open(row.id)">详情</el-button>
            <el-button v-if="!row.is_closed" link type="warning"
                       @click="formDialog.open(row)">编辑</el-button>
            <el-button v-if="row.status === 'pending' || row.status === 'processing'"
                       link type="warning" @click="actionDialog.open('disposal', row.id)">
              处置
            </el-button>
            <el-button v-if="row.status === 'recheck'" link type="primary"
                       @click="actionDialog.open('recheck', row.id)">复检</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="meta.total"
        :current-page="meta.page"
        :page-size="meta.page_size"
        :page-sizes="[10, 20, 50]"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <HazardFormDialog ref="formDialog" @saved="load" />
    <HazardActionDialog ref="actionDialog" @saved="load" />
    <HazardDetailDrawer ref="drawer" @updated="load" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { hazardousTreeApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'
import { formatNumber } from '@/utils/format'

import HazardActionDialog from './HazardActionDialog.vue'
import HazardDetailDrawer from './HazardDetailDrawer.vue'
import HazardFormDialog from './HazardFormDialog.vue'

const route = useRoute()
const formDialog = ref(null)
const actionDialog = ref(null)
const drawer = ref(null)
const dateRange = ref([])

const { options: statusOptions } = useEnumOptions('hazard_status')
const { options: levelOptions } = useEnumOptions('hazard_risk_level')
const { options: typeOptions } = useEnumOptions('hazard_risk_type')

const { filters, meta, items, summary, loading, load, search, resetFilters, handlePageChange, handleSizeChange } =
  useListQuery(hazardousTreeApi.list, {
    initialFilters: {
      keyword: '',
      green_space_id: route.query.green_space_id ? Number(route.query.green_space_id) : null,
      status: '',
      risk_level: '',
      risk_type: '',
      date_from: '',
      date_to: '',
      open: route.query.open === 'true',
      overdue: route.query.overdue === 'true',
    },
  })

function onDateChange(value) {
  filters.date_from = value?.[0] || ''
  filters.date_to = value?.[1] || ''
  search()
}

function rowClassName({ row }) {
  if (row.status === 'closed') return 'row-closed'
  if (row.risk_level === 'major' || (row.task?.is_overdue)) return 'row-danger'
  return ''
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除危树「${row.tree_name}」（${row.tree_no}）吗？已登记养护作业的排危任务会保留，仅解除关联。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    const result = await hazardousTreeApi.remove(row.id)
    ElMessage.success(result?.kept_task ? '危树已删除，排危任务予以保留' : '危树已删除')
    await load()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  }
}
</script>

<style scoped>
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

.cell-main {
  font-weight: 500;
}

.cell-sub {
  color: #909399;
  font-size: 12px;
}

.risk-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
}

.danger-text {
  color: #f56c6c;
}

.warning-text {
  color: #e6a23c;
}

:deep(.row-danger) {
  background-color: #fef6f5;
}

:deep(.row-closed) {
  color: #a8abb2;
}
</style>
