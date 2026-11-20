# Bảo mật khi làm việc

## 1. Ca USB: hết giờ, muốn chép lô về nhà làm tiếp
Tuyệt đối không được sao chép dữ liệu dataset ra thiết bị lưu trữ ngoài như USB cá nhân, ổ cứng di động, hoặc gửi qua email cá nhân/cloud cá nhân (Google Drive, Zalo, Telegram). Dữ liệu huấn luyện của dự án là tài sản sở hữu trí tuệ và có thể chứa các thông tin bảo mật/riêng tư chưa được công bố. Việc gửi qua email cá nhân hoặc nhờ người ngoài làm hộ vi phạm nghiêm trọng cam kết bảo mật NDA và chính sách quản trị dữ liệu. Giải pháp đúng: báo cáo với team lead/quản lý dự án để xin gia hạn thời gian làm việc trên máy trạm của công ty, hoặc sử dụng kết nối VPN nội bộ có kiểm soát an ninh mạng của tổ chức.

## 2. Năm việc: được hay không
1. Mở job được giao trên máy công ty: ĐƯỢC. Đây là môi trường làm việc chuẩn hóa, được quản lý thiết bị và bảo mật mạng an toàn theo quy định.
2. Chụp màn hình gửi người quen: KHÔNG ĐƯỢC. Chụp màn hình phát tán hình ảnh dataset ra bên ngoài làm lộ dữ liệu chưa release và vi phạm thỏa thuận bảo mật dữ liệu.
3. Chép lô ra USB: KHÔNG ĐƯỢC. Sao chép dữ liệu ra thiết bị ngoài tiềm ẩn nguy cơ thất thoát dữ liệu, lây nhiễm mã độc và vi phạm chính sách Data Loss Prevention (DLP).
4. Dán nhãn thật lên chatbot công cộng: KHÔNG ĐƯỢC. Các chatbot công cộng có thể lưu log prompt vào máy chủ bên thứ ba để huấn luyện mô hình của họ, gây rò rỉ dữ liệu gán nhãn độc quyền.
5. Đưa tài khoản CVAT cho đồng nghiệp: KHÔNG ĐƯỢC. Mỗi người gắn với định danh annotator/reviewer cụ thể để truy vết trách nhiệm và tính lương; chia sẻ tài khoản làm mất tính toàn vẹn của audit log và vi phạm Access Control.

## 3. Ca khuôn mặt: thấy mặt người rõ trong lô, guideline yêu cầu làm mờ
Khi phát hiện khuôn mặt người nhìn rõ trong lô ảnh (ví dụ ảnh `000000017207` và `000000001993` có hình ảnh người đi bộ rõ mặt), quyết định bắt buộc đối với lô là kết luận HOLD toàn bộ lô dữ liệu. Người gán nhãn không được tự ý xóa ảnh hoặc tự dùng phần mềm ngoài làm mờ ảnh vì sẽ làm sai lệch cấu trúc dataset, hỏng mask phân đoạn và sai lệch mã hash SHA256 trong manifest. Cần giữ nguyên hiện trạng, ghi nhận sự kiện vi phạm quyền riêng tư và báo ngay cho Quản lý dự án (Project Manager) cùng bộ phận Data Governance để áp dụng quy trình xử lý ẩn danh hóa đạt chuẩn GDPR/Privacy trước khi lô được release.
