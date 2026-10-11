# Hướng dẫn sử dụng: bộ công cụ làm short video (TikTok / Reels / Shorts)

Năm kỹ năng chạy trong Claude Code, gọi bằng lệnh `/...`. Tất cả đều xuất video dọc 1080×1920 H.264/AAC, phụ đề karaoke tím (trắng chuyển tím theo từng từ, tối đa 2 dòng, dòng đầu cố định cách đáy 676 px).

| Lệnh | Việc làm | Cần Docker? |
|---|---|---|
| `/short-video` | Chủ đề → bài fanpage → kịch bản → video hoàn chỉnh | Có (lấy clip stock) |
| `/edit-video` | Cắt, ghép, chuyển cảnh, tốc độ, mờ dần, zoom, logo cho video có sẵn | Không |
| `/auto-subtitle` | Nhận dạng giọng nói, soát lỗi, dịch, gắn phụ đề karaoke (Việt/Anh) | Không |
| `/news-video` | Làm short từ một hoặc nhiều link bài báo: ảnh chụp bài báo, hình minh họa, giọng đọc tóm tắt, phụ đề, chân trang tiêu đề và nguồn | Có (clip stock) |
| `/dub-video` | Lồng tiếng Anh sang Việt hoặc Việt sang Anh | Không |
| `/clip-video` | Cắt nhiều short dọc từ một video ngang dài 15-30 phút theo các thông điệp chính (Claude chọn, bạn duyệt), có tiêu đề chữ và phụ đề karaoke | Không |

## 1. `/short-video`: từ chủ đề đến video

```
/short-video <thể loại>: <chủ đề> --<đối tượng> [--voice female|male] [--mode voice|music|both]
```

Quy trình 3 bước, **dừng chờ duyệt sau bước 1 và bước 2**:
1. **Bài fanpage** → `posts/<slug>.md`
2. **Kịch bản** (5-6 cảnh, mỗi cảnh có lời đọc + 3 từ khóa tìm hình) → `specs/<slug>.json`
3. **Video** → `videos/<slug>/`

**Cú pháp thống nhất:**
```
/short-video tranh luận: chia đôi tiền khi hẹn hò --trẻ
/short-video info: lợi ích của việc dậy sớm --trung_niên
/short-video tâm sự: ai sẽ bên bạn khi mệt --trung_niên
/short-video góc nhìn: áp lực đồng trang lứa --trẻ
/short-video nhận định: https://vnexpress.net/<bài-báo> --trẻ
```
- **Thể loại** là chữ trước dấu `:` đầu tiên: `tranh luận`, `info`, `tâm sự`, `góc nhìn`, `nhận định` (không có thì mặc định tranh luận).
- **Đối tượng** là `--trẻ` hoặc `--trung_niên` (mặc định trẻ).
- Thể loại và đối tượng tự chọn **giọng đọc, tốc độ, nhạc nền, độ dài, văn phong** (giá trị ở `profiles.json` và `voices.json`):

| Thể loại | Đối tượng | Giọng (nữ / nam) | Tốc độ gốc | Nhạc nền | Độ dài |
|---|---|---|---|---|---|
| tranh luận | trẻ | `female-young` / `male-young` | +10% | Oh Please | 30-45 s, 110-135 từ |
| tranh luận | trung niên | `female-mature` / `male-mature` | +10% | Hopeful | 30-45 s, 110-135 từ |
| info | trẻ | như trên | +8% | Touch | 52-58 s, 160-180 từ |
| info | trung niên | như trên | +8% | Crystaline | 52-58 s, 160-180 từ |
| tâm sự | trẻ | như trên | +3% | Final Soliloquy | 46-55 s, 130-155 từ |
| tâm sự | trung niên | như trên | +3% | No.2 Remembering Her | 46-55 s, 130-155 từ |
| góc nhìn | trẻ | như trên | +5% | Crystaline | 50-60 s, 150-175 từ |
| góc nhìn | trung niên | như trên | +5% | Hopeful | 50-60 s, 150-175 từ |
| nhận định | trẻ | như trên | +6% | Touch | 50-60 s, 150-175 từ |
| nhận định | trung niên | như trên | +6% | Crystaline | 50-60 s, 150-175 từ |

