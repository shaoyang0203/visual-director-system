"""Deterministic name gate for confirmed masters.

Names come from the curated mapping in knowledge/names.json, never from every
search keyword in the index. A group holds one design name with explicitly
registered equivalent expressions. Matching is per group so two different
design names both have to survive compilation.
"""
import json
import re

from contracts import ROOT, require

MAP_PATH = ROOT / "knowledge" / "names.json"
NAME_FACETS = ("妆容", "妆发", "发型", "发式", "服装", "衣", "首服", "冠", "饰",
               "hair", "makeup", "clothing", "styling", "outfit")
_CACHE = None


def groups():
    global _CACHE
    if _CACHE is None:
        try:
            payload = json.loads(MAP_PATH.read_text(encoding="utf-8"))
        except OSError as exc:
            require(False, "名称映射缺失或不可读: " + str(exc))
        except ValueError as exc:
            require(False, "名称映射不是合法 JSON: " + str(exc))
        require(payload.get("schema") == "vds-name-map-1", "名称映射格式无效")
        rows = payload.get("groups")
        require(isinstance(rows, list) and rows, "名称映射为空")
        index = json.loads((ROOT / "knowledge/index.json").read_text(encoding="utf-8"))
        entry_ids = {entry["id"] for entry in index.get("entries", [])}
        names = {}
        aliases = {}
        alias_owner = {}
        seen_groups = set()
        for row in rows:
            require(type(row) is dict and set(row) == {"id", "entry", "names", "aliases"}, "名称映射条目字段错误")
            require(re.fullmatch(r"CH-[0-9]{2,3}:\d+", row["id"]) is not None, "名称映射组 ID 格式无效: " + str(row["id"]))
            require(row["id"].startswith(row["entry"] + ":"), "名称映射组 ID 与条目不一致: " + str(row["id"]))
            require(row["id"] not in seen_groups and row["id"], "名称映射组 ID 重复")
            require(row["entry"] in entry_ids, "名称映射引用了不存在的知识条目: " + str(row["entry"]))
            require(type(row["names"]) is list and row["names"] and
                    all(type(x) is str and len(x.strip()) >= 2 for x in row["names"]), "名称映射缺少有效标准名称")
            require(type(row["aliases"]) is list and
                    all(type(x) is str and len(x.strip()) >= 2 for x in row["aliases"]), "名称映射别名过短或无效")
            seen_groups.add(row["id"])
            for name in row["names"]:
                key = normalize(name)
                require(key not in names, "标准名称跨组重复: " + name)
                names[key] = row["id"]
            for alias in row["aliases"]:
                key = normalize(alias)
                if all(ord(ch) < 128 for ch in alias):
                    require(len(alias.strip()) >= 3, "英文别名过短，可能误命中其他词: " + alias)
                require(key not in alias_owner or alias_owner[key] == row["id"], "别名跨组重复: " + alias)
                alias_owner[key] = row["id"]
                aliases[key] = row["id"]
        require(not (set(aliases) & set(names)), "别名与其他名称组的标准名称冲突")
        _CACHE = rows
    return _CACHE


def normalize(text):
    return re.sub(r"\s+", " ", text.casefold()).strip()


def expression_language(expression):
    if any("\u4e00" <= ch <= "\u9fff" for ch in expression):
        return "zh"
    if all(ord(ch) < 128 for ch in expression):
        return "en"
    return "other"


def present(body_norm, expression):
    expr = normalize(expression)
    if not expr:
        return False
    if any("\u4e00" <= ch <= "\u9fff" for ch in expr):
        return expr in body_norm
    escaped = re.escape(expr).replace(r"\ ", r"\s+")
    pattern = r"(?<![a-z0-9])" + escaped + r"(?![a-z0-9])"
    return re.search(pattern, body_norm) is not None


def find_groups(value):
    """Registered groups whose name or alias occurs in a confirmed fact value."""
    if not isinstance(value, str):
        return []
    value_norm = normalize(value)
    found = []
    for group in groups():
        expressions = group["names"] + group["aliases"]
        if any(present(value_norm, expression) for expression in expressions):
            found.append(group)
    return found


def group_status(body_norm, group, language):
    """matched / missing / not_checked for one group."""
    if language not in ("zh", "en"):
        return "not_checked", []
    expressions = group["names"] + group["aliases"]
    matched = [expression for expression in expressions if present(body_norm, expression)]
    if matched:
        return "matched", matched
    target = [expression for expression in expressions if expression_language(expression) == language]
    if target:
        return "missing", target
    return "not_checked", []
