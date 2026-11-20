# Trạng thái review đề ẩn — chưa phải bài nộp cuối

Release: `lab250_62d7641abb98`. Hiện nhận 4 dòng confirmed do Hoàng Nhật Anh — 2A202603813 xuất sau khi xem ảnh. Bản riêng để đối chiếu nằm tại `../reviews/nhat_anh.csv`.

| Ảnh | Loại lỗi người xem chốt |
|---|---|
| img_0061 | category_swap |
| img_0062 | category_swap |
| img_0079 | missing_box |
| img_0086 | class_swap |

Riêng `img_0062`, người xem xác nhận thêm qua trao đổi rằng cả hai xe đang xét là truck. Ghi chú CSV đã bỏ câu còn chờ phóng to/chốt. `img_0086` giữ verdict confirmed từ CSV gốc, làm rõ kết luận thay câu ghi chú còn chờ chốt. Không thêm kết luận của thành viên khác.

`rules.json` có 12 lỗi luật. `candidates.json` giữ nguyên bản 206 tín hiệu trên 98 ảnh đã dùng cho trang review. Kế hoạch chia 19 ảnh chỉ là một phần hàng đợi: cần người điều phối giải quyết các ảnh/tín hiệu còn lại, không coi những tín hiệu ngoài 19 ảnh tự động là rejected.

Còn thiếu kết quả các ảnh phân công cho Duy (0006, 0028, 0036, 0045), Hùng (0115, 0117, 0120, 0131), Kiên (0145, 0146, 0169, 0171), Cường (0226, 0238, 0245), cùng việc rà soát phần hàng đợi ngoài kế hoạch. Mọi confirmed/rejected phải do người xem quyết định, ghi rõ người xem và bằng chứng nhìn thấy.

Đã thử gộp 12 lỗi luật + 4 lỗi đã xác nhận thành 16 mục trong file **cục bộ** `runs/de_an/errors.nhat_anh.partial.json`. Chưa đặt thành `errors.json` cuối trong thư mục nộp. Khi nhóm đã tổng hợp review đầy đủ, người điều phối chạy từ gốc repo:

```powershell
py -X utf8 scripts/merge_review.py --rules submission/de_an/rules.json --review submission/de_an/review_log.csv --out submission/de_an/errors.json
```

Kiểm tra từng lỗi ngữ nghĩa trong errors có dòng confirmed tương ứng và ghi chú đủ bằng chứng trước khi nộp.
