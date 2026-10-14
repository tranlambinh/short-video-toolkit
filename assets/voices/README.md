# Giọng nhân bản (VieNeu-TTS)

Đặt ở đây file ghi âm giọng muốn nhân bản, rồi dùng `--voice vieneu-clone`.

- Tên file mặc định: `clone.wav` (khóa `vieneu-clone` trong `voices.json`). Muốn có nhiều giọng thì thêm khóa mới với `"engine": "vieneu", "ref_audio": "assets/voices/<file>.wav"`.
- Độ dài 3-8 giây, một người nói, rõ lời, ít tiếng ồn, không nhạc nền. VieNeu tự lọc ồn và cắt còn 8 giây.
- Sau khi thêm, chạy `python voice_demo.py --check vieneu-clone` để nghe thử và xem cao độ trung bình (F0); ghi số đó vào `"f0"` của khóa để lên/xuống giọng theo câu cho chuẩn.
- Chỉ nhân bản giọng của bạn hoặc của người đã đồng ý. File ở thư mục này không được đưa lên git.
