# Bộ công cụ làm short video dọc (TikTok / Reels / Shorts)

Sáu kỹ năng chạy trong **Claude Code**, gọi bằng lệnh `/...`. Video xuất ra dọc 1080×1920, có phụ đề karaoke tím chạy theo giọng đọc, chủ yếu cho tiếng Việt (có hỗ trợ tiếng Anh).

| Lệnh | Việc làm |
|---|---|
| `/short-video` | Chủ đề → bài fanpage → kịch bản → video có giọng đọc, nhạc, phụ đề |
| `/news-video` | Link bài báo (một hoặc nhiều) → video có ảnh chụp bài báo, hình minh họa, giọng đọc tóm tắt, chân trang nguồn |
| `/clip-video` | Video ngang dài 15-30 phút → nhiều short dọc theo các thông điệp chính, có tiêu đề chữ |
| `/auto-subtitle` | Video có tiếng nói → phụ đề karaoke (Việt/Anh), có soát lỗi và dịch |
| `/edit-video` | Cắt, ghép, chuyển cảnh, tốc độ, zoom, gắn logo (có chế độ hàng loạt) |
| `/dub-video` | Lồng tiếng: video tiếng Anh sang giọng đọc tiếng Việt, hoặc video tiếng Việt sang giọng đọc tiếng Anh (nguồn: file, YouTube, Google Drive) |

Hướng dẫn chi tiết từng lệnh, tham số và prompt mẫu: [`docs/SU-DUNG.md`](docs/SU-DUNG.md). Bản tương tác: mở `docs/huong-dan.html` bằng trình duyệt.

## Bạn cần có
- **Claude Code** đã đăng nhập (các bước viết bài, kịch bản, chọn clip do Claude làm).
- **Python 3.10-3.12**, **ffmpeg** (bản đầy đủ), **Docker Desktop**, trình duyệt Chrome (hoặc để script tự cài Chromium).
- Khóa **Pexels** miễn phí: <https://www.pexels.com/api/> (cho clip stock).
- Khoảng **5 GB** ổ đĩa trống (model nhận dạng giọng nói 1,5 GB, Docker image, cộng chỗ cho video).
- Mạng internet (giọng đọc edge-tts và tải clip cần mạng).

## Cài đặt

**1. Tải repo**
```bash
git clone <địa-chỉ-repo-riêng-tư> ShortVideo
cd ShortVideo
```

**2. Chạy script cài (cài thư viện Python, trình duyệt, model, Docker image)**

Windows (PowerShell):
```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```
macOS / Linux:
```bash
bash setup.sh
```
Script cần vài phút (phần lớn là tải model). Nếu thiếu `ffmpeg` hoặc Docker, nó báo cách cài; cài xong chạy lại.

**3. Điền khóa Pexels**: mở file `.env` (script đã tạo từ `.env.example`) và dán khóa vào sau `PEXELS_API_KEY=`.

**4. Thêm nhạc nền**: bỏ vài file `.mp3` miễn phí bản quyền vào `assets/music/` (xem [`assets/music/README.md`](assets/music/README.md)). Repo không kèm nhạc. Không có nhạc thì video chỉ có giọng đọc.

**5. Kiểm tra**
```bash
python check.py
```
Mọi dòng `OK` là sẵn sàng; dòng `FAIL` có kèm cách sửa, dòng `warn` là phần tùy chọn.

## Mỗi lần làm việc
Mở terminal trong thư mục repo, bật môi trường Python, rồi mở Claude Code:

Windows:
```powershell
.\.venv\Scripts\Activate.ps1
claude
```
macOS / Linux:
```bash
source .venv/bin/activate
claude
```
Mở Docker Desktop trước nếu dùng `/short-video` hoặc `/news-video`.

## Video đầu tiên
Trong Claude Code gõ:
```
/news-video https://vnexpress.net/<một-bài-báo-bất-kỳ>
```
Claude lấy bài, viết lời đọc và dừng để bạn duyệt; bạn trả lời "ok" thì nó dựng (5-8 phút). Video nằm ở `videos/news/<tên-bài>/`.

