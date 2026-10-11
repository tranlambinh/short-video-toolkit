---
description: Chỉnh sửa video có sẵn: cắt, ghép (có chuyển cảnh), tăng/giảm tốc, mờ dần, zoom chậm, chèn logo
argument-hint: <đường dẫn video> [mô tả chỉnh sửa, ví dụ "cắt 5-40 giây, thêm logo góc trái trên, mờ dần cuối"]
---

Yêu cầu chỉnh sửa: $ARGUMENTS

Dùng `edit_video.py` (ffmpeg) ở thư mục dự án. Không bao giờ sửa file gốc; luôn ghi file mới vào `videos/edited/` (đặt tên dễ hiểu, ví dụ `<tên>-edit.mp4`).

## Cách làm
1. Xác định các video đầu vào và việc cần làm. Nếu thiếu thông tin quan trọng (đường dẫn logo, khoảng thời gian cắt, vị trí logo) thì hỏi lại ngắn gọn, đừng đoán.
2. Chạy lệnh (ghép các tùy chọn cần thiết):
```
python edit_video.py <video1> [video2 ...] -o videos/edited/<tên>.mp4 [tùy chọn]
```
| Việc cần làm | Tùy chọn |
|---|---|
| Cắt đoạn | `--trim 5-40` (mỗi video một `--trim` theo thứ tự, `-` = giữ nguyên; thời gian dạng `12.5`, `1:05`) |
| Ghép nhiều video | liệt kê nhiều file; thêm `--transition 0.6` để chuyển cảnh mờ |
| Đổi kích thước | `--size 1080x1920` (dọc, TikTok/Reels/Shorts), `--fit cover` (cắt tràn khung, mặc định) hoặc `contain` (viền đen) |
| Tốc độ | `--speed 1.2` (0.5 đến 4) |
| Mờ dần vào/ra | `--fade-in 0.5 --fade-out 0.8` (cả hình và tiếng) |
| Zoom chậm | `--zoom 1.12` (phóng từ 1.0x lên 1.12x suốt video; chậm trên video dài) |
| Hàng loạt (nhiều video, cùng cài đặt) | `--batch` kèm thư mục hoặc ký tự đại diện, ví dụ `python edit_video.py --batch "videos/clips/ten/*.mp4" -o videos/edited/ten --logo logo.png --suffix logo` |
| Chèn logo | `--logo logo.png --logo-pos tl|tr|bl|br|c --logo-size 14 --logo-opacity 0.9 --logo-margin 40`; chỉ hiện một đoạn: `--logo-from 0 --logo-to 5` |
3. Kiểm tra kết quả: đọc dòng kết quả của script (kích thước, thời lượng), rồi lấy vài khung hình bằng ffmpeg (đầu, giữa, cuối, chỗ chuyển cảnh) và xem. Báo thẳng nếu có gì lạ (logo bị che, hình bị cắt mất chủ thể, âm thanh mất).
4. Báo đường dẫn file kết quả và hỏi tôi có muốn gửi sang điện thoại không (giới hạn gửi 30 MB; nếu file lớn hơn thì nén một bản sao bằng ffmpeg, ví dụ `-b:v 3M`).

## Lưu ý
- Logo nên là PNG nền trong. Trên TikTok/Reels, góc trên phải và vùng đáy hay bị giao diện che; góc trái trên thường an toàn hơn.
- Video đã có phụ đề cứng (burned-in) thì không gỡ được; chèn thêm chữ sẽ chồng lên.
- Để thêm phụ đề tự động vào video có tiếng nói, dùng `/auto-subtitle`.

## Làm hàng loạt (nhiều video một lần)
Thêm `--batch`: mỗi đầu vào (file, thư mục, hoặc dạng `videos/clips/ten/*.mp4`) được xử lý riêng với **cùng một bộ cài đặt** (logo, mờ dần, zoom...), `-o` lúc đó là **thư mục** kết quả và mỗi file có thêm đuôi `-<suffix>` (mặc định `-edit`, ví dụ `--suffix logo` ra `clip-01-logo.mp4`). Không ghép các video với nhau và không dùng `--trim` khi chạy `--batch`.
- File lỗi hoặc không tồn tại chỉ bị báo, các file còn lại vẫn chạy; cuối cùng in số file thành công và thất bại.
- Thời gian khoảng 30 giây mỗi video ngắn (vài chục giây); video càng dài càng lâu, vì mỗi file được mã hóa lại.
- Chèn logo hàng loạt: `python edit_video.py --batch "<thư mục hoặc mẫu>" -o <thư mục kết quả> --logo logo.png --logo-pos tl --logo-size 14 --suffix logo`.
