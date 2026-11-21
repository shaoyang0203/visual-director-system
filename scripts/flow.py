"""One-host workflow with explicit user receipts and bounded coordination."""
from uuid import uuid4
from contracts import VERSION, digest, require
from master import allows_unspecified, is_approved, latest, render, verify_revision
from compile_checks import body, inspect
import adapter

COMPOSITION_AXES = ("subject_scale_position", "framing_crop", "foreground_occlusion", "background_information",
                    "spatial_relations", "visual_hierarchy", "negative_space_overall")


def ratio_review_required(state):
    current = latest(state)
    baseline = state["masters"][0]
    for event in reversed(state["events"]):
        if event["type"] == "coordination" and event["result"] == "pass":
            baseline = next(m for m in state["masters"] if m["revision"] == event["revision"])
            break
    def ratio(master):
        key = master["globals"]["aspect_ratio"]
        return None if key is None else adapter.ratio_text(master["items"][key]["value"], normalized=True)
    return ratio(baseline) != ratio(current)

MODES = ("explore", "direct", "limited")
DIRECTION_RANGE = (2, 5)


def task_mode(state):
    """Snapshots created before task modes existed are exploration tasks."""
    return state.get("mode", "explore")


def new_task(task_id, request, limits=None, mode="explore", user_ref=None):
    require(type(request) is str and bool(request.strip()), "需求不能为空")
    require(mode in MODES, "任务模式无效：explore / direct / limited")
    limits = limits or {"max_coordination_rounds": 3, "max_integrity_retries": 1}
    require(set(limits) == {"max_coordination_rounds", "max_integrity_retries"}, "预算字段错误")
    require(type(limits["max_coordination_rounds"]) is int and limits["max_coordination_rounds"] >= 1 and
            type(limits["max_integrity_retries"]) is int and limits["max_integrity_retries"] >= 0, "预算必须是有效整数")
    state = {"data_version": 1, "version": VERSION, "task_id": task_id, "request": request, "mode": mode,
             "limits": limits, "phase": "exploring", "concepts": [], "selected": None,
             "masters": [], "displays": [], "approvals": [], "attempts": {},
             "compilations": [], "corrections": [], "events": [],
             "coordination": {"epoch": uuid4().hex, "round": 0, "status": "pending", "issues": []}}
    if mode != "explore":
        # A direct or limited task takes its direction from the user's own request.
        # This records where the direction came from; it is not an approval of any master.
        require(type(user_ref) is str and bool(user_ref.strip()), "直接创作或整理任务须提供用户需求消息来源 user_ref")
        state["concepts"] = [{"id": mode, "source": "user_request", "user_ref": user_ref}]
        state["selected"] = mode
        state["phase"] = "designing"
        state["events"].append({"type": "direct_entry", "mode": mode, "user_ref": user_ref})
    else:
        require(user_ref is None, "探索任务的方向来源在 select 时记录")
    return state

def set_concepts(state, concepts):
    require(task_mode(state) == "explore", "直接创作或整理任务没有方向选项；需要探索请新建 explore 任务")
    require(not state["masters"], "已有母版请局部修改，不重置任务")
    require(state["selected"] is None, "已选择创意方向，不能覆盖方案列表；重新探索请建立新任务并重新选择")
    low, high = DIRECTION_RANGE
    require(type(concepts) is list and low <= len(concepts) <= high, "方向选项按需提供 2–5 个")
    for c in concepts:
        require(type(c) is dict and set(c) == {"id", "core", "focus", "feature", "scene"}, "方案字段错误")
        require(all(type(v) is str and v.strip() for v in c.values()), "方案内容不能为空")
    require(len({c["id"] for c in concepts}) == len(concepts), "方案 ID 重复")
    require(len({c["scene"] for c in concepts}) == len(concepts), "完整构思重复")
    state["concepts"] = concepts
    return {"saved": True, "semantic_diversity": "需宿主 LLM 判断，程序只检查重复和结构"}

def select(state, concept_id, user_ref):
    require(task_mode(state) == "explore", "直接创作或整理任务已由用户需求确定方向，无需选择")
    require(not state["masters"] and user_ref, "需方向选择来源；已有母版请修改")
    require(any(c["id"] == concept_id for c in state["concepts"]), "方案不存在")
    state["selected"] = concept_id
    state["phase"] = "designing"
    state["events"].append({"type": "direction_selected", "user_ref": user_ref, "concept_id": concept_id})
    return {"saved": True, "master_approved": False}

