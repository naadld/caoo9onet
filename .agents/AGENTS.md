# Guidelines cho Project O9O

## Cấu hình cào (Scraping) trong file `step1_direct_stream.py`

Khi thực hiện việc thay đổi các cặp Grade tiếp theo (ví dụ chuyển từ Grade 7-8 sang Grade 9-10), cần ghi nhớ các điểm sau:

1. **Giới hạn phạm vi GDrive Index:**
   Tool hiện tại đã được tối ưu để CHỈ quét index thư mục tương ứng với cặp Grade đang được cấu hình trong biến `TARGET_PAIRS` hoặc `active_pairs`. TUYỆT ĐỐI không rollback lại thành quét toàn bộ root folder (`rclone lsf -R REMOTE_BASE`) vì hệ thống đã lưu lượng file lớn của các Grade 1-6 và K4-K5. Việc quét toàn bộ sẽ gây timeout 60s/120s dẫn đến tool hiểu nhầm GDrive trống trơn và tải lại từ đầu, gây lãng phí dung lượng và CPU.

2. **Cơ chế Local Database Cache:**
   Script đang sử dụng cơ chế đọc `database_Grade X.json` để bỏ qua các bài đã tải thành công. Khi chạy cấu hình cặp Grade mới, cơ chế này sẽ tự động load đúng json của Grade đó để tối ưu thời gian.

3. **Yêu cầu BẮT BUỘC về xử lý video (Không stream trực tiếp dạng Pipe):**
   *Nguồn của trang web o9o là các file dạng `.m3u8` (chia nhỏ thành `.ts`).*
   - KHÔNG ĐƯỢC dùng cơ chế True Pipe Streaming (ví dụ: `yt-dlp -o - | rclone rcat`) để ghi thẳng lên Google Drive.
   - Nguyên nhân 1: Nếu ghi nguyên bản `.ts`, video sẽ không phải là chuẩn `.mp4` đầy đủ.
   - Nguyên nhân 2: Nguồn video có dính lỗi timestamp âm (`negative_ts`), nếu không qua xử lý sẽ bị lỗi đen khung hình ở giây 0:00 (Frame 0:00 bị đen) và không tua (seek) được trên trình duyệt.
   - Bắt buộc phải lưu tạm vào ổ cứng local (thư mục `.tmp_stream`), giữ nguyên flag `--remux-video mp4` và `--postprocessor-args "ffmpeg:-movflags +faststart -avoid_negative_ts make_zero"` để yt-dlp và ffmpeg chuẩn hoá file MP4 xong 100% rồi mới upload qua lệnh `rclone copyto`.

4. **Dọn dẹp thư mục rác (Temp):**
   Các video đang chờ xử lý bằng ffmpeg sẽ nằm ở `.tmp_stream/`. Nếu tool bị gián đoạn ngang chừng, thư mục này có thể phình to. Thi thoảng cần kiểm tra và xoá thư mục rác nếu báo đầy dung lượng VPS.
