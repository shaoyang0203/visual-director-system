"""Merged coverage remains valid; synthetic attestations do not test LLM concision."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
import flow
from test_appearance import appearance_master
from test_regressions import approved, candidate, review


def merged_case():
    master = appearance_master()
    # Same chosen makeup is referenced by a second design item in another zone.
    master['items']['di-makeup-repeat'] = copy.deepcopy(master['items']['di-makeup'])
    master['zones']['lighting_color'].append('di-makeup-repeat')
    master['changes'].append(dict(item_id='di-makeup-repeat', operation='add',
                                 reason='Synthetic duplicate fact', source_ref='synthetic:test'))
    state = approved(master=master)
    artifact = candidate(state)
    texts, ids = [], []
    for segment in artifact['segments']:
        ids.extend(segment['item_ids'])
        if segment['text'] not in texts:
            texts.append(segment['text'])
    artifact['segments'] = [dict(text=' '.join(texts), item_ids=ids)]
    return state, artifact


class CompactCoverage(unittest.TestCase):
    def test_shared_sentence_covers_two_items_without_repeating_name(self):
        state, artifact = merged_case()
        self.assertEqual(artifact['segments'][0]['text'].count('棕色烟熏眼妆'), 1)
        attestation = review(state, artifact)
        for key in ('di-makeup', 'di-makeup-repeat'):
            attestation['item_results'][key]['note'] = 'Synthetic shared evidence:「棕色烟熏眼妆，边缘柔和晕染。」'
        self.assertEqual(flow.submit(state, artifact, attestation)['result'], 'pass')
        self.assertEqual(flow.deliver(state)['prompt'].count('棕色烟熏眼妆'), 1)

    def test_all_ids_cannot_cover_a_deleted_name(self):
        state, artifact = merged_case()
        artifact['segments'][0]['text'] = artifact['segments'][0]['text'].replace('棕色烟熏眼妆', '自然妆容')
        result = flow.submit(state, artifact, review(state, artifact))
        self.assertEqual(result['result'], 'fail')
        self.assertTrue(any('di-makeup' in problem for problem in result['problems']))
        with self.assertRaises(ValueError):
            flow.deliver(state)

    def test_merged_text_still_requires_all_coverage_ids(self):
        state, artifact = merged_case()
        artifact['segments'][0]['item_ids'].remove('di-makeup-repeat')
        result = flow.submit(state, artifact, review(state, artifact))
        self.assertEqual(result['result'], 'fail')
        self.assertTrue(any('遗漏设计事实' in problem for problem in result['problems']))


if __name__ == '__main__':
    unittest.main()
