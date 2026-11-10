"""Historical KB retrieval and synthetic pipeline checks; no LLM or image tests."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
import flow
import knowledge
from contracts import validate_master
from test_regressions import approved, candidate, fixture, review


class HistoricalHairIntegration(unittest.TestCase):
    def test_all_historical_entries_retrieve_with_sources_and_three_digit_ids(self):
        ids = [f'CH-{number:02}' for number in range(59, 113)]
        knowledge.validate_refs(['KB:' + value for value in ids])
        for start in range(0, len(ids), 5):
            batch = ids[start:start + 5]
            result = knowledge.show(batch)
            self.assertEqual([row['entry']['id'] for row in result['entries']], batch)
            source_ids = {row['id'] for row in result['sources']}
            for row in result['entries']:
                self.assertTrue(set(row['entry']['sources']) <= source_ids)
                self.assertEqual(row['entry']['model_execution'], 'untested')
        with self.assertRaises(ValueError):
            knowledge.validate_refs(['KB:CH-999'])

    def test_search_finds_period_and_shape_candidates(self):
        cases = [('高髻', 'CH-65'), ('秦俑发髻', 'CH-94'),
                 ('乌纱帽', 'CH-100'), ('民国 分头', 'CH-107')]
        for query, expected in cases:
            with self.subTest(query=query):
                result = knowledge.search(query, domain='character-art', limit=5)
                self.assertIn(expected, [row['id'] for row in result['results']])

    def test_excerpt_sources_cannot_claim_full_text_verification(self):
        catalog = knowledge.source_catalog()
        excerpt_rows = [row for row in catalog if row['access_status'] == 'indexed_excerpt_only']
        self.assertTrue(excerpt_rows)
        warnings = {row['id'] for row in knowledge.audit()['source_warnings']}
        self.assertTrue({row['id'] for row in excerpt_rows} <= warnings)
        mutated = copy.deepcopy(catalog)
        row = next(row for row in mutated if row['access_status'] == 'indexed_excerpt_only')
        row['latest_verification']['status'] = 'opened_primary_content'
        original_read = knowledge.read

        def altered_read(path):
            data = original_read(path)
            if path == knowledge.KB / 'sources.json':
                data['sources'] = mutated
            return data

        with patch.object(knowledge, 'read', side_effect=altered_read):
            with self.assertRaises(ValueError):
                knowledge.source_catalog()

    def test_hair_and_headwear_survive_existing_master_and_compile_contract(self):
        master = fixture()
        master['master_id'] = 'synthetic-historical-hair'
        hair = copy.deepcopy(master['items']['di-styling'])
        hair.update(facet='发型与首服', value='头发收束在乌纱帽内，帽翅向两侧展开。',
                    source_refs=['synthetic:historical-design', 'KB:CH-100'])
        master['items']['di-history-hair'] = hair
        master['zones']['character_art'].append('di-history-hair')
        master['changes'].append(dict(item_id='di-history-hair', operation='add',
                                      reason='Synthetic fixture', source_ref='synthetic:historical-design'))
        validate_master(master)
        self.assertEqual(len(master['zones']), 9)
        state = approved(master=master)
        self.assertIn(hair['value'], flow.show(state)['text'])
        self.assertIn('di-history-hair', flow.prepare_manifest(state)['manifest']['facts'])
        incomplete = candidate(state)
        incomplete['segments'] = [row for row in incomplete['segments']
                                  if 'di-history-hair' not in row['item_ids']]
        self.assertEqual(flow.submit(state, incomplete, review(state, incomplete))['result'], 'fail')
        state = approved(master=master)
        complete = candidate(state)
        self.assertEqual(flow.submit(state, complete, review(state, complete))['result'], 'pass')
        self.assertIn(hair['value'], flow.deliver(state)['prompt'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
