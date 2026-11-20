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
- **Số liệu đo đạc thực nghiệm đối chiếu Detection ↔ Panoptic (Hoàng Nhật Anh — 2A202603813):**
  - Kết quả đo lưu chi tiết trong `submission/measurements/cross_check_5007.json` và `submission/measurements/clean_threshold_profiles.json`.
  - **Lô sạch `lab250_9144bc8fd60b` (50 ảnh, 0 lỗi luật):** Cách cũ chỉ xét bbox tạo 52 tín hiệu trên 22 ảnh; thuật toán mới sử dụng pixel mask phân đoạn tạo ra 2 tín hiệu `instance_merge` trên 2 ảnh. Đây là các bất đồng tự nhiên của lô không cài lỗi, bắt buộc cần mắt người kiểm tra để giải thích.
  - **Lô luyện `lab250_afa095a47015` (seed 5007, 250 ảnh):** Có 10 lỗi luật; 25 tín hiệu trên 21 ảnh (gồm 12 `instance_merge`, 8 bất đồng lớp, 3 `missing_box`, 2 `bbox_drift`).
- **Ngưỡng đã chọn và cách chọn (không dùng `_private`):**
  - Ghép YOLO sang pixel mask, đối chiếu tên lớp, chọn segment thing không phải crowd có bbox IoU cao nhất. Tính containment bằng số pixel segment nằm trong box chia tổng pixel thật của segment (không lấy trường `area` khai báo thay cho số pixel thực).
  - *Bất đồng lớp (`class_swap` / `category_swap`):* IoU $\ge 0.45$ và containment $\ge 0.80$. Đây là tín hiệu nghi vấn; người xem ảnh quyết định `class_swap` hay `category_swap`.
  - *Hộp trôi lệch (`bbox_drift`):* Cùng lớp, IoU $\ge 0.15$, containment $< 0.85$, box chiếm $\ge 0.5\%$ diện tích ảnh và segment đủ lớn ($\ge \max(256\text{ px}, 0.2\%\text{ diện tích ảnh})$).
  - *Gộp thực thể (`instance_merge`):* Một segment có pixel riêng trong hai box cùng lớp; mỗi phần riêng $\ge 15\%$, hợp hai box chứa $\ge 80\%$ pixel segment, IoU hai box $\le 0.45$. Không suy diễn gộp chỉ vì bbox segment chứa hai tâm box.
  - *Thiếu box (`missing_box`):* Segment thing đủ lớn và không có box detection nào ghép hợp lý.
  - *Đo thực nghiệm ba cấu hình trên cùng 50 ảnh sạch:* sensitive = 4 tín hiệu/4 ảnh; balanced = 2 tín hiệu/2 ảnh; strict = 1 tín hiệu/1 ảnh. Nhóm quyết định chọn cấu hình **balanced** vì hàng đợi sạch nhỏ và tránh siết tất cả ngưỡng chỉ để giảm thêm một tín hiệu mà làm sót lỗi (FN). Không dùng đề ẩn hoặc thư mục `_private` để tinh chỉnh ngưỡng.

---

## 2. Vì sao báo hết ứng viên làm F1 giảm?
**Trả lời bằng số liệu thực tế đo đạc của Nhóm 05:**
- Báo mọi ứng viên thành lỗi làm tăng nghiêm trọng False Positives (FP): ngay trên lô sạch không cài lỗi, cách cũ sinh ra 52 tín hiệu và thuật toán pixel mới vẫn sinh ra 2 tín hiệu tự nhiên. Nếu coi toàn bộ tín hiệu này là lỗi thì tất cả đều là báo giả.
- Trên seed luyện tập 5007, bộ đối chiếu tự động sinh ra hàng chục ứng viên nghi vấn, nhưng thực tế trong lô chỉ có **8 lỗi gán nhãn thật**.
- Với cùng số lượng lỗi thật phát hiện được (TP) và bỏ sót (FN), việc thêm lượng lớn FP làm mẫu số của công thức $F_1 = \frac{2\text{TP}}{2\text{TP} + \text{FP} + \text{FN}}$ tăng vọt:
  - Nếu tự động nhận hết 181 ứng viên vào `errors.json`: Precision tụt từ $100\%$ ($8/8$) xuống còn $\frac{8}{181} \approx 4.4\%$, và điểm $F_1$ tụt từ $1.0$ xuống dưới $0.08$!
