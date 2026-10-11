---
description: Tự động tạo phụ đề karaoke tím (tiếng Việt hoặc tiếng Anh) cho một video có tiếng nói, có bước soát lỗi và dịch
argument-hint: <đường dẫn video> [--lang vi|en|auto] [--to vi|en] [--no-review]
---

Video và tùy chọn: $ARGUMENTS

Dùng `auto_subtitle.py` (Whisper medium chạy trên CPU, model đã tải ở `models/faster-whisper-medium`). Không sửa file gốc; kết quả nằm ở `videos/auto-sub/<tên>-sub.mp4`, các file trung gian ở `work/auto-sub/<tên>/`.

Tham số trong dòng trên:
- `--lang vi|en|auto`: ngôn ngữ trong video (mặc định `auto`; nếu biết thì ghi rõ để nhận dạng chuẩn hơn).
- `--to vi|en`: ngôn ngữ phụ đề muốn có. Không ghi thì phụ đề trùng ngôn ngữ trong video. Khác nhau thì phải dịch (bước 3).
- `--no-review`: bỏ bước soát lỗi và dựng luôn.

## Các bước
1. **Nhận dạng giọng nói** (chạy từ thư mục dự án; khoảng 0,65 lần thời lượng video):
```
python auto_subtitle.py <video> --lang <vi|en|auto> --transcribe-only
```
Kết quả: `work/auto-sub/<tên>/transcript.json` (có mốc thời gian từng từ) và `transcript.txt`.
2. **Soát lỗi** (bỏ qua nếu có `--no-review`): đọc `transcript.json`, sửa những chỗ Whisper nghe sai dựa vào ngữ cảnh (ví dụ tiếng Việt hay sai dấu hoặc từ gần âm: "chi đôi" thành "chia đôi", "ngăn hàng" thành "ngang hàng"; tên riêng và từ mượn tiếng Anh). Chỉ sửa trường `text` của từng segment (giữ nguyên `start`, `end`; mốc từng từ sẽ tự chia lại theo `text`). Lưu bản sửa thành `transcript_fixed.json`. Hiển thị cho tôi danh sách các chỗ đã sửa và các chỗ còn nghi ngờ (đánh dấu rõ), rồi **chờ tôi duyệt** trước khi dựng.
3. **Dịch** (chỉ khi `--to` khác ngôn ngữ trong video): dịch `text` của mỗi segment sang ngôn ngữ đích, tự nhiên, ngắn gọn (phụ đề tối đa 2 dòng), giữ nguyên số segment và thời gian. Lưu thành `transcript_<ngôn ngữ>.json`. Mốc từng từ lúc này chỉ là ước lượng đều trong segment, nên báo tôi biết.
4. **Dựng video có phụ đề**:
```
python auto_subtitle.py <video> --transcript work/auto-sub/<tên>/<transcript_fixed hoặc transcript_xx>.json
```
Phụ đề karaoke: chữ trắng chuyển tím theo từng từ, tối đa 2 dòng, dòng đầu cố định ở độ cao 676 px tính từ đáy (video dọc 1080×1920) nên không nhảy lên xuống. Video ngang tự đặt thấp hơn (0,78 chiều cao). Nếu muốn đổi độ cao: `--pos-y <tỉ lệ chiều cao>`.
5. **Kiểm tra**: lấy vài khung hình (đầu, giữa, cuối) xem chữ có đúng dấu, không tràn khung, không che mặt hoặc chữ có sẵn. Báo đường dẫn, thời lượng, dung lượng và hỏi tôi có muốn gửi sang điện thoại không (giới hạn 30 MB).

## Lưu ý
- Nhận dạng tiếng Việt bằng Whisper không hoàn hảo: nhạc nền lớn, nhiều người nói chen nhau, giọng địa phương nặng, tên riêng, từ lóng sẽ sai nhiều hơn. Bước soát lỗi là bắt buộc nếu định đăng.
- Video đã có phụ đề cứng thì phụ đề mới sẽ chồng lên, hãy dùng bản gốc chưa có chữ.
- Đoạn không có tiếng nói (chỉ nhạc) sẽ không có phụ đề. Muốn chỉnh tay: sửa `transcript.json` rồi chạy lại bước 4.
- Muốn xuất phụ đề rời: `work/auto-sub/<tên>/subs.srt` (chữ thường, không có karaoke) và `subs.ass`.
