# moss-image-layout 专用规则

与[交付格式](deliver.md)一起使用。仅在用户明确需要位置、群像关系或文字排版的布局控制时使用。Layout 来自已经定好的画面，写 JSON 时不重新改布局。

格式示例（坐标只是 `1024×1024` 画布的格式示意，须替换为实际设计）：

```json
{"summary":{"meta":["poster"],"canvas":"single","caption":"整体画面与风格描述"},"items":[{"label":"text","caption":"标题样式与位置","text":"原始画面文字","bbox":[-416,-384,-288,384]},{"label":"object","caption":"主体可见描述","bbox":[-192,-288,384,288]}],"bbox_coord_space":"abs_centralized","bbox_format":"yxyx"}
```

- `summary` 描述整体画面；`items` 是平面元素列表，使用 `label`、`caption`、`bbox`；文字元素另含逐字保真的 `text`。支持 `object`、`character`、`text` 三类；可选的 `tags`、`palette` 只写已定的画面事实。
- 坐标为中心原点绝对像素，顺序为 `[y_min,x_min,y_max,x_max]`；`x` 向右、`y` 向下；宽 `W`、高 `H` 时合法范围分别为 `±W/2`、`±H/2`。不混用归一化坐标、左上原点或其他 bbox 顺序。
- 必须有明确的画布像素尺寸：宽高为 16 的倍数的正整数，宽高比与画幅严格一致。用户没给且无法确定时先问，不猜默认分辨率。
- 交付前自行核对：JSON 语法有效、没有重复键、坐标都是边界内整数、造型名称与画面文字没有遗漏。代码块里输出紧凑的单行 JSON，画幅与画布尺寸写在代码块上方。

官方参考（2026-11-01）：[MOSS 官方 README](https://github.com/OpenMOSS/MOSS-Image/blob/main/README.md)、[USERGUIDE](https://github.com/OpenMOSS/MOSS-Image/blob/main/USERGUIDE.md)。Layout 在官方指南中属于实验能力，语法正确不代表模型能精确落实全部坐标。