- **Bản chất kỹ thuật:** Thuật toán chỉ nhận biết sai lệch hình học (IoU thấp, che khuất, viền chồng lấn). Chỉ có **mắt người (Human Review)** khi mở ảnh trực tiếp mới nhận diện được ngữ cảnh thực tế (góc chụp nghiêng, hai vật nằm sát nhau như bàn và ghế, người bị biển báo che) để xác nhận chính xác lỗi thật và loại bỏ báo giả.

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
  - *Tính toàn vẹn dữ liệu (Data Integrity):* Chứng minh chính xác tuyệt đối rằng từng file ảnh, nhãn, mask không bị biến đổi, không bị sửa đổi trái phép hoặc không bị hỏng hóc vật lý trong quá trình truyền tải và lưu trữ (SHA-256 khớp manifest chứng minh bytes hiện tại khớp từng bit bytes đã khai báo).
  - *Tính bất biến (Immutability):* Cho phép kiểm toán (audit) độc lập để xác minh lô bàn giao v2 không bị ghi đè hay chỉnh sửa lén lút sau khi đã đóng gói.
- **Hash KHÔNG chứng minh:**
  - *Chất lượng ngữ nghĩa và tính đúng đắn của nhãn (Semantic Correctness):* Một bức ảnh bị gán nhãn sai hoàn toàn (ví dụ dán nhãn cái cốc thành con chó) hay bounding box bị trôi lệch ra ngoài thì file `.txt` chứa tọa độ sai đó vẫn có một mã băm SHA256 hoàn toàn hợp lệ.
  - Manifest cũng phải được đối chiếu cùng `release_id`; một manifest bị thay thế cùng dữ liệu không tự tạo bằng chứng nguồn gốc đáng tin.
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

**Đề ẩn (`lab250_62d7641abb98`):** chạy cùng công cụ trên `delivery/` của đề ẩn, xác định lớp `truck`, cảnh `scene_100`, `scene_777`; tier_a 3 ảnh (`img_0146`, `img_0157`, `img_0240`), tier_b 3 ảnh (`img_0019`, `img_0084`, `img_0169`), notify: `A01`, `A02`, `Q01`, `Q03`.

---

## 6. Bug hoặc điểm chưa rõ trong lab (nếu có)
1. **Lỗi mã hóa UTF-8 trên môi trường Windows:**
   - Khi chạy `py -X utf8 -u scripts/run_lab.py --seeds 5007` trên Windows, tiến trình Python con do `run_lab.py` gọi không tự động kế thừa cờ `-X utf8`. `inject_release.py` đã ghi xong lô nhưng phát sinh `UnicodeEncodeError` (console cp1252) khi in dòng thông báo tiếng Việt cuối cùng; làm `run_lab.py` dừng trước khi kịp ghi lineage.
   - Giải pháp: Đặt biến môi trường `$env:PYTHONUTF8 = '1'` trước khi thực thi để toàn bộ tiến trình con đều chạy UTF-8 an toàn.
2. **Kiểm tra thống kê nhãn (H9 trong `check_handover.py`):**
   - Bộ kiểm tra yêu cầu từ điển thống kê `label_summary.csv` phải khớp chính xác các lớp thực tế có mặt trong tập `v2/labels` (76 lớp có nhãn), nếu điền đầy đủ cả 80 lớp COCO với count = 0 thì lệnh so khớp `summ == counts` sẽ báo FAIL. Nhóm đã điều chỉnh sinh đúng các lớp hiện diện để đạt chuẩn 17/17 PASS.
3. **Quy tắc gộp lỗi `merge_review.py`:**
   - Cần đảm bảo các lỗi đưa vào `review_log.csv` thuộc danh mục `metrics.SEMANTIC_TYPES`. Nhóm đã đối soát chặt chẽ giữa validator và human review.
