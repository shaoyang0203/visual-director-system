# 本地工具

有 Python 不等于必须走工具流程。各工具按需单独使用：

|需要|工具|是否进入审批流程|
|---|---|---|
|查知识条目|`scripts/knowledge.py`（第5节）|否|
|长期偏好、模板、存档|`scripts/prefs.py`（第6节）|否|
|MOSS Layout 结构校验、任务记录、严格存档、程序校验后交付|`scripts/pa15.py`（第1–4节）|是|

调用：用解释器绝对路径加 `-B -X utf8`；`--data-dir` 指向技能源码之外、跨会话不变的目录（工具拒绝写入源码目录）。完整选项用 `--help`。
工具只做结构、版本、哈希与名称证据检查，不调用模型，不证明语义正确、用户已阅读或图像质量。

## 1 任务模式与流程（scripts/pa15.py）

|模式|适用|流程|
|---|---|---|
|`explore`|用户想探索，或方向确有分歧|`new` → `concepts`（2–5 个方向）→ `select --user-ref` → `master` → `coordinate` → `show` → `approve` → `manifest` → `submit` → `deliver`|
|`direct`|需求已明确的直接创作|`new --mode direct --user-ref <用户需求消息>` → `master` → `coordinate` → `show` → `approve` → `manifest` → `submit` → `deliver`|
|`limited`|已有提示词整理、翻译、迁移|同 `direct`，`--mode limited`；全部设计项与 `medium` 须来自原文明示（`user_specified`）。原文没写媒介或画幅时用 `schema_version: "0.3.1"`，把 `globals.medium` / `globals.aspect_ratio` 设为 `null`；画幅也可记为待确认建议（`model_added/pending/adjustable_design`），经整版批准后才进入成品。用户要求改风格或补设计时改建 `direct` 任务|

修改：`change --user-ref` → `master`（新 revision）→ `coordinate` → `show` → `approve` → `manifest` → `submit` → `deliver`。

- `direct/limited` 的 `--user-ref` 只记录方向来自用户需求，**不是**母版批准。
- `approve` 必须引用展示当前 revision 后用户本人的确认消息，程序拒绝复用 `direct_entry` 或 `direction_selected` 的同一 `user_ref`（仅拦截同一引用复用，仍无法验证外部消息真实性）。
- 媒介、画幅为 `null` 只在 `limited` + `0.3.1` 下放行；其他模式和 `0.3.0` 仍必填。画幅为 `null` 时候选 `parameters.aspect_ratio` 也填 `null`，Adapter 不输出比例行或块外比例；MOSS Layout 需要明确画幅与画布尺寸，缺失时 manifest 拒绝。程序只检查 `design_source` 标签与结构，不验证所填内容是否真出自原文。
- 文本路径的“同轮预览”在工具路径下只是预览：未 `approve` 前不执行 `submit/deliver`，也不称“已交付”。用户确认后再补走 approve → manifest → submit → deliver。
- 已选方向不能覆盖方案列表；重新探索请新建任务。直接/整理任务不接受 `concepts/select`。
- 旧快照没有 `mode` 字段时按 `explore` 处理。

## 2 母版 JSON

Schema：[visual-master.schema.json](../schemas/visual-master.schema.json)。

- 九区域：创作意图与用户约束、创意方向与叙事瞬间、视觉主体与层级、人物美术、场景美术、动作与空间关系、摄影与构图、光影与色彩、材质与视觉表现。区域引用设计项 ID，可为空；媒介、画幅、画面文字放 `globals`。
- `items` 以稳定 ID 为键，三个字段相互独立：
  - `design_source`：`user_specified` / `model_added` / `jointly_formed`
  - `confirmation_status`：`pending` / `confirmed` / `rejected`
  - `constraint_strength`：`hard_constraint` / `confirmed_design` / `adjustable_design`
- 用户指定项为 `confirmed`。用户确认模型补充项后，来源仍是 `model_added`，强度不自动升为硬约束。当前母版不含 `rejected` 项。
- 可编译 kind：`visual_fact`、`medium`、`aspect_ratio`、`image_text`。`intent/constraint` 不直译为画面文字；constraint 的 `realized_by` 指向落实它的正向事实。
- 画面文字：`literal` 保留原字符与换行，`appearance` 写位置、颜色、字形与相对字号。
- 画幅：`width/height` 为正整数，没有缺省值；未定比例时不生成可编译母版（`limited` 任务原文未给比例时可为 `null`，见第1节）。用户比例为 `user_specified/confirmed/hard_constraint`；模型初选为 `model_added/pending`。理由写在 facet 或 `changes.reason`，依据放 `source_refs`（如 `KB:CA-09`）。
- 面部与妆发放在人物美术区，可用 facet“脸型与五官”“妆容”“发型”“肤质与妆面”“当下状态”；只有实际选定且可见的才是 `visual_fact`。无妆与裸妆分别记录。服装只记本图选定的衣件、层次、颜色材质、轮廓与必要纹饰。
- 同一事实只记录一次，以 ID 在多个区域复用；开放项不生成占位事实。
- 每次修改产生新 `revision`，写 `parent_revision` 与准确 `changes`；区域或 globals 引用变化另写 `structure_changes`：`{"path":"zones.character_art","reason":"…","source_ref":"…"}`，逐项覆盖实际变化，无差异或空理由会被拒绝。
- 整版批准保存在独立 ApprovalRecord，绑定快照哈希；`master --authorization` 只填真实修改授权（`user_ref`、`item_ids`）。

