"""Deterministic gate; LLM review is an explicit, hash-bound attestation."""
import re
from contracts import COMPILED_KINDS, VERSION, digest, require
from master import is_approved, latest
from terms import NAME_FACETS, find_groups, group_status, normalize, present
import adapter

AXES = ("omissions", "additions", "relations", "requirements")


def prepare(state, target=None):
    master = latest(state)
    require(is_approved(state, master), "拒绝编译：用户尚未确认当前母版版本")
    require(state["coordination"]["status"] == "pass", "拒绝编译：整体协调尚未通过")
    selected = adapter.route(state.get("compilation_target", "generic") if target is None else target)
    adapter.validate_ratio(selected, master["items"][master["globals"]["aspect_ratio"]]["value"])
    require(state["attempts"].get(str(master["revision"]), 0) < 1 + state["limits"]["max_integrity_retries"],
            "编译重试预算已耗尽，请报告问题；不得降低要求")
    facts = {key: item for key, item in master["items"].items() if item["kind"] in COMPILED_KINDS}
    constraints = {key: item for key, item in master["items"].items() if item["kind"] == "constraint"}
    manifest = {"master_id": master["master_id"], "revision": master["revision"],
                "master_hash": digest(master), "adapter_id": selected["id"],
                "aspect_ratio_delivery": selected,
                "facts": facts, "constraints": constraints, "version": VERSION}
    return {"manifest": manifest, "manifest_hash": digest(manifest),
            "host_instruction": "LLM 从本清单编译紧凑自然语言 segments；先合并同一对象的重复事实，再组织正文，保留全部独立限定与名称。"
            "九区域用于检查，不逐区复述；一个segment可覆盖多个item_ids，同一句引文可支持多个实际表达的事实。"
            "设计理由和检查说明留在内部，逐项复核覆盖；程序不证明去重质量。比例只填parameters.aspect_ratio，不在segments预写画幅控制。"
            "target按本次已选路由填写（省略只表示generic），Adapter依据aspect_ratio_delivery决定最终块内/块外位置。"
            "候选可带有效 language 标记（如 zh-CN、en、ja）声明正文语言；省略时按路由默认语言。自动名称别名检查只覆盖 zh/en，"
            "其他合法语言一律 not_checked，不能静默按中英文处理；其复核 note 必须写出母版原名称或原描述（短值可整体引用，长值优先引用待复核名称），"
            "并给出对应段落引文「…」；短于4字的正文引文须是登记名称/别名或母版原文并按词边界核对。"
            "matched 只代表列出的名称组，其余名称与语义仍由逐项复核。四个语义轴不能用覆盖 ID 代替。不得补充视觉事实。"}


def body(candidate):
    return adapter.render(candidate)["prompt"]


def target_language(candidate, route):
    value = candidate.get("language")
    if value is None:
        value = (route.get("language_policy") or {}).get("default_prompt_language") or "zh-CN"
    require(type(value) is str and value.strip(), "language 字段无效")
    tag = value.strip().lower().replace("_", "-")
    require(re.fullmatch(r"[a-z]{2,3}(-[a-z0-9]{2,8})*", tag) is not None,
            "language 不是有效的语言标记")
    return tag.split("-")[0]


def description_text(candidate):
    route = adapter.route(candidate.get("target", "generic"))
    if route["prompt"] == "json-layout":
        from moss_layout import description_text as layout_description
        return layout_description(candidate)
    return body(candidate)


def name_checks(master, candidate):
    """Per-item name status; submit and deliver share this entry point."""
    route = adapter.route(candidate.get("target", "generic"))
    language = target_language(candidate, route)
    is_layout = route["prompt"] == "json-layout"
    if is_layout:
        description = normalize(description_text(candidate))
    segment_texts = {}
    for segment in candidate["segments"]:
        for key in segment["item_ids"]:
            segment_texts.setdefault(key, []).append(segment["text"])
    checks = []
    for key in master["zones"]["character_art"]:
        item = master["items"][key]
        if item["kind"] != "visual_fact":
            continue
        item_text = description if is_layout else normalize("\n".join(segment_texts.get(key, [])))
        matched = find_groups(item["value"])
        if matched:
            overall = "matched"
            details = []
            for group in matched:
                status, detail = group_status(item_text, group, language)
                if status == "missing":
                    overall = "missing"
                elif status == "not_checked" and overall != "missing":
                    overall = "not_checked"
                details.append({"group": group["id"], "names": group["names"],
                                "aliases": group["aliases"], "status": status,
                                "matched_or_expected": detail})
            checks.append({"item_id": key, "facet": item["facet"], "status": overall,
                           "groups": details, "requires_review": overall == "not_checked",
                           "coverage": "列出的名称组", "reason": "registered name group"})
        else:
            review_required = any(word in item["facet"] for word in NAME_FACETS)
            checks.append({"item_id": key, "facet": item["facet"], "status": "not_checked",
                           "groups": [], "requires_review": review_required,
                           "coverage": "无已登记名称组",
                           "reason": "名称映射未识别到登记名称；" +
                                     ("名称类 facet，需语义复核原文与译名" if review_required
                                      else "facet 非名称类，名称未自动检查，由逐项语义复核覆盖")})
    return {"language": language, "checks": checks}