Giọng trẻ nhanh và cao hơn, giọng trung niên chậm và trầm hơn. **Cột nhạc nền là tên file nhạc của tác giả bộ công cụ; repo không kèm nhạc.** Bạn bỏ nhạc miễn phí của mình vào `assets/music/` rồi đổi tên file trong mục `music` của `profiles.json` (xem `assets/music/README.md`); thiếu file thì dùng file đầu tiên trong thư mục, thư mục trống thì video chỉ có giọng đọc.
- **Văn phong trẻ:** xưng "bạn/mình", câu ngắn, hook trực diện, ví dụ đời thường, 2-5 emoji, hình người 20-30 tuổi. **Trung niên:** câu dài hơn, điềm đạm, ví dụ gia đình/sức khỏe/tài chính, 0-2 emoji, hình người 40-55 tuổi.
- **Tranh luận:** hai quan điểm đối lập (bài là văn xuôi, không nhãn "phe"); luật an toàn: trung lập, không kích động vùng miền/sắc tộc/tôn giáo, không công kích cá nhân, không chốt đúng sai, hai bên công bằng, không bịa số liệu, không gài bình luận giả. **Info:** 4-5 ý có tiêu đề. **Tâm sự:** giọng kể xưng "mình", ấm và chậm.

**Tham số:**
| Tham số | Giá trị | Mặc định | Ý nghĩa |
|---|---|---|---|
| `--mode` | `voice` / `music` / `both` | `voice` | có giọng đọc / nhạc lớn không giọng / cả hai |
| `--trẻ` / `--trung_niên` | đối tượng | trẻ | tuổi giọng, văn phong, nhạc |
| `--voice` | `female` / `male` hoặc khóa trong `voices.json` | `female` | giới tính giọng (ghép với đối tượng thành `female-young`, `male-mature`...); khóa khác như `piper-vais` dùng đúng giọng đó |

**Thư viện giọng** (`voices.json`; xem bằng `python short_video.py --list-voices`; nghe thử bằng `python voice_demo.py --check`, file mẫu ở `videos/voice-samples/`):

| `--voice` | Loại | Mô tả |
|---|---|---|
| `female`, `male` | edge-tts (cần internet) | giọng gốc HoaiMy (nữ), NamMinh (nam) |
| `female-young`, `male-young` | edge-tts | trẻ trung: cao hơn, nhanh hơn, tươi sáng |
| `female-mature`, `male-mature` | edge-tts | trung niên: trầm hơn, chậm rãi, điềm đạm |
| `piper-vais` | Piper (offline) | giọng nữ, tốt nhất trong ba giọng Piper (Whisper nhận lại 97% câu mẫu) |
| `piper-25h` | Piper (offline) | chất lượng thấp hơn (85%) |
| `piper-vivos-male` | Piper (offline) | giọng nam, thử nghiệm, nghe kém nhất (85%) |
| tên giọng edge-tts bất kỳ | edge-tts | ví dụ `en-US-AvaNeural` cho tiếng Anh |

Mọi giọng đều được chỉnh cao độ, tốc độ, âm lượng **theo từng câu** (câu hỏi lên giọng và chậm, câu cảm thán sáng và to, câu cuối chậm và trầm). Giọng edge-tts dùng tham số gốc; Piper dùng `length_scale` (tốc độ), `rubberband` (cao độ) và gain (âm lượng). Muốn thêm giọng hoặc chỉnh độ lệch, sửa `voices.json`. Piper cần `pip install piper-tts` và các file giọng ở `models/piper/` (tải bằng `python -m piper.download_voices vi_VN-vais1000-medium --download-dir models/piper`). Giấy phép từng bộ dữ liệu giọng có thể khác nhau, nên kiểm tra thẻ mô hình trên Hugging Face trước khi dùng thương mại.

**File xuất ra** (`videos/<slug>/`): `<slug>-voice-<giọng>.mp4` (giọng đọc + nhạc nhỏ, ví dụ `<slug>-voice-female-young.mp4`), `<slug>-music.mp4` (nhạc lớn). File trên 29 MB có thêm `-share.mp4` (nén để gửi điện thoại, giới hạn 30 MB).

**Chạy tay không qua Claude:**
```
python short_video.py specs/<slug>.json [--mode ...] [--voice ...] [--reuse-footage] [--skip-render]
```
- `--reuse-footage`: dựng lại giọng/phụ đề mà không tải lại clip hình.
- `--skip-render`: chỉ ghép lại (đổi nhạc, độ cao phụ đề), không cần Docker.

