---
description: Từ chủ đề → bài fanpage → kịch bản → short video dọc 9:16 có phụ đề karaoke tím; chọn thể loại và đối tượng để tự khớp giọng, nhạc, nhịp, văn phong
argument-hint: [tranh luận:|info:|tâm sự:|góc nhìn:|nhận định:] <chủ đề> [--trẻ|--trung_niên] [--voice female|male] [--mode voice|music|both]
---

Lệnh: $ARGUMENTS

## Cú pháp (thống nhất)
```
/short-video <thể loại>: <chủ đề> --<đối tượng> [--voice female|male] [--mode voice|music|both]
```
Ví dụ:
```
/short-video tranh luận: chia đôi tiền khi hẹn hò --trẻ
/short-video info: lợi ích của việc dậy sớm --trung_niên
/short-video tâm sự: ai sẽ bên bạn khi mệt --trung_niên
/short-video góc nhìn: áp lực đồng trang lứa --trẻ
/short-video nhận định: <link bài báo hoặc chủ đề> --trẻ
/short-video info: mẹo ngủ ngon --trẻ --voice male --mode both
```

**Tách tham số trước khi viết nội dung** (các tham số không đưa vào bài viết hay kịch bản):

1. **Thể loại** = phần chữ trước dấu `:` đầu tiên, nếu khớp một trong năm (không phân biệt hoa thường và dấu):
   - `tranh luận` (hoặc `tranh_luận`) → `tranh-luan`
   - `info` (hoặc `thông tin`) → `info`
   - `tâm sự` (hoặc `tam su`) → `tam-su`
   - `góc nhìn` (hoặc `goc nhin`, `phân tích`) → `goc-nhin`
   - `nhận định` (hoặc `nhan dinh`, `bình luận`) → `nhan-dinh`

   Không có dấu `:` hoặc không khớp thì cả câu là chủ đề, thể loại mặc định là `tranh-luan`.
2. **Đối tượng** = `--trẻ` hoặc `--trung_niên` (chấp nhận `--tre`, `--trung-nien`, `--young`, `--mature`). Mặc định `--trẻ`.
3. `--voice female|male` (mặc định `female`): chọn **giới tính** giọng đọc. Ghép với đối tượng thành giọng cụ thể: `female-young`, `female-mature`, `male-young`, `male-mature`. Ghi một khóa khác của `voices.json` (ví dụ `piper-vais`, hoặc tên giọng edge-tts như `en-US-AvaNeural`) thì dùng đúng giọng đó. Danh sách: `python short_video.py --list-voices`.
4. `--mode voice` (mặc định) = video có giọng đọc; `music` = nhạc lớn, không giọng; `both` = cả hai bản.

Nếu cú pháp mơ hồ (đối tượng lạ, thể loại không rõ) thì hỏi lại một câu ngắn, đừng đoán.

## Thể loại và đối tượng quyết định gì
Giá trị nằm ở `profiles.json` (nhịp, nhạc) và `voices.json` (giọng); kịch bản chỉ cần ghi `genre` và `audience`.

| Thể loại | Đối tượng | Giọng (nữ / nam) | Tốc độ gốc | Nhạc nền | Độ dài |
|---|---|---|---|---|---|
| tranh luận | trẻ | `female-young` / `male-young` | +10% | Oh Please - Telecasted | 30-45 s, 110-135 từ |
| tranh luận | trung niên | `female-mature` / `male-mature` | +10% | Hopeful - Nat Keefe | 30-45 s, 110-135 từ |
| info | trẻ | như trên | +8% | Touch - Anno Domini Beats | 52-58 s, 160-180 từ |
| info | trung niên | như trên | +8% | Crystaline - Quincas Moreira | 52-58 s, 160-180 từ |
| tâm sự | trẻ | như trên | +3% | Final Soliloquy - Asher Fulero | 46-55 s, 130-155 từ |
| tâm sự | trung niên | như trên | +3% | No.2 Remembering Her - Esther Abrami | 46-55 s, 130-155 từ |
| góc nhìn | trẻ | như trên | +5% | Crystaline - Quincas Moreira | 50-60 s, 150-175 từ |
| góc nhìn | trung niên | như trên | +5% | Hopeful - Nat Keefe | 50-60 s, 150-175 từ |
| nhận định | trẻ | như trên | +6% | Touch - Anno Domini Beats | 50-60 s, 150-175 từ |
| nhận định | trung niên | như trên | +6% | Crystaline - Quincas Moreira | 50-60 s, 150-175 từ |