Vài ví dụ khác:
```
/short-video tâm sự: ai sẽ bên bạn khi mệt --trung_niên
/short-video góc nhìn: áp lực đồng trang lứa --trẻ
/short-video nhận định: https://vnexpress.net/<bài-báo> --trẻ
/short-video tranh luận: nên nói thẳng hay nói khéo --trẻ
/news-video <link báo nước ngoài> --voice male --audience trung_niên
/clip-video https://www.youtube.com/watch?v=<id> --to vi
/auto-subtitle D:\video\bai-giang.mp4 --lang vi
```

## Tùy chỉnh
- **Giọng đọc:** `voices.json` (đổi giọng, cao độ, tốc độ). Xem thử mọi giọng: `python voice_demo.py`.
- **Thể loại, đối tượng, nhạc, độ dài:** `profiles.json`.
- **Nhạc từng thể loại:** đổi tên file trong mục `music` của `profiles.json` thành file của bạn.
- **Giọng offline (không cần mạng):** `--voice vieneu-maianh` (VieNeu-TTS, nghe tự nhiên nhất, 7 giọng có sẵn và nhân bản giọng của bạn) hoặc `--voice piper-vais` (nhẹ, nhanh). Script cài đã tải sẵn; cài tay: `pip install vieneu` rồi `python setup_models.py --skip-whisper --piper --vieneu`.

## Xử lý lỗi thường gặp
| Hiện tượng | Cách xử lý |
|---|---|
| `Docker is running: FAIL` hoặc `short-video-maker did not come up` | Mở Docker Desktop, đợi nó báo đang chạy, thử lại. Xem log: `docker logs short-video-maker`. |
| `NoAudioReceived` khi tạo giọng | Dịch vụ giọng đọc đôi khi từ chối một câu; script tự thử lại với tốc độ khác, nên chờ thêm. |
| Video không có nhạc | Chưa có file trong `assets/music/`. |
| `/news-video` báo "nội dung ngắn" | Trang bị chặn hoặc có paywall; thử bài khác. |
| Lỗi font hoặc chữ vỡ phụ đề | Máy cần font Arial (Windows, macOS có sẵn; Linux: cài `ttf-mscorefonts-installer` hoặc font tương đương). |
| Tải YouTube lỗi | `pip install -U yt-dlp`; một số video cần trình chạy JavaScript (Deno) theo hướng dẫn của yt-dlp. |
| Nhận dạng giọng chậm | Chạy trên CPU nên khoảng 0,65-1,4 lần thời lượng video; video 30 phút mất 20-45 phút. |
| `python` không tìm thấy trong Claude Code | Bạn chưa bật môi trường (`.venv`) trước khi chạy `claude`. |

## Lưu ý
- **Chưa kiểm tra trên macOS và Linux:** mã đã bỏ các đường dẫn riêng của Windows, nhưng tác giả chỉ chạy thật trên Windows 11. Trên Mac chip Apple, Docker image của short-video-maker có thể chạy chậm (giả lập) hoặc lỗi; nếu gặp, báo lại người tạo repo.
- **Bản quyền:** chỉ làm với nội dung bạn có quyền dùng. `/news-video` chụp trang và tóm tắt bằng lời mới, luôn ghi nguồn; nên xin phép tòa soạn nếu dùng thương mại. Xem [`CREDITS.md`](CREDITS.md).
- **Chất lượng giọng:** các giọng được chỉnh bằng số đo cao độ và nhận dạng lại, người làm chưa nghe từng giọng; hãy nghe thử trước khi đăng.
- **Hình stock chỉ để minh họa**, có thể không sát nội dung; video tự gắn nhãn "Hình minh họa".

## Cấu trúc thư mục
`.claude/commands/` các lệnh · `*.py` mã chính · `voices.json`, `profiles.json` cấu hình · `docs/` hướng dẫn · `specs/examples/` kịch bản mẫu · `patch/` bản vá ẩn phụ đề của short-video-maker · `assets/music/` nhạc của bạn · `models/` model tải về · `work/` file trung gian · `videos/` thành phẩm · `posts/` bài đăng.