**File kịch bản `specs/<slug>.json`:**
```json
{
  "slug": "ten-ngan",
  "genre": "tranh-luan",
  "audience": "tre",
  "scenes": [
    {"vi": "Lời đọc cũng là phụ đề...", "terms": ["english stock term", "another term", "third term"]}
  ]
}
```
Chỉ cần `genre` và `audience`; giọng, tốc độ, nhạc lấy từ profile. Muốn đổi riêng thì thêm `rate`, `music` (file trong `assets/music` hoặc thư viện của short-video-maker) hoặc `voice` vào file. Xem giá trị sẽ dùng mà không dựng: `python short_video.py specs/<slug>.json --dry-run`. Giọng đọc biểu cảm theo câu: câu hỏi chậm và cao hơn, câu cảm thán sáng và to hơn, câu cuối chậm và trầm.

## 2. `/edit-video`: chỉnh video có sẵn

```
/edit-video <đường dẫn video> <mô tả việc cần làm>
```
Dùng `edit_video.py`; không sửa file gốc; ghi vào `videos/edited/`.

| Việc | Tùy chọn |
|---|---|
| Cắt | `--trim 5-40` (mỗi video một `--trim`, `-` = giữ nguyên; thời gian `12.5`, `1:05`) |
| Ghép | nhiều file đầu vào; `--transition 0.6` chuyển cảnh mờ |
| Kích thước | `--size 1080x1920`, `--fit cover` (cắt tràn, mặc định) / `contain` (viền đen) |
| Tốc độ | `--speed 1.2` (0.5-4) |
| Mờ dần | `--fade-in 0.5 --fade-out 0.8` (hình + tiếng) |
| Zoom chậm | `--zoom 1.12` |
| Logo | `--logo logo.png --logo-pos tl|tr|bl|br|c --logo-size 14 --logo-opacity 0.9 --logo-margin 40 --logo-from 0 --logo-to 5` |

```
python edit_video.py a.mp4 b.mp4 -o videos/edited/out.mp4 --trim 5-17 --trim 0-10 --transition 0.6 --fade-out 0.8 --logo logo.png --logo-pos tl
```
**Hàng loạt:** thêm `--batch` để áp dụng cùng một cài đặt (ví dụ logo) cho nhiều video, mỗi video xử lý riêng:
```
python edit_video.py --batch "videos/clips/ten/*.mp4" -o videos/edited/ten --logo logo.png --logo-pos tl --suffix logo
```
Đầu vào có thể là file, thư mục hoặc dạng `*.mp4`; `-o` là thư mục kết quả; file lỗi chỉ bị báo, các file khác vẫn chạy.

Logo nên là PNG nền trong. Không gỡ được phụ đề cứng có sẵn.

## 3. `/auto-subtitle`: phụ đề tự động

```
/auto-subtitle <đường dẫn video> [--lang vi|en|auto] [--to vi|en] [--no-review]
```
Dùng `auto_subtitle.py` + `karaoke.py`; Whisper medium chạy trên CPU (model ở `models/faster-whisper-medium`, khoảng 0,65 lần thời lượng video).

Quy trình: nhận dạng (`--transcribe-only`) → **soát lỗi** (Claude sửa chỗ nghe sai, bạn duyệt) → dịch nếu `--to` khác ngôn ngữ video → dựng video.

```
python auto_subtitle.py video.mp4 --lang vi --transcribe-only
python auto_subtitle.py video.mp4 --transcript work/auto-sub/video/transcript_fixed.json
```
Tham số script: `--lang`, `--transcribe-only`, `--transcript <json>`, `--out`, `--pos-y <tỉ lệ chiều cao>` (mặc định 0,647 cho video dọc; video ngang tự đặt thấp hơn).
Kết quả: `videos/auto-sub/<tên>-sub.mp4`; trung gian ở `work/auto-sub/<tên>/` gồm `transcript.json` (sửa tay được), `transcript.txt`, `subs.ass`, `subs.srt`.
Giới hạn: nhạc nền lớn, nhiều người nói, giọng nặng, tên riêng sẽ sai nhiều hơn; video đã có phụ đề cứng sẽ bị chồng chữ.

## 4. `/clip-video`: cắt nhiều short từ một video dài

```
/clip-video <file | link YouTube | link Google Drive> [--lang vi|en|auto] [--to vi|en] [--len 30-60] [--layout blur|crop] [--title-seconds 4]
```
Dùng `clip_video.py`. Nguồn là file trên máy, link YouTube (tải bằng yt-dlp) hoặc link Google Drive (chia sẻ "Anyone with the link", tải bằng gdown). Video ngang 15-30 phút, tiếng Việt hoặc tiếng Anh.

