# Nhạc nền

Repo **không kèm nhạc**. Hãy tự chọn nhạc miễn phí bản quyền và bỏ file `.mp3` (hoặc `.m4a`, `.wav`) vào thư mục này.

Nguồn gợi ý (đọc kỹ giấy phép từng bài, nhất là khi đăng thương mại):
- YouTube Audio Library (studio.youtube.com → Audio Library)
- Pixabay Music (pixabay.com/music)
- Free Music Archive (freemusicarchive.org)

Cách chương trình chọn nhạc:
1. Nếu `profiles.json` hoặc kịch bản ghi tên một file (trường `music`) và file đó có ở đây, dùng đúng file đó.
2. Không có thì dùng file nhạc đầu tiên (theo thứ tự tên) trong thư mục này.
3. Thư mục trống thì video chỉ có giọng đọc, không nhạc (chế độ `--mode music` sẽ báo lỗi vì cần nhạc).

Đặt nhạc riêng cho từng thể loại: sửa mục `music` trong `profiles.json` thành tên file của bạn.
