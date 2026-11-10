"""Appearance KB and existing master pipeline integration, not visual evaluation.

All user messages and semantic attestations below are synthetic test fixtures.
These tests cannot decide whether a style suits a character or looks natural.
"""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
import flow
import knowledge
from contracts import ContractError, validate_master
from test_regressions import approved, candidate, fixture, review


def appearance_master():
    master = fixture()
    master['master_id'] = 'synthetic-appearance'
    master['items']['di-styling']['value'] = '黑色长发，外套衣领整齐。'
    additions = [
        ('di-face', '脸型', '略长的椭圆脸，下颌柔和收束。', 'CH-13'),
        ('di-features', '五官', '眉形平缓，鼻尖圆润。', 'CH-14'),
        ('di-makeup', '妆容', '棕色烟熏眼妆，边缘柔和晕染。', 'CH-30'),
        ('di-hair', '发型', '黑色长发扎成低马尾。', 'CH-47'),
        ('di-skin', '肤质与妆面', '哑光底妆保留自然皮肤纹理。', 'CH-15'),
        ('di-state', '当下状态', '低马尾束紧，额前有少量散落碎发。', 'CH-17'),
    ]
    for item_id, facet, value, kb in additions:
        item = copy.deepcopy(master['items']['di-styling'])
        item.update(facet=facet, value=value, source_refs=['synthetic:appearance-design', 'KB:' + kb])
        if item_id == 'di-face':
            item.update(design_source='user_specified', confirmation_status='confirmed',
                        constraint_strength='hard_constraint', source_refs=['synthetic:user-face', 'KB:' + kb])
        master['items'][item_id] = item
        master['zones']['character_art'].append(item_id)
        master['changes'].append(dict(item_id=item_id, operation='add', reason='Synthetic appearance fixture',
                                      source_ref='synthetic:appearance-design'))
    return master


class AppearanceIntegration(unittest.TestCase):
    def test_all_new_entries_can_be_retrieved_and_refs_validated(self):
        ids = [f'CH-{number:02}' for number in range(13, 59)]
        knowledge.validate_refs(['KB:' + entry_id for entry_id in ids])
        for start in range(0, len(ids), 5):
            batch = ids[start:start + 5]
            result = knowledge.show(batch)
            self.assertEqual([row['entry']['id'] for row in result['entries']], batch)
            available_sources = {row['id'] for row in result['sources']}
            for row in result['entries']:
                self.assertEqual(row['entry']['model_execution'], 'untested')
                self.assertTrue(set(row['entry']['sources']) <= available_sources)
        with self.assertRaises(ValueError):
            knowledge.validate_refs(['KB:CH-999'])

    def test_names_find_the_appropriate_specialty_entries(self):
        for query, wanted in [('烟熏妆', 'CH-30'), ('低马尾', 'CH-47'),
                              ('长脸', 'CH-13'), ('cut crease', 'CH-37')]:
            with self.subTest(query=query):
                result = knowledge.search(query, domain='character-art', limit=5)
                self.assertIn(wanted, [row['id'] for row in result['results']])

    def test_appearance_fields_render_and_require_compilation_coverage(self):
        master = appearance_master()
        validate_master(master)
        self.assertEqual(master['schema_version'], '0.3.0')
        self.assertEqual(len(master['zones']), 9)
        state = approved(master=master)
        rendered = flow.show(state)['text']
        for item_id in ('di-face', 'di-features', 'di-makeup', 'di-hair', 'di-skin', 'di-state'):
            self.assertIn(master['items'][item_id]['value'], rendered)
        packet = flow.prepare_manifest(state)
        self.assertIn('di-makeup', packet['manifest']['facts'])
        incomplete = candidate(state)
        incomplete['segments'] = [row for row in incomplete['segments'] if 'di-makeup' not in row['item_ids']]
        self.assertEqual(flow.submit(state, incomplete, review(state, incomplete))['result'], 'fail')
        state = approved(master=master)
        complete = candidate(state)
        self.assertEqual(flow.submit(state, complete, review(state, complete))['result'], 'pass')
        delivered = flow.deliver(state)['prompt']
        self.assertIn(master['items']['di-makeup']['value'], delivered)
        self.assertIn(master['items']['di-hair']['value'], delivered)

    def test_dropped_makeup_name_fails_even_when_item_id_is_declared(self):
        state = approved(master=appearance_master())
        artifact = candidate(state)
        for segment in artifact['segments']:
            if 'di-makeup' in segment['item_ids']:
                segment['text'] = '面部干净，肤色自然。'
        attestation = review(state, artifact)
        attestation['item_results']['di-makeup']['note'] = '合成声明；正文引文「面部干净」'
        report = flow.submit(state, artifact, attestation)
        self.assertEqual(report['result'], 'fail')
        self.assertIn('名称', ';'.join(report['problems']))

    def test_review_without_body_quote_is_rejected(self):
        state = approved(master=appearance_master())
        artifact = candidate(state)
        attestation = review(state, artifact)
        for key in attestation['item_results']:
            attestation['item_results'][key]['note'] = '合成声明'
        report = flow.submit(state, artifact, attestation)
        self.assertEqual(report['result'], 'fail')
        self.assertIn('引文', ';'.join(report['problems']))

    def test_appearance_revision_invalidates_approval_and_locked_face_is_protected(self):
        state = approved(master=appearance_master())
        changed = copy.deepcopy(state['masters'][-1])
        changed.update(revision=2, parent_revision=1, changes=[
            dict(item_id='di-face', operation='update', reason='Synthetic requested change', source_ref='synthetic:user')])
        changed['items']['di-face']['value'] = '圆脸。'
        before = copy.deepcopy(state)
        with self.assertRaises(ContractError):
            flow.save_master(state, changed)
        self.assertEqual(state, before)
        flow.begin_change(state, 'synthetic:user-face-change')
        flow.save_master(state, changed, {'user_ref': 'synthetic:user-face-change', 'item_ids': ['di-face']})
        with self.assertRaises(ContractError):
            flow.prepare_manifest(state)
        flow.coordinate(state, 'pass', [], 'Synthetic declaration, not visual review', ['character_art'])
        flow.show(state)
        flow.approve(state, 2, 'synthetic:user-v2-confirmation')
        self.assertEqual(flow.prepare_manifest(state)['manifest']['master_hash'],
                         state['approvals'][-1]['master_hash'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
