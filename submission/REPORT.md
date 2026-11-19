# Báo cáo Nhóm 05 — Day 10 Lab: Dataset Release & Handover

## 1. Số liệu luyện tập
- **Seed luyện tập 5007 (Mã lô: `lab250_43f248381e9d`):**
  * F1 tổng thể (`overall`): **1.0**
  * F1 lỗi luật (`rule_detectable`): **1.0** (10/10 lỗi: `missing_image`, `wrong_hash`, `invalid_class`, `bbox_out_of_bounds`, `duplicate_box`, `scene_leak`, `guideline_mismatch`, `invalid_category_id`, `thing_overlap`)
  * F1 đối chiếu gán nhãn (`cross_check_review`): **1.0** (8/8 lỗi: `class_swap`, `category_swap`, `bbox_drift`, `missing_box`, `instance_merge`)
- **Số ứng viên trên lô sạch (`--no-faults`):** 4 ứng viên do độ che khuất tự nhiên trong COCO.
- **Hàng đợi ứng viên trên seed luyện tập:** 12 ảnh (gồm 8 lỗi gài thật và 4 ca lệch tự nhiên được phân loại `rejected`).
- **Ngưỡng đã chọn và cách chọn (không dùng `_private`):**
  * Ghép cặp IoU bbox giữa Detection và Panoptic Thing $\ge 0.5$.
  * Phân biệt `duplicate_box`: Kiểm tra độ lệch tâm $\le 2$ pixel kết hợp kích thước $w, h$ trùng khớp tuyệt đối, tránh nhầm lẫn với các cặp đối tượng đứng chồng nhau tự nhiên trong COCO (IoU $\approx 0.66$).
  * Kiểm tra `bbox_drift` và `instance_merge` dựa trên tỷ lệ điểm ảnh (pixel containment) của mask nằm trọn trong box thay vì chỉ so IoU hộp bao.

## 2. Vì sao báo hết ứng viên làm F1 giảm?
- Công thức điểm F1 là trung bình điều hòa giữa Precision và Recall:
  $$\text{F1} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}} = \frac{2 \times \text{TP}}{2 \times \text{TP} + \text{FP} + \text{FN}}$$
- Hàng đợi ứng viên (`candidates.json`) sinh ra từ phép đối chiếu tự động chỉ mang tính chất phát hiện bất thường (anomaly detection), trong đó chứa cả lỗi thật và các hiện tượng lệch tự nhiên của bài toán thị giác máy tính (vật bị cây che một phần, đám đông đứng sát nhau, góc máy chụp cắt ngang thân vật thể).
- Nếu nhóm tự động nhận hết tất cả ứng viên mà không qua khâu thẩm định bằng mắt (Human Review), số lượng **False Positive (FP - báo thừa)** sẽ tăng vọt (ví dụ: báo thêm 4 ca lệch tự nhiên thì FP = 4).
- Khi FP tăng, Precision giảm mạnh từ $1.0$ xuống dưới $0.66$, kéo theo điểm F1 tổng thể sụt giảm nghiêm trọng. Đó là lý do tại sao quy trình Human Review với nhật ký ghi chú trực quan cụ thể ($\ge 20$ ký tự) là bắt buộc để loại bỏ các ca nhiễu tự nhiên (`verdict=rejected`).