Giọng trẻ cộng thêm khoảng +6% tốc độ và cao hơn; giọng trung niên chậm hơn khoảng 8% và trầm hơn (đã tính sẵn trong `voices.json`, nên tốc độ nghe thực tế: trẻ nhanh nhất, trung niên chậm rãi). Nhạc nền chọn theo tâm trạng ghi trong thư viện, chưa nghe thử từng bài; nếu không hợp thì sửa `profiles.json` hoặc ghi `music` trong file kịch bản.

## Văn phong theo đối tượng
- **Trẻ (khoảng 18-30 tuổi):** xưng "bạn" và "mình", câu ngắn (khoảng 8-14 chữ), nhịp nhanh, hook trực diện gây tò mò, từ ngữ đời thường và hiện đại (có thể một hai từ thông dụng của giới trẻ, không lạm dụng tiếng lóng, không giáo huấn). Ví dụ gần gũi: công việc đầu tiên, mạng xã hội, thuê nhà, hẹn hò, deadline. Bài đăng có 2-5 emoji. Hình: người 20-30 tuổi, cà phê, văn phòng sáng, thành phố; thêm `young` vào `terms`.
- **Trung niên (khoảng 40-55 tuổi):** xưng "bạn" hoặc "chúng ta" ("mình" với tâm sự), câu dài hơn (khoảng 12-20 chữ), nhịp chậm, điềm đạm, từ ngữ chững chạc và giàu trải nghiệm, không tiếng lóng. Ví dụ gần gũi: gia đình, con cái, cha mẹ già, sức khỏe, công việc ổn định, tài chính. Bài đăng ít emoji (0-2). Hình: người 40-55 tuổi, bữa cơm gia đình, thiên nhiên, ánh sáng ấm; thêm `middle aged` hoặc `mature` vào `terms`.

Pexels không lọc được độ tuổi; từ khóa chỉ làm tăng khả năng ra đúng người, nên sau khi dựng phải xem lại hình.

Làm lần lượt 3 bước. **Dừng lại chờ tôi duyệt sau bước 1 và bước 2**, không render khi chưa được đồng ý.
Chọn `<slug>` ngắn, không dấu, gạch ngang (ví dụ `tuoi-40`).

## Luật an toàn của thể loại tranh luận (bắt buộc)
Theo tài liệu "Viral content instruction": chủ đề được đóng khung thành hai quan điểm đối lập để khán giả bình luận chọn bên.
1. Vai trò là **người giữ nhịp trung lập**, không nghiêng hẳn về một phía, không miệt thị phía còn lại.
2. **Không kích động thù oán** vùng miền, sắc tộc, tôn giáo. Chủ đề nhạy cảm (Bắc-Nam, thế hệ) thì chỉ bàn về văn hóa ứng xử, phong cách làm việc, thói quen chi tiêu.
3. **Không công kích cá nhân**: chỉ tranh luận quan điểm, không nhắc ngoại hình, nhân phẩm.
4. **Không chốt đúng/sai tuyệt đối**: luôn kết thúc bằng câu hỏi ngỏ.
5. Hai quan điểm **đều có lập luận thuyết phục và công bằng về độ dài**. Không dựng "rơm". Không bịa số liệu hay trích dẫn nghiên cứu.
6. Không đưa mẹo tạo bình luận giả (dùng tài khoản phụ để gài bình luận); chỉ khuyến nghị ghim một bình luận thật có chất lượng sau khi đăng.
Bốn nhóm chủ đề: Văn hóa & Lối sống · Giá trị & Tiêu chuẩn (tiền bạc, cái đẹp, hạnh phúc) · Mối quan hệ & Tình cảm · Công sở & Sự nghiệp.

## Bước 1. Bài viết fanpage (theo thể loại, áp dụng văn phong của đối tượng)
**Tranh luận:** văn xuôi tự nhiên, **không dùng nhãn "Phe A / Phe B", không có mục "góc trung lập"** (hai quan điểm chỉ hiện qua lời dẫn):
- Mở bằng câu hỏi lựa chọn hai thế lực đối lập, rồi một câu như "Nói thật đi, bạn chọn cách nào?".
- Một đoạn kể quan điểm thứ nhất (2-3 câu, lập luận mạnh nhất), một đoạn quan điểm thứ hai độ dài tương đương.
- **Đa dạng cách dẫn, không lặp một cụm cố định giữa các bài.** Quan điểm thứ nhất: "Với nhiều người...", "Một số người cho rằng...", "Không ít người tin rằng...", "Có người nghĩ...", "Nhiều người sẽ nói...". Quan điểm thứ hai: "Ở chiều ngược lại, không ít người băn khoăn...", "Nhưng cũng có người lại nghĩ khác...", "Song cũng có tiếng nói cho rằng...", "Phía bên kia thì hỏi:...", "Tuy nhiên, nhiều người không đồng tình...". Không dùng chữ "phe".
- 1-2 câu khép lại nhẹ nhàng, không ai sai hoàn toàn; câu hỏi ngỏ cuối bài mời bình luận chọn cách mình nghiêng về, kèm một tình huống thật.

