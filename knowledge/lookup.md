# 查询入口

只为两类问题来这里：**选名字**、**问后果**。知识库不回答“还该加点什么”。找到条目后只读该条 `## ID` 一节（文件中的锚点如 `#ch-19`），不读整本。条目编号只作内部依据，不写进提示词。

## 选名字

|要选或要确认的|去哪|
|---|---|
|现代妆容风格、眼妆技法|[妆容与发型目录](nav-makeup-hair.md) → [CH-19~38](character/makeup-styles.md#ch-19)|
|现代发型：剪裁、披发、束盘、编发、背梳|[妆容与发型目录](nav-makeup-hair.md) → [CH-39~58](character/hairstyles.md#ch-39)|
|按情境选妆发；面部、肤质、状态的表达粒度|[CH-13~18](character/appearance-foundations.md#ch-13)|
|秦汉至民国发式、首服|[历史发式目录](nav-historical-hair.md)，基础 [CH-59~62](character/historical-hair-foundations.md#ch-59)|
|秦汉至现代服装|[服装目录](nav-clothing.md)，基础 [CH-113~116](character/clothing-foundations.md#ch-113)|
|整体造型：服装、发妆、配饰、身份与历史|[CH-01~06](character/design.md#ch-01)|
|衣片连接、廓形层次、体态受力、发妆遮挡、场合与携带|[CH-07~12](character/construction-styling.md#ch-07)|

选名字时的提醒：
- 历史发式中，发髻、首服、发罩、架饰要分清：幞头、冠冕是首服；䯼髻、大拉翅要有底座和固定。代表时期与人物关联用于排序，允许跨时代借鉴；阶层影响体量、材料、饰物。
- 服装按用户的粒度定主衣和必要搭配；领襟、衣长、袖型、裙裤轮廓、腰带只取识别或结构需要的部分。旗袍有多种廓形与开衩；变体只取已选的那一种。
- 名称描述造型本身，不用“学生妆”“舞女妆”这类职业标签；韩系、港风、新中式是风格标签，与人群外貌无关。

## 问后果

|推演时说不准的|去哪|
|---|---|
|此刻选哪个阶段，动作的可见证据是什么|[DR-01](director/narrative-staging.md#dr-01)、[DR-12](director/staging-decisions.md#dr-12)|
|整体场面怎样组织成一个画面|[DR-02](director/narrative-staging.md#dr-02)、[DR-11](director/staging-decisions.md#dr-11)|
|手、脚的接触，视线和遮挡在这个机位下能否看清|[DR-03](director/narrative-staging.md#dr-03)|
|多人、多道具：分组、归属、唯一对象|[DR-13](director/staging-decisions.md#dr-13)|
|主体会不会被淹没；层级、信息量、疏密节奏、视觉引导|[DR-04/05](director/narrative-staging.md#dr-04)、[DR-14](director/staging-decisions.md#dr-14)|
|有意的艺术反差、整体统一、几个选择互相牵制|[DR-06~08](director/integration-review.md#dr-06)|
|改了一处会牵动哪里；问题出在设计、写法还是模型|[DR-09/10](director/integration-review.md#dr-09)、[DR-15](director/staging-decisions.md#dr-15)|
|景别、透视、机位、构图密度|[CA-01~08](camera/design.md#ca-01)|
|画幅选择、参考图比例、改比例要动什么|[CA-09~18](camera/aspect-ratios.md#ca-09)|
|裁切与必见、机位边缘、人物与环境尺度、焦段与焦点|[CA-19~23](camera/shot-planning.md#ca-19)|
|光从哪里来、是否可信|[LC-01~03](lighting/foundations.md#lc-01)|
|光的软硬、衰减、光比、曝光、光色|[LC-04~08](lighting/foundations.md#lc-04)|
|脸上的阴影形状；Loop 布光与环形灯的区别|[LC-09~13](lighting/portrait-patterns.md#lc-09)|
|夜宴、雨廊、霓虹、明亮室内、暗场|[LC-14~18](lighting/scenarios.md#lc-14)|
|配色、肤色与环境反射|[LC-19/20](lighting/color.md#lc-19)|
|色彩面积与主辅、类似色、混合光、影子的形状|[LC-21~28](lighting/color-organization.md#lc-21)|
|空间是否成立、陈设用途、天气联动|[SC-01~04](scene/design.md#sc-01)|
|建筑连续、门廊庭院、家具任务面、道具、天气与植被|[SC-05~10](scene/spatial-design.md#sc-05)|
|纤维与布料、固体、水、皮肤在光下的样子|[MA-01~06](materials/appearance.md#ma-01)|
|织物组织、纱与蕾丝、绒与皮、珠石、玻璃、木石干湿|[MA-07~12](materials/surface-design.md#ma-07)|

## 读条目时

条目里有些用语与本系统不同：“母版”指当前画面设计；“Adapter / Compiler”指交付格式与写成品；“严格模式 / 确认”指用户要求先看设计再写提示词；“领域 / 总导演”指你从不同专业角度考虑同一画面；事实 ID、依赖图、source_refs、三字段、pass/fail/uncertain 等是知识编写时的流程用语，本系统不做这些记录，也不设门禁，遇到不确定时说明依据和缺口即可。条目里的英文例句是表达示例，不是要照抄的模板。来源与核实边界见 [sources.md](sources.md)。所有条目均未经真实出图验证。
