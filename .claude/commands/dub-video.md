---
description: Lồng tiếng (voice-over) cho video: video tiếng Anh sang giọng đọc tiếng Việt, hoặc video tiếng Việt sang giọng đọc tiếng Anh; nguồn là file, link YouTube hoặc link Google Drive
argument-hint: <nguồn> [--to vi|en] [--voice female|male] [--subs] [--bg 0.12]
---

Yêu cầu: $ARGUMENTS

## Cú pháp
```
/dub-video <nguồn> [--from auto|en|vi] [--to vi|en] [--voice female|male] [--subs] [--bg 0.12] [--rate 0]
```
- **Nguồn:** đường dẫn file trên máy, link YouTube, hoặc link Google Drive (chia sẻ "Anyone with the link").
- Ngôn ngữ nguồn tự nhận dạng; `--to` không ghi thì lồng sang ngôn ngữ còn lại (Anh sang Việt, Việt sang Anh).
- `--voice female|male`: giọng nữ hoặc nam (mặc định nữ). Nói rõ "giọng nam trung niên" thì dùng `male-mature` (tiếng Việt) hoặc `en-male-mature` (tiếng Anh). Cũng nhận mọi khóa trong `voices.json`.
- `--subs`: gắn thêm phụ đề karaoke tím bằng ngôn ngữ lồng tiếng (dựng lại hình nên chậm hơn). Không ghi thì giữ nguyên hình, chỉ thay âm thanh.
- `--bg`: mức âm gốc nghe được dưới giọng lồng, từ 0 đến 1 (mặc định 0,12; `0` là tắt hẳn âm gốc, nên dùng khi muốn sạch tiếng).

Chỉ làm với video của bạn hoặc video bạn có quyền dùng lại. Nhắc một lần ngắn nếu link YouTube trông không phải của người dùng; không từ chối vì chuyện đó.

## Quy trình (dừng chờ tôi duyệt ở bước 3)

**Bước 1. Chuẩn bị** (chạy nền, lâu: nhận dạng khoảng 0,65-1,4 lần thời lượng video):
```
python dub_video.py prepare "<nguồn>" [--from en|vi|auto] [--to vi|en] [--name <tên-ngắn>]
```
Script tải video nếu là link, chép lời bằng Whisper medium, chia lời thành các **đơn vị lồng tiếng** (mỗi đơn vị một đến vài câu, tối đa khoảng 12 giây) và lưu `work/dub/<tên>/dub.json` cùng `transcript_for_llm.txt`. Mỗi dòng là `[số] mm:ss-mm:ss (x giây, tối đa N từ) lời gốc`. Kết quả được lưu lại, chạy lại rất nhanh; muốn nhận dạng lại thì thêm `--force`.

**Bước 2. Dịch.** Đọc toàn bộ `transcript_for_llm.txt` (chia nhỏ nếu dài) và viết `work/dub/<tên>/translations.json` dạng `{"0": "lời dịch", "1": "..."}`: **mỗi đơn vị phải có một bản dịch**, khóa là số trong ngoặc vuông.
- **Dịch để đọc thành tiếng:** tự nhiên, nói được, không dịch từng chữ; giữ nguyên nghĩa, không thêm hay bớt ý, không "sửa" lập luận của người nói.
- **Giữ trong ngân sách:** số từ không vượt "tối đa N từ" của dòng đó (giọng lồng phải đọc xong trong khoảng thời gian của câu gốc). Dịch ngắn gọn hơn chứ không dài hơn; câu dài quá sẽ bị đọc nhanh hoặc cắt cuối.
- **Sang tiếng Việt:** tên riêng, thương hiệu, thuật ngữ quen thuộc giữ nguyên; số, ngày, phần trăm, tiền tệ viết bằng chữ ("hai mươi phần trăm"), vì giọng đọc không đọc được ký hiệu; từ viết tắt đọc theo chữ cái viết bằng chữ cái cách nhau ("ây ai") nếu giọng hay đọc sai.
- **Sang tiếng Anh:** số viết bằng chữ số thường ổn; địa danh và tên người Việt giữ nguyên dấu; tránh tiếng lóng dịch sát chữ.
- Câu ngắn như "ừ", "vâng" dịch thành một từ ngắn tương ứng, không bỏ trống.
- Nội dung nhạy cảm (chính trị, tôn giáo, y tế): dịch trung lập đúng lời người nói; không thêm nhận xét.

