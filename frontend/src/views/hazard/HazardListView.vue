<template>
  <div class="page">
    <PageHeader title="危树排查" description="登记巡查与专项排查中发现的危树，生成排危任务并跟踪处置与复检闭环">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">登记危树</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="危树编号 / 树种 / 位置 / 排查人" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <div style="width: 220px">
          <GreenSpaceSelect v-model="filters.green_space_id" placeholder="按绿地筛选" @update:model-value="search" />
        </div>
        <el-select v-model="filters.status" placeholder="处置状态" clearable @change="search">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.risk_level" placeholder="风险等级" clearable @change="search">
          <el-option v-for="item in riskOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.hazard_type" placeholder="风险类型" clearable @change="search">
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.source" placeholder="排查来源" clearable @change="search">
          <el-option v-for="item in sourceOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="发现开始" end-placeholder="发现结束" @change="onDateChange" />
        <el-checkbox v-model="filters.open_only" label="仅看未闭环" border @change="search" />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="resetFilters">重置</el-button>
      </div>
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 株危树，
          未闭环 <strong class="open-count">{{ summary?.open_count ?? 0 }}</strong>（
          待处置 <strong>{{ summary?.pending ?? 0 }}</strong>、
          处置中 <strong>{{ summary?.in_progress ?? 0 }}</strong>、
          待复检 <strong>{{ summary?.resolved ?? 0 }}</strong>），
          已闭环 <strong>{{ summary?.closed ?? 0 }}</strong>
        </span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column label="危树编号 / 树种" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="cell-main">{{ row.tree_name }}<span v-if="row.tree_count > 1"> × {{ row.tree_count }}</span></div>
            <div class="cell-sub">{{ row.hazard_no }}</div>
          </template>
        </el-table-column>
        <el-table-column label="所属绿地" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="位置" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.location || '-' }}</template>
        </el-table-column>
        <el-table-column label="风险类型" width="110">
          <template #default="{ row }">
            <EnumTag group="hazard_type" :value="row.hazard_type" :label="row.hazard_type_label" />
          </template>
        </el-table-column>
        <el-table-column label="风险等级" width="90">
          <template #default="{ row }">
            <EnumTag group="hazard_risk_level" :value="row.risk_level" :label="row.risk_level_label" />
          </template>
        </el-table-column>
        <el-table-column prop="found_date" label="发现日期" width="105" />
        <el-table-column label="处置时限" width="105">
          <template #default="{ row }">{{ row.dispose_deadline || '-' }}</template>
        </el-table-column>
        <el-table-column label="排危任务" width="150">
          <template #default="{ row }">
            <template v-if="row.task">
              <div class="cell-sub">{{ row.task.task_no }}</div>
              <EnumTag group="task_status" :value="row.task.status" :label="row.task.status_label" />
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="92">
          <template #default="{ row }">
            <EnumTag group="hazard_status" :value="row.status" :label="row.status_label" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="drawer.open(row.id)">详情</el-button>
            <el-button link type="primary" @click="formDialog.open(row)">编辑</el-button>
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
    <HazardDetailDrawer ref="drawer" @updated="load" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { hazardTreeApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'

import HazardDetailDrawer from './HazardDetailDrawer.vue'
import HazardFormDialog from './HazardFormDialog.vue'

const route = useRoute()
const formDialog = ref(null)
const drawer = ref(null)
const dateRange = ref([])

const { options: statusOptions } = useEnumOptions('hazard_status')
const { options: riskOptions } = useEnumOptions('hazard_risk_level')
const { options: typeOptions } = useEnumOptions('hazard_type')
const { options: sourceOptions } = useEnumOptions('hazard_source')

const { filters, meta, items, summary, loading, load, search, resetFilters, handlePageChange, handleSizeChange } =
  useListQuery(hazardTreeApi.list, {
    initialFilters: {
      keyword: '',
      green_space_id: route.query.green_space_id ? Number(route.query.green_space_id) : null,
      status: '',
      risk_level: '',
      hazard_type: '',
      source: '',
      date_from: '',
      date_to: '',
      open_only: false,
    },
  })

function onDateChange(value) {
  filters.date_from = value?.[0] || ''
  filters.date_to = value?.[1] || ''
  search()
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(
      row.task
        ? `危树「${row.tree_name}（${row.hazard_no}）」已生成排危任务 ${row.task.task_no}，删除危树后任务将保留为普通养护任务，是否继续？`
        : `确认删除危树「${row.tree_name}（${row.hazard_no}）」吗？复检记录将一并删除。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await hazardTreeApi.remove(row.id)
    ElMessage.success('危树记录已删除')
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

.open-count {
  color: #f56c6c;
}
</style>
