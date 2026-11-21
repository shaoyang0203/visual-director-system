# 交付契约

## 目标与路由卡

用户指定目标时读对应卡；未指定时用 generic，并告诉用户可以指定模型。多目标时每个目标各读一张卡、各核对一次。

|目标（别名见 registry.json）|卡|
|---|---|
|generic|[generic.md](adapters/generic.md)|
|gpt-web|[gpt.md](adapters/gpt.md)|
|midjourney|[midjourney.md](adapters/midjourney.md)|
|krea2|[krea2.md](adapters/krea2.md)|
|grok-web|[grok.md](adapters/grok.md)|
|qwen-image-2.1|[qwen-image.md](adapters/qwen-image.md)|
|z-image|[z-image.md](adapters/z-image.md)|
|gemini-image|[gemini.md](adapters/gemini.md)|
|seedream|[seedream.md](adapters/seedream.md)|
|moss-image|[moss.md](adapters/moss.md)|
|moss-image-layout|[moss-layout.md](adapters/moss-layout.md)|

用户点名表外模型时，说明不在本版范围，可明确改用 generic。SDXL、Pony、Illustrious、Anima、FLUX（含 Klein）为用户确定的排除项。

## 适配

- 只做等义转换：语言、语序、分段、合并、格式与比例位置；主体数量、动作、场景、空间、主光、颜色、风格保持不变。
- 语言按卡的默认；用户长期语言偏好替换默认语言，卡的结构不变，末尾一行提示如 `[语言：中文（路由默认英文）]`。
- 画面文字逐字保留原语言、标点和换行。
- 比例按卡的位置只出现一次。卡上不支持该比例时说明并让用户选择。

## 格式

- 提示词放一个代码块；块外设置（比例、尺寸）放在代码块上方。
- 正文只写正向画面描述；内部ID、来源、复核记录、接口字段与平台外围能力留在成品外。
- 参数按目标路由卡与用户明确要求提供；像素尺寸仅来自用户给定或可核实的目标设置。
- 继续压缩会损失含义时停止。仍超出卡上建议长度时，列出可删的次要设计及代价，由用户决定。
