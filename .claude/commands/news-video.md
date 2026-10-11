---
description: Làm short video dọc từ một hoặc nhiều link bài báo: ảnh chụp bài báo và hình minh họa, giọng đọc tóm tắt, phụ đề karaoke phía trên chân trang có tiêu đề và nguồn
argument-hint: <link> [<link> ...] [--audience trẻ|trung_niên] [--voice female|male]
---

Yêu cầu: $ARGUMENTS

## Cú pháp
```
/news-video <link> [<link> ...] [--audience trẻ|trung_niên] [--voice female|male]
```
Một link làm một video; nhiều link làm hàng loạt (mỗi link một video). **Giọng đọc mặc định là nữ trẻ (`female-young`), luôn đọc truyền cảm** (lên xuống giọng và đổi nhịp theo câu mạnh hơn khoảng 50%, áp dụng cho mọi giọng và độ tuổi). `--audience trung_niên` đổi sang giọng trung niên điềm đạm; `--voice male` đổi sang giọng nam; `--audience none` dùng giọng gốc không chỉnh.

## Khung hình (1080×1920)
- **Tiêu đề bài báo** ở dải đầu khung (cao 230 px, tối đa 3 dòng).
- **Phần nội dung** (cao 1210 px, ngay dưới tiêu đề): ảnh chụp trang bài báo cuộn chậm xuống (cảnh đầu và cảnh cuối) xen với clip stock minh họa (có nhãn "Hình minh họa").
- **Phụ đề karaoke tím** ở vị trí cố định phía trên chân trang.
- **Chân trang** (cao 270 px): dòng "Nguồn: <tên báo> · <ngày>".

## Quy trình (dừng chờ tôi duyệt ở bước 3)
**Bước 1. Lấy bài** (chạy một lần cho tất cả link):
```
python news_video.py fetch "<link1>" "<link2>" ...
```
Script mở từng bài trong Chrome ẩn (khung điện thoại), tắt popup đồng ý cookie và thanh dính, chụp ảnh trang (tự cắt khoảng trống quảng cáo ở đầu trang nếu có), trích văn bản bằng trafilatura. Lưu `work/news/<slug>/`: `article.json`, `article.txt`, `screenshot.png`. Dòng log nào có "nội dung ngắn" nghĩa là bài có thể bị chặn, cần đăng nhập hoặc không phải bài báo.

**Bước 2. Đọc và viết lời đọc cho từng bài.**
- Đọc `article.txt` đầy đủ và xem `screenshot.png`: có popup, quảng cáo che chữ, màn hình đăng nhập hay paywall không? Bài bị chặn hoặc quá ngắn thì báo tôi và bỏ qua. Bài là ý kiến, quảng cáo hoặc châm biếm thì nói rõ.
- Viết `work/news/<slug>/script.json`:
```json
{
  "title": "Tiêu đề trên chân trang (tiêu đề bài báo; chỉ rút gọn nếu quá dài, giữ nguyên nghĩa)",
  "source": "VnExpress",
  "scenes": [
    {"vi": "Lời đọc...", "visual": "article"},
    {"vi": "Lời đọc...", "visual": "stock", "terms": ["english term", "another term", "third term"]}
  ]
}
```
- **Quy tắc nội dung (bắt buộc):** chỉ dùng thông tin có trong bài; không thêm số liệu, bối cảnh hay nhận định của riêng mình; giữ giọng trung lập; giữ nguyên số liệu, ngày tháng và tên riêng; nêu nguồn ("Theo VnExpress...") ở ít nhất một câu hoặc để chân trang ghi nguồn; tóm tắt bằng lời của mình, không chép nguyên văn cả đoạn. Bài tiếng Anh thì viết lời đọc và tiêu đề trên khung bằng tiếng Việt (dịch sát nghĩa tiêu đề gốc; ghi tiêu đề gốc trong báo cáo cho tôi). Số, ngày, phần trăm viết bằng chữ ("tám tháng mười", "không phẩy hai phần trăm") vì giọng đọc không đọc được ký hiệu. Chủ đề nhạy cảm (tai nạn, tội phạm, nạn nhân, trẻ em): chỉ nêu sự kiện như bài đã đưa, không mô tả hình ảnh gây sốc, không suy đoán danh tính.
- **Độ dài: không giới hạn thời lượng. Quan trọng là đủ ý của bài.** Đọc hết bài và đưa vào mọi ý chính: sự kiện, số liệu, các bên liên quan, bối cảnh, phản biện hoặc góc nhìn khác mà bài nêu, kết luận. Bài ngắn thì video ngắn, bài dài thì video dài (thường 6-12 cảnh, một hai câu mỗi cảnh). Cảnh đầu và cuối là `article`; xen thêm cảnh `article` ở giữa khi đang nói đúng đoạn có trong ảnh chụp; các cảnh còn lại là `stock`.
- **`terms` cho cảnh `stock`:** 3 từ khóa tiếng Anh chung chung, cụ thể về hình ảnh (người làm việc, máy móc, thành phố...), tránh tên riêng, thương hiệu, người cụ thể. Đây là hình **minh họa**, không phải ảnh sự kiện; không chọn hình có thể làm người xem hiểu nhầm đó là cảnh thật của bài.

**Bước 3. Cho tôi duyệt cả lô.** Hiển thị bảng: slug | tiêu đề | nguồn | số từ | ước tính thời lượng | ghi chú (bài bị chặn, popup, nhạy cảm, bài ý kiến). Kèm lời đọc từng bài. **Dừng lại chờ tôi duyệt hoặc sửa.**

**Bước 4. Dựng.**
```
python news_video.py build --all [--voice male] [--audience trung-nien]
```
(`--all` dựng mọi bài đã có `script.json` mà chưa có video; hoặc ghi tên `<slug>` cụ thể.) Chạy nền, khoảng 5-8 phút mỗi video (phần lớn là tải clip stock). Kết quả: `videos/news/<slug>/<slug>.mp4`; ảnh ghép khung giữa mỗi cảnh ở `work/news/<slug>/montage.png`.

**Bước 5. Kiểm tra.** Xem `montage.png` của từng video: ảnh chụp có đọc được không và có popup/quảng cáo/chữ bị cắt không; tiêu đề chân trang đủ rõ và không bị cắt; phụ đề nằm trên chân trang và không chồng lên hình; hình stock có sát nội dung và không có logo thương hiệu nổi bật không. Báo tôi mọi vấn đề. Kèm gợi ý chú thích đăng: tóm tắt một hai câu và dòng "Nguồn: <tên báo>: <link>". Hỏi tôi có muốn gửi sang điện thoại không (giới hạn 30 MB).

## Bản quyền và đạo đức (nhắc ngắn một lần)
Video trích ảnh chụp trang bài báo và tóm tắt bằng lời mới, luôn ghi nguồn và gợi ý kèm link; nên có sự đồng ý của tòa soạn nếu dùng thương mại hoặc đăng thường xuyên. Không đưa video như tin do mình đưa; không sửa số liệu. Hình stock chỉ để minh họa.

## Giới hạn
- Clip stock không sát nội dung bằng ảnh thật của sự kiện; tòa soạn có thể chặn robot hoặc dùng paywall nên một số bài không lấy được.
- Ảnh chụp lấy phần đầu bài (khoảng 1700 px theo khung điện thoại), nên chữ cuộn chậm chỉ trong phần đầu.
- Trích văn bản tự động đôi khi lẫn dòng thừa (chú thích ảnh, tên tác giả); đọc lại trước khi viết lời.