def validate_limited_master(master):
    ratio_id = master["globals"]["aspect_ratio"]
    for key, item in master["items"].items():
        if key == ratio_id:
            if item["design_source"] != "user_specified":
                require(item["design_source"] == "model_added" and
                        item["confirmation_status"] == "pending" and
                        item["constraint_strength"] == "adjustable_design",
                        "整理任务未指定画幅时，仅允许记录为待确认的可调整工具设置建议: " + key)
            continue
        require(item["design_source"] == "user_specified",
                "整理任务（limited）不得新增非用户指定的设计事实或默认媒介；用户要求改风格或补设计时请新建 direct 任务: " + key)


def save_master(state, master, authorization=None):
    require(state["selected"], "尚未选择创意方向")
    require(any(c["id"] == state["selected"] for c in state["concepts"]), "已选方向不在当前方案中，须重新选择")
    change = verify_revision(state, master, authorization)
    if task_mode(state) == "limited":
        validate_limited_master(master)
    state["masters"].append(master)
    state["phase"] = "designing"
    state["coordination"]["status"] = "pending"
    state["events"].append({"type": "master_revision", "revision": master["revision"], **change})
    return {"saved": True, **change}

def begin_change(state, user_ref):
    require(user_ref and state["masters"], "修改需用户来源及既有母版")
    state["coordination"] = {"epoch": uuid4().hex, "round": 0, "status": "pending", "issues": []}
    state["events"].append({"type": "user_change", "user_ref": user_ref})
    state["phase"] = "designing"
    return {"saved": True}

def coordinate(state, result, issues, summary, domains, aspect_ratio_review=None):
    require(result in ("pass", "fail", "uncertain") and type(issues) is list and summary, "协调结论无效")
    allowed = {"character_art", "scene_art", "camera_composition", "lighting_color", "material_appearance"}
    require(type(domains) is list and set(domains) <= allowed, "专业领域无效")
    c = state["coordination"]
    require(c["round"] < state["limits"]["max_coordination_rounds"], "已达三轮或配置上限，需向用户说明冲突")
    require(result != "pass" or not issues, "存在未解决问题不能标记 pass")
    if aspect_ratio_review is not None:
        require(type(aspect_ratio_review) is dict and set(aspect_ratio_review) == set(COMPOSITION_AXES), "画幅构图复核范围不完整")
        for note in aspect_ratio_review.values():
            require(type(note) is dict and set(note) == {"result", "note"} and note["result"] in ("pass", "fail", "uncertain")
                    and type(note["note"]) is str and bool(note["note"].strip()), "画幅构图复核记录无效")
        require(result != "pass" or all(note["result"] == "pass" for note in aspect_ratio_review.values()),
                "画幅构图仍fail或uncertain，不能协调通过")
    require(result != "pass" or not ratio_review_required(state) or aspect_ratio_review is not None,
            "画幅变化后须复核人物尺度位置、裁切、前景、背景、空间、层级及留白；不能只改比例参数")
    c.update({"round": c["round"] + 1, "status": result, "issues": issues})
    state["events"].append({"type": "coordination", "revision": latest(state)["revision"],
                            "result": result, "summary": summary, "domains": domains, "epoch": c["epoch"],
                            "master_hash": digest(latest(state)), "aspect_ratio_review": aspect_ratio_review})
    state["phase"] = "awaiting_confirmation" if result == "pass" else "needs_attention"
    return {"saved": True, "round": c["round"], "result": result}

def show(state):
    master = latest(state)
    text = render(master, is_approved(state, master), allows_unspecified(state))
    receipt = {"revision": master["revision"], "master_hash": digest(master), "render_hash": digest(text)}
    state["displays"].append(receipt)
    return {"text": text, "render_receipt": receipt, "saved": True,
            "note": "宿主仍须将完整文本展示给用户；工具无法证明人已阅读。"}

def approve(state, revision, user_ref):
    master = latest(state)
    require(type(revision) is int and revision == master["revision"] and
            type(user_ref) is str and bool(user_ref.strip()), "必须确认当前具体版本并提供用户确认来源")
    prior_refs = {e["user_ref"].strip() for e in state.get("events", [])
                  if e.get("type") in ("direct_entry", "direction_selected") and type(e.get("user_ref")) is str}
    prior_refs.update(c["user_ref"].strip() for c in state.get("concepts", [])
                      if type(c) is dict and type(c.get("user_ref")) is str)
    require(user_ref.strip() not in prior_refs,
            "批准引用不能复用需求或方向选择的 user_ref；须提供展示当前母版后的用户确认引用")
    require(state["coordination"]["status"] == "pass", "整体协调未通过")
    require(any(d["revision"] == revision and d["master_hash"] == digest(master) for d in state["displays"]), "尚未渲染展示当前母版")
    receipt = {"revision": revision, "master_hash": digest(master), "user_ref": user_ref}
    state["approvals"].append(receipt)
    state["phase"] = "approved"
    return {"saved": True, "approval": receipt}

