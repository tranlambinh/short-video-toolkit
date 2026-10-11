# Nguồn và giấy phép của các thành phần

Mã trong repo này do người tạo repo viết. Các thành phần bên dưới thuộc về chủ sở hữu của chúng; hãy tự đọc giấy phép trước khi dùng thương mại.

| Thành phần | Dùng để | Ghi chú |
|---|---|---|
| [short-video-maker](https://github.com/gyoridavid/short-video-maker) (Docker image `gyoridavid/short-video-maker`) | tìm và dựng clip stock | giấy phép của dự án đó; repo chỉ có file vá `patch/PortraitVideo.js` để ẩn phụ đề của nó |
| [Pexels](https://www.pexels.com/license/) | ảnh/clip stock | cần khóa API riêng; ghi nhận nguồn theo điều khoản Pexels |
| [edge-tts](https://github.com/rany2/edge-tts) | giọng đọc Việt/Anh | dùng dịch vụ đọc của Microsoft Edge qua mạng; không có bảo đảm dịch vụ luôn sẵn sàng |
| [Piper](https://github.com/rhasspy/piper) và các giọng `vi_VN` (vais1000, 25hours_single, vivos) | giọng đọc offline | tải từ `rhasspy/piper-voices`; xem giấy phép từng giọng tại đó |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) và model `Systran/faster-whisper-medium` | nhận dạng giọng nói | MIT / giấy phép model trên Hugging Face |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp), [gdown](https://github.com/wkentaro/gdown) | tải video | chỉ tải video bạn có quyền dùng lại |
| [Playwright](https://playwright.dev/), [trafilatura](https://github.com/adbar/trafilatura) | chụp và trích nội dung bài báo | |
| [OpenCV](https://opencv.org/), [Pillow](https://python-pillow.org/), [NumPy](https://numpy.org/) | xử lý hình | |
| FFmpeg | dựng và ghép video | |

**Nhạc nền:** repo không kèm nhạc. Bạn tự chọn nhạc miễn phí bản quyền (xem `assets/music/README.md`).

**Nội dung bài báo:** `/news-video` chụp trang và tóm tắt bằng lời mới, luôn ghi nguồn; nên xin phép tòa soạn nếu dùng thương mại hoặc đăng thường xuyên.
