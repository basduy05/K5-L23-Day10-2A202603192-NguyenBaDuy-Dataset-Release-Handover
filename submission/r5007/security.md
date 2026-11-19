# Báo cáo Tuân thủ Bảo mật Dữ liệu

> Áp dụng trực tiếp cho lô bàn giao `lab250_43f248381e9d` (Seed 5007), tuân thủ quy chuẩn quản trị và bảo vệ dữ liệu doanh nghiệp.

## 1. Ca USB: hết giờ, muốn chép lô về nhà làm tiếp
- **Hành động cần làm:** Tuyệt đối không cắm USB cá nhân, không tải dữ liệu lên Google Drive cá nhân, và không gửi file qua email cá nhân để mang về nhà làm. Cần lưu lại tiến độ công việc trên hệ thống nội bộ công ty, báo cáo với Team Lead xin phép gia hạn thời gian làm việc hoặc xin phê duyệt sử dụng giải pháp VPN / Remote Desktop có kiểm soát an ninh của công ty nếu cần làm việc từ xa.
- **Lý do:** Dữ liệu dự án là tài sản bảo mật của tổ chức, việc sao chép ra thiết bị cá nhân hoặc chuyển qua kênh mạng không an toàn vi phạm nghiêm trọng chính sách bảo mật thông tin (Data Loss Prevention - DLP), có nguy cơ làm rò rỉ dữ liệu thương mại, lộ thông tin khách hàng và dẫn đến trách nhiệm pháp lý cá nhân. Nhờ người ngoài làm hộ cũng là hành vi chia sẻ trái phép dữ liệu nội bộ cho bên thứ ba không có cam kết bảo mật NDA.

## 2. Năm việc: được hay không
1. **Mở job được giao trên máy công ty:** **ĐƯỢC**. Đây là môi trường làm việc chuẩn hóa, được kiểm soát bởi các chính sách an toàn thông tin của công ty.
2. **Chụp màn hình gửi người quen:** **KHÔNG ĐƯỢC**. Hành vi này vi phạm thỏa thuận bảo mật NDA, làm lộ dữ liệu hình ảnh, chú thích và thông tin dự án ra bên ngoài.
3. **Chép lô ra USB:** **KHÔNG ĐƯỢC**. Thiết bị lưu trữ ngoài tiềm ẩn nguy cơ lây nhiễm mã độc, thất lạc phần cứng và làm thất thoát tài sản dữ liệu của doanh nghiệp.
4. **Dán nhãn thật lên chatbot công cộng:** **KHÔNG ĐƯỢC**. Các dịch vụ AI công cộng (như ChatGPT, Claude bản miễn phí) có thể sử dụng dữ liệu đầu vào của người dùng để tái huấn luyện mô hình, làm rò rỉ toàn bộ dữ liệu nhãn nội bộ lên internet.
5. **Đưa tài khoản CVAT cho đồng nghiệp:** **KHÔNG ĐƯỢC**. Tài khoản CVAT gắn liền với định danh cá nhân (annotator/reviewer ID) phục vụ kiểm toán chất lượng (Audit Trail). Cho mượn tài khoản sẽ phá vỡ tính trách nhiệm và tính toàn vẹn của dữ liệu truy vết.

## 3. Ca khuôn mặt: thấy mặt người rõ trong lô, guideline yêu cầu làm mờ
- **Quyết định chất lượng:** **HOLD toàn bộ lô dữ liệu**. Báo cáo ngay lập tức cho Team Lead, Quản lý dự án và Cán bộ Bảo vệ Dữ liệu (DPO - Data Protection Officer).
- **Lý do không tự ý làm mờ hay xóa file:** 
  1. File ảnh đã được đóng gói và niêm phong bằng mã băm SHA256 trong `manifest.json`. Việc tự ý mở ảnh chỉnh sửa điểm ảnh (pixel) hoặc xóa tệp sẽ làm thay đổi mã SHA256, phá vỡ tính toàn vẹn (Data Integrity) và khiến toàn bộ quy trình kiểm toán dòng dõi thất bại.
  2. Việc tự sửa cục bộ sẽ che giấu lỗi hệ thống tại khâu tiền xử lý ẩn danh hóa tự động (Anonymization Pipeline), khiến các lô dữ liệu sau này tiếp tục lặp lại lỗi vi phạm quyền riêng tư.
- **Minh chứng cụ thể trong lô:** Ảnh `000000000139` trong thư mục `runs/r5007/delivery/images/000000000139.jpg` có chứa hình ảnh người với khuôn mặt hiển thị rõ nét, chưa được làm mờ theo đúng quy định bảo vệ dữ liệu cá nhân.
