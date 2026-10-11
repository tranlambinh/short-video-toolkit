---
description: Cắt nhiều short video dọc 9:16 từ một video ngang dài 15-30 phút; Claude đọc bản chép lời để tìm các thông điệp chính, bạn chọn clip nào làm, mỗi clip có tiêu đề chữ và phụ đề karaoke tím
argument-hint: <file | link YouTube | link Google Drive> [--lang vi|en|auto] [--to vi|en] [--len 30-60] [--layout blur|crop] [--title-seconds 4]
---

Yêu cầu: $ARGUMENTS

## Cú pháp
```
/clip-video <nguồn> [--lang vi|en|auto] [--to vi|en] [--len 30-60] [--layout blur|crop] [--title-seconds 4]
```
- **Nguồn:** đường dẫn file trên máy, link YouTube, hoặc link Google Drive (file phải chia sẻ ở chế độ "Anyone with the link"). Với file tải lên, bạn chỉ cần cho đường dẫn.
- `--lang`: ngôn ngữ trong video (mặc định `auto`; ghi rõ thì nhận dạng chuẩn hơn).
- `--to`: ngôn ngữ phụ đề và tiêu đề trên short. Không ghi thì giống ngôn ngữ trong video. Khác nhau (ví dụ video tiếng Anh, `--to vi`) thì Claude dịch phụ đề của các clip được chọn.
- `--len`: độ dài mỗi short, mặc định 30-60 giây.
- `--layout`: ép một kiểu khung cho mọi clip; không ghi thì Claude chọn theo nội dung (xem bên dưới).
- `--title-seconds`: tiêu đề hiện bao lâu ở đầu clip (mặc định 4 giây, `0` = suốt clip).

Chỉ làm với video của bạn hoặc video bạn có quyền dùng lại. Nhắc một lần ngắn nếu link YouTube trông không phải của người dùng; không từ chối vì chuyện đó.

## Quy trình (dừng chờ tôi chọn clip ở bước 3)

**Bước 1. Chuẩn bị** (chạy nền, lâu: nhận dạng khoảng 0,65-1,4 lần thời lượng video, nên 30 phút mất 20-45 phút):
```
python clip_video.py prepare "<nguồn>" --lang <vi|en|auto> [--name <tên-ngắn>]
```
Script tải video nếu là link, chép lời bằng Whisper medium, lưu `work/clips/<tên>/`: `transcript.json`, `transcript_for_llm.txt` (các đoạn đánh số `[12] 03:41-03:52 lời`) và `frames.png` (8 khung hình dọc theo video). Kết quả được lưu lại nên chạy lại rất nhanh; muốn nhận dạng lại thì thêm `--force`.

**Bước 2. Phân tích: tìm thông điệp chính.**
- Đọc toàn bộ `transcript_for_llm.txt` (chia nhỏ nếu dài) và xem `frames.png`.
- **Chọn khung** cho từng clip:
  - `crop` (9:16 bám theo mặt người nói, hình lớn): một người nói trực diện trước máy quay, nền gọn.
  - `blur` (cả khung ngang ở giữa, nền mờ, tiêu đề ở trên, phụ đề ở dưới): slide, chia sẻ màn hình, nhiều người trong khung, hoặc nội dung cần thấy toàn cảnh.
  - Video gốc đã dọc thì script tự bỏ qua bước đổi khung.
