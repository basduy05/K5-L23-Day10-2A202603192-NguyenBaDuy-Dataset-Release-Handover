# Báo cáo Nhóm 05

**Thành viên:** Nguyễn Bá Duy (Nhóm trưởng), Hoàng Nhật Anh, Phạm Mạnh Hùng, Đỗ Huy Kiên, Nguyễn Đức Cường  
**Mã lớp / Nhóm:** K5-L23 · Nhóm 05  
**Seed luyện tập:** `5007` (Lô v1: `lab250_43f248381e9d`, Lô v2: `lab250_43f248381e9d_v2`)  
**Đề ẩn nghiệm thu:** Lô `lab250_62d7641abb98` (`de_an_05`)  

---

## 1. Số liệu luyện tập
- **F1 theo seed 5007 (rule / cross_check / overall):**
  - F1 lỗi luật (rule): **1.0** (bắt trọn 10/10 lỗi luật mức cấu trúc và định dạng).
  - F1 lỗi gán nhãn (cross_check): **1.0** (xác nhận đúng 8/8 lỗi ngữ nghĩa qua Human Review).
  - F1 tổng thể (overall): **1.0** (18/18 lỗi được phát hiện và xử lý chính xác).
  - F1 truy vết (trace): **tier_a = 1.0, tier_b = 1.0, notify = 1.0**.
- **Số ứng viên trên lô sạch (`--no-faults`):**
  - Chạy `validator/validate.py` trên `runs/clean/delivery` cho ra **0 lỗi luật** và 142 ứng viên nghi vấn tự nhiên.
  - Hàng đợi trên seed luyện tập: 181 ứng viên trên 88 ảnh (lọc ra danh sách 20 ảnh đại diện phân công review).
- **Ngưỡng đã chọn và cách chọn (không dùng `_private`):**
  - Nhóm tự thiết kế và hiệu chỉnh ngưỡng (calib) dựa trên lô sạch `runs/clean`:
    1. *Bất đồng lớp (class/category swap):* IoU giữa box detection và segment panoptic $\ge 0.50$ nhưng nhãn lớp không tương thích.
    2. *Thiếu box detection (missing box):* Segment panoptic thuộc nhóm `thing` có diện tích lớn ($> 1500\text{ px}$) nhưng IoU với toàn bộ box detection bằng 0.
    3. *Hộp trôi lệch (bbox drift):* Cùng nhãn lớp nhưng IoU giữa box detection và segment panoptic nằm trong khoảng $0.20 \le \text{IoU} < 0.65$.
    4. *Gộp thực thể (instance merge):* Một segment panoptic bao phủ từ 2 bounding box detection cùng lớp trở lên.

---

## 2. Vì sao báo hết ứng viên làm F1 giảm?
**Trả lời bằng số liệu thực tế của Nhóm 05:**
- Trên seed luyện tập 5007, bộ đối chiếu tự động sinh ra **181 ứng viên nghi vấn**, nhưng thực tế trong lô chỉ có **8 lỗi gán nhãn thật**.
- Nếu nhóm tự động nhận hết (auto-accept) toàn bộ 181 ứng viên đưa vào `errors.json` mà không mở ảnh xem:
  - Số lượng lỗi nộp: $181$. Số lỗi đúng: $8$. Số lỗi báo sai (False Positives): $173$.
  - Độ chính xác (Precision) giảm nghiêm trọng: từ **$100\%$ ($8/8$) tụt xuống chỉ còn $\frac{8}{181} \approx 4.4\%$**!
  - Điểm F1 tương ứng sẽ tụt từ **$1.0$ xuống dưới $0.08$**, khiến nhóm mất sạch điểm chất lượng gán nhãn.
- **Bản chất kỹ thuật:** Bộ đối chiếu thuật toán chỉ phát hiện các điểm sai lệch hình học (IoU thấp, che khuất, viền không khít). Chỉ có **mắt người (Human Review)** khi mở ảnh trực tiếp mới xác định được bản chất vật thể thực tế để loại bỏ các trường hợp lệch tự nhiên (góc nhìn nghiêng, hai vật nằm sát nhau như bàn và ghế, người bị biển báo che).

---

## 3. Quyết định và lineage
- **Kết quả QC v1 lô `lab250_43f248381e9d`:** Phát hiện **18 lỗi trên 250 ảnh** (tỉ lệ lỗi đạt **$7.2\%$**).
- **Kết luận:** Theo quy định ngưỡng Day 7 (tỉ lệ lỗi $> 2.0\%$), Nhóm 05 bắt buộc ban hành quyết định **HOLD** (dừng phát hành và cấm huấn luyện đối với lô v1).
- **Giải thích vì sao run `R-021` phải xem lại hoặc train lại:**
  - Khi thực hiện truy vết tác động (`python scripts/lineage.py impact --release-id lab250_43f248381e9d`), hệ thống cảnh báo:  
    `R-021: affected=True action=review_or_retrain`.
  - **Nguyên nhân cốt lõi:** Quá trình huấn luyện mô hình học sâu là quá trình tối ưu hóa hàm mất mát dựa trên dữ liệu. Việc phát hành lô mới v2 không thể tự sửa chữa trọng số (weights) của mô hình `R-021` đã bị nhiễm độc (poisoned/corrupted) bởi $7.2\%$ nhãn sai lệch và bounding box lệch lạc trong v1. Do đó, model `R-021` bắt buộc phải được đánh giá lại trên tập validation độc lập hoặc huấn luyện lại hoàn toàn (retrain) từ lô sạch v2.