**Bước 3. Cho tôi duyệt.** Hiển thị: tổng số đơn vị, thời lượng, giọng sẽ dùng, và 6 dòng mẫu (gốc và dịch cạnh nhau, chọn đầu, giữa, cuối). Nhắc những chỗ bạn không chắc nghĩa hoặc thuật ngữ. **Dừng lại chờ tôi duyệt hoặc sửa**, trừ khi tôi đã bảo làm luôn.

**Bước 4. Dựng:**
```
python dub_video.py render <tên> [--voice female|male|<khóa>] [--subs] [--bg 0.12] [--rate 0]
```
Mỗi đơn vị được tổng hợp giọng rồi đặt đúng mốc thời gian của câu gốc; câu dịch dài hơn thì đọc nhanh lên (tối đa khoảng +50%, sau đó tăng nhịp nhẹ), vẫn không kịp thì cắt đuôi rất ngắn. Âm gốc tự nhỏ xuống khi giọng lồng đọc. Kết quả: `videos/dub/<tên>/<tên>-<ngôn ngữ>.mp4`, kèm `.srt` (phụ đề) và `.txt` (kịch bản đã dịch). Script báo bao nhiêu đơn vị phải đọc nhanh và đơn vị nào bị cắt. Dựng lại sau khi sửa dịch chỉ tổng hợp lại các đơn vị đã đổi, rất nhanh.

**Bước 5. Kiểm tra và giao.**
- Nếu có đơn vị bị cắt hoặc đọc nhanh quá: rút gọn bản dịch của các đơn vị đó trong `translations.json` rồi chạy `render` lại.
- Kiểm tra bằng cách lấy vài khung hình (nếu dùng `--subs`) và nhận dạng lại âm thanh kết quả (`python auto_subtitle.py <video> --transcribe-only` rồi so với kịch bản đã dịch) để chắc giọng lồng đúng chỗ và đọc đúng chữ.
- Báo đường dẫn, độ dài, dung lượng và những điều chưa chắc. Hỏi tôi có muốn thêm phụ đề (`--subs`), đổi giọng, hoặc gắn logo (`/edit-video`) không.

## Giới hạn cần nói thẳng
- **Một giọng cho cả video.** Nhiều người nói chen nhau vẫn chỉ có một giọng lồng, không tách người nói và không giữ giọng gốc của họ.
- **Không tách được tiếng nói khỏi nhạc nền:** âm gốc chỉ được hạ nhỏ xuống, nên có thể nghe thấy lẫn tiếng gốc rất nhỏ; muốn sạch hãy dùng `--bg 0`, nhưng khi đó mất luôn nhạc và tiếng môi trường.
- **Độ dài tiếng khác nhau:** dịch Anh sang Việt thường dài hơn nên có đoạn phải đọc nhanh; chất lượng khớp phụ thuộc vào việc dịch ngắn gọn.
- Video đã có phụ đề cứng (chữ in sẵn trên hình): thêm `--subs` sẽ chồng chữ; hãy bỏ `--subs` hoặc dùng video không có phụ đề.
- Không khớp khẩu hình; phù hợp video có cảnh người nói ở xa, video minh họa hoặc video có hình thay đổi.
- Nhận dạng giọng nói có lỗi (nhạc lớn, giọng nặng, tên riêng); lỗi nhận dạng sẽ thành lỗi dịch, nên đọc lại các dòng nghi ngờ trước khi dựng.
- Giọng edge-tts cần internet và đôi khi trả lỗi `NoAudioReceived` (script tự thử lại).
- Tôi chưa nghe thử chất lượng giọng lồng; hãy nghe một đoạn trước khi đăng.