Quy trình:
1. **Chuẩn bị:** `python clip_video.py prepare "<nguồn>" --lang vi` tải video (nếu là link), chép lời bằng Whisper medium (lâu: khoảng 0,65-1,4 lần thời lượng), lưu `work/clips/<tên>/transcript.json`, `transcript_for_llm.txt` (các đoạn đánh số) và `frames.png`.
2. **Claude tìm thông điệp chính:** đọc bản chép lời, đề xuất các clip tự đứng được, có câu mở cuốn, kết ở cuối một ý, dài 30-60 giây; ghi `plan.json`. Số clip do nội dung quyết định.
3. **Bạn chọn** clip nào làm.
4. Claude sửa lỗi nhận dạng và dịch phụ đề (nếu `--to` khác ngôn ngữ video) cho các clip được chọn.
5. **Dựng:** `python clip_video.py render <tên> --clips 1,3,5` ra `videos/clips/<tên>/clip-NN-<tiêu đề>.mp4` và `index.md` (tiêu đề, thời gian, câu mở, gợi ý chú thích đăng).

Mỗi short: 1080×1920, **tiêu đề chữ trắng nền hộp tím ở đầu clip** (mặc định 4 giây), phụ đề karaoke tím, mờ tiếng đầu cuối, chuẩn hóa âm lượng. Hai kiểu khung cho video ngang:
- `blur`: cả khung ngang ở giữa trên nền mờ, tiêu đề phía trên, phụ đề phía dưới. An toàn cho slide, chia sẻ màn hình, nhiều người.
- `crop`: cửa sổ 9:16 bám theo mặt người nói (OpenCV), phóng lên 1080×1920. Hợp một người nói trực diện; video gốc 1080p sẽ hơi mềm.

Giới hạn: Claude chọn clip theo lời nói và vài khung hình mẫu, không xem liên tục cả video; nhận dạng tiếng Việt vẫn có lỗi; bám mặt chỉ nhận mặt chính diện; tải từ YouTube và Drive phụ thuộc vào chia sẻ và chính sách của dịch vụ. Chỉ dùng với video của bạn hoặc video bạn có quyền dùng lại.

## 5. `/news-video`: short từ link bài báo (hàng loạt được)

```
/news-video <link> [<link> ...] [--audience trẻ|trung_niên] [--voice female|male]
```
Dùng `news_video.py`. Một link làm một video, nhiều link làm cả lô. **Giọng mặc định: nữ trẻ (`female-young`), truyền cảm hơn** (lên xuống giọng và đổi nhịp theo câu mạnh hơn khoảng 50%, cấu hình `express` của thể loại `news` trong `profiles.json`).

Khung 1080×1920:
- **Tiêu đề bài báo** ở dải đầu khung (cao 230 px).
- **Phần nội dung** (cao 1210 px): ảnh chụp trang bài báo cuộn chậm (cảnh đầu và cuối) xen với clip stock minh họa từ Pexels (có nhãn "Hình minh họa").
- **Phụ đề karaoke tím** phía trên chân trang.
- **Chân trang** (cao 270 px): "Nguồn: <tên báo> · <ngày>".

Quy trình (Claude dừng chờ bạn duyệt cả lô trước khi dựng):
1. `python news_video.py fetch "<link1>" "<link2>"`: mở từng bài trong Chrome ẩn (khung điện thoại), tắt popup cookie, chụp ảnh trang, trích văn bản. Lưu ở `work/news/<slug>/`.
2. Claude đọc từng bài và viết `script.json`: tóm tắt trung lập chỉ bằng thông tin trong bài (không giới hạn thời lượng, đủ ý của bài, thường 6-12 cảnh, số viết bằng chữ), cảnh đầu và cuối là ảnh chụp, các cảnh giữa là clip minh họa.
3. Bạn duyệt bảng các bài (tiêu đề, nguồn, độ dài, ghi chú).
4. `python news_video.py build --all` dựng các bài đã có kịch bản và chưa có video; ra `videos/news/<slug>/<slug>.mp4` và ảnh ghép kiểm tra `work/news/<slug>/montage.png`. `python news_video.py status` cho biết bài nào đã lấy, đã có kịch bản, đã dựng.

Lưu ý: trang bị chặn hoặc có paywall thì không lấy được nội dung đủ (script báo "nội dung ngắn"); clip stock chỉ minh họa, không phải ảnh sự kiện; luôn ghi nguồn và nên xin phép tòa soạn nếu dùng thương mại. Tóm tắt bằng lời mới, không thêm thông tin ngoài bài.

