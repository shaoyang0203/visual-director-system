"""Candidate regressions: task modes, on-demand directions, correction options and document routing.

Semantic reviews here are synthetic fixtures; they do not prove prompt quality or image results.
"""
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from testtmp import tempdir
import flow
from contracts import ContractError
from harness_store import Store
from test_regressions import candidate, fixture, review

CONCEPT = lambda x: dict(id=x, core=x, focus=x, feature=x, scene='Scene ' + x)


def limited_fixture():
    master = fixture()
    ratio_id = master['globals']['aspect_ratio']
    for key, item in master['items'].items():
        if key == ratio_id:
            item.update(design_source='model_added', confirmation_status='pending',
                        constraint_strength='adjustable_design')
        else:
            item.update(design_source='user_specified', confirmation_status='confirmed',
                        constraint_strength='hard_constraint')
    return master


def run_to_delivery(state, master=None):
    flow.save_master(state, fixture() if master is None else master)
    flow.coordinate(state, 'pass', [], 'Synthetic attestation, not a visual evaluation', ['camera_composition'])
    flow.show(state)
    return state


class TaskModes(unittest.TestCase):
    def test_direct_task_records_request_source_but_not_approval(self):
        state = flow.new_task('direct', 'Synthetic explicit request', mode='direct', user_ref='synthetic:user-request')
        self.assertEqual((state['mode'], state['selected'], state['phase']), ('direct', 'direct', 'designing'))
        self.assertEqual(state['events'][-1], {'type': 'direct_entry', 'mode': 'direct', 'user_ref': 'synthetic:user-request'})
        self.assertEqual(state['approvals'], [])
        run_to_delivery(state)
        # A text preview cannot enter manifest, submit or delivery before a real approval exists.
        before = copy.deepcopy(state)
        with self.assertRaises(ContractError):
            flow.prepare_manifest(state)
        report = flow.submit(state, {}, {})
        self.assertEqual((report['result'], report['saved'], report['attempt']), ('fail', False, 0))
        with self.assertRaises(ContractError):
            flow.deliver(state)
        self.assertEqual(state, before)
        with self.assertRaises(ContractError):
            flow.approve(state, 1, '')
        flow.approve(state, 1, 'synthetic:user-confirmed-v1')
        flow.prepare_manifest(state)
        artifact = candidate(state)
        self.assertEqual(flow.submit(state, artifact, review(state, artifact))['result'], 'pass')
        self.assertIn('formatted', flow.deliver(state))

    def test_limited_task_uses_same_gates(self):
        state = flow.new_task('limited', 'Synthetic prompt cleanup', mode='limited', user_ref='synthetic:user-prompt')
        self.assertEqual(state['selected'], 'limited')
        # Rejects model_added visual_fact items without mutating state.
        before = copy.deepcopy(state)
        with self.assertRaises(ContractError):
            flow.save_master(state, fixture())
        self.assertEqual(state, before)
        # Rejects model_added medium shortcut (sneaking default photography medium into polish tasks).
        bad_medium = limited_fixture()
        bad_medium['items'][bad_medium['globals']['medium']].update(
            design_source='model_added', confirmation_status='pending', constraint_strength='adjustable_design')
        with self.assertRaises(ContractError):
            flow.save_master(state, bad_medium)
        self.assertEqual(state, before)
        # Rejects unapproved suggested ratio marked confirmed or jointly_formed.
        bad_ratio = limited_fixture()
        bad_ratio['items'][bad_ratio['globals']['aspect_ratio']]['confirmation_status'] = 'confirmed'
        with self.assertRaises(ContractError):
            flow.save_master(state, bad_ratio)
        self.assertEqual(state, before)
        # Accepts all user_specified facts + pending adjustable ratio suggestion, still gated by real approval.
        run_to_delivery(state, limited_fixture())
        with self.assertRaises(ContractError):
            flow.deliver(state)
        before_approve = copy.deepcopy(state)
        with self.assertRaises(ContractError):
            flow.approve(state, 1, 'synthetic:user-prompt')
        self.assertEqual(state, before_approve)
        flow.approve(state, 1, 'synthetic:user-confirmed-limited-v1')
        flow.prepare_manifest(state)
        artifact = candidate(state)
        self.assertEqual(flow.submit(state, artifact, review(state, artifact))['result'], 'pass')
        self.assertIn('formatted', flow.deliver(state))

    def test_approve_rejects_reused_direction_or_entry_ref(self):
        # 1. Direct task cannot reuse direct_entry user_ref for approval; state remains unchanged.
        direct = flow.new_task('d-ref', 'Synthetic', mode='direct', user_ref='synthetic:req-1')
        run_to_delivery(direct)
        snap_direct = copy.deepcopy(direct)
        for bad in ('synthetic:req-1', '  synthetic:req-1  '):
            with self.assertRaises(ContractError):
                flow.approve(direct, 1, bad)
            self.assertEqual(direct, snap_direct)
        flow.approve(direct, 1, 'synthetic:confirm-after-show-1')
        self.assertEqual(len(direct['approvals']), 1)
        # 2. Explore task cannot reuse direction_selected user_ref for approval.
        explore = flow.new_task('e-ref', 'Synthetic')
        flow.set_concepts(explore, [CONCEPT(x) for x in 'ABC'])
        flow.select(explore, 'A', 'synthetic:select-1')
        run_to_delivery(explore)
        snap_explore = copy.deepcopy(explore)
        with self.assertRaises(ContractError):
            flow.approve(explore, 1, 'synthetic:select-1')
        self.assertEqual(explore, snap_explore)
        flow.approve(explore, 1, 'synthetic:confirm-after-show-2')
        self.assertEqual(len(explore['approvals']), 1)

    def test_direct_and_limited_require_request_source(self):
        for mode in ('direct', 'limited'):
            for ref in (None, '', '   '):
                with self.assertRaises(ContractError):
                    flow.new_task('x', 'Synthetic', mode=mode, user_ref=ref)
        with self.assertRaises(ContractError):
            flow.new_task('x', 'Synthetic', mode='auto')
        with self.assertRaises(ContractError):
            flow.new_task('x', 'Synthetic', mode='explore', user_ref='synthetic:not-a-selection')

    def test_direct_task_rejects_direction_steps(self):
        state = flow.new_task('direct', 'Synthetic', mode='direct', user_ref='synthetic:user-request')
        before = copy.deepcopy(state)
        with self.assertRaises(ContractError):
            flow.set_concepts(state, [CONCEPT(x) for x in 'AB'])
        with self.assertRaises(ContractError):
            flow.select(state, 'direct', 'synthetic:user')
        self.assertEqual(state, before)

    def test_explore_accepts_two_to_five_directions(self):
        for count in (2, 3, 4, 5):
            state = flow.new_task('explore', 'Synthetic')
            flow.set_concepts(state, [CONCEPT(x) for x in 'ABCDE'[:count]])
            self.assertEqual(len(state['concepts']), count)
        for count in (0, 1, 6):
            state = flow.new_task('explore', 'Synthetic')
            with self.assertRaises(ContractError):
                flow.set_concepts(state, [CONCEPT(x) for x in 'ABCDEF'[:count]])
            self.assertEqual(state['concepts'], [])

    def test_snapshot_without_mode_behaves_as_explore(self):
        state = flow.new_task('legacy', 'Synthetic')
        del state['mode']
        flow.set_concepts(state, [CONCEPT(x) for x in 'ABC'])
        flow.select(state, 'B', 'synthetic:user')
        self.assertEqual(state['selected'], 'B')
        run_to_delivery(state)
        before = copy.deepcopy(state)
        with self.assertRaises(ContractError):
            flow.approve(state, 1, 'synthetic:user')
        self.assertEqual(state, before)
        flow.approve(state, 1, 'synthetic:legacy-user-confirmed-v1')
        self.assertEqual(state['phase'], 'approved')

    def test_cli_direct_mode(self):
        with tempdir('pa-direct-cli-') as temp:
            base = [sys.executable, '-B', '-X', 'utf8', str(ROOT / 'scripts/pa15.py'), '--data-dir', temp]
            missing = subprocess.run(base + ['--task', 'd1', 'new', '--request', 'Synthetic', '--mode', 'direct'],
                                     capture_output=True, encoding='utf-8')
            self.assertEqual(missing.returncode, 1)
            self.assertFalse(Store(temp).exists('d1'))
            done = subprocess.run(base + ['--task', 'd2', 'new', '--request', 'Synthetic', '--mode', 'direct',
                                          '--user-ref', 'synthetic:user-request'], capture_output=True, encoding='utf-8')
            self.assertEqual(done.returncode, 0, done.stderr)
            state = Store(temp).load('d2')
            self.assertEqual((state['mode'], state['selected'], state['approvals']), ('direct', 'direct', []))


