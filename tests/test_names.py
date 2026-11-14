"""Name-map regressions for V1.6.3: mapping coverage, language, layout, not_checked."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
import flow
import terms
from compile_checks import name_checks, name_problems, review_hash
from test_appearance import appearance_master
from test_regressions import approved, candidate, review
from testtmp import tempdir


def groups_for(value):
    return [group['entry'] for group in terms.find_groups(value)]


def status_for(value, body, language):
    group = terms.find_groups(value)[0]
    return terms.group_status(terms.normalize(body), group, language)


class NameMapCases(unittest.TestCase):
    def test_01_chinese_name_and_alias(self):
        self.assertIn('CH-30', groups_for('烟熏妆'))
        self.assertEqual(status_for('烟熏妆', '妆容为烟熏妆', 'zh'), ('matched', ['烟熏妆']))
        self.assertEqual(status_for('烟熏妆', '妆容为烟熏眼妆', 'zh')[0], 'matched')

    def test_02_english_variants(self):
        for body in ('Smokey Eye', 'smoky eye', 'smoky eyes', 'smoky eye makeup'):
            with self.subTest(body=body):
                self.assertEqual(status_for('烟熏妆', body, 'en')[0], 'matched')
        self.assertEqual(status_for('裸妆', 'no-makeup makeup', 'en')[0], 'matched')

    def test_03_english_omission_of_ponytail_is_missing(self):
        self.assertEqual(status_for('低马尾', 'She has short black hair.', 'en')[0], 'missing')

    def test_04_english_master_name_is_detected(self):
        self.assertEqual(groups_for('Smokey Eye'), ['CH-30'])
        self.assertEqual(status_for('Smokey Eye', 'smoky eyes', 'en')[0], 'matched')

    def test_05_bare_makeup_is_not_no_makeup(self):
        self.assertEqual(status_for('裸妆', '无妆，肤色干净', 'zh')[0], 'missing')

    def test_06_keywords_are_not_names(self):
        for value in ('清纯女大学生', '角色背景是校园日常', '提示词表达粒度'):
            with self.subTest(value=value):
                self.assertEqual(groups_for(value), [])

    def test_07_two_names_both_required(self):
        value = '烟熏妆，黑色长发扎成低马尾'
        self.assertEqual(sorted(groups_for(value)), ['CH-30', 'CH-47'])
        body = '妆容为烟熏妆，头发自然披散'
        first = terms.find_groups('烟熏妆')[0]
        second = terms.find_groups('低马尾')[0]
        self.assertEqual(terms.group_status(terms.normalize(body), first, 'zh')[0], 'matched')
        self.assertEqual(terms.group_status(terms.normalize(body), second, 'zh')[0], 'missing')

    def test_08_subtype_is_not_replaced_by_broader_word(self):
        self.assertEqual(groups_for('低马尾'), ['CH-47'])
        self.assertEqual(status_for('低马尾', '马尾', 'zh')[0], 'missing')

    def test_09_mapping_covers_names_not_foundations(self):
        rows = terms.groups()
        self.assertGreaterEqual(len(rows), 200)
        entries = {row['entry'] for row in rows}
        for foundation in ('CH-01', 'CH-05', 'CH-13', 'CH-59', 'CH-113'):
            self.assertNotIn(foundation, entries)


def chinese_candidate(state, language='zh-CN'):
    artifact = candidate(state)
    artifact['language'] = language
    return artifact


def rewrite(artifact, texts):
    for segment in artifact['segments']:
        for key in segment['item_ids']:
            if key in texts:
                segment['text'] = texts[key]


class NameFlowCases(unittest.TestCase):
    def test_10_duplicate_workflow_names_pass_both_languages(self):
        for language, texts in (
            ('zh-CN', {'di-makeup': '妆容为烟熏眼妆，边缘柔和。', 'di-hair': '低马尾保持束紧。', 'di-state': '额前碎发自然。'}),
            ('en', {'di-makeup': 'a smoky eye with softened edges', 'di-hair': 'hair in a low ponytail', 'di-state': 'natural loose strands'}),
        ):
            with self.subTest(language=language):
                master = appearance_master()
                master['items']['di-state']['value'] = '额前碎发自然。'
                state = approved(master=master)
                artifact = chinese_candidate(state, language)
                rewrite(artifact, texts)
                self.assertEqual(flow.submit(state, artifact, review(state, artifact))['result'], 'pass')

    def test_11_missing_name_blocks_submit_and_deliver(self):
        state = approved(master=appearance_master())
        artifact = chinese_candidate(state)
        rewrite(artifact, {'di-hair': '黑色长发自然披散。'})
        report = flow.submit(state, artifact, review(state, artifact))
        self.assertEqual(report['result'], 'fail')
        self.assertIn('低马尾', ';'.join(report['problems']))
        with self.assertRaises(ValueError):
            flow.deliver(state)

    def test_12_not_checked_requires_semantic_marker(self):
        master = appearance_master()
        master['items']['di-styling']['facet'] = '服装'
        master['items']['di-makeup']['value'] = '裸妆，底妆自然。'
        master['items']['di-hair']['value'] = '低马尾束紧。'
        master['items']['di-styling']['value'] = '灰色长外套。'
        master['items']['di-state']['value'] = '额前碎发自然。'
        state = approved(master=master)
        artifact = chinese_candidate(state, 'en')
        rewrite(artifact, {'di-makeup': 'No-makeup Makeup', 'di-hair': 'low ponytail',
                           'di-styling': 'a gray coat', 'di-state': 'natural strands'})
        attest = review(state, artifact)
        attest['item_results']['di-styling']['note'] = '正文引文「gray coat」'
        report = flow.submit(state, artifact, attest)
        self.assertEqual(report['result'], 'fail')
        self.assertIn('not_checked', ';'.join(report['problems']))
        checks = {row['item_id']: row['status'] for row in report['name_checks']}
        self.assertEqual(checks['di-styling'], 'not_checked')
        attest['item_results']['di-styling']['note'] = '母版「灰色长外套」，正文「gray coat」为译名；正文引文「gray coat」'
        report = flow.submit(state, artifact, attest)
        self.assertEqual(report['result'], 'pass')
        delivered = flow.deliver(state)
        self.assertEqual({row['item_id']: row['status'] for row in delivered['name_checks']}['di-styling'], 'not_checked')

    def test_13_wrong_subject_and_negation_are_only_word_matches(self):
        state = approved(master=appearance_master())
        artifact = chinese_candidate(state)
        rewrite(artifact, {'di-makeup': '她旁边的女性化了烟熏妆，主角仍是裸妆。'})
        report = flow.submit(state, artifact, review(state, artifact))
        self.assertEqual(report['result'], 'pass')
        self.assertEqual([row['status'] for row in report['name_checks'] if row['item_id'] == 'di-makeup'], ['matched'])
        self.assertEqual(status_for('烟熏妆', '本图不采用烟熏妆。', 'zh')[0], 'matched')

    def test_15_mixed_body_has_no_ratio_gate(self):
        self.assertEqual(status_for('烟熏妆', 'A portrait with 烟熏妆 and warm window light', 'en')[0], 'matched')
        self.assertEqual(status_for('低马尾', 'A portrait with a low ponytail', 'zh')[0], 'matched')

    def test_16_english_omission_blocks(self):
        master = appearance_master()
        master['items']['di-state']['value'] = '额前碎发自然。'
        state = approved(master=master)
        artifact = chinese_candidate(state, 'en')
        rewrite(artifact, {'di-makeup': 'a smoky eye', 'di-hair': 'She has short black hair.',
                           'di-state': 'natural strands'})
        report = flow.submit(state, artifact, review(state, artifact))
        self.assertEqual(report['result'], 'fail')
        self.assertIn('低马尾', ';'.join(report['problems']))

    def test_17_bare_is_not_no_makeup_flow(self):
        for body, expected in (('肤色干净，无妆。', 'fail'), ('裸妆，肤色干净。', 'pass')):
            with self.subTest(body=body):
                master = appearance_master()
                master['items']['di-makeup']['value'] = '裸妆，底妆自然。'
                master['items']['di-state']['value'] = '额前碎发自然。'
                state = approved(master=master)
                artifact = chinese_candidate(state)
                rewrite(artifact, {'di-makeup': body, 'di-state': '额前碎发自然。'})
                self.assertEqual(flow.submit(state, artifact, review(state, artifact))['result'], expected)

    def test_18_submit_and_deliver_name_checks_are_identical(self):
        state = approved(master=appearance_master())
        artifact = chinese_candidate(state)
        report = flow.submit(state, artifact, review(state, artifact))
        self.assertEqual(report['result'], 'pass')
        delivered = flow.deliver(state)
        self.assertEqual(report['name_checks'], delivered['name_checks'])
        self.assertEqual(report['name_language'], delivered['name_language'])

    def test_19_english_master_name_flows(self):
        master = appearance_master()
        master['items']['di-makeup']['value'] = 'Smokey Eye'
        master['items']['di-hair']['value'] = 'low ponytail'
        master['items']['di-state']['value'] = 'natural strands'
        state = approved(master=master)
        artifact = chinese_candidate(state, 'en')
        rewrite(artifact, {'di-makeup': 'smoky eyes', 'di-hair': 'low ponytail', 'di-state': 'natural strands'})
        self.assertEqual(flow.submit(state, artifact, review(state, artifact))['result'], 'pass')

    def test_20_language_is_bound_to_review(self):
        state = approved(master=appearance_master())
        zh = chinese_candidate(state, 'zh-CN')
        en = copy.deepcopy(zh)
        en['language'] = 'en'
        self.assertNotEqual(review_hash(zh), review_hash(en))
        attest = review(state, zh)
        failed = flow.submit(state, en, attest)
        self.assertEqual(failed['result'], 'fail')
        self.assertIn('语义复核与成品或母版不匹配', ';'.join(failed['problems']))
        no_lang = copy.deepcopy(zh)
        no_lang.pop('language')
        self.assertNotEqual(review_hash(zh), review_hash(no_lang))
        attest_no = review(state, no_lang)
        report = flow.submit(state, no_lang, attest_no)
        self.assertEqual(report['result'], 'pass')
        self.assertEqual(report['name_language'], 'zh')
        qwen = approved(master=appearance_master(), target='qwen-image-2.1')
        q_art = chinese_candidate(qwen)
        q_art.pop('language')
        q_report = flow.submit(qwen, q_art, review(qwen, q_art))
        self.assertEqual(q_report['result'], 'pass')
        self.assertEqual(q_report['name_language'], 'en')

    def test_21_language_values(self):
        for value in ('', '中文', 'en US', '123', 123):
            with self.subTest(value=value):
                state = approved(master=appearance_master())
                artifact = chinese_candidate(state)
                artifact['language'] = value
                report = flow.submit(state, artifact, review(state, artifact))
                self.assertEqual(report['result'], 'fail')
                self.assertTrue(any('language' in problem for problem in report['problems']))
        for value, base in (('fr', 'fr'), ('ja-JP', 'ja')):
            with self.subTest(value=value):
                state = approved(master=appearance_master())
                artifact = chinese_candidate(state)
                artifact['language'] = value
                report = flow.submit(state, artifact, review(state, artifact))
                self.assertEqual(report['result'], 'pass')
                self.assertEqual(report['name_language'], base)
                checks = {row['item_id']: row for row in report['name_checks']}
                self.assertEqual(checks['di-makeup']['status'], 'not_checked')
                self.assertTrue(checks['di-makeup']['requires_review'])

    def test_26_short_master_value(self):
        master = appearance_master()
        master['items']['di-styling']['facet'] = '服装'
        master['items']['di-styling']['value'] = '曲裾'
        state = approved(master=master)
        artifact = chinese_candidate(state, 'en')
        rewrite(artifact, {'di-styling': 'a short robe'})
        report = flow.submit(state, artifact, review(state, artifact))
        self.assertEqual(report['result'], 'pass')
        check = next(row for row in report['name_checks'] if row['item_id'] == 'di-styling')
        self.assertEqual(check['status'], 'not_checked')
        bad = review(state, artifact)
        bad['item_results']['di-styling']['note'] = '正文引文「a short robe」'
        report = flow.submit(state, artifact, bad)
        self.assertEqual(report['result'], 'fail')
        self.assertIn('母版原名称或原描述', ';'.join(report['problems']))

    def test_27_unchecked_name_priority_and_unrelated_quote(self):
        master = appearance_master()
        master['items']['di-makeup']['value'] = '曲裾袍，冷调紫唇'
        state = approved(master=master)
        artifact = chinese_candidate(state, 'en')
        rewrite(artifact, {'di-makeup': 'a robe'})
        bad = review(state, artifact)
        bad['item_results']['di-makeup']['note'] = '母版「冷调紫唇」；正文引文「a robe」'
        report = flow.submit(state, artifact, bad)
        self.assertEqual(report['result'], 'fail')
        self.assertIn('母版原名称或原描述', ';'.join(report['problems']))
        state = approved(master=master)
        artifact = chinese_candidate(state, 'en')
        rewrite(artifact, {'di-makeup': 'a robe'})
        good = review(state, artifact)
        good['item_results']['di-makeup']['note'] = '母版「曲裾袍」；正文引文「a robe」'
        report = flow.submit(state, artifact, good)
        self.assertEqual(report['result'], 'pass')
        check = next(row for row in report['name_checks'] if row['item_id'] == 'di-makeup')
        self.assertEqual(check['status'], 'not_checked')
        state = approved(master=master)
        artifact = chinese_candidate(state, 'en')
        rewrite(artifact, {'di-makeup': 'a robe'})
        unrelated = review(state, artifact)
        unrelated['item_results']['di-makeup']['note'] = '母版「曲裾袍」；正文引文「完全不同」'
        report = flow.submit(state, artifact, unrelated)
        self.assertEqual(report['result'], 'fail')
        self.assertIn('对应段落引文', ';'.join(report['problems']))

    def test_28_short_body_quote_is_boundary_checked(self):
        master = appearance_master()
        master['items']['di-hair']['value'] = '波波头'
        state = approved(master=master)
        artifact = chinese_candidate(state, 'en')
        rewrite(artifact, {'di-hair': 'bob'})
        report = flow.submit(state, artifact, review(state, artifact))
        self.assertEqual(report['result'], 'pass')
        check = next(row for row in report['name_checks'] if row['item_id'] == 'di-hair')
        self.assertEqual(check['status'], 'matched')

    def test_22_partial_recognition_is_disclosed(self):
        master = appearance_master()
        master['items']['di-makeup']['value'] = '烟熏妆，冷调紫唇'
        state = approved(master=master)
        artifact = chinese_candidate(state)
        rewrite(artifact, {'di-makeup': '烟熏妆，冷调紫唇'})
        report = flow.submit(state, artifact, review(state, artifact))
        self.assertEqual(report['result'], 'pass')
        check = next(row for row in report['name_checks'] if row['item_id'] == 'di-makeup')
        self.assertEqual(check['status'], 'matched')
        self.assertEqual(check['coverage'], '列出的名称组')
        self.assertIn('matched 只代表列出的名称组', report['limitation'])

    def test_23_two_names_one_without_english_alias(self):
        master = appearance_master()
        master['items']['di-makeup']['value'] = '烟熏妆，曲裾袍'
        state = approved(master=master)
        artifact = chinese_candidate(state, 'en')
        rewrite(artifact, {'di-makeup': 'smoky eye and a gray coat'})
        attest = review(state, artifact)
        attest['item_results']['di-makeup']['note'] = '正文引文「smoky eye」'
        report = flow.submit(state, artifact, attest)
        self.assertEqual(report['result'], 'fail')
        check = next(row for row in report['name_checks'] if row['item_id'] == 'di-makeup')
        self.assertEqual(check['status'], 'not_checked')
        self.assertEqual({row['status'] for row in check['groups']}, {'matched', 'not_checked'})
        attest['item_results']['di-makeup']['note'] = '母版原文「烟熏妆，曲裾袍」；正文引文「smoky eye」'
        report = flow.submit(state, artifact, attest)
        self.assertEqual(report['result'], 'pass')
        check = next(row for row in report['name_checks'] if row['item_id'] == 'di-makeup')
        self.assertEqual(check['status'], 'not_checked')

    def test_24_nonstandard_facet_is_still_reported(self):
        master = appearance_master()
        master['items']['di-styling']['facet'] = '外观'
        master['items']['di-styling']['value'] = '冷调紫唇'
        state = approved(master=master)
        artifact = chinese_candidate(state)
        rewrite(artifact, {'di-styling': '干净的脸'})
        report = flow.submit(state, artifact, review(state, artifact))
        self.assertEqual(report['result'], 'pass')
        check = next(row for row in report['name_checks'] if row['item_id'] == 'di-styling')
        self.assertEqual(check['status'], 'not_checked')
        self.assertFalse(check['requires_review'])

    def test_25_mapping_failures_are_loud(self):
        original, original_cache = terms.MAP_PATH, terms._CACHE
        try:
            with tempdir('name-map-') as folder:
                bad = folder / 'bad.json'
                bad.write_text('{', encoding='utf-8')
                terms.MAP_PATH = bad
                terms._CACHE = None
                with self.assertRaises(ValueError):
                    terms.groups()
                conflict = folder / 'conflict.json'
                conflict.write_text(json.dumps({'schema': 'vds-name-map-1', 'groups': [
                    {'id': 'CH-19:1', 'entry': 'CH-19', 'names': ['裸妆'], 'aliases': ['shared']},
                    {'id': 'CH-20:1', 'entry': 'CH-20', 'names': ['韩系清透妆'], 'aliases': ['shared']}]},
                    ensure_ascii=False), encoding='utf-8')
                terms.MAP_PATH = conflict
                terms._CACHE = None
                with self.assertRaises(ValueError):
                    terms.groups()
                short = folder / 'short.json'
                short.write_text(json.dumps({'schema': 'vds-name-map-1', 'groups': [
                    {'id': 'CH-19:1', 'entry': 'CH-19', 'names': ['裸妆'], 'aliases': ['ab']}]},
                    ensure_ascii=False), encoding='utf-8')
                terms.MAP_PATH = short
                terms._CACHE = None
                with self.assertRaises(ValueError):
                    terms.groups()
                name_conflict = folder / 'name-conflict.json'
                name_conflict.write_text(json.dumps({'schema': 'vds-name-map-1', 'groups': [
                    {'id': 'CH-19:1', 'entry': 'CH-19', 'names': ['裸妆'], 'aliases': []},
                    {'id': 'CH-20:1', 'entry': 'CH-20', 'names': ['韩系清透妆'], 'aliases': ['裸妆']}]},
                    ensure_ascii=False), encoding='utf-8')
                terms.MAP_PATH = name_conflict
                terms._CACHE = None
                with self.assertRaises(ValueError):
                    terms.groups()
                terms.MAP_PATH = folder / 'missing.json'
                terms._CACHE = None
                with self.assertRaises(ValueError):
                    terms.groups()
        finally:
            terms.MAP_PATH = original
            terms._CACHE = original_cache

    def test_14_layout_uses_description_fields_only(self):
        def layout_case(caption, items, meta=()):
            master = appearance_master()
            master['items']['di-hair']['value'] = '黑色长发自然垂下。'
            master['items']['di-state']['value'] = '肩背放松。'
            state = approved(master=master, target='moss-image-layout')
            ratio = state['masters'][-1]['items'][state['masters'][-1]['globals']['aspect_ratio']]['value']
            facts = [key for seg in candidate(state)['segments'] for key in seg['item_ids']]
            obj = {'summary': {'meta': list(meta), 'canvas': 'single', 'caption': caption},
                   'items': items, 'bbox_coord_space': 'abs_centralized', 'bbox_format': 'yxyx'}
            cand = {'master_hash': candidate(state)['master_hash'], 'target': 'moss-image-layout',
                    'language': 'zh-CN',
                    'segments': [{'text': json.dumps(obj, ensure_ascii=False), 'item_ids': facts}],
                    'parameters': {'aspect_ratio': ratio, 'image_size': {'width': 512, 'height': 640}}}
            return flow.submit(state, cand, review(state, cand))

        ok_items = [{'label': 'character', 'caption': '妆容为烟熏妆，近景胸像', 'bbox': [-16, -16, 16, 16]}]
        self.assertEqual(layout_case('烟熏妆近景', ok_items)['result'], 'pass')
        meta_only = layout_case('干净的脸', [{'label': 'character', 'caption': '干净的脸', 'bbox': [-16, -16, 16, 16]}],
                                meta=['烟熏妆'])
        self.assertEqual(meta_only['result'], 'fail')
        text_only = layout_case('干净的脸', [
            {'label': 'character', 'caption': '干净的脸', 'bbox': [-16, -16, 16, 16]},
            {'label': 'text', 'caption': '牌子', 'text': '烟熏妆', 'bbox': [-16, -16, 16, 16]}])
        self.assertEqual(text_only['result'], 'fail')


if __name__ == '__main__':
    unittest.main(verbosity=2)