**Info:** giọng gần gũi, có chiều sâu, theo bài "Tuổi 40": câu mở đúc kết một ý lớn; 4-5 ý có tiêu đề ngắn (emoji theo đối tượng) và 2-3 câu giải thích; kết bằng câu hỏi kéo bình luận. Không nêu số liệu hay trích dẫn không chắc.

**Nhận định:** bài **đưa ra một kết luận rõ ràng** về một sự việc hoặc một bài báo (khác góc nhìn, vốn mở nhiều phía mà không chốt). Nguồn là một link bài báo hoặc một chủ đề; nếu là link, đọc kỹ bài và dùng dữ kiện trong bài. Cấu trúc: tiêu đề ngắn; câu "Nhận định của mình:" nêu kết luận trong 1-2 câu; mức độ chắc chắn (thấp, vừa hay cao); 3 căn cứ, mỗi căn cứ gắn một dữ kiện cụ thể từ nguồn; "điều có thể làm nhận định này sai" (điều kiện, dữ kiện còn thiếu); "điều nên theo dõi tiếp"; một câu hỏi mời người đọc phản biện. Quy tắc bắt buộc: (1) tách ba lớp rõ ràng: dữ kiện của nguồn, suy luận của mình, và điều chưa biết; (2) ghi rõ đây là ý kiến, không phải sự thật đã kiểm chứng; (3) **không dự đoán giá cổ phiếu hay tài sản, không khuyến nghị mua, bán hay giữ, không nói điều gì "chắc chắn tăng/giảm"**, với tin tài chính chỉ nhận định về ý nghĩa của thông tin; (4) không gán ý đồ hay đánh giá đạo đức cá nhân khi nguồn không nêu bằng chứng; (5) không bịa số liệu, trích dẫn hay thông tin ngoài nguồn; số tự tính phải ghi "tính từ các số trong bài"; (6) với chủ đề chính trị hoặc nhạy cảm, chỉ nhận định về vấn đề công khai, nêu phản bác hợp lý nhất của phía còn lại.

**Góc nhìn:** bài phân tích điềm tĩnh, nhìn một vấn đề từ nhiều phía để người đọc nghĩ khác đi, không kể chuyện riêng và không cổ vũ một phe. Cấu trúc: tiêu đề ngắn nêu vấn đề; một câu mở đổi góc nhìn ("nếu đổi góc nhìn một chút..."); 3-4 ý, mỗi ý một tiêu đề ngắn (emoji số 1️⃣ 2️⃣ 3️⃣ theo thứ tự lập luận) và 2-3 câu giải thích; một ý cuối nêu cách dùng hoặc cách hiểu có ích; một câu chốt là câu hỏi đáng hỏi; kết bằng câu hỏi mời bình luận. Quy tắc: không bịa số liệu, tên nghiên cứu hay trích dẫn; chỉ dùng khái niệm phổ biến mà mình chắc (ví dụ "so sánh xã hội") và nêu không có năm hay tác giả; không phán đúng sai, không gán lỗi cho một nhóm người, nêu rõ khi một ý chỉ là cách nhìn.

**Tâm sự:** giọng kể xưng "mình", ấm và chậm; mở bằng một khoảnh khắc đời thường, đi qua vài cảm nhận, kết bằng câu hỏi nhẹ mời chia sẻ. Không bịa chi tiết đời tư cụ thể (tên, sự kiện), chỉ dùng cảm nhận phổ biến. Không khuyên răn.

Lưu vào `posts/<slug>.md` và hiển thị đầy đủ để tôi duyệt.

## Bước 2. Chuyển thành kịch bản video
Khi bài viết đã duyệt, soạn `specs/<slug>.json` **chỉ ghi thể loại và đối tượng**, để giọng, tốc độ, nhạc lấy từ profile:
```json
{
  "slug": "<slug>",
  "genre": "tranh-luan",
  "audience": "tre",
  "scenes": [
    {"vi": "Câu hook mở đầu...", "terms": ["english stock search", "terms", "for pexels"]}
  ]
}
```
Chỉ thêm `rate`, `music` hoặc `voice` vào file khi tôi yêu cầu đổi riêng (các trường này ghi đè profile).

