# Bảo mật khi làm việc

> Gắn với lô `lab250_43f248381e9d` (seed 5007, 250 ảnh COCO) và lô v2 nhóm vừa bàn giao. Người viết: Nguyễn Đức Cường.

## 1. Ca USB: hết giờ, muốn chép lô về nhà làm tiếp
Không chép lô ra USB hay ổ cá nhân. Lô 5007 có ảnh người thật nhìn rõ mặt (ví dụ `000000004395`, `000000001296`), nên mang ra khỏi máy công ty là để lộ dữ liệu cá nhân và vi phạm hợp đồng bảo mật. USB dễ mất, không mã hoá, và không ai ghi lại được bản sao đó đã đi đâu.
Gửi lô về email cá nhân cũng sai vì dữ liệu rời khỏi hệ thống công ty và nằm lại trên máy chủ thư bên ngoài. Nhờ người khác làm hộ còn sai hơn: người đó không được giao job, không ký cam kết, và lineage sẽ ghi sai người gán/kiểm.
Cách đúng: dừng ở đúng chỗ đang làm, ghi tiến độ vào job (ví dụ "đã review xong ứng viên 1–15 của r5007"), bàn giao cho ca sau qua kênh chính thức. Nếu thật sự cần làm tiếp ngoài giờ thì xin quản lý cấp quyền truy cập từ xa qua máy/VPN của công ty, dữ liệu vẫn ở trong hệ thống.

## 2. Năm việc: được hay không
- **Mở job được giao trên máy công ty: Được.** Đúng người, đúng job, đúng thiết bị; mọi thao tác đều có log, và đó là điều kiện để `truyvet.csv` ghi đúng annotator/reviewer.
- **Chụp màn hình gửi người quen: Không được.** Ảnh chụp màn hình vẫn là bản sao dữ liệu (có thể có mặt người, như ảnh `000000001296`), rời khỏi hệ thống và không thu hồi được.
- **Chép lô ra USB: Không được.** Lý do như mục 1: mất kiểm soát bản sao, dễ thất lạc, không có log.
- **Dán nhãn thật lên chatbot: Không được.** Chatbot công cộng là bên thứ ba, có thể lưu hoặc dùng dữ liệu để huấn luyện. Ở lab này ảnh COCO là công khai nên nhóm được hỏi AI và đã ghi vào `prompts.md`; với dữ liệu dự án thật thì không.
- **Đưa tài khoản CVAT cho đồng nghiệp: Không được.** Tài khoản gắn với một người; dùng chung thì log và lineage ghi sai người làm, khi có ticket (như ticket lớp `cup` của lô này) sẽ không biết phải báo ai. Đồng nghiệp cần việc thì nhờ quản lý giao job cho tài khoản của họ.

## 3. Ca khuôn mặt: thấy mặt người rõ trong lô, guideline yêu cầu làm mờ
Trong lô 5007 có ảnh mặt người nhìn rõ, chưa được làm mờ:
- `000000004395` (scene_225, job J02, người gán A05, người kiểm Q01): chân dung một người đàn ông mặc sơ mi trắng thắt cà vạt, mặt chiếm phần lớn khung hình.
- `000000001296` (scene_694, job J01, người gán A01, người kiểm Q03): cận mặt một phụ nữ đang cầm điện thoại, nhìn rõ mắt, mũi, miệng.

Việc cần làm: **Hold** lô (không Release, không đưa cho team AI train), ghi lại tên các ảnh vi phạm, và **báo người phụ trách** dự án (và người phụ trách bảo vệ dữ liệu nếu có) qua kênh chính thức.
Không tự làm mờ hay xoá ảnh vì:
- sửa ảnh làm đổi sha256, lệch manifest và phá lineage;
- che mất lỗi gốc ở khâu ẩn danh hoá, nên các lô sau vẫn lặp lại lỗi đó;
- người kiểm không có quyền quyết định cách xử lý dữ liệu cá nhân.
Bản đã làm mờ phải là một lô mới có lô cha (v1 → v2), do người có thẩm quyền xử lý theo quy trình.