## 6. `/dub-video`: lồng tiếng Anh sang Việt hoặc Việt sang Anh

```
/dub-video <nguồn> [--from auto|en|vi] [--to vi|en] [--voice female|male] [--subs] [--bg 0.12] [--rate 0]
```
Nguồn là file trên máy, link YouTube hoặc link Google Drive (chia sẻ "Anyone with the link"). Ngôn ngữ nguồn tự nhận dạng; `--to` không ghi thì lồng sang ngôn ngữ còn lại.

Quy trình (dừng chờ duyệt ở bước 3):
1. **Chuẩn bị:** `python dub_video.py prepare "<nguồn>"` tải video, chép lời bằng Whisper medium, chia lời thành các đơn vị lồng tiếng (một đến vài câu, tối đa khoảng 12 giây), mỗi đơn vị có "số từ tối đa" theo thời lượng.
2. **Dịch:** Claude dịch từng đơn vị (dịch để đọc thành tiếng, ngắn gọn, giữ trong ngân sách từ) và ghi `work/dub/<tên>/translations.json`.
3. **Duyệt:** bạn xem vài dòng mẫu rồi xác nhận hoặc sửa.
4. **Dựng:** `python dub_video.py render <tên> [--voice ...] [--subs]` tổng hợp giọng cho từng đơn vị, đặt đúng mốc thời gian câu gốc (đọc nhanh lên nếu dài, tối đa khoảng +50% rồi tăng nhịp nhẹ, vẫn không kịp thì cắt đuôi rất ngắn), hạ âm gốc xuống khi giọng lồng đọc, ghép lại. Kết quả `videos/dub/<tên>/<tên>-<ngôn ngữ>.mp4` kèm `.srt` và `.txt` (kịch bản đã dịch). Dựng lại sau khi sửa dịch chỉ tổng hợp lại các đơn vị đã đổi.

| Tham số | Giá trị | Mặc định | Ý nghĩa |
|---|---|---|---|
| `--to` | `vi` / `en` | ngôn ngữ còn lại | ngôn ngữ giọng lồng |
| `--voice` | `female` / `male` / khóa `voices.json` | `female` | giọng lồng (tiếng Anh: `en-female`, `en-male`, `en-male-mature`) |
| `--subs` | cờ | tắt | gắn phụ đề karaoke bằng ngôn ngữ lồng tiếng (dựng lại hình, chậm hơn) |
| `--bg` | 0 đến 1 | 0,12 | mức âm gốc nghe được dưới giọng lồng (`0` tắt hẳn) |
| `--rate` | số nguyên (%) | 0 | tốc độ đọc cơ bản |

Prompt mẫu:
- `/dub-video https://www.youtube.com/watch?v=<id> --to vi --voice male`
- `/dub-video D:ideoai-noi-tieng-anh.mp4 --subs`
- `/dub-video https://drive.google.com/file/d/<id>/view --to en --voice female --bg 0`

Giới hạn: một giọng cho cả video (không tách người nói, không giữ giọng gốc), không tách được tiếng nói khỏi nhạc nền (chỉ hạ nhỏ âm gốc), không khớp khẩu hình, video có phụ đề cứng sẽ bị chồng chữ khi thêm `--subs`, lỗi nhận dạng thành lỗi dịch nên cần đọc lại các dòng nghi ngờ. Khớp thời gian đã kiểm tra bằng cách nhận dạng lại giọng lồng của hai video thử (Việt sang Anh và Anh sang Việt): từng câu bắt đầu lệch khoảng 0,2 giây so với câu gốc; chất lượng giọng chưa được nghe thử.

## Thư mục
`posts/` bài đăng · `specs/` kịch bản · `videos/` thành phẩm (`videos/clips/` cho các short cắt từ video dài, `videos/news/` cho video từ bài báo) · `work/` file trung gian · `assets/music/` nhạc · `models/` Whisper medium · `patch/` bản vá ẩn phụ đề của short-video-maker · `docker-compose.yml` server tìm clip (cổng 3123).

## Yêu cầu
Xem hướng dẫn cài đặt trong `README.md` (script `setup.ps1` hoặc `setup.sh` cài gần hết, `python check.py` kiểm tra lại). Cần Docker Desktop đang chạy (cho `/short-video` và `/news-video`), `ffmpeg`, Python 3.10-3.12 với các thư viện trong `requirements.txt`, file `.env` có `PEXELS_API_KEY`. Giọng edge-tts cần internet và đôi khi lỗi `NoAudioReceived` (script tự thử lại).