def missing_names(check):
    names = []
    for group in check["groups"]:
        if group["status"] == "missing":
            names.extend(group["names"])
    return names


def master_evidence(note, value, groups):
    """A short value may be quoted as a whole; a longer one should name the unchecked name."""
    note_norm = normalize(note)
    value_norm = normalize(value)
    if not value_norm:
        return False
    unchecked = [name for group in groups if group["status"] == "not_checked" for name in group["names"]]
    if unchecked:
        return any(normalize(name) in note_norm for name in unchecked)
    if len(value_norm) < 4:
        return value_norm in note_norm
    first_clause = re.split(r"[，。；、]", value_norm)[0].strip()
    if len(first_clause) >= 4:
        windows = {first_clause[i:i + 4] for i in range(len(first_clause) - 3)}
    else:
        windows = {first_clause} if first_clause else set()
    return any(window in note_norm for window in windows)


def quote_evidence(note, texts, value, groups):
    """A body quote must occur in the fact's own segment; short quotes need registered/master support."""
    expressions = {normalize(expr) for group in groups for expr in group["names"] + group["aliases"]}
    value_norm = normalize(value)
    texts_norm = [normalize(text) for text in texts]
    for quote in re.findall(r"「([^」]+)」", note):
        quote_norm = normalize(quote)
        if len(quote_norm) < 2:
            continue
        if len(quote_norm) >= 4:
            if any(quote_norm in text for text in texts_norm):
                return True
            continue
        if not any(present(text, quote) for text in texts_norm):
            continue
        if quote_norm in expressions or quote_norm in value_norm:
            return True
    return False


def name_problems(master, candidate, review=None):
    """Shared name gate for submit and deliver; returns (checks, problems)."""
    names = name_checks(master, candidate)
    problems = []
    segment_texts = {}
    for segment in candidate["segments"]:
        for key in segment["item_ids"]:
            segment_texts.setdefault(key, []).append(segment["text"])
    for check in names["checks"]:
        if check["status"] == "missing":
            problems.append("母版名称未进入正文: " + ",".join(missing_names(check)) +
                            " (" + check["item_id"] + ")")
    if review is not None:
        for check in names["checks"]:
            if check["status"] != "not_checked" or not check.get("requires_review"):
                continue
            item_id = check["item_id"]
            note = review["item_results"].get(item_id, {}).get("note", "")
            value = master["items"][item_id]["value"]
            if not isinstance(value, str):
                continue
            if not master_evidence(note, value, check["groups"]):
                problems.append("not_checked 项复核未写出母版原名称或原描述: " + item_id)
            if not quote_evidence(note, segment_texts.get(item_id, []), value, check["groups"]):
                problems.append("not_checked 项复核缺少对应段落引文: " + item_id)
    return names, problems


def review_hash(candidate):
    value = {"segments": candidate["segments"], "parameters": candidate["parameters"]}
    if "target" in candidate:
        value.update({"target": candidate["target"], "route": adapter.route(candidate["target"]),
                      "delivery": adapter.render(candidate)})
    if "language" in candidate:
        value.update({"language": candidate["language"]})
    return digest(value)


