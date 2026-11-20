# 澄港 · 港口燃油密度放行复核

按燃油等级比对油样密度，对异常样复检，带着化验快照申请船舶调拨，主管放行时原子扣减罐量，并记录到港补罐与船岸计量对账；新增清线许可、泊位窗口、封存留样和独立委托复检。

模拟客户澄港燃供有14名化验与调拨人员，管理VLSFO低硫燃料油和MGO轻柴油。当前化验员在纸簿记样品，主管凭固定密度门限核准，调拨组另记罐量；等级差异被忽略、异常样没复检、调拨与油样脱节是三个痛点。上游为储罐取样及密度/黏度/硫记录，本项目替代分布比对、复检与调拨审签，下游交付带化验依据的实船供油指令档案。本演示不连接实船输油设备。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build --wait
# 默认 SEED_DEMO=true 自动seed，也可手工幂等重跑
docker compose exec -T backend python -m scripts.seed_demo
```

前端 http://localhost:18228 ，API http://localhost:19228/docs ，PostgreSQL localhost:17728。结束 `docker compose down -v --remove-orphans` 会删除本项目演示卷。

|角色|账号|密码|权限|
|---|---|---|---|
|admin 调拨主管|admin@chenggang.local|Harbor2026!|登记/暂停/恢复储罐、固定罐容密度基准、化验、调拨放行、收油入罐与对账结案|
|chemist 化验员|chemist@chenggang.local|Harbor2026!|收样、比对、复检、申请调拨；收油计划/化验核对、计量记录/调查依据；不能签放行、入罐或结案|
|viewer 船代观察员|viewer@chenggang.local|Harbor2026!|只读九页、规格和交接记录|

## 九个业务模块

- 罐区日志：罐号唯一、等级固定、Decimal升数非负；主管可暂停调拨。暂停不影响化验，申请和放行都会拦截。
- 收样登记：每瓶FuelSample有来源Tank外键、唯一编号、15℃密度、黏度、硫；待测样与参考样明确分开。
- 密度与复检：Python worker仅用同等级reference=True样拟合。异常样补复检密度和文字说明，原始读数保留。复检仍超等级规格时状态rejected，申请会拒绝；通过规格后retested。任何调拨引用会冻结该油样复检。
- 调拨放行：申请时必须合格且不超当前罐量；复制等级/密度/黏度/硫快照。申请不预留油量；主管放行锁Transfer和Tank、复核状态及规格、原子扣减。超量、罐暂停、重复放行均不会扣量。

- 到港补罐验收：TankReceipt计划→化验核对→主管入罐；等级须同罐、密度/黏度/硫均符合规格，最终入罐再次查active状态与剩余罐容。TankCapacity一对一记录罐容及存油密度，主管只可建立一次，容量≥当前存量、密度符合本等级，禁止覆盖初始基准。入罐锁收油单与Tank，再更新体积和加权密度，重复入罐拒绝；保存入罐前后体积、密度、签署人快照。新罐可在本页折叠表单建基准，历史未配置的罐仍可原流程调拨，收油则须先补基准。
- 船舶计量对账：只对released调拨登记表前/表后和船收量，表后必须递增。分别以调拨量作分母计算表计及船收差率，绝对值≤1%为matched，否则variance。超差必须≥8字调查依据才可由主管结案；结案快照冻结表底、差率、调拨化验、调查和签署人。对账不再次改罐量，不能重复登记或结案。

参考样不可申请实船调拨，也不会被业务收样接口写成参考样。调拨存在独立化验快照，防止后续修订改变已放行依据。

### 一天工作剧本

08:30主管核TK-06 VLSFO 50000L；09:00化验员收FS-20261117-01密度980、黏度130、硫0.35%；09:30 worker按VLSFO60条参考比对为合格；10:00 FS-OFF原样1035被判异常；10:30未复检申请被拒；11:00复测1040仍超内控规格，申请仍拒；13:00重新取中层油样、排气和核温后密度984，签注复检合格；14:00 TR-26017为澄海17申请5000L；14:10主管批准清线许可并确认受油泊位窗口；14:15主管放行，TK-06余45000L；15:00两份各30000L调拨争罐量，只有一份成功，余15000L；16:00交接簿查原样、复检、化验快照与签署人。

16:30到港收油计划RC-DEMO-17为TK-06补5000L，15℃密度985、黏度130、硫0.35%；主管核对100000L罐容后入罐，若当前存量15000L/密度975，更新至20000L/加权密度977.5，原后数均有快照。17:00对TR-26017放行5000L核表10000→15100、船收4900L，差率+2%/-2%；未调查主管结案被拒，补温度补偿与船舱测深复核依据后主管签结。TK-06罐量不因对账再次改变。

## 算法与规格

seed42生成120条固定参考样，VLSFO/MGO各60；它们有独立等级与密度范围。对单个等级的参考密度`StandardScaler`后拟合`KernelDensity(kernel='gaussian',bandwidth=.3)`。将参考样自身log likelihood第5分位作为低似然阈值；待测样只调用transform/score_samples，不进入fit。返回等级、参考编号/数值、参考数、阈值、待测分数、70点物理量纲概率密度曲线，均由worker实际计算。

原样合格需同时达到KDE阈值和等级规格。KDE判异表示需要复测，不直接代表成品不可用。复检记录经化验员签注、达到等级硬规格可人工解除异常；这里不对复检值二次做自动KDE拒绝。等级演示内控值：VLSFO密度925–1010、黏度10–380、硫≤0.5%；MGO密度820–890、黏度1–12、硫≤0.1%。密度kg/m³@15℃，黏度mm²/s。这些是本场景演示值，并非完整海事检验标准。参考不足20条或无变化时失败，原样未合格不能调拨。

## 技术与职责

|层|实现|
|---|---|
|前端|原生HTML/CSS/ES modules，Nginx1.27，港务日志/罐区/化验签注布局|
|后端|Python3.12/FastAPI/SQLAlchemy2/psycopg3|
|算法|scikit-learn1.6/NumPy，独立worker通过Redis7队列计算|
|数据|PostgreSQL16，外键/唯一键/范围约束，Decimal体积与化验值|
|横切|JWT8小时/PBKDF2/三角色、业务审计、请求追踪、全局错误恢复|

`backend/src/models.py`为Tank/FuelSample/Transfer；`schemas.py`请求范围；`density_model.py`按级KDE与规格函数；`transfer_service.py`资格/复检/化验快照与锁罐放行；`worker.py`队列/心跳；`main.py`路由；`middlewares.py`两个中间件。`backend/scripts/seed_demo.py`按自然键只补缺失记录，不覆盖修改。

`backend/src/receipt_models.py`新增TankCapacity/TankReceipt/LoadingReconciliation三张关联表，原表列不变；`receipt_schemas.py`校验罐基准、收油测值和表计输入；`receipt_service.py`锁罐入量、加权密度、调查结案；`receipt_routes.py`提供`/tank-capacities`、`/tank-receipts`及`/loading-reconciliations`。create_all非破坏性建表，旧数据无需改列迁移。

前端`pages/tanks.js`、`samples.js`、`evidence.js`、`transfers.js`分别处理罐、收样、分布复检、调拨；新增`receipts.js`收油计划/罐容基准/核对入罐，`reconciliations.js`船岸表计与调查结案。`components/logbook.js`共享shell/heading/sampleTag/tankTag/notice；样品状态标签在收样和复检复用；`utils/api.js`会话/API/store，`utils/format.js`数字/转义/上海时间。角色、油样状态、收油状态、对账状态在`backend/src/constants.py`与`frontend/src/constants.js`定义；等级规格在backend constants及GET /grades供页面复用；角色和状态实际使用处为security.py/main.py/worker.py/transfer_service.py以及前端页面。

五服务frontend/backend/worker/db/redis有独立健康检查；backend/worker依赖db/redis healthy，前端等待backend。命名卷db-data/redis-data/artifacts；worker共享卷保存模型证据和心跳。Nginx /api/剥前缀代理，后端路由无/api双重前缀。`.env.example`提供COMPOSE_PROJECT_NAME、三端口、JWT_SECRET、DOCKER_SUBNET；内部DATABASE_URL/REDIS_URL/SEED_DEMO在Compose设置。由于宿主默认地址池耗尽，显式10.221.29.0/24，可通过DOCKER_SUBNET改为无冲突网段。

本地开发：backend目录安装requirements，配置Postgres/Redis连接后`uvicorn src.main:app --reload`；前端继续Nginx代理。测试脚本、JSON、截图、日志独立放外层test-artifacts/gb-1029，源码不含测试产物。

## 已知范围

不接储罐计量仪、真实化验仪、船代通知或物理阀门。到港收油按体积加权计算15℃密度，没有温度体积换算或管线存油修正；初始密度是主管计量基准，后续出油按均质假设不改存油密度。新增收油不会污染KDE参考，也不会自动使旧油样过期；生产环境应增加新罐存量取样与有效期联动。船岸超差可留调查依据结案，但不自动补量/退款或判定责任。复检为密度和人工说明，黏度/硫沿用原样，未实现照片或签名证书上传。参考与待测均为模拟数据，KDE分数是参考相似性，不是合格概率；规格仅覆盖三项演示内控。单worker/Redis list，无任务取出后进程崩溃的可靠重投。已放行调拨不可撤销返罐；申请不预扣，最终不足会被拒。演示账号与JWT密钥部署前替换。

License: MIT.


## V3 港务协作三模块

- 管线清线许可：主管登记 FuelLine（油品等级、额定L/min、最低清线L）；化验员仅为requested调拨登记/修订LinePermit，冲洗量达标、清线等级与调拨/管线一致、管线idle才可主管批准。批准后证据冻结；批准不预占资源。所有新放行须有permitted许可，事务内锁行再次检查，并将管线busy、许可in_use与扣罐量共同提交。不同罐争同管线也只能一单成功。
- 船舶受油窗口：Berth登记最大吃水；化验员为requested调拨登记起止时间、吃水及泊位。主管确认时锁Transfer→Berth→Window，同泊位confirmed/in_use/completed区间不能重叠、时间须有效、吃水须合格。PostgreSQL默认READ COMMITTED下在泊位锁后读取重叠记录；两个不同调拨并发确认同泊位，只能一份成功。放行还检查窗口总分钟×管线额定流量≥调拨量，并记录泊位/船舶快照。窗口可提前审批，起点不是实际阀门开通时刻。
- 燃油留样与委托：released调拨才可登记RetainedSample；一调拨一封样、seal_code全局唯一、500–5000mL、登记日起至少90天。主管仅向有效封样委托，存在未结案委托时不允许重复；化验员一次登记密度及报告依据，按原油品等级标记超规格；主管结案冻结结果，超规格须至少8字处置依据。委托不修改原FuelSample、原调拨化验或KDE参考。

正式调拨放行必须同时满足两项新前置。历史已released记录保持原状；旧requested单须补许可和窗口。主管在管线页填写至少8字完工依据可释放管线与泊位一次；船岸计量对账结案也自动完成同一资源释放，重复不再动库存。已完成窗口仍保留在重叠历史中。

新增后端harbor_models/schemas/service/routes.py及前端pages/lines.js、windows.js、retention.js，6张关联表由create_all补建，原表无新增列。seed只按自然键补两条输油管线和两座泊位，双跑不覆盖在用状态、许可、预约或检验记录。登录后导航共9页，前端仍为原生HTML/CSS/JS。

V3范围：清线量与完工依据来自人工记录，不控制泵阀；时间按用户北京时间输入、后端保存UTC，页面标注UTC；额定流量只做窗口容量检查，未模拟泵速/温度补偿/实时船位。泊位当前无取消/改期功能，计划错误须新调拨，已完成历史区间保持占位证据。留样无温控传感器、封条照片、物流或检测报告附件；委托密度是人工外部报告，不重新训练KDE，不判定法律责任。详细真实证据见test-artifacts/gb-1029/v3。