- **Tiêu chí một thông điệp chính:** tự đứng được (không cần nghe phần trước), có một ý trọn vẹn, câu mở đầu cuốn hoặc gây tò mò, có giá trị thực tế, cảm xúc hoặc bất ngờ, dài đúng `--len`. Kết thúc ở cuối một ý, không cắt giữa câu. Các clip không chồng lên nhau. Đừng cắt theo kiểu làm đổi nghĩa lời người nói.
- **Số clip** do Claude đề xuất theo nội dung (thường khoảng một clip mỗi 3-5 phút, không ép đủ số lượng); người dùng chọn làm bao nhiêu.
- Với mỗi ứng viên ghi: `id`, `title` (tối đa khoảng 6-8 từ, cụ thể, bằng ngôn ngữ `--to`, không giật tít sai nội dung), `start_seg`, `end_seg` (số đoạn trong bản chép lời), `layout`, `hook` (câu mở), `why` (vì sao hay), `caption` (gợi ý chú thích đăng, có thể kèm hashtag), và chấm điểm 1-10.
- Lưu `work/clips/<tên>/plan.json` theo mẫu trong phần đầu `clip_video.py` (thời gian cắt tự lấy theo từ đầu và từ cuối của đoạn, thêm một chút đệm).

**Bước 3. Cho tôi chọn.** Hiển thị bảng: id | tiêu đề | thời gian (mm:ss-mm:ss) | độ dài | câu mở | vì sao hay | khung | điểm; kèm gợi ý nên làm những clip nào trước. **Dừng lại chờ tôi chọn** (ví dụ "làm 1, 3, 5").

**Bước 4. Hoàn thiện clip được chọn.**
- Sửa lỗi nhận dạng rõ ràng trong các đoạn được chọn (tiếng Việt hay sai dấu và từ gần âm) bằng cách ghi lại câu đúng vào `translations` của clip, khóa là số đoạn.
- Nếu `--to` khác ngôn ngữ trong video: dịch từng đoạn của các clip được chọn sang ngôn ngữ đích, tự nhiên, ngắn gọn, vào `translations`. Mốc từng từ khi đó chỉ chia đều theo đoạn; báo tôi biết.

**Bước 5. Dựng:**
```
python clip_video.py render <tên> --clips 1,3,5 [--title-seconds 4] [--layout blur|crop]
```
Mỗi clip: cắt đúng đoạn, đổi sang 1080×1920, tiêu đề chữ trắng nền hộp tím ở đầu clip, phụ đề karaoke tím, mờ tiếng đầu cuối, chuẩn hóa âm lượng. Kết quả ở `videos/clips/<tên>/clip-NN-<tiêu đề>.mp4` kèm `index.md` (tiêu đề, thời gian, câu mở, chú thích gợi ý). Thêm `--dry-run` để xem giờ cắt mà chưa dựng.

**Bước 6. Kiểm tra và giao:**
- Lấy vài khung hình mỗi clip (đầu, giữa, cuối) bằng ffmpeg và xem: tiêu đề có đọc rõ không, phụ đề có đúng dấu và đúng vị trí không, khung `crop` có bám đúng người không (script báo "face found in N samples"; 0 nghĩa là không thấy mặt chính diện và đã căn giữa), có logo hay thương hiệu rõ nét không.
- Báo đường dẫn, độ dài, dung lượng từng clip và những điều chưa chắc (ví dụ mặt nghiêng không bám được). Hỏi tôi có muốn chèn logo (`/edit-video`) hoặc gửi sang điện thoại không (giới hạn gửi 30 MB).

## Giới hạn cần nói thẳng
- Claude chọn clip dựa vào **lời nói** (bản chép lời) và vài khung hình mẫu, không xem liên tục cả video. Đoạn hay nhờ hình ảnh hoặc cử chỉ có thể bị bỏ sót.
- Chép lời tiếng Việt vẫn có lỗi; nhạc nền lớn hoặc nhiều người nói chen nhau làm kém hơn.
- Bám mặt dùng OpenCV (mặt chính diện); nhiều người trong khung hoặc mặt nghiêng thì nên dùng `blur`.
- Video gốc 1080p cắt `crop` rồi phóng lên 1080×1920 sẽ hơi mềm; `blur` giữ nguyên độ nét.
- Tải từ Google Drive và YouTube phụ thuộc vào chia sẻ và chính sách của dịch vụ; nếu lỗi thì tải về rồi đưa đường dẫn file.