---

## 4. Hash chứng minh điều gì và KHÔNG chứng minh điều gì?
- **Hash CHỨNG MINH:**
  - *Tính toàn vẹn dữ liệu (Data Integrity):* Chứng minh chính xác tuyệt đối rằng từng file ảnh, nhãn, mask không bị biến đổi, không bị sửa đổi trái phép hoặc không bị hỏng hóc vật lý trong quá trình truyền tải và lưu trữ.
  - *Tính bất biến (Immutability):* Cho phép kiểm toán (audit) độc lập để xác minh lô bàn giao v2 không bị ghi đè hay chỉnh sửa lén lút sau khi đã đóng gói.
- **Hash KHÔNG chứng minh:**
  - *Chất lượng ngữ nghĩa và tính đúng đắn của nhãn (Semantic Correctness):* Một bức ảnh bị gán nhãn sai hoàn toàn (ví dụ dán nhãn cái cốc thành con chó) hay bounding box bị trôi lệch ra ngoài thì file `.txt` chứa tọa độ sai đó vẫn có một mã băm SHA256 hoàn toàn hợp lệ.
  - Mã hash chỉ trả lời câu hỏi: *"Dữ liệu này có nguyên vẹn như lúc đóng gói không?"*, chứ không thể trả lời câu hỏi: *"Dữ liệu này có được dán nhãn đúng quy định không?"*.

---

## 5. Truy vết
Công cụ: `tools/trace_query.py <delivery> --out trace.json` (thư viện chuẩn, chỉ đọc `delivery/`, không ghi cứng tên lớp, cảnh hay ảnh).

- **Lớp bị đổi quy tắc:** đọc `guideline/changelog.md`. Seed 5007: `cup`, quy tắc mới từ v1.3 (cup bị che >50% hoặc ở mép ảnh vẫn phải gán box).
- **Cảnh team AI nêu:** các `scene_id` có trong `metadata.json` xuất hiện trong `incoming/ticket.md`. Seed 5007: `scene_473`, `scene_493`.
- **Điều kiện chung:** ảnh thuộc job có guideline cũ hơn v1.3 theo `jobs.csv` (seed 5007: J01–J04) **và** `labels/<ảnh>.txt` có ít nhất một box lớp đó.
- **tier_a** = ảnh đạt điều kiện nằm trong cảnh ticket nêu (3 ảnh); **tier_b** = các ảnh đạt điều kiện còn lại, chưa ai báo (6 ảnh).
- **notify** = annotator và reviewer của các job chứa ảnh tier_a/tier_b: A04, A05, Q01. Không báo hết người của mọi job cũ, vì có job cũ không có ảnh nào chứa `cup`.
- **Kết quả tự đo (`score_findings.py`):** tier_a 1.0, tier_b 1.0, notify 1.0.

**Vì sao lấy guideline theo job, không theo ảnh:** người gán làm theo guideline đang áp dụng cho job khi job được tạo, nên job mới quyết định ảnh có bị gán theo quy tắc cũ hay không. Cột guideline ghi ở từng ảnh trong `metadata.json` có thể sai, chính là lỗi `guideline_mismatch` mà validator bắt; dùng cột đó sẽ đưa nhầm hoặc bỏ sót ảnh.

**Đề ẩn:** chạy cùng công cụ trên `delivery/` của đề, ra lớp `truck`, cảnh `scene_100`, `scene_777`; tier_a 3 ảnh, tier_b 3 ảnh, notify A01, A02, Q01, Q03, khớp với kết quả Duy làm độc lập.

---

## 6. Bug hoặc điểm chưa rõ trong lab (nếu có)
1. **Kiểm tra thống kê nhãn (H9 trong `check_handover.py`):**
   - Bộ kiểm tra yêu cầu từ điển thống kê `label_summary.csv` phải khớp chính xác các lớp thực tế có mặt trong tập `v2/labels` (76 lớp có nhãn), nếu điền đầy đủ cả 80 lớp COCO với count = 0 thì lệnh so khớp `summ == counts` sẽ báo FAIL. Nhóm đã điều chỉnh sinh đúng các lớp hiện diện để đạt chuẩn 17/17 PASS.
2. **Quy tắc gộp lỗi `merge_review.py`:**
   - Cần đảm bảo các lỗi đưa vào `review_log.csv` thuộc danh mục `metrics.SEMANTIC_TYPES`. Nhóm đã đối soát chặt chẽ giữa validator và human review.
