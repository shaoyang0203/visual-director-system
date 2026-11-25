反馈QQ群：805857748

# 视觉导演系统 V1.9-Flash-Turbo（`visual-director-v1-9-flash-turbo`）

像懂审美的摄影师与导演一样构思画面、统筹主光·摆位·配色、调配笔墨权重，将一切抽象概念彻底落地为单帧可见的视觉元素，**一轮直出**自然简练的正向文生图提示词。

- **零脚本 · 零填表 · 零外部存档**：不跑任何脚本，无多轮停点折腾，不在工作区创建任何隐藏目录，一句话几秒钟直接出词。
- **幕后视觉统筹（主光 · 横竖屏摆位 · 协调衬主体配色）**：内置三张精炼知识库（[主光](knowledge/主光.md)、[构图](knowledge/构图.md)、[配色](knowledge/配色.md)），自动匹配最佳宽高比、区分「竖屏人像居中主打」与「横屏人景偏置意境」，用协调底盘衬托主角色彩，绝不把理论解释废话塞进提示词。
- **正向单帧强防雷**：历史人名、典故与抽象概念强制拆解为直观衣冠地貌；彻底清零否定词与跨时间渐变词；严守景别可见边界与唯一第一视觉锚点。
- **参考图当轮反推与多平台适配**：支持参考图整图忠实反推与当轮指定元素借用（宿主支持看图时可用）；按需适配 `Krea 2`、`Midjourney`、`Grok`、`GPT`、`Qwen-Image`、`即梦 (Seedream)`、`Z-Image / MOSS-Image`、`Gemini-Image` 等主流生图平台。

---

## 目录结构

```text
visual-director-v1-9-flash-turbo/
├── SKILL.md                   # 技能核心主规则入口
├── README.md                  # 项目发行说明
├── knowledge/
│   ├── 主光.md                # 人像与自然实景主光选型库
│   ├── 构图.md                # 横竖屏画幅选择与人物景物空间摆位指南
│   └── 配色.md                # 色彩协调与衬托主体的幕后配法
└── references/
    ├── targets.md             # 目标生图平台交付格式速查表
    └── manual.md              # 用户常用说法速览
```

---

## 安装与使用

将解压后的 `visual-director-v1-9-flash-turbo` 文件夹（或克隆后的本仓库目录）放入对应智能体宿主的 `skills/` 目录即可启用（例如 `.agents/skills/`、`~/.gemini/config/skills/`、`~/.codex/skills/`、`~/.claude/skills/` 或 `.dsh/skills/`），也可放进工作区后直接对 Agent 说：

> 请读取 `visual-director-v1-9-flash-turbo/SKILL.md`，用这个技能帮我写提示词。

日常使用直接描述想画的内容或情绪即可一轮拿到提示词；发送 `说明` 或 `怎么用` 可查看常用说法示例。本场对话内的要求全程遵守，不跨会话自动保存偏好或模板。

## 问题反馈与许可说明

- 问题与建议交流：GitHub [Issues](https://github.com/shaoyang0203/visual-director-system/issues) / [Discussions](https://github.com/shaoyang0203/visual-director-system/discussions) 或反馈 QQ 群 `805857748`。
- 本项目采用 **PolyForm Strict License 1.0.0** 授权：允许个人学习、研究、测试等非商业用途；未经作者单独授权，禁止修改、制作衍生版本、重新分发或商业使用。
