"""Synthetic geometry tests: no training data, hidden answers or network."""
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validator.cross_check import (
    DEFAULT_THRESHOLDS, MaskPixels, delivery_file, image_candidates,
    profile_candidates, read_boxes,
)
from validator import cross_check


def mask_fixture(rectangles, width=100, height=100):
    pixels = bytearray(width * height * 3)
    for sid, (x, y, w, h) in rectangles:
        for row in range(y, y + h):
            for col in range(x, x + w):
                offset = (row * width + col) * 3
                pixels[offset:offset + 3] = sid.to_bytes(3, 'little')
    return MaskPixels(width, height, pixels, {sid for sid, _ in rectangles}), pixels


def box(rectangle, label='cat', line=1):
    return {'px_box': rectangle, 'class_name': label, 'line': line,
            'area_fraction': rectangle[2] * rectangle[3] / 10000}


CATEGORIES = {1: {'name': 'cat', 'isthing': 1},
              2: {'name': 'wall', 'isthing': 0}}


class CrossCheckTest(unittest.TestCase):
    def test_pixel_centers_and_high_rgb_segment_id(self):
        mask, _ = mask_fixture([(66051, (0, 0, 4, 3))], 4, 3)
        self.assertEqual(mask.counts[66051], 12)
        self.assertEqual(mask.count_inside(66051, [.5, .5, 1, 1]), 1)
        self.assertEqual(mask.count_inside(66051, [-2, -2, 3, 3]), 1)
        self.assertEqual(mask.count_inside(66051, [2, 2, 0, 1]), 0)

    def test_correct_match_is_quiet_and_disagreement_requires_review(self):
        mask, _ = mask_fixture([(1, (10, 10, 40, 40))])
        segment = {'id': 1, 'category_id': 1, 'bbox': [10, 10, 40, 40]}
        self.assertEqual(image_candidates('renamed', [box(segment['bbox'])],
                                         [segment], CATEGORIES, mask), [])
        rows = image_candidates('renamed', [box(segment['bbox'], 'dog')],
                                [segment], CATEGORIES, mask)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['possible_types'], ['class_swap', 'category_swap'])
        self.assertNotIn('verdict', rows[0])
        self.assertEqual(rows[0]['containment'], 1)

    def test_enclosing_bbox_without_segment_pixels_is_not_merge(self):
        # A long segment bbox encloses both centers, but its pixels occur only
        # inside the first detection. The old center heuristic reported a merge.
        mask, _ = mask_fixture([(1, (10, 10, 20, 20)), (1, (79, 49, 1, 1))])
        segment = {'id': 1, 'category_id': 1, 'bbox': [10, 10, 70, 40]}
        rows = image_candidates('arbitrary', [box([10, 10, 20, 20]),
                                box([50, 10, 20, 20], line=2)], [segment], CATEGORIES, mask)
        self.assertNotIn('instance_merge', [r['type'] for r in rows])

    def test_two_disjoint_pixel_groups_detect_merge_once(self):
        mask, _ = mask_fixture([(1, (10, 10, 20, 20)), (1, (60, 10, 20, 20))])
        segment = {'id': 1, 'category_id': 1, 'bbox': [10, 10, 70, 20]}
        rows = image_candidates('arbitrary', [box([10, 10, 20, 20]),
                                box([60, 10, 20, 20], line=2)], [segment], CATEGORIES, mask)
        self.assertEqual([r['type'] for r in rows], ['instance_merge'])
        self.assertEqual(rows[0]['mask_union_containment'], 1)

    def test_duplicate_boxes_are_not_merge(self):
        mask, _ = mask_fixture([(1, (10, 10, 40, 40))])
        segment = {'id': 1, 'category_id': 1, 'bbox': [10, 10, 40, 40]}
        rows = image_candidates('arbitrary', [box(segment['bbox']),
                                box(segment['bbox'], line=2)], [segment], CATEGORIES, mask)
        self.assertEqual(rows, [])

    def test_drift_uses_pixels_even_with_high_bbox_iou(self):
        mask, _ = mask_fixture([(1, (10, 10, 40, 40))])
        segment = {'id': 1, 'category_id': 1, 'bbox': [10, 10, 40, 40]}
        rows = image_candidates('arbitrary', [box([20, 10, 40, 40])], [segment], CATEGORIES, mask)
        self.assertEqual([r['type'] for r in rows], ['bbox_drift'])
        self.assertGreater(rows[0]['iou'], .5)
        self.assertEqual(rows[0]['containment'], .75)

    def test_missing_uses_actual_area_and_excludes_crowd_stuff(self):
        mask, _ = mask_fixture([(1, (10, 10, 40, 40))])
        segment = {'id': 1, 'category_id': 1, 'bbox': [10, 10, 40, 40], 'area': 1}
        rows = image_candidates('arbitrary', [], [segment], CATEGORIES, mask)
        self.assertEqual(rows[0]['type'], 'missing_box')
        self.assertEqual(rows[0]['area'], 1600)
        for modified in ({**segment, 'iscrowd': 1}, {**segment, 'category_id': 2}):
            self.assertEqual(image_candidates('arbitrary', [], [modified], CATEGORIES, mask), [])

    def test_manifest_path_cannot_escape_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'escapes delivery'):
                delivery_file(Path(directory), '../not-delivery.txt')

    def test_invalid_class_nan_and_bad_boxes_are_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            label = Path(directory) / 'label.txt'
            label.write_text('0.5 .5 .5 .4 .4\n0 nan .5 .4 .4\n'
                             '0 .5 .5 -.4 .4\n9 .5 .5 .4 .4\n'
                             '0 .5 .5 .4 .4\n', encoding='utf-8')
            rows = read_boxes(label, ['cat'], 100, 100)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['line'], 5)

    def test_delivered_files_mapping_and_profiles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, pixels = mask_fixture([(1, (10, 10, 40, 40))])
            cross_check.pngutil.write_rgb(root / 'mask.png', 100, 100, pixels)
            (root / 'unrelated-file.jpg').write_bytes(b'not decoded by cross-check')
            (root / 'label.txt').write_text('1 .3 .3 .4 .4\n', encoding='utf-8')
            manifest = {'any-key': {'image': 'unrelated-file.jpg', 'mask': 'mask.png',
                                    'label': 'label.txt'}}
            doc = {'categories': [dict(id=k, **v) for k, v in CATEGORIES.items()],
                   'images': [{'id': 99, 'file_name': 'unrelated-file.jpg', 'width': 100, 'height': 100}],
                   'annotations': [{'image_id': 99, 'segments_info': [
                       {'id': 1, 'category_id': 1, 'bbox': [10, 10, 40, 40]}]}]}
            rows = profile_candidates(root, manifest, ['cat', 'dog'], doc,
                                      {'normal': DEFAULT_THRESHOLDS,
                                       'disabled': replace(DEFAULT_THRESHOLDS, class_iou=1.1)})
            self.assertEqual(rows['normal'][0]['image'], 'any-key')
            self.assertEqual(rows['disabled'], [])
            # Results can be serialized directly as the validator CLI expects.
            json.dumps({'candidates': rows['normal']})
            doc['images'][0]['width'] = 101
            with self.assertRaisesRegex(ValueError, 'dimensions differ'):
                profile_candidates(root, manifest, ['cat', 'dog'], doc, {'normal': DEFAULT_THRESHOLDS})


if __name__ == '__main__':
    unittest.main()