Quy tắc chung: 5-6 cảnh; số viết bằng chữ ("bốn mươi", không "40"), tránh ký hiệu và emoji vì giọng đọc không đọc được; `terms` là 3 từ khóa tiếng Anh cụ thể, hợp hình ảnh đời thực trên Pexels (người, đồ vật, cảnh vật), tránh khái niệm trừu tượng và tránh nơi dễ lộ thương hiệu (phố, quán, màn hình ứng dụng). Độ dài từ lấy theo bảng ở trên (đo thực tế khoảng 3 từ/giây; 190 từ đã ra hơn 60 giây).

- **Tranh luận:** Hook (nêu ngay hai thế lực đối lập, 1 câu, tối đa khoảng 15 từ) → quan điểm thứ nhất (1-2 cảnh) → quan điểm thứ hai (1-2 cảnh, độ dài tương đương) → câu hỏi mở. **Không gọi tên "phe" trong lời đọc**, chuyển quan điểm bằng câu tự nhiên, đa dạng cách dẫn như ở Bước 1. CTA hỏi "bạn nghiêng về cách nào?". `terms` của hai quan điểm khác hẳn nhau về hình ảnh.
- **Info:** cảnh đầu là hook, mỗi ý một cảnh ngắn, cảnh cuối là câu hỏi kêu gọi.
- **Nhận định:** cảnh đầu nêu nhận định (hook, tối đa khoảng 15 từ, mở bằng "Nhận định của mình:" hoặc tương tự), 2-3 cảnh căn cứ (mỗi cảnh một dữ kiện kèm ý nghĩa), một cảnh "điều có thể làm mình sai", cảnh cuối mời phản biện; nói rõ mức độ chắc chắn. Giọng chắc, rõ, không phán quyết; hình minh họa ý, không có người thật bị gán ý đồ.
- **Góc nhìn:** cảnh đầu nêu câu "đổi góc nhìn" (hook, tối đa khoảng 15 từ), mỗi ý một cảnh (2-3 câu, bắt đầu bằng ý chính), một cảnh chốt bằng câu hỏi đáng hỏi, cảnh cuối mời bình luận. Giọng điềm đạm, rõ ràng; hình minh họa ý (người, nơi chốn, đồ vật đời thường), tránh hình quá cảm xúc như ở tâm sự.
- **Tâm sự:** cảnh đầu là khoảnh khắc mở đầu, giữa là những cảm nhận, cảnh cuối là câu hỏi nhẹ; hình dịu, ánh sáng ấm.

Hiển thị bảng cảnh | lời đọc | từ khóa hình, kèm giọng, nhạc và độ dài dự kiến, để tôi duyệt.

## Bước 3. Sản xuất video
Khi kịch bản đã duyệt, chạy từ thư mục dự án (chạy nền, khoảng 6-10 phút), thêm tham số tôi đã chỉ định:
```
python short_video.py specs/<slug>.json [--voice female|male] [--mode voice|music|both]
```
`genre` và `audience` đã nằm trong file kịch bản; muốn đổi tạm thì thêm `--genre ... --audience ...`. Xem trước các giá trị sẽ dùng mà không dựng: thêm `--dry-run`. Script tự bật Docker nếu cần, tạo giọng đọc (edge-tts hoặc Piper offline, đọc từng câu với cao độ, tốc độ, âm lượng theo ý nghĩa), dựng hình stock từng cảnh, gắn phụ đề karaoke tím cố định vị trí và xuất vào `videos/<slug>/`:
- `<slug>-voice-<giọng>.mp4`: giọng đọc + nhạc nhỏ, ví dụ `<slug>-voice-female-young.mp4`, `<slug>-voice-male-mature.mp4`.
- `<slug>-music.mp4`: nhạc lớn, không giọng đọc (`--mode music` hoặc `both`).
Muốn đổi giọng/chế độ cho video đã dựng mà không tải lại hình: thêm `--reuse-footage`.

Sau khi chạy xong:
1. Đọc kết quả script, báo thời lượng so với mục tiêu của thể loại, kích thước và cảnh báo.
2. Xem `work/<slug>/preview*.png` và ảnh ghép `work/<slug>/montage.png` (tạo bằng ffmpeg, mỗi cảnh một khung giữa) để kiểm tra phụ đề và hình, **kể cả hình có đúng độ tuổi của đối tượng không và có logo/thương hiệu rõ nét không** (không đăng được). Nếu lệch, đề xuất đổi `terms` rồi chạy lại.
3. Hỏi tôi có muốn gửi video sang điện thoại không (dùng bản `-share.mp4` nếu có, vì giới hạn gửi là 30 MB).

Lỗi thường gặp: edge-tts đôi khi báo `NoAudioReceived` (script tự thử lại); Docker Desktop phải đang chạy.
