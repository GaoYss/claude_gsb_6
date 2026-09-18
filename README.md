# 城市绿地养护记录系统

面向城市绿化养护单位的一体化记录系统：以**绿地台账**为主线，串联**养护任务登记**、**养护记录录入**、**绿植更换记录**与**危树排查闭环**，并提供养护总览看板。

- 后端：Flask 3 + SQLAlchemy 2 + Flask-Migrate + Gunicorn（分层：api / schemas / services / models）
- 前端：Vue 3 + Vite + Vue Router + Pinia + Element Plus + ECharts（按业务模块拆分视图）
- 数据库：本地默认 SQLite，容器编排使用 PostgreSQL 16
- 部署：docker-compose 一键拉起 db / backend / frontend（nginx 托管静态资源并反向代理 /api）

## 一、功能模块

| 模块 | 页面 | 主要能力 |
| --- | --- | --- |
| 养护总览 | `/dashboard` | 绿地与养护总量指标、近半年记录与工时趋势、绿地类型/任务类型/更换原因分布、逾期任务提醒、养护工作量排名 |
| 绿地台账 | `/green-spaces` | 绿地建档（编号自动生成）、按行政区/类型/等级/状态/关键字检索、档案详情（概览 + 近期任务/记录/更换 + 更换原因汇总）、删除保护 |
| 养护任务 | `/tasks` | 任务登记（编号按日生成）、按状态/类型/优先级/绿地/计划日期区间/逾期筛选、状态流转（待执行→进行中→已完成/已取消）、任务详情与执行进度 |
| 养护记录 | `/records` | 记录录入（可关联任务，也可登记日常巡查）、工时/天气/材料/质量评定、质量分布与工时汇总、记录详情 |
| 绿植更换 | `/replacements` | 更换登记（植株、类别、规格、数量、原因、原植株状况、供苗单位、单价与金额）、按类别/原因统计与占比、按绿地/日期区间筛选 |
| 危树排查 | `/hazards` | 危树登记（风险等级、判定依据、处置要求，可关联来源巡查记录）、一键生成排危任务、处置状态流转（待处置→处置中→待复检→已闭环）、复检结论登记（合格闭环/不合格退回）、未闭环危树在台账与看板单独计数 |

## 二、目录结构

```
.
├── backend/                     # Flask 后端
│   ├── app/
│   │   ├── __init__.py          # 应用工厂：装配扩展、蓝图、错误处理、CLI
│   │   ├── config.py            # 配置（SQLite / PostgreSQL 切换）
│   │   ├── constants.py         # 业务字典（唯一枚举来源，下发给前端）
│   │   ├── errors.py            # 业务异常与全局错误响应
│   │   ├── cli.py               # init-db / reset-db / seed 命令
│   │   ├── api/                 # 接口层：每个业务模块一个 Blueprint
│   │   │   ├── green_spaces.py
│   │   │   ├── maintenance_tasks.py
│   │   │   ├── maintenance_records.py
│   │   │   ├── plant_replacements.py
│   │   │   ├── hazard_trees.py
│   │   │   ├── statistics.py
│   │   │   └── meta.py
│   │   ├── schemas/             # 校验层：写库字段校验 + 查询条件解析
│   │   │   ├── common.py        # 链式字段校验器
│   │   │   ├── filters.py       # 列表过滤条件
│   │   │   └── green_space.py / maintenance_task.py / maintenance_record.py / plant_replacement.py / hazard_tree.py
│   │   ├── services/            # 业务层：事务、编号生成、跨模块规则
│   │   │   ├── base_service.py  # 通用增删改与编号冲突重试
│   │   │   ├── code_generator.py
│   │   │   ├── green_space_service.py
│   │   │   ├── maintenance_task_service.py
│   │   │   ├── maintenance_record_service.py
│   │   │   ├── plant_replacement_service.py
│   │   │   ├── hazard_tree_service.py
│   │   │   └── statistics_service.py
│   │   ├── models/              # 模型层：SQLAlchemy 模型与序列化
│   │   └── utils/               # 响应封装、分页、日期、排序等
│   ├── tests/                   # pytest 测试（接口 + 业务规则 + 端到端流程）
│   ├── docker/entrypoint.sh     # 等库就绪 → 建表 → 可选写入演示数据
│   ├── requirements.txt
│   └── wsgi.py                  # 入口（flask run / gunicorn 共用）
│
├── frontend/                    # Vue 3 前端
│   ├── src/
│   │   ├── api/                 # 按模块拆分的接口封装 + axios 拦截器
│   │   ├── components/common/   # PageHeader、StatCard、EnumTag、绿地/任务/记录选择器、图表容器
│   │   ├── composables/         # useListQuery（列表分页筛选）、useEnumOptions
│   │   ├── layouts/             # DefaultLayout（侧边导航 + 顶栏）
│   │   ├── router/              # 路由（按模块懒加载）
│   │   ├── stores/              # Pinia：字典缓存、布局状态
│   │   ├── styles/              # 全局样式与主题变量
│   │   ├── utils/               # 数值/面积/金额/日期格式化
│   │   └── views/               # 视图：dashboard / green-space / task / record / replacement / hazard
│   ├── docker/nginx.conf        # 静态资源 + /api 反向代理
│   ├── vite.config.js           # 开发代理 /api → 后端
│   └── package.json
│
├── docker-compose.yml           # db + backend + frontend 编排
├── .env.example
└── README.md
```