def submit(state, candidate, review):
    from compile_checks import prepare
    try:
        require_manifest(state)
        prepare(state)
    except (ValueError, KeyError, TypeError) as exc:
        # Rejected preconditions do not consume attempts or overwrite a prior record.
        attempt = state["attempts"].get(str(state["masters"][-1]["revision"]), 0) if state["masters"] else 0
        return {"saved": False, "result": "fail", "structural": "fail", "semantic": "not_run",
                "problems": [str(exc)], "attempt": attempt}
    try:
        report = inspect(state, candidate, review)
    except (ValueError, KeyError, TypeError) as exc:
        # Even malformed submissions consume the same bounded retry budget.
        report = {"result": "fail", "structural": "fail", "semantic": "not_run", "problems": [str(exc)]}
    rev = str(latest(state)["revision"])
    state["attempts"][rev] = state["attempts"].get(rev, 0) + 1
    record = {"candidate": candidate, "review": review, "report": report,
              "revision": int(rev), "master_hash": digest(latest(state)),
              "attempt": state["attempts"][rev]}
    state["compilations"].append(record)
    state["phase"] = "ready_to_deliver" if report["result"] == "pass" else "compile_blocked"
    return {"saved": True, **report, "attempt": state["attempts"][rev]}


def require_manifest(state):
    master = latest(state)
    require("compilation_target" in state, "请先执行 manifest，明确记录当前版本的编译目标")
    selected = adapter.route(state["compilation_target"])["id"]
    require(any(event["type"] == "adapter_selected" and
                event.get("revision") == master["revision"] and
                event.get("master_hash") == digest(master) and
                adapter.route(event["target"])["id"] == selected
                for event in state["events"]), "当前母版版本尚未生成有效 manifest，请重新执行")


def prepare_manifest(state, target=None):
    from compile_checks import prepare
    packet = prepare(state, target)
    selected = packet["manifest"]["aspect_ratio_delivery"]["target"]
    state["compilation_target"] = selected
    state["events"].append({"type": "adapter_selected", "target": selected,
                            "revision": latest(state)["revision"], "master_hash": digest(latest(state))})
    return {**packet, "saved": True}

def deliver(state):
    master = latest(state)
    require_manifest(state)
    require(is_approved(state, master) and state["coordination"]["status"] == "pass", "当前母版未获有效确认或协调未通过")
    require(bool(state["compilations"]), "尚未完成编译")
    c = state["compilations"][-1]
    require(c["report"]["result"] == "pass" and c["master_hash"] == digest(master), "成品未通过或已过期")
    if "compilation_target" in state:
        require(adapter.route(state["compilation_target"])["id"] ==
                adapter.route(c["candidate"].get("target", "generic"))["id"], "目标路由已变，旧成品不能交付")
    from compile_checks import name_problems, review_hash
    require(c["review"]["artifact_hash"] == review_hash(c["candidate"]), "成品或路由已变，须重新复核")
    names, name_problems_list = name_problems(master, c["candidate"], c["review"])
    require(not name_problems_list, "成品名称检查未通过: " + "; ".join(name_problems_list))
    ratio = c["candidate"]["parameters"]["aspect_ratio"]
    return {**adapter.render(c["candidate"]), "aspect_ratio": ratio,
            "revision": master["revision"], "review": c["report"],
            "name_checks": names["checks"], "name_language": names["language"],
            "delivery": "通用自然语言，画幅位置遵循已选Adapter；未调用图像模型。"}

def correction(state, record):
    require(type(record) is dict and set(record) == {"issue", "intent", "options"}, "纠偏字段错误")
    require(type(record["issue"]) is str and bool(record["issue"].strip()), "纠偏问题描述不能为空")
    require(record["intent"] in ("unclear", "intentional_contrast", "conflict"), "意图判断错误")
    require(type(record["options"]) is list and 2 <= len(record["options"]) <= 3, "纠偏须含严格执行及1–2个替代方案")
    require(all(type(x) is dict for x in record["options"]), "纠偏选项必须为对象")
    modes = [x.get("mode") for x in record["options"]]
    require(modes[0] == "strict" and modes[1:] in (["local"], ["reconstruct"], ["local", "reconstruct"]),
            "纠偏首项须为严格执行，替代方案按局部调整、推荐重构顺序且不重复")
    for option in record["options"]:
        require(set(option) == {"mode", "design", "changes", "reason", "expected"} and
                all(type(x) is str and bool(x.strip()) for x in option.values()), "纠偏方案说明不完整")
    state["corrections"].append(record)
    return {"saved": True, "applied": False, "message": "建议不自动覆盖用户要求；等待选择。"}

