# 路由官方核实记录

从 V1.6.3 各路由文件迁出的核实记录，运行时不需要读取；更新路由卡时据此重新核实。记录不证明出图效果。

## gemini

官方核实：2026-11-01，[Google图像生成指南](https://ai.google.dev/gemini-api/docs/image-generation)。官方提供自然语言、画面文字和比例描述示例，支持语言包含zh-CN；型号参数能力不作本地实测保证。

## gpt

官方核实：2026-11-01，[OpenAI Image prompting — Prompting fundamentals](https://developers.openai.com/api/docs/guides/image-prompting#prompting-fundamentals)。官方建议复杂请求分段并选用易读、易维护的格式；实际图像效果需另行验证。

## grok

官方核实：2026-11-01，[xAI Image Prompting Guide](https://docs.x.ai/developers/model-capabilities/images/prompting-guide#write-the-subject-first)。官方针对 `grok-imagine-image-2.0` 建议主体先行；这是编译参考，不证明当前网页端后端身份或出图效果。未迁移API或图像编辑能力。

## krea2

编译依据为本地开源模型说明，不将官网服务的Creativity、Moodboard或网站扩写器纳入本地默认路由。语言选择由宿主LLM执行；Python Adapter仍只进行现有交付排版，不自动翻译。
官方核实：2026-11-01，[开源Prompting guidelines](https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md)推荐自然语言，可使用详细描述，也不要求繁复提示词工程，画面文字建议加引号。中文默认是用户确认的产品约定，不宣称官方只支持中文或中文必然优于其他语言。

## midjourney

官方核实：2026-11-01，[Midjourney Prompt Basics](https://docs.midjourney.com/hc/en-us/articles/32023408776205-Prompt-Basics)。官方建议清楚、简短的画面描述，避免冗长指令，同时说明重要细节需要保留、细节减少会降低控制；未规定本项目通用字数上限。实际图像效果待验证。
依据：2026-11-01已读取的[Midjourney Prompt Basics](https://docs.midjourney.com/hc/en-us/articles/32023408776205-Prompt-Basics)建议简短直接、保留重要细节；以上压缩步骤及母版确认边界是用户批准的产品实施规则，不冒充官方字数标准。
官方核实：2026-11-01，[Raw](https://docs.midjourney.com/hc/en-us/articles/32634113811853-Raw)、[Stylize](https://docs.midjourney.com/hc/en-us/articles/32196176868109-Stylize)。本条补充选择知识与交付说明，不宣称已经验证实际图像效果，也不迁移其他专用参数能力。

## moss-layout

官方核实：2026-11-01，[MOSS官方README](https://github.com/OpenMOSS/MOSS-Image/blob/main/README.md)、[USERGUIDE](https://github.com/OpenMOSS/MOSS-Image/blob/main/USERGUIDE.md)。Layout在官方指南中属于实验能力；本次程序检查不代表真实生图或所有checkpoint已经验证。

## qwen-image

官方核实：2026-11-01，[PE-T2I模型卡](https://huggingface.co/Qwen/Qwen-Image-2.1-PE-T2I)、[官方改写指令](https://huggingface.co/Qwen/Qwen-Image-2.1-PE-T2I/blob/main/system_prompt.txt)、[图像模型与工作流](https://github.com/QwenLM/Qwen-Image-2.1)。英文观察式是所采用的官方改写风格，不代表图像模型只能接收英文；单段与长度取舍、代码块交付按用户批准的产品规则执行。官方改写器中自行补设计、按题材默认比例的逻辑不接管本产品母版。

## seedream

官方核实：2026-11-01，[火山引擎生成指南](https://docs.volcengine.com/docs/ark/image-generation-tutorial?redirect=1&lang=zh)、[提示词语言与长度说明](https://docs.volcengine.com/docs/ark/image-generation-api?lang=zh&redirect=1)。所引接口文档仅用于核实模型与提示词能力，不引入API调用。

## z-image

官方核实依据：2026-11-01读取的[Tongyi-MAI/Z-Image官方仓库](https://github.com/Tongyi-MAI/Z-Image)包含中文自然语言示例，生成宽高作为工作流参数传入。中文默认和描述长度是用户确定的产品约定，不宣称中文是唯一支持语言，也不承诺实际执行效果。

