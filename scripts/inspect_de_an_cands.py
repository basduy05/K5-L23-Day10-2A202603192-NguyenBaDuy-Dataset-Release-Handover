import zipfile, json
from pathlib import Path

z = zipfile.ZipFile('data_source/cache/panoptic_annotations_trainval2017.zip')
doc = json.loads(z.open('annotations/panoptic_val2017.json').read())
cats = {c['id']: c for c in doc['categories']}
anns_by_img = {a['image_id']: a for a in doc['annotations']}
imgs_by_fn = {im['file_name']: im for im in doc['images']}

matches = {
  'img_0015': '000000091779.jpg',
  'img_0031': '000000100582.jpg',
  'img_0076': '000000088462.jpg',
  'img_0091': '000000092939.jpg',
  'img_0094': '000000089556.jpg',
  'img_0130': '000000106757.jpg',
  'img_0134': '000000084664.jpg',
  'img_0148': '000000097337.jpg',
  'img_0168': '000000091500.jpg',
  'img_0174': '000000099114.jpg',
  'img_0180': '000000095786.jpg',
  'img_0198': '000000084362.jpg',
  'img_0229': '000000099428.jpg',
  'img_0237': '000000084650.jpg',
  'img_0249': '000000086220.jpg',
}

cands = [x for x in json.load(open('submission/de_an/candidates.json', encoding='utf-8'))['candidates'] if x['type'] != 'instance_merge']

for c in cands:
    img_name = c['image']
    coco_fn = matches[img_name]
    coco_im = imgs_by_fn[coco_fn]
    coco_ann = anns_by_img[coco_im['id']]
    cat_names = [cats[s['category_id']]['name'] for s in coco_ann['segments_info']]
    det_cls = c['det_class']
    pan_cls = c['pan_class']
    print(f"{img_name}: Det='{det_cls}', Pan='{pan_cls}' -> COCO categories: {cat_names}")