def inspect(state, candidate, review):
    required = {"master_hash", "segments", "parameters"}
    allowed = (required, required | {"target"}, required | {"language"}, required | {"target", "language"})
    require(type(candidate) is dict and set(candidate) in allowed, "成品字段错误")
    if "language" in candidate:
        require(type(candidate["language"]) is str and bool(candidate["language"].strip()), "language 字段无效")
    packet = prepare(state, candidate.get("target", "generic"))
    manifest = packet["manifest"]
    if "compilation_target" in state:
        require(adapter.route(state["compilation_target"])["id"] == manifest["adapter_id"],
                "成品目标与本次已选路由不同，不能回落通用或其他模型排版")
    problems = []
    require(candidate["master_hash"] == manifest["master_hash"], "成品母版版本过期")
    require(type(candidate["segments"]) is list and bool(candidate["segments"]), "成品段落为空")
    covered = set()
    segment_texts = {}
    for segment in candidate["segments"]:
        require(type(segment) is dict and set(segment) == {"text", "item_ids"}, "段落字段错误")
        require(type(segment["text"]) is str and bool(segment["text"].strip()), "段落文本为空")
        require(type(segment["item_ids"]) is list and bool(segment["item_ids"]), "段落缺少覆盖引用")
        require(all(type(x) is str for x in segment["item_ids"]), "覆盖引用类型错误")
        covered.update(segment["item_ids"])
        for key in segment["item_ids"]:
            segment_texts.setdefault(key, []).append(segment["text"])
    expected = set(manifest["facts"])
    ratio_id = latest(state)["globals"]["aspect_ratio"]
    is_layout = manifest["aspect_ratio_delivery"]["prompt"] == "json-layout"
    parameter_keys = {"aspect_ratio", "image_size"} if is_layout else {"aspect_ratio"}
    require(type(candidate["parameters"]) is dict and set(candidate["parameters"]) == parameter_keys, "参数字段错误")
    if candidate["parameters"]["aspect_ratio"] != manifest["facts"][ratio_id]["value"]:
        problems.append("画幅与母版不同")
    adapter.ratio_text(candidate["parameters"]["aspect_ratio"])
    problems += adapter.control_problems(candidate, [item["value"]["literal"] for item in manifest["facts"].values()
                                                     if item["kind"] == "image_text"])
    master = latest(state)
    rendered_body = body(candidate)
    covered.add(ratio_id)
    if expected - covered:
        problems.append("遗漏设计事实: " + ",".join(sorted(expected - covered)))
    if covered - expected:
        problems.append("未知或不可编译设计项: " + ",".join(sorted(covered - expected)))
    if is_layout:
        from moss_layout import visible_texts
        rendered_texts = visible_texts(candidate)
    else:
        rendered_texts = [rendered_body]
    for key, item in manifest["facts"].items():
        if item["kind"] == "image_text" and not any(item["value"]["literal"] in text for text in rendered_texts):
            problems.append("画面文字未逐字保留: " + key)
    require(type(review) is dict and set(review) == {"master_hash", "artifact_hash", "reviewer", "evidence_ref", "axes", "item_results"}, "语义复核字段错误")
    require(review["master_hash"] == manifest["master_hash"] and review["artifact_hash"] == review_hash(candidate), "语义复核与成品或母版不匹配")
    require(type(review["reviewer"]) is str and bool(review["reviewer"].strip()) and
            type(review["evidence_ref"]) is str and bool(review["evidence_ref"].strip()), "缺少语义复核来源")
    require(type(review["axes"]) is dict and set(review["axes"]) == set(AXES), "语义复核轴不完整")
    require(type(review["item_results"]) is dict and set(review["item_results"]) == expected, "逐项语义复核范围不完整")
    results = []
    for value in list(review["axes"].values()) + list(review["item_results"].values()):
        require(type(value) is dict and set(value) == {"result", "note"}, "语义复核结论结构错误")
        require(value["result"] in ("pass", "fail", "uncertain") and type(value["note"]) is str and bool(value["note"].strip()), "语义复核结论无效")
        results.append(value["result"])
    names, name_issues = name_problems(master, candidate, review)
    problems += name_issues
    checks_by_id = {check["item_id"]: check for check in names["checks"]}
    for key, item in manifest["facts"].items():
        if item["kind"] != "visual_fact":
            continue
        note = review["item_results"][key]["note"]
        check = checks_by_id.get(key)
        groups = check["groups"] if check else []
        if not quote_evidence(note, segment_texts.get(key, []), item["value"], groups):
            problems.append("复核缺少可核对的对应段落引文: " + key)
    semantic = "fail" if "fail" in results else "uncertain" if "uncertain" in results else "pass"
    result = "fail" if problems or semantic == "fail" else semantic
    return {"result": result, "structural": "fail" if problems else "pass", "semantic": semantic,
            "problems": problems, "name_checks": names["checks"], "name_language": names["language"],
            "assurance_mode": "python-plus-host-llm-attestation",
            "limitation": "Python 不证明自然语言等义；matched 只代表列出的名称组，其余名称与语义由逐项复核；not_checked 不因复核 pass 改为 matched。"}