## 三、快速开始

### 方式一：docker-compose（推荐）

```bash
cp .env.example .env          # 可选：调整端口、数据库口令、是否写入演示数据
docker compose up -d --build
```

启动后访问：

- 前端：<http://localhost:8090>
- 后端接口：<http://localhost:5000/api/v1/meta/health>
- PostgreSQL：`localhost:5432`（容器内 `db:5432`）

首次启动会自动建表；`SEED_DEMO_DATA=true` 时会写入一批演示数据（7 处绿地、15 条任务、22 条养护记录、8 条更换记录）。停止与清理：

```bash
docker compose down            # 停止容器，保留数据库卷
docker compose down -v         # 连同数据库卷一起清理
```

### 方式二：本地开发

后端（Python 3.11+，默认使用 SQLite，数据库文件位于 `backend/instance/green_space.db`）：

```bash
cd backend
pip install -r requirements.txt
flask --app wsgi seed --reset      # 建表 + 写入演示数据（可省略）
flask --app wsgi run --debug       # http://127.0.0.1:5000
```

前端（Node 18+）：

```bash
cd frontend
npm install
npm run dev                        # http://127.0.0.1:5173，/api 自动代理到 5000
```

生产构建与本地预览：

```bash
cd frontend && npm run build && npm run preview
```

## 四、环境变量

| 变量 | 作用 | 默认值 |
| --- | --- | --- |
| `DATABASE_URL` | 数据库连接串，留空则使用 SQLite | 空（SQLite） |
| `AUTO_CREATE_TABLES` | 启动时自动建表 | `true` |
| `SEED_DEMO_DATA` | 容器启动时写入演示数据 | `false`（compose 中为 `true`） |
| `CORS_ORIGINS` | 允许的跨域来源 | `*` |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | 分页默认与上限 | `10` / `100` |
| `INSTANCE_DIR` | SQLite 数据文件目录 | `backend/instance` |
| `VITE_API_BASE_URL` | 前端接口前缀 | `/api/v1` |
| `VITE_PROXY_TARGET` | 开发代理目标 | `http://127.0.0.1:5000` |

## 五、接口一览（前缀 `/api/v1`）

