"""Clothing retrieval and synthetic compilation coverage; no visual evaluation."""
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
from contracts import validate_master
from test_regressions import approved, candidate, fixture, review


def clothing_master():
    master = fixture()
    master['master_id'] = 'synthetic-clothing'
    # Use an explicitly chosen common ratio for the synthetic cross-route case.
    # The unmodified 4:5 fixture is correctly rejected by the Grok route.
    ratio_id = master['globals']['aspect_ratio']
    master['items'][ratio_id]['value'] = {'width': 2, 'height': 3}
    for change in master['changes']:
        if change['item_id'] == ratio_id:
            change['reason'] = 'Synthetic 2:3 case for layered clothing coverage'
    master['items']['di-styling']['value'] = '头发收束于后脑，耳侧留少量碎发。'
    for ident, facet, value, reference in (
        ('di-outer', '外衣', '深蓝宽袖氅衣，两侧开裾，衣缘窄镶边。', 'CH-151'),
        ('di-inner', '内衣层次', '氅衣开口内露出连续的浅色长衣下摆。', 'CH-150'),
    ):
        item = copy.deepcopy(master['items']['di-styling'])
        item.update(facet=facet, value=value,
                    source_refs=['synthetic:clothing-design', 'KB:' + reference])
        master['items'][ident] = item
        master['zones']['character_art'].append(ident)
        master['changes'].append(dict(item_id=ident, operation='add',
                                     reason='Synthetic fixture', source_ref='synthetic:clothing-design'))
    return master


class ClothingIntegration(unittest.TestCase):
    def test_clothing_entries_retrieve_with_sources_without_changing_existing_ids(self):
        ids = [f'CH-{number}' for number in range(113, 185)]
        knowledge.validate_refs(['KB:' + value for value in ids])
        for start in range(0, len(ids), 5):
            batch = ids[start:start + 5]
            result = knowledge.show(batch)
            self.assertEqual([row['entry']['id'] for row in result['entries']], batch)
            sources = {row['id'] for row in result['sources']}
            for row in result['entries']:
                self.assertTrue(set(row['entry']['sources']) <= sources)
                self.assertEqual(row['entry']['model_execution'], 'untested')
        self.assertEqual(knowledge.show(['CH-65'])['entries'][0]['entry']['id'], 'CH-65')
        with self.assertRaises(ValueError):
            knowledge.validate_refs(['KB:CH-185'])

    def test_named_clothes_are_discoverable_across_periods(self):
        for query, wanted in [('曲裾', 'CH-117'), ('褙子', 'CH-130'),
                              ('辫线袍', 'CH-134'), ('飞鱼服', 'CH-141'),
                              ('氅衣', 'CH-151'), ('旗袍', 'CH-158'),
                              ('列宁装', 'CH-160'), ('卫衣', 'CH-166'),
                              ('风衣', 'CH-174'), ('新中式', 'CH-183')]:
            with self.subTest(query=query):
                result = knowledge.search(query, domain='character-art', limit=5)
                self.assertIn(wanted, [row['id'] for row in result['results']])

    def test_layered_clothing_requires_complete_coverage_in_existing_routes(self):
        master = clothing_master()
        validate_master(master)
        self.assertEqual(len(master['zones']), 9)
        for target in ('generic', 'grok-web', 'qwen-image-2.1'):
            with self.subTest(target=target):
                state = approved(master=master, target=target)
                rendered = flow.show(state)['text']
                self.assertIn(master['items']['di-outer']['value'], rendered)
                self.assertIn(master['items']['di-inner']['value'], rendered)
                incomplete = candidate(state)
                incomplete['segments'] = [row for row in incomplete['segments']
                                          if 'di-inner' not in row['item_ids']]
                self.assertEqual(flow.submit(state, incomplete, review(state, incomplete))['result'], 'fail')
                state = approved(master=master, target=target)
                complete = candidate(state)
                self.assertEqual(flow.submit(state, complete, review(state, complete))['result'], 'pass')
                delivered = flow.deliver(state)['prompt']
                for ident in ('di-outer', 'di-inner'):
                    self.assertIn(master['items'][ident]['value'], delivered)


if __name__ == '__main__':
    unittest.main(verbosity=2)
