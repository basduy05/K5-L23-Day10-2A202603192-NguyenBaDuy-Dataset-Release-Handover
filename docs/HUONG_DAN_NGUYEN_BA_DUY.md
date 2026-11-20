# Hướng dẫn chi tiết dành riêng cho Trưởng nhóm: Nguyễn Bá Duy (MSHV: 2A202603192)

> **Dự án:** Lab Day 10 — Bàn giao Dataset & Truy vết (VinAI)  
> **Seed luyện tập:** `5007` | **Mã lô v1:** `lab250_43f248381e9d`  
> **Repo:** [K5-L23-Day10-2A202603192-NguyenBaDuy-Dataset-Release-Handover](https://github.com/basduy05/K5-L23-Day10-2A202603192-NguyenBaDuy-Dataset-Release-Handover)

---

## 1. Vai trò & Sứ mệnh cốt lõi của Trưởng nhóm

Là **Trưởng nhóm (Team Leader) kiêm Kỹ sư Kiến trúc Kiểm định (Lead Validator Architect)**, bạn chịu trách nhiệm cao nhất về:
1. **Kiến trúc và giải thuật Validator (`validator/validate.py`)**: Đảm bảo bắt trọn 100% (F1 = 1.0) cả 9 loại lỗi luật trên bất kỳ seed nào và không báo sai trên lô sạch.
2. **Điều phối tiến độ 5 thành viên theo 6 Checkpoints (CP0 $\rightarrow$ CP6)** trong 4 giờ.
3. **Trực tiếp tham gia Human Review ở Pha 2** (thẩm định 20% ứng viên được chia).
4. **Đại diện nhóm trả lời vấn đáp kỹ thuật chuyên sâu** về Validator và kiến trúc hệ thống trước giảng viên/coach.
5. **Thực hiện tối thiểu 2 commit Git có nội dung** mang tên và email cá nhân.

---

## 2. Checklist công việc chi tiết theo từng mốc thời gian

```mermaid
timeline
    title Timeline công việc của Nguyễn Bá Duy (4 giờ)
    00:15 : CP0 - Khởi tạo & Phân công : Sinh seed 5007, tạo clean set, cập nhật TEAM.md
    00:55 : CP1 - Hoàn thiện Validator : Chạy validate.py, đạt F1 lỗi luật = 1.0
    01:50 : CP2 - Human Review : Mở ảnh thẩm định 20% ứng viên, ghi review_log.csv
    02:45 : CP3-CP4 - Giám sát Lineage & v2 : Kiểm tra Đỗ Huy Kiên đóng gói v2 (H1-H15 PASS)
    03:15 : CP5-CP6a - Kiểm tra Truy vết & Security : Kiểm tra Cường làm trace.json, check 17/17 PASS
    03:55 : CP6b - Chỉ huy Đề ẩn 40' : Chạy validator trên đề ẩn, chia review, xuất nộp
```

---

## 3. Hướng dẫn kỹ thuật từng pha & Lệnh thực thi

### Pha 0: Chuẩn bị & Môi trường (0:00 - 0:15)
- **Mục tiêu**: Đảm bảo dữ liệu và lô luyện tập sẵn sàng.
- **Lệnh thực hiện trên PowerShell**:
  ```powershell
  # 1. Kiểm tra Python
  py --version

  # 2. Sinh lô luyện tập seed 5007 (Đã chạy thành công)
  py scripts/run_lab.py --seeds 5007

  # 3. Sinh lô sạch để hiệu chuẩn ngưỡng (Đã chạy thành công)
  py scripts/inject_release.py --seed 5 --no-faults --out runs/clean

  # 4. Kiểm tra Git config cá nhân để commit đúng tên
  git config user.name "Nguyen Ba Duy"
  git config user.email "2A202603192@vinuni.edu.vn"
  ```

---

### Pha 1: Trọng tâm của Duy — Validator 9 Lỗi Luật (0:15 - 0:55)
- **Mục tiêu**: Đạt **F1 = 1.0** nhóm lỗi luật trên `runs/r5007` và **0 lỗi** trên `runs/clean`.
- **File phụ trách**: `validator/validate.py` (Đã được khởi tạo hoàn chỉnh).
- **Lệnh chạy và tự đo**:
  ```powershell
  # 1. Chạy trên lô sạch (Kỳ vọng: "Phát hiện 0 lỗi luật")
  py validator/validate.py runs/clean/delivery --out runs/clean/rules.json

  # 2. Chạy trên seed luyện tập 5007
  py validator/validate.py runs/r5007/delivery --out runs/r5007/rules.json --candidates runs/r5007/candidates.json

  # 3. Đo điểm F1 lỗi luật
  py -c "import shutil; shutil.copy('runs/r5007/rules.json', 'runs/r5007/errors.json')"
  py scripts/score_findings.py --run runs/r5007
  ```
  *Kết quả kỳ vọng màn hình xuất ra:*
  ```text
  # Tự đo — seed 5007
  - Số lỗi nộp: 10
  - F1 tổng ≈ 0.7 · lỗi luật ≈ 1.0 · lỗi gán nhãn ≈ —
  ```

---

### Pha 2: Tham gia Human Review cùng nhóm (0:55 - 1:50)
- **Nhiệm vụ của Duy**: Nhận danh sách 20% ứng viên đầu tiên từ `runs/r5007/candidates.json` do Hùng phân chia.
- Mở ảnh bằng tool:
  ```powershell
  py scripts/visualize_helper.py --run runs/r5007 --image <tên_ảnh>
  ```
- Ghi nhận vào `review_log.csv`:
  - Quan sát vật thể thực tế trong ảnh (phóng to nếu ảnh nhỏ).
  - Ghi nhận `confirmed` nếu phát hiện nhãn sai, hoặc `rejected` nếu chỉ là che khuất tự nhiên.
  - Ghi chú `note` $\ge 20$ ký tự: nói rõ thấy gì (ví dụ: `"mo anh xem ro: xe tai mui kin mau trang, detection ghi nham car"`).

---

### Pha 3 & 4: Điều phối & Giám sát Bàn giao v2 (1:50 - 2:45)
- Nhắc nhở **Đỗ Huy Kiên**:
  - Ghi quyết định HOLD vào `lineage.jsonl`:
    ```powershell
    py scripts/lineage.py record --event decision --release-id lab250_43f248381e9d --decision HOLD
    py scripts/lineage.py impact --release-id lab250_43f248381e9d
    ```
  - Tạo thư mục v2: `runs/r5007/handover/lab250_43f248381e9d_v2/` đủ 7 thành phần.
  - Đóng gói và kiểm tra:
    ```powershell
    py scripts/pack_release.py runs/r5007/handover/lab250_43f248381e9d_v2
    py scripts/lineage.py record --event release --release-id lab250_43f248381e9d_v2 --parent lab250_43f248381e9d
    py scripts/check_handover.py --run runs/r5007
    ```
  - Duy kiểm tra: Phải đạt PASS từ **H1 đến H15**.

---

### Pha 5 & 6a: Giám sát Truy vết & An toàn Thông tin (2:45 - 3:15)
- Nhắc nhở **Nguyễn Đức Cường**:
  - Hoàn thiện `runs/r5007/trace.json` (`tier_a`, `tier_b`, `notify`).
  - Hoàn thiện `runs/r5007/security.md` (3 tình huống gắn với lô).
- **Duy chạy lệnh nghiệm thu tổng thể**:
  ```powershell
  py scripts/check_handover.py --run runs/r5007
  ```
  **Yêu cầu tối thượng: Đạt 17/17 PASS (Tổng: 17 PASS, 0 FAIL)!**

---

### Pha 6b: Chỉ huy Tác chiến Đề ẩn 40 phút (3:15 - 3:55)
- Khi nhận đề ẩn từ giảng viên:
  1. Duy lập tức chạy lệnh quét lỗi luật:
     ```powershell
     py validator/validate.py <thu_muc_de_an>/delivery --out de_an/rules.json --candidates de_an/candidates.json
     ```
  2. Bắn file `candidates.json` cho cả 5 người, chia mỗi người xem 3-4 ảnh trong 15 phút.
  3. Gom file `review_log.csv`, chạy gộp:
     ```powershell
     py scripts/merge_review.py --rules de_an/rules.json --review de_an/review_log.csv --out de_an/errors.json
     ```
  4. Trích xuất `de_an/trace.json`.
  5. Xuất bài nộp:
     ```powershell
     py scripts/export_submission.py --run runs/r5007
     ```
  6. Git commit và push lên GitHub trước hạn chót 5 phút.

---

## 4. Cẩm nang Vấn đáp (Oral Defense Q&A) dành cho Nguyễn Bá Duy

Giảng viên sẽ chọn ngẫu nhiên 1 trong các câu hỏi sau để hỏi bạn trong 3 phút:

### Câu 1: Giải thích đoạn code bắt lỗi `wrong_hash` và vì sao không được chỉ kiểm tra định dạng độ dài 64 ký tự?
> **Trả lời:**  
> "Trong `validator/validate.py`, hàm `sha256_file` đọc toàn bộ mảng byte của file ảnh trên đĩa và gọi `hashlib.sha256()`. Sau đó so khớp chuỗi hex với `item['image_sha256']` khai báo trong `manifest.json`.  
> Lý do không thể chỉ kiểm tra độ dài 64 ký tự là vì lỗi gài `wrong_hash` sử dụng mã SHA256 hoàn toàn hợp lệ về mặt định dạng (64 ký tự hex), nhưng là mã băm của một file ảnh khác trong lô! Nếu chỉ regex độ dài 64 ký tự thì sẽ bỏ sót 100% lỗi này. Việc tính lại hash thực tế là nguyên tắc cốt lõi để bảo đảm tính toàn vẹn dữ liệu (Data Integrity)."

### Câu 2: Giải thích giải thuật phát hiện `duplicate_box` và vì sao không được dùng ngưỡng IoU thấp?
> **Trả lời:**  
> "Trong bộ dữ liệu COCO thực tế, có rất nhiều vật thể tự nhiên chồng lấn lên nhau (ví dụ: người ngồi cạnh nhau, các đồ vật trên bàn ăn) với IoU tự nhiên có thể lên tới 0.66. Nếu ta dùng ngưỡng IoU thấp (như 0.6 hay 0.7), ta sẽ báo nhầm rất nhiều box tự nhiên là lỗi duplicate (bị trừ điểm F1 nặng vì báo thừa).  
> Giải thuật của em kiểm tra: Hai box phải cùng `class_id`, kích thước chiều rộng và chiều cao gần như tuyệt đối bằng nhau ($|w_1 - w_2| < 10^{-4}$ và $|h_1 - h_2| < 10^{-4}$), và độ lệch tâm chỉ trong khoảng 1-2 pixel ($|x_1 - x_2| \le 2.5/W$ và $|y_1 - y_2| \le 2.5/H$). Đây chính xác là hành vi nhân bản box bị gài."

### Câu 3: Giải thích lỗi `thing_overlap` trong Panoptic và cách phát hiện?
> **Trả lời:**  
> "Lỗi `thing_overlap` xảy ra khi một vật thể (donor) bị một vật thể khác (receiver) đè lên chiếm mất điểm ảnh trên mask PNG, nhưng thuộc tính diện tích `area` trong `panoptic.json` của vật thể donor vẫn giữ nguyên con số cũ.  
> Để phát hiện, em dùng `pngutil.read_rgb()` để giải mã mask PNG, đếm số lượng pixel thực tế của từng `segment_id`. Nếu `area` khai báo trong JSON lớn hơn số pixel thực tế đếm được từ $\ge 10$ pixel, em xác định đây là lỗi `thing_overlap`."

### Câu 4: Nếu giảng viên yêu cầu: "Hãy sửa validator để chấp nhận box tràn viền tới 3% thay vì 1%", bạn sửa ở đâu?
> **Trả lời:**  
> "Dạ, em vào hàm `validate_rules()` trong file `validator/validate.py`, tìm đoạn kiểm tra `bbox_out_of_bounds`.  
> Hiện tại điều kiện đang là:  
> `if x - w/2 < -0.01 or y - h/2 < -0.01 or x + w/2 > 1.01 or y + h/2 > 1.01:`  
> Em sẽ sửa hằng số `-0.01` thành `-0.03` và `1.01` thành `1.03`."

### Câu 5: `scene_leak` có target là gì và tại sao lại nguy hiểm trong Machine Learning?
> **Trả lời:**  
> "Target của `scene_leak` là `scene_id` (ví dụ `scene_123`), không phải tên ảnh.  
> Lỗi này cực kỳ nguy hiểm vì nó vi phạm nguyên tắc độc lập giữa tập Train và Validation. Các ảnh trong cùng một cảnh thường có chung góc chụp, ánh sáng và bối cảnh. Nếu một cảnh xuất hiện ở cả Train và Val, mô hình sẽ 'học vẹt' bối cảnh thay vì học đặc trưng tổng quát của vật thể, dẫn đến việc độ chính xác khi đánh giá trên tập Val bị thổi phồng giả tạo (Data Snooping / Leakage)."

---

## 5. Kế hoạch Git Commit của Nguyễn Bá Duy

Để đạt trọn 4 điểm phần Commit cá nhân, Duy cần thực hiện 2 commits bằng tài khoản cá nhân:

```powershell
# Commit 1 (P1): Sau khi viết xong validator và test rules
git add validator/validate.py
git commit -m "P1 (Duy): Implement core rule validator in validator/validate.py catching 9 rule fault types"

# Commit 2 (P2): Sau khi tham gia review và hoàn thiện kiểm định
git add submission/TEAM.md docs/HUONG_DAN_NGUYEN_BA_DUY.md
git commit -m "P1-P2 (Duy): Verify rule F1=1.0 on r5007 and calibrate on clean set, update team docs"

# Push lên GitHub
git push origin main
```