统一响应结构：成功 `{"success": true, "code": 0, "message": "ok", "data": ...}`；失败 `{"success": false, "code": 4xxxx, "message": "...", "data": {"字段": "提示"}}`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/meta/enums` | 全部业务字典（前端下拉唯一来源） |
| GET | `/meta/health` | 健康检查（含数据库连通性） |
| GET | `/green-spaces` | 台账列表（`keyword`/`district`/`green_type`/`maintenance_grade`/`status`/`sort`/`order`/分页，返回汇总） |
| GET | `/green-spaces/options` | 绿地下拉选项（排除已归档） |
| GET | `/green-spaces/districts` | 行政区及绿地处数 |
| POST | `/green-spaces` | 新增绿地（编号可留空自动生成） |
| GET | `/green-spaces/{id}` | 绿地详情 |
| GET | `/green-spaces/{id}/profile` | 绿地档案（概览统计 + 近期任务/记录/更换） |
| PUT | `/green-spaces/{id}` | 更新绿地（编号不可改） |
| DELETE | `/green-spaces/{id}?force=true` | 删除绿地（有关联数据时需 `force`） |
| GET/POST | `/maintenance-tasks` | 任务列表 / 登记任务（`status`/`task_type`/`priority`/`green_space_id`/`date_from`/`date_to`/`overdue`） |
| GET/PUT/DELETE | `/maintenance-tasks/{id}` | 任务详情（含执行进度与记录） / 更新 / 删除（有记录时需 `force`，记录会保留但解除关联） |
| PATCH | `/maintenance-tasks/{id}/status` | 任务状态流转 |
| GET/POST | `/maintenance-records` | 记录列表（`task_id`/`green_space_id`/`quality_result`/`weather`/`unlinked`/日期区间，返回汇总） / 录入记录 |
| GET/PUT/DELETE | `/maintenance-records/{id}` | 记录详情（含关联更换记录） / 更新 / 删除 |
| GET | `/maintenance-records/summary` | 记录汇总（条数、工时、质量分布） |
| GET/POST | `/plant-replacements` | 更换记录列表（`green_space_id`/`plant_category`/`reason`/日期区间，返回汇总） / 登记更换 |
| GET/PUT/DELETE | `/plant-replacements/{id}` | 详情 / 更新 / 删除 |
| GET | `/plant-replacements/summary` | 更换汇总（按植物类别、更换原因） |
| GET/POST | `/hazard-trees` | 危树列表（`status`/`risk_level`/`hazard_type`/`source`/`green_space_id`/`open_only`/日期区间，返回汇总） / 登记危树 |
| GET/PUT/DELETE | `/hazard-trees/{id}` | 危树详情（含复检记录与排危任务） / 更新 / 删除（复检记录级联删除，排危任务保留） |
| PATCH | `/hazard-trees/{id}/status` | 处置状态流转（待处置/处置中/待复检，已闭环只能经复检合格到达） |
| POST | `/hazard-trees/{id}/generate-task` | 按登记信息生成排危任务（养护类型「危树排危」，优先级随风险等级） |
| POST | `/hazard-trees/{id}/reinspections` | 登记复检结论（合格→已闭环，不合格→退回处置中） |
| GET | `/statistics/dashboard` | 看板聚合数据（总览 + 分布 + 趋势 + 榜单 + 提醒 + 未闭环危树 + 最近动态） |
| GET | `/statistics/overview` `/distributions` `/trends` `/ranking` `/reminders` | 看板分项接口 |

## 六、业务规则

1. **业务编号**：绿地 `GS-年份-序号`（如 `GS-2026-0001`），任务 `MT-YYYYMMDD-序号`，养护记录 `MR-YYYYMMDD-序号`，更换记录 `PR-YYYYMMDD-序号`，危树 `HT-YYYYMMDD-序号`；留空自动生成，唯一约束冲突时自动重试，编号创建后不可修改。
2. **任务状态联动**（`maintenance_record_service`）：
   - 任务下有养护记录后，任务自动从「待执行」进入「进行中」；
   - 存在**合格**记录且**没有不合格**记录时，任务自动置为「已完成」并写入完成时间；
   - 存在不合格记录时任务保持「进行中」，必须整改复检（把记录改判为合格或删除）后才会完成，手动「标记完成」同样会被拒绝；
   - 删除养护记录后按剩余记录重新推算任务状态，避免出现「已完成却没有记录」；已取消的任务不允许补录记录。
3. **绿地归属一致性**：养护记录可只填绿地（日常养护）或只填任务（绿地自动跟随任务）；两者同时提供时必须属于同一绿地。更换记录若关联养护记录，必须是同一绿地的记录。
4. **日期约束**：养护日期、更换日期不得早于绿地建成日期。
5. **金额核算**：更换金额 = 数量 × 单价，由后端统一计算；未填单价时金额留空，前端提示补录。
6. **删除保护**：删除绿地时若已存在任务/记录/更换/危树数据会返回 409 并给出数量明细，需 `force=true` 才级联删除；删除任务时养护记录默认保留（解除关联），避免养护履历丢失。
7. **危树闭环**（`hazard_tree_service`）：
   - 危树登记后可一键生成排危任务（养护类型「危树排危」，优先级按风险等级映射：一般→中、较大→高、重大→紧急），生成后危树自动进入「处置中」，同一危树只能生成一次；
   - 处置状态按「待处置→处置中→待复检」手动流转，「已闭环」只能由复检合格自动到达，不能手动设置；
   - 复检结论为合格时危树闭环并写入闭环时间，不合格时退回「处置中」继续整改，复检记录全程留痕；
   - 未闭环（待处置/处置中/待复检）的危树在绿地台账列表、绿地档案与养护总览看板中单独计数与列示；
   - 删除危树时复检记录一并清除，已生成的排危任务保留为普通养护任务。
8. **字典单一来源**：所有枚举在 `backend/app/constants.py` 定义，前端通过 `/meta/enums` 获取并缓存，前后端不重复维护。

## 七、数据模型

| 表 | 说明 | 关键字段 |
| --- | --- | --- |
| `green_space` | 绿地台账 | `code`(唯一)、`name`、`district`、`green_type`、`maintenance_grade`、`area_sqm`、`status`、`manager`、`established_date` |
| `maintenance_task` | 养护任务 | `task_no`(唯一)、`green_space_id`、`task_type`、`plan_date`、`priority`、`executor`、`status`、`completed_at` |
| `maintenance_record` | 养护记录 | `record_no`(唯一)、`task_id`(可空)、`green_space_id`、`record_date`、`work_content`、`worker`、`work_hours`、`weather`、`quality_result` |
| `plant_replacement` | 绿植更换记录 | `replacement_no`(唯一)、`green_space_id`、`maintenance_record_id`(可空)、`plant_name`、`plant_category`、`quantity`、`unit`、`reason`、`unit_price`、`amount` |
| `hazard_tree` | 危树登记 | `hazard_no`(唯一)、`green_space_id`、`maintenance_record_id`(可空)、`task_id`(可空)、`tree_name`、`tree_count`、`source`、`hazard_type`、`risk_level`、`judgment_basis`、`disposal_measure`、`dispose_deadline`、`status`、`closed_at` |
| `hazard_reinspection` | 危树复检记录 | `hazard_tree_id`、`recheck_date`、`result`、`inspector`、`note` |

绿地删除时任务/记录/更换/危树级联清理；任务与养护记录之间、养护记录与更换记录之间为可空外键（`SET NULL`），保证养护履历可独立留存；危树的复检记录随危树级联删除。

## 八、测试

```bash
cd backend
python -m pytest              # 61 个用例：接口、校验、跨模块规则、端到端流程
```

覆盖重点：绿地编号生成与唯一性、枚举与字段校验、列表过滤/排序/分页、任务状态自动流转与手动流转限制、记录删除后的状态回退、更换金额核算、危树登记校验/排危任务生成/复检闭环与退回/未闭环计数、删除保护与强制删除、统计聚合口径一致性、演示数据自洽性。

## 九、常见问题

- **前端页面正常但数据为空**：确认后端已启动且 `/api/v1/meta/health` 返回 `database: up`；容器方式下检查 `docker compose ps` 中 backend 是否 `healthy`。
- **端口被占用**：修改 `.env` 中的 `FRONTEND_PORT` / `BACKEND_PORT`，或在本地开发时用 `flask --app wsgi run --port 5001` 并同步调整 `VITE_PROXY_TARGET`。
- **数据库结构变更**：切换 `AUTO_CREATE_TABLES=false` 后使用 Flask-Migrate：`flask --app wsgi db init && flask --app wsgi db migrate -m "描述" && flask --app wsgi db upgrade`。
- **重置演示数据**：`flask --app wsgi seed --reset`；容器方式可执行 `docker compose exec backend flask --app wsgi seed --reset`。