## 3 协调与纠偏

- `coordinate --input`：`result`（pass/fail/uncertain）、`issues`、`summary`、`domains`（`character_art/scene_art/camera_composition/lighting_color/material_appearance`）。pass 时 issues 必须为空。每个候选或每次用户修改最多 3 轮（可配置），内部改版不重置。
- 画幅相对上次通过的母版改变后，另填 `aspect_ratio_review`：`subject_scale_position、framing_crop、foreground_occlusion、background_information、spatial_relations、visual_hierarchy、negative_space_overall`，各为 `{"result","note"}`，全部 pass 才能通过。
- 可选领域记录字段：DomainRequest（`request_id、domain、base_master_ref、goal、relevant_item_ids、requirements_refs、allowed_change_scope`，可加 `design_problem、knowledge_query、knowledge_refs`）；DomainProposal（`request_id、base_master_ref、proposed_changes、dependency_changes、cross_domain_issues、requires_user_decision、summary`，可加 `knowledge_refs、applicability_reason、rejected_alternatives、visible_facts、unresolved_questions`）。这是宿主文本接口，没有独立领域执行器。
- `correction --input`：`issue`、`intent`（unclear/intentional_contrast/conflict）、`options`。首项为 `strict`（严格执行），其后 1–2 个替代方案，按 `local`、`reconstruct` 顺序；每项含 `mode、design、changes、reason、expected`。记录不自动改动用户要求。

## 4 编译与交付

- `manifest --target <路由>`：绑定当前 revision、母版哈希与路由；改版或换路由后重新执行。省略 target 时沿用已选，初次为 generic。manifest 只选表达方式，不改画幅。
- 候选 JSON：`master_hash`；`segments`（每段 `text`、`item_ids`）；`parameters.aspect_ratio`（width/height；母版未指定画幅时为 null）；`target`；可选 `language`（BCP-47 风格，如 `zh-CN`、`en`）。只有 `moss-image-layout` 另需 `parameters.image_size`，segment 为一个完整 Layout JSON（见 [moss-layout.md](adapters/moss-layout.md)）。segments 不写比例，由 Adapter 按路由生成。
- 复核 JSON 绑定 `master_hash` 与 `artifact_hash`，写 `reviewer`、`evidence_ref`、各维度与每个可编译 ID 的 `result/note`。检查 omissions、additions、relations、requirements；任一必要项 fail/uncertain 不放行。失败最多自动修复一次，重新 manifest 不重置预算。
- 名称证据（只在工具路径执行）：
  1. 按 [names.json](../knowledge/names.json) 的名称组检查人物美术区每个 visual_fact：出现名称或登记别名记 `matched`；目标语言有登记表达却未出现记 `missing`（阻止提交与交付）；映射未覆盖记 `not_checked`。
  2. `not_checked` 的 note 写出母版原名称或原描述，并附覆盖该项的段落原句引文「…」；短于4字的引文须是登记名称或母版原文且按词边界命中。`not_checked` 不会因复核 pass 变成 matched。
  3. 自动别名只覆盖 zh 与 en；其他合法语言一律 `not_checked`。语言改变后旧复核失效。
  4. Layout 只从 `summary.caption` 与人物/物件 `caption` 取证。
- `deliver` 返回 `prompt`、`external_settings` 与完整 `formatted`；宿主展示 `formatted`，不再另加块外比例。

## 5 知识工具（scripts/knowledge.py）

离线只读。`show CA-03 CA-20` 一次读 1–5 个已知 ID；不知道 ID 时 `search "雨夜 湿地 反射" --limit 3`。`audit` 检查 ID、关联、来源与索引同步；`build-index` 仅维护时使用。工具不判断适用性。

## 6 偏好（scripts/prefs.py）

与任务共用 `--data-dir`：`init / status / template add|list|show|on|off|stop|resume / query / archive add / infer / set`。模板默认全部关闭，`on` 是唯一让模板自动生效的动作。`archive add` 仍执行完整必填校验，不支持直接归档 `0.3.1` 媒介或画幅为 `null` 的整理母版。读写规则见 [偏好协议](preferences.md)。

## 7 数据与恢复

每次业务修改发布新快照，`CURRENT` 原子切换，旧快照保留。恢复旧快照须确认无写入进程、由用户指定，不自动删锁或清历史。`preview --case portrait/environment/correction` 是预写合成示例，需要交互终端，其语义评审是作者预写，不是在线模型执行。
