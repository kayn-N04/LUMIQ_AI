# LUMIQ AI — Dịch vụ tạo ảnh áo

Ứng dụng FastAPI tạo ảnh áo bằng AI, có giao diện tiếng Việt để tải ảnh áo, họa tiết,
chọn màu và xem kết quả. API cũng có thể được tích hợp với React/Laravel.

## Chạy cục bộ

```powershell
python -m venv .venv
# Chỉ sao chép mẫu nếu chưa có .env; không ghi đè cấu hình đang dùng.
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Điền CF_ACCOUNT_ID và CF_API_TOKEN trong .env. Không công khai file này.
Mở http://127.0.0.1:7860 để sử dụng giao diện hoặc /docs để thử API bằng Swagger UI.
Máy chủ mặc định chỉ lắng nghe 127.0.0.1:7860.

## API hiện có

| Method | Endpoint | Chức năng |
| --- | --- | --- |
| GET | / | Thông tin dịch vụ |
| GET | /health | Trạng thái tiến trình, không kiểm tra kết nối/model Cloudflare |
| GET | /api/colors | Danh sách tên màu và mã HEX; giữ nguyên có HEX null |
| POST | /api/generate | Tạo ảnh, nhận multipart/form-data |
| GET | /outputs/{name} | Đọc ảnh PNG đã tạo |
| GET | /docs | Tài liệu tương tác |

POST /api/generate nhận shirt và pattern (file bắt buộc); garment_color (mặc định Giữ nguyên);
center_x=50, center_y=45, print_width=25, rotation=0. Tọa độ 0–100%,
độ rộng 1–100%, góc xoay -180–180 độ theo chiều kim đồng hồ.
Màu lấy đúng tên từ /api/colors. PNG/JPEG/WebP, mỗi file tối đa 10 MB và 25 megapixel.

Phản hồi thành công:

```json
{"image_url":"/outputs/ao-xxxxxxxxxxxx.png","status":"Hoàn tất"}
```

image_url là đường dẫn tương đối của dịch vụ AI. Laravel phải tải ảnh từ dịch vụ
và lưu vào storage của website hoặc chuyển tiếp ảnh cho React; không đưa địa chỉ
127.0.0.1 của server vào giao diện khách hàng.

Lỗi xử lý dùng trường error; lỗi validation mặc định FastAPI dùng detail.
HTTP 400: dữ liệu không hợp lệ; 413: file quá lớn; 422: validation hoặc bộ lọc nhà cung cấp;
502/503/504: nhà cung cấp, cấu hình hoặc kết nối; 500: lỗi nội bộ.

## Luồng xử lý

1. Kiểm tra lựa chọn và ảnh đầu vào.
2. U2Netp qua rembg tách nền họa tiết khi cần, giữ khung ảnh.
3. Pillow tạo bố cục một họa tiết ở vị trí đã chọn.
4. Prompt yêu cầu hình in duy nhất, màu vải đã chọn, nền trắng và giữ form áo.
5. Cloudflare tạo ảnh; lưu PNG trong output/ và xóa dữ liệu tạm.

Ảnh gửi Cloudflare tối đa cạnh dài 1024 px; ảnh chạy tách nền tối đa 2048 px.
CF_OUTPUT_WIDTH/HEIGHT mặc định 512 x 512. AI có thể làm lệch chi tiết, màu hoặc form áo.

## Tích hợp tiếp theo

API tạo ảnh hiện xử lý đồng bộ. Laravel nên quản lý queue, người dùng, hạn mức,
trạng thái thiết kế và quyền xem ảnh. Dịch vụ này chưa có xác thực, giới hạn lượt
hay hàng đợi; giữ nó trong mạng nội bộ trước khi bổ sung bảo vệ cho bản production.
Không cần CORS nếu React chỉ gọi Laravel và Laravel gọi FastAPI.

## Cấu trúc

- app.py: HTTP API.
- templates/ và static/: giao diện web.
- services/: điều phối, tách nền, bố cục, prompt và Cloudflare.
- tests/: kiểm thử hồi quy API, bố cục/xoay họa tiết, màu áo, cache và giới hạn xử lý;
  chạy bằng `.\.venv\Scripts\python.exe -m unittest discover -s tests`, không gọi Cloudflare thật.
- .models/: model CPU đã tải; .venv/: môi trường Python.
- output/: ảnh thành phẩm; .env: cấu hình bí mật.

## Giấy phép

MIT, xem LICENSE. Model, thư viện và dịch vụ Cloudflare có điều khoản riêng.

## Chế độ Giữ nguyên

Ảnh đầu ra dùng ảnh áo gốc ở độ phân giải gốc, chỉ thay pixel có alpha của họa tiết mới.
Cloudflare vẫn chạy để gợi ý sáng tối cho hình in. Chỉ lấy thay đổi độ sáng đã làm mượt,
giới hạn tối đa 3 mức RGB trên họa tiết; không sao chép màu vải hoặc hình do AI vẽ lại.
Vì vậy màu vải, form áo, logo cũ và nền bên ngoài họa tiết được giữ nguyên pixel.
Chế độ này không uốn hình in theo phối cảnh do AI tự tạo. Dùng ảnh áo nền trắng nếu cần
thành phẩm nền trắng: giữ nguyên không tự thay phông nền của ảnh gốc.
Các lựa chọn màu khác tiếp tục dùng ảnh Cloudflare trả về, yêu cầu nền trắng bằng prompt.

## Hiệu năng

- Cache tách nền theo nội dung file, tối đa 8 ảnh/32 MB RAM mỗi tiến trình; tự xóa khi dừng dịch vụ. Không cache ảnh tạo bởi Cloudflare.
- Tái sử dụng kết nối HTTP Cloudflare, không tự gửi lại yêu cầu lỗi.
- Giới hạn 2 tác vụ tạo ảnh đồng thời mỗi tiến trình; yêu cầu vượt giới hạn nhận 429 và Retry-After: 5. Laravel nên xếp hàng và thử lại có giới hạn.
- PNG trung gian dùng nén nhanh không mất dữ liệu; bước bảo toàn áo giảm ảnh RGBA trung gian và chia nhỏ xử lý mảng.
- Thời gian sinh ảnh trên Cloudflare vẫn phụ thuộc nhà cung cấp; cache chỉ tăng tốc xử lý cục bộ cho họa tiết đã dùng.