class Corrections(unittest.TestCase):
    def option(self, mode):
        return dict(mode=mode, design='Synthetic', changes='Synthetic', reason='Synthetic', expected='Synthetic')

    def test_strict_plus_one_or_two_alternatives(self):
        for modes in (['strict', 'local'], ['strict', 'reconstruct'], ['strict', 'local', 'reconstruct']):
            state = flow.new_task('c', 'Synthetic')
            result = flow.correction(state, {'issue': 'Synthetic conflict', 'intent': 'conflict',
                                             'options': [self.option(m) for m in modes]})
            self.assertFalse(result['applied'])
        for modes in (['strict'], ['local', 'strict'], ['strict', 'reconstruct', 'local'], ['strict', 'local', 'local'],
                      ['local', 'reconstruct']):
            state = flow.new_task('c', 'Synthetic')
            with self.assertRaises(ContractError):
                flow.correction(state, {'issue': 'Synthetic conflict', 'intent': 'conflict',
                                        'options': [self.option(m) for m in modes]})
            self.assertEqual(state['corrections'], [])


class DocumentRouting(unittest.TestCase):
    """Package structure only: it does not prove that a host LLM reads or follows these files."""

    def links(self, path):
        text = path.read_text(encoding='utf-8')
        return [t.split('#')[0] for t in re.findall(r'\]\(([^)\s]+)\)', text) if not re.match(r'^[a-z]+:', t)]

    def test_entry_reading_table_targets_exist(self):
        targets = self.links(ROOT / 'SKILL.md')
        self.assertIn('references/core.md', targets)
        for target in targets:
            self.assertTrue((ROOT / target).is_file(), target)

    def test_every_registered_route_has_a_card_listed_in_delivery_contract(self):
        registry = json.loads((ROOT / 'adapters/registry.json').read_text(encoding='utf-8'))
        listed = {('references/' + t) for t in self.links(ROOT / 'references/deliver.md')}
        for row in registry['adapters']:
            ref = row['compiler_policy']['reference']
            self.assertTrue((ROOT / ref).is_file(), ref)
            self.assertIn(ref, listed, row['target'])

    def test_core_keeps_project_specific_rules(self):
        core = (ROOT / 'references/core.md').read_text(encoding='utf-8')
        for phrase in ('年轻成年中国女性', '无妆和裸妆是两件事', '没有统一默认', '未经工具批准的预览', '泛称顶替不了已定名称'):
            self.assertIn(phrase, core)

    def test_relative_links_resolve(self):
        broken = []
        for path in ROOT.rglob('*.md'):
            for target in self.links(path):
                if target and not (path.parent / target).resolve().exists():
                    broken.append(path.relative_to(ROOT).as_posix() + ' -> ' + target)
        self.assertEqual(broken, [])


if __name__ == '__main__':
    unittest.main()
