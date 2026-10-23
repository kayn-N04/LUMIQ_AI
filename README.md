# LUMIQ AI — Thiết kế ảnh áo bằng AI

## Chạy

```powershell
git clone https://github.com/kayn-N04/LUMIQ_AI.git
cd LUMIQ_AI
python -m venv .venv
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Cấu hình CF_ACCOUNT_ID, CF_API_TOKEN trong .env (không chia sẻ token).
Model mặc định: @cf/black-forest-labs/flux-2-klein-4b.
CF_OUTPUT_WIDTH và CF_OUTPUT_HEIGHT điều khiển kích thước đầu ra, mặc định 512 x 512.
Mở http://127.0.0.1:7860. Sau khi sửa code phải dừng và khởi động lại máy chủ.

## Quy trình

1. Tải ảnh áo và họa tiết, chỉnh vị trí/kích thước dự kiến.
2. Chọn Giữ nguyên, Đen (#171717), Đỏ (#C62828), Xanh navy (#14213D), Xanh mint (#A8DCC8) hoặc Be nhạt (#E8DCC6). Bảng màu được định nghĩa tại services/prompt_builder.py và dùng chung cho web/CLI.
3. Khi nhấn tạo ảnh: rembg/U2Netp tách nền họa tiết trên CPU; PNG đã có alpha được giữ nguyên khung ảnh. Lần đầu tải model vào .models/, các lần sau tái sử dụng model trong bộ nhớ.
4. Đặt đúng một họa tiết đã tách nền lên ảnh áo bằng cùng công thức vị trí/kích thước như bản xem trước. Gửi bố cục này và ảnh họa tiết tham chiếu tới Cloudflare. Prompt yêu cầu hoàn thiện hình in đã có, không thêm bản sao, và đổi màu riêng vải áo. Mỗi yêu cầu gọi tạo ảnh một lần, không tự thử lại hoặc chuyển sang ghép ảnh.
5. Lưu ảnh AI trả về trong output/ và cung cấp nút tải PNG. Xóa các ảnh đầu vào tạm sau xử lý.

Bản xem trước chỉ là phác vị trí: chưa tách nền, đổi màu hoặc mô phỏng nếp vải.
Tọa độ tính theo phần trăm khung ảnh. Bố cục gửi AI giữ khung họa tiết sau tách nền để tránh lệch kích thước. Nên dùng áo trơn: hình in có sẵn trong ảnh gốc không được tự động xóa.
AI không bảo đảm nguyên vẹn chữ, màu HEX hoặc phông nền từng pixel. Kiểm tra thành phẩm trước khi sử dụng.
Tách nền tự động có thể bỏ sót chi tiết nhỏ; dùng PNG đã tách nền nếu kết quả không phù hợp.
Ảnh đầu vào tối đa 10 MB/25 megapixel; ảnh gửi AI giới hạn cạnh dài 1024 px.
Họa tiết cần tách nền được giới hạn 2048 px trước khi xử lý để giảm bộ nhớ.

## CLI

```powershell
.\.venv\Scripts\python.exe main.py --shirt "ao.png" --pattern "hoa-tiet.png" --x 50 --y 45 --width 25 --color "Xanh navy"
```

CLI dùng cùng luồng AI với web. --output chọn nơi lưu PNG.
services/image_layout.py chỉ tạo bố cục đầu vào cho AI.

## Kiểm tra

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Kiểm thử dùng API giả lập, không tốn lượt Cloudflare. Kiểm thử thực tế cần tài khoản có quyền Workers AI và kết nối mạng.
HTTP 400: ảnh/tham số không hợp lệ; 413: upload quá lớn; 422: bộ lọc nội dung; 502/503/504: lỗi dịch vụ/cấu hình/kết nối.

Ảnh đầu ra luôn được yêu cầu dùng nền trắng thuần #FFFFFF, không bóng đổ ngoài áo. Prompt giữ nguyên silhouette, cổ, vai, tay, thân, gấu, đường may, nếp vải và góc chụp từ ảnh đầu vào. Đây là ràng buộc gửi AI, không phải bảo đảm hình học từng pixel.

## Giấy phép

Mã nguồn dự án được phát hành theo MIT, xem LICENSE. Model AI, thư viện và dịch vụ Cloudflare áp dụng giấy phép và điều khoản riêng của bên cung cấp. Không đưa API token hoặc ảnh riêng vào repository.
