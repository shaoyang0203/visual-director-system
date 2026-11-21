"""Limited (prompt cleanup) tasks with no medium or aspect ratio in the user's original prompt.

Synthetic reviews only: these tests check gates and rendering, not prompt quality or images.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from testtmp import tempdir
import flow
from contracts import COMPILED_KINDS, ContractError, digest, validate_master
from test_regressions import fixture, review

# The user's real E2 prompt (古风师姐), recorded fact by fact without additions.
E2_FACTS = [
    ('visual_subject_hierarchy', '人物身份', '一位绝美东方古风师姐'),
    ('character_art', '发型', '高发髻'),
    ('character_art', '发色发长', '乌黑长发'),
    ('character_art', '发饰', '古风发簪流苏配饰'),
    ('character_art', '脸型与五官', '精致五官'),
    ('character_art', '服装', '浅米色透纱飘逸古风长裙'),
    ('character_art', '服装结构', '高开叉裙装'),
    ('character_art', '服装配饰', '金色腰封'),
    ('character_art', '身材', '丰满曼妙身材'),
    ('action_spatial_relations', '动作', '正向镜头缓步走来，双臂自然舒展'),
    ('scene_art', '场景', '中式古典庭院场景，青石板小路，古树院墙'),
    ('lighting_color', '光线', '影视柔光'),
    ('camera_composition', '景深', '景深虚化'),
]
SOURCE = 'user:e2-original-prompt'


def item(kind, facet, value, source='user_specified'):
    return {'kind': kind, 'facet': facet, 'value': value, 'design_source': source, 'source_refs': [SOURCE],
            'confirmation_status': 'confirmed' if source == 'user_specified' else 'pending',
            'constraint_strength': 'hard_constraint' if source == 'user_specified' else 'adjustable_design',
            'depends_on': []}


def e2_master(medium=None, ratio=None, version='0.3.1'):
    zones = {zone: [] for zone in ('intent_constraints', 'creative_direction_moment', 'visual_subject_hierarchy',
                                   'character_art', 'scene_art', 'action_spatial_relations', 'camera_composition',
                                   'lighting_color', 'material_visual_expression')}
    items = {}
    for n, (zone, facet, value) in enumerate(E2_FACTS, 1):
        key = 'di-e2-%02d' % n
        items[key] = item('visual_fact', facet, value)
        zones[zone].append(key)
    globals_ = {'medium': None, 'aspect_ratio': None, 'image_text': []}
    if medium is not None:
        items['di-medium'] = item('medium', '媒介', medium)
        globals_['medium'] = 'di-medium'
    if ratio is not None:
        items['di-ratio'] = item('aspect_ratio', '画幅', ratio)
        globals_['aspect_ratio'] = 'di-ratio'
    return {'schema_version': version, 'master_id': 'e2-cleanup', 'revision': 1, 'parent_revision': None,
            'zones': zones, 'globals': globals_, 'items': items,
            'changes': [{'item_id': key, 'operation': 'add', 'reason': '原文明示', 'source_ref': SOURCE} for key in items]}


def approved_limited(master, target='generic'):
    state = flow.new_task('e2', 'E2 古风师姐原文整理', mode='limited', user_ref='msg:e2-request')
    flow.save_master(state, master)
    flow.coordinate(state, 'pass', [], 'Synthetic attestation, not a visual evaluation', ['character_art'])
    flow.show(state)
    flow.approve(state, 1, 'msg:e2-user-confirmed-v1')
    flow.prepare_manifest(state, target)
    return state


def artifact(state, target):
    master = state['masters'][-1]
    ratio_id = master['globals']['aspect_ratio']
    segments = [{'text': value['value'], 'item_ids': [key]} for key, value in master['items'].items()
                if value['kind'] in COMPILED_KINDS and value['kind'] != 'aspect_ratio']
    return {'master_hash': digest(master), 'target': target, 'language': 'zh-CN', 'segments': segments,
            'parameters': {'aspect_ratio': None if ratio_id is None else copy.deepcopy(master['items'][ratio_id]['value'])}}


def deliver(state, target):
    built = artifact(state, target)
    report = flow.submit(state, built, review(state, built))
    return report, (flow.deliver(state) if report['result'] == 'pass' else None)


class UnspecifiedGlobals(unittest.TestCase):
    def test_e2_without_medium_or_ratio_delivers_without_additions(self):
        for target, forbidden in (('generic', ('建议画幅',)), ('gpt-web', ('Aspect ratio',)), ('midjourney', ('--ar',)),
                                  ('qwen-image-2.1', ('建议画幅',))):
            state = approved_limited(e2_master(), target)
            shown = flow.show(state)['text']
            self.assertIn('媒介：未指定', shown)
            self.assertIn('画幅：未指定', shown)
            self.assertEqual(state['events'][-1]['type'], 'adapter_selected')
            report, output = deliver(state, target)
            self.assertEqual(report['result'], 'pass', (target, report['problems']))
            self.assertIsNone(output['external_settings'])
            self.assertIsNone(output['aspect_ratio'])
            for word in forbidden + ('写实', '摄影', '均匀照明'):
                self.assertNotIn(word, output['formatted'], target)
            for _, _, value in E2_FACTS:
                self.assertIn(value, output['prompt'])

    def test_candidate_cannot_add_ratio_when_master_leaves_it_unspecified(self):
        state = approved_limited(e2_master(), 'gpt-web')
        built = artifact(state, 'gpt-web')
        built['parameters']['aspect_ratio'] = {'width': 2, 'height': 3}
        report = flow.submit(state, built, review(state, built))
        self.assertEqual(report['result'], 'fail')
        self.assertIn('母版未指定画幅，成品不得自行添加', report['problems'])

    def test_explicit_medium_and_ratio_are_kept(self):
        for version in ('0.3.0', '0.3.1'):
            state = approved_limited(e2_master('写实摄影', {'width': 2, 'height': 3}, version), 'gpt-web')
            report, output = deliver(state, 'gpt-web')
            self.assertEqual(report['result'], 'pass', report['problems'])
            self.assertIn('写实摄影', output['prompt'])
            self.assertTrue(output['prompt'].rstrip().endswith('Aspect ratio: 2:3.'))

    def test_layout_needs_a_real_ratio_and_canvas(self):
        state = flow.new_task('e2', 'E2', mode='limited', user_ref='msg:e2-request')
        flow.save_master(state, e2_master())
        flow.coordinate(state, 'pass', [], 'Synthetic attestation', ['character_art'])
        flow.show(state)
        flow.approve(state, 1, 'msg:e2-user-confirmed-v1')
        before = copy.deepcopy(state)
        with self.assertRaises(ContractError) as caught:
            flow.prepare_manifest(state, 'moss-image-layout')
        self.assertIn('画幅与画布尺寸', str(caught.exception))
        self.assertEqual(state, before)

    def test_other_modes_keep_required_medium_and_ratio(self):
        for mode, ref in (('direct', 'msg:req'), ('explore', None)):
            state = flow.new_task('x', 'Synthetic', mode=mode, user_ref=ref)
            if mode == 'explore':
                flow.set_concepts(state, [dict(id=x, core=x, focus=x, feature=x, scene='S' + x) for x in 'AB'])
                flow.select(state, 'A', 'msg:select')
            before = copy.deepcopy(state)
            with self.assertRaises(ContractError):
                flow.save_master(state, e2_master())
            self.assertEqual(state, before)
        with self.assertRaises(ContractError):
            validate_master(e2_master())
        # Schema 0.3.0 never accepts null globals, even for a limited task.
        with self.assertRaises(ContractError):
            validate_master(e2_master(version='0.3.0'), allow_unspecified=True)
        validate_master(e2_master(), allow_unspecified=True)
        validate_master(fixture())

    def test_snapshot_without_mode_is_not_limited(self):
        state = flow.new_task('legacy', 'Synthetic')
        del state['mode']
        flow.set_concepts(state, [dict(id=x, core=x, focus=x, feature=x, scene='S' + x) for x in 'ABC'])
        flow.select(state, 'A', 'msg:select')
        with self.assertRaises(ContractError):
            flow.save_master(state, e2_master())
        flow.save_master(state, fixture())

    def test_unapproved_limited_master_cannot_compile_or_deliver(self):
        state = flow.new_task('e2', 'E2', mode='limited', user_ref='msg:e2-request')
        flow.save_master(state, e2_master())
        flow.coordinate(state, 'pass', [], 'Synthetic attestation', ['character_art'])
        flow.show(state)
        before = copy.deepcopy(state)
        with self.assertRaises(ContractError):
            flow.prepare_manifest(state)
        self.assertEqual(flow.submit(state, {}, {})['saved'], False)
        with self.assertRaises(ContractError):
            flow.deliver(state)
        with self.assertRaises(ContractError):
            flow.approve(state, 1, 'msg:e2-request')
        self.assertEqual(state, before)

    def test_requested_restyle_is_not_a_limited_task(self):
        restyled = e2_master()
        restyled['items']['di-medium'] = item('medium', '媒介', '水彩插画', source='model_added')
        restyled['globals']['medium'] = 'di-medium'
        restyled.update(revision=2, parent_revision=1,
                        changes=[{'item_id': 'di-medium', 'operation': 'add', 'reason': '用户要求改成水彩', 'source_ref': 'msg:restyle'}],
                        structure_changes=[{'path': 'globals.medium', 'reason': '用户要求改成水彩', 'source_ref': 'msg:restyle'}])
        state = flow.new_task('e2', 'E2', mode='limited', user_ref='msg:e2-request')
        flow.save_master(state, e2_master())
        flow.begin_change(state, 'msg:restyle')
        before = copy.deepcopy(state)
        with self.assertRaises(ContractError) as caught:
            flow.save_master(state, restyled)
        self.assertIn('direct', str(caught.exception))
        self.assertEqual(state, before)
        # The same redesign is accepted in a direct task built from the restyle request.
        direct = flow.new_task('e2d', 'E2 改成水彩', mode='direct', user_ref='msg:restyle')
        first = copy.deepcopy(restyled)
        first.update(revision=1, parent_revision=None,
                     changes=[{'item_id': key, 'operation': 'add', 'reason': 'r', 'source_ref': SOURCE} for key in restyled['items']])
        first.pop('structure_changes')
        first['globals']['aspect_ratio'] = 'di-ratio'
        first['items']['di-ratio'] = item('aspect_ratio', '画幅', {'width': 3, 'height': 4}, source='model_added')
        first['changes'].append({'item_id': 'di-ratio', 'operation': 'add', 'reason': 'r', 'source_ref': SOURCE})
        flow.save_master(direct, first)

    def test_cli_validate_limited_flag(self):
        with tempdir('pa-limited-validate-') as temp:
            path = Path(temp) / 'e2.json'
            path.write_text(json.dumps(e2_master(), ensure_ascii=False), encoding='utf-8')
            base = [sys.executable, '-B', '-X', 'utf8', str(ROOT / 'scripts/pa15.py'), 'validate', '--input', str(path)]
            self.assertEqual(subprocess.run(base, capture_output=True, encoding='utf-8').returncode, 1)
            self.assertEqual(subprocess.run(base + ['--limited'], capture_output=True, encoding='utf-8').returncode, 0)


if __name__ == '__main__':
    unittest.main()