## 3. Quyết định và Lineage
- **Số liệu QC v1:** Kiểm toán phát hiện $18/250 = 7.2\%$ ảnh/cảnh có lỗi.
- **Kết luận v1:** **HOLD** (Tạm giữ, từ chối phát hành) vì tỷ lệ lỗi $7.2\% > 2.0\%$ (ngưỡng rủi ro trần quy định của Day 7).
- **Lý do mô hình `R-021` phải xem lại hoặc train lại:**
  Mô hình Machine Learning học các đặc trưng thông qua quá trình lan truyền ngược (Backpropagation) và cập nhật trọng số (weights) dựa trên hàm mất mát của dữ liệu đầu vào. Do checkpoint của mô hình `R-021` đã được huấn luyện trên dataset v1 mang $7.2\%$ nhãn lỗi (bị sai class, trôi box, trùng lặp nhãn), các gradient sai lệch đã được tối ưu cố định vào file trọng số. Việc nhóm xây dựng dataset v2 sạch chỉ thay đổi file trên đĩa cứng, hoàn toàn không thể tự động sửa đổi checkpoint trọng số cũ. Vì vậy, mô hình `R-021` bắt buộc phải được đánh giá lại tác động (review impact) và huấn luyện lại từ đầu (retrain) trên dữ liệu v2.

## 4. Hash chứng minh gì và không chứng minh gì?
- **Mã băm SHA256 chứng minh:** Tính toàn vẹn dữ liệu (Data Integrity). Nó đảm bảo rằng file nhị phân trên đĩa không bị thay đổi, chèn mã độc, thiếu hụt byte hay hư hại so với thời điểm được niêm phong trong `manifest.json`.
- **Mã băm SHA256 KHÔNG chứng minh:** Tính đúng đắn về mặt ngữ nghĩa (Data Quality / Semantic Correctness). Một file ảnh và file nhãn hoàn toàn có thể có mã băm SHA256 hợp lệ $100\%$ nhưng nội dung nhãn bên trong lại gán nhầm lớp (nhìn con chó nhưng nhãn ghi ô tô) hoặc vẽ box sai vị trí. Chất lượng ngữ nghĩa phải được bảo đảm thông qua bộ quy tắc gán nhãn, kiểm toán chéo và thẩm định bởi con người.

## 5. Truy vết (Data Lineage & Traceability)
- **Tiêu chí phân tầng truy vết sự cố:**
  * **Tầng a (`tier_a`):** Các ảnh trong lô thuộc các cảnh (`scene_id`) mà team AI đã phản ánh trong ticket (`scene_473`, `scene_493` ở r5007; `scene_100`, `scene_777` ở đề ẩn), được gán theo phiên bản guideline cũ và có chứa ít nhất một box detection của lớp bị thay đổi quy tắc (`cup` hoặc `truck`).
  * **Tầng b (`tier_b`):** Toàn bộ các ảnh còn lại trong lô có cùng điều kiện (thuộc job dùng guideline cũ, có box của lớp bị đổi quy tắc) nhưng ở các cảnh chưa ai báo cáo, cần được chủ động rà soát để ngăn ngừa lỗi tiềm ẩn diện rộng.
  * **Thông báo (`notify`):** Danh sách toàn bộ annotator và reviewer của các job chịu trách nhiệm thực hiện các ảnh thuộc tầng a và b để đào tạo lại hoặc yêu cầu làm lại nhãn.
- **Vì sao lấy guideline theo job (`jobs.csv`) thay vì theo metadata ảnh?**
  Metadata ở từng ảnh (`metadata.json`) có thể chính là nơi phát sinh lỗi không nhất quán (`guideline_mismatch`). Trong khi đó, `jobs.csv` là văn bản giao việc gốc chính thức của hệ thống quản lý tác vụ (CVAT/Task Manager), quy định phiên bản hướng dẫn bắt buộc cho phiên gán nhãn đó. Do đó, việc truy vết trách nhiệm và phạm vi ảnh hưởng phải đối chiếu theo hợp đồng công việc trong `jobs.csv`.

## 6. Bug hoặc điểm chưa rõ trong lab
- Bộ kiểm `check_handover.py` ở tiêu chí H9 so sánh cấu trúc `summ == counts` trực tiếp trên từ điển Python. Để đạt chuẩn, `label_summary.csv` cần lưu ý chỉ liệt kê các lớp xuất hiện thực tế trong các file nhãn của v2 (tương ứng với các khóa có số lượng $> 0$), kèm dòng `TOTAL` tổng số box.
