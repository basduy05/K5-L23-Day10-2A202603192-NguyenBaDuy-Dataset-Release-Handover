Release: lab250_43f248381e9d_v2
Parent: lab250_43f248381e9d
Số ảnh: 241
Số nhãn: 1695
Guideline: v1.2 (J01-J04), v1.3 (J05-J10)
QC v1: 18/250 = 7.2%
Kết luận v1: Hold — Tỉ lệ lỗi 7.2% vượt ngưỡng 2.0% của Day 7, dừng phát hành v1.
Kết luận v2: Release — Đã tách 9 ảnh lỗi nhãn detection sang rework_queue.csv, giữ nguyên nhãn detection hợp lệ, sửa hash và đồng nhất split train/val.
Ghi chú: Sửa split cho scene_315 về train; cập nhật hash đúng cho 000000000785 và 000000023272 sau khi mở ảnh kiểm tra nguyên vẹn; tách 9 ảnh gán nhãn sai giao lại đúng annotator/reviewer theo jobs.csv; 5 ảnh lỗi thuộc panoptic (000000012576, 000000012639, 000000017207, 000000021465, 000000021503) có nhãn detection đúng nên ở lại v2, chuyển thông tin cho team panoptic.
