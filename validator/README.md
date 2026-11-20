# Validator của nhóm

Chạy từ thư mục gốc repo bằng Python 3.10 trở lên:

```
python validator/validate.py <thư_mục_delivery> --out <errors.json> [--candidates <candidates.json>]
```

Chỉ đọc thư mục delivery được truyền vào; chỉ thư viện chuẩn; không mạng. Xem [GUIDE.md](../GUIDE.md) Pha 1–2 và [RULES.md](../RULES.md).

`validate.py` giữ phần kiểm luật; `cross_check.py` sinh tín hiệu đối chiếu. File `--out` chỉ chứa lỗi luật. File `--candidates` là hàng đợi cho người xem, không tự thêm vào lỗi cuối.

Đối chiếu đổi box YOLO thành pixel, ghép lớp qua tên và chọn segment thing theo bbox IoU. Segment id đọc từ RGB của mask: R + 256G + 65536B. Sau đó đếm pixel thật bên trong box theo tâm pixel; bỏ crowd và stuff. Các dải pixel cùng id trên mỗi hàng giúp tái sử dụng mask khi thử nhiều ngưỡng.

- Bất đồng lớp cần IoU ≥ 0,45 và containment ≥ 0,80; người xem phân biệt `class_swap` với `category_swap`.
- `bbox_drift` cần cùng lớp, IoU ≥ 0,15 và containment < 0,85, cùng bộ lọc diện tích.
- `instance_merge` cần hai phần pixel riêng ≥ 15%, hợp hai box chứa ≥ 80% segment, IoU hai box ≤ 0,45. Hai tâm nằm trong bbox segment chưa đủ.
- `missing_box` xét segment đủ lớn khi không có box IoU ≥ 0,15, cũng không có box cùng lớp với IoU ≥ 0,02 và containment ≥ 0,50.

Diện tích tối thiểu của segment cho drift/merge/missing là max(256 pixel, 0,2% ảnh); box xét drift chiếm ≥ 0,5% ảnh. Ngưỡng tập trung tại `Thresholds`; số đo và định danh vùng nằm ngay trong từng candidate. Đường dẫn manifest thoát khỏi delivery bị từ chối trong module đối chiếu; mask hỏng hoặc mapping thiếu gây lỗi rõ ràng.

Đo hàng đợi trên lô sạch, không dùng đáp án:

```powershell
py -X utf8 validator/benchmark_cross_check.py runs/clean/delivery --out runs/clean/cross_check_benchmark.json
py -X utf8 validator/validate.py runs/r5007/delivery --out runs/r5007/rules.json --candidates runs/r5007/candidates.json
py -X utf8 -m unittest discover -s tests -p test_cross_check.py -v
```

Benchmark so sánh sensitive/balanced/strict trong một lần đọc mask. Balanced cho 2 tín hiệu/2 ảnh trên 50 ảnh sạch, seed 5007 cho 25 tín hiệu/21 ảnh. Xem [số liệu](../submission/measurements/cross_check_5007.json) và [báo cáo](../submission/REPORT.md) về cách chọn ngưỡng và giới hạn. Đây chưa phải F1/recall. Các kiểm thử dùng ảnh mask giả, không đọc dữ liệu gốc hay đáp án.

Hàng đợi vẫn cần người xem: vật bị che, matching nhầm và nhiều box cùng lớp có thể gây nhiễu. Box quá rộng chứa trọn mask và đối tượng nhỏ có thể bị bỏ sót. Giữ bản candidates đã dùng để review; lưu một lượt chạy mới ở đường dẫn khác nếu cần so sánh.
