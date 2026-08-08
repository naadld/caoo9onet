# HƯỚNG DẪN VẬN HÀNH DỰ ÁN ABEKA VIDEO SCRAPER (huongdan.md)

Tệp này lưu trữ toàn bộ **Quy trình chuẩn (SOP)** và **Quy tắc an toàn hệ thống** cho AI Agent (Antigravity) mỗi khi khởi tạo session làm việc với người dùng.

---

## 🎯 1. Yêu Cầu Và Quy Trình Chuẩn Mỗi Khi Kích Hoạt

Khi người dùng đưa ra yêu cầu cào dữ liệu (ví dụ: *"chạy Lớp 4"*, *"cào Lớp 2 và Lớp 5"*, hoặc *"chạy tự động"*), Agent bắt buộc phải tuân thủ đúng **3 Bước Chuẩn Độc Lập** sau:

### 🔹 BƯỚC 1: CÀO VIDEO & ĐẨY SANG GOOGLE DRIVE (Step 1)
* **QUY TẮC PHÂN BỔ LỚP (GRADE EXEMPTION & PRIORITY)**:
  * 📌 **TIEU CHUẨN XÁC MINH HOÀN THÀNH 100% (STRICT COMPLETION CRITERIA)**:
    Một Lớp chỉ được coi là hoàn thành 100% và đưa vào **Danh sách loại trừ (Exemption list)** khi thỏa mãn đủ **3 điều kiện thực tế**:
    1. Đã cào đủ **170/170 Ngày học**.
    2. Trong mỗi thư mục Ngày (`Ngày xxx`), **phải có đầy đủ tất cả thư mục Môn học (Subjects)** theo khung chương trình.
    3. Trong từng thư mục Môn học, **phải có tệp video `.mp4` hoàn chỉnh, dung lượng hợp lệ (> 100 KB), không lỗi stream và xem được bình thường**.
  * 🎯 **Thứ tự ưu tiên cào**: Cào theo thứ tự **từ nhỏ đến lớn** (Các lớp đã hoàn thành 100%: `K4`, `K5`, `Grade 1`, `Grade 2`, `Grade 3`, `Grade 4`, `Grade 5`, `Grade 6`, `Grade 7`, `Grade 8`, `Grade 9`, `Grade 10`).
  * 📌 **Cặp đang cào hiện tại**: `Grade 11 & Grade 12 (11-12)`.
* **Cấu hình lớp theo yêu cầu của người dùng**:
  * **Chạy đơn 1 Lớp** (Ví dụ: *Chạy Lớp 4*): Cấu hình `TARGET_PAIRS = [["Grade 4"]]` trong `scripts/step1_direct_stream.py`.
  * **Chạy cặp song song** (Ví dụ: *Grade 1 & Grade 3*): Cấu hình `TARGET_PAIRS = [["Grade 1", "Grade 3"]]`.
  * **Chạy tự động thứ tự chuẩn (từ nhỏ đến lớn)**: Cấu hình mảng 14 lớp:
    `TARGET_PAIRS = [["K4", "K5"], ["Grade 1", "Grade 3"], ["Grade 2", "Grade 4"], ["Grade 5", "Grade 6"], ["Grade 7", "Grade 8"], ["Grade 9", "Grade 10"], ["Grade 11", "Grade 12"]]`.
* **Cơ chế nạp 2 bước nguyên tử (Chống tạo thư mục rác)**:
  * Tải video từ `o9o.net` về thư mục tạm `.tmp_stream/{uuid}/` trên máy chủ.
  * Chỉ khi video **tải hoàn tất 100%** (xác minh dung lượng > 100 KB và không lỗi), lệnh mới thực hiện `rclone copyto` đẩy file sang Google Drive (`Abeka_Videos/{Grade}/Ngày {day}/{subject}/{file}.mp4`).
  * Nếu quá trình tải bị hủy hoặc đứt mạng: Tệp tạm bị xóa ngay lập tức, **tuyệt đối không khởi tạo thư mục rỗng/rác trên Google Drive**.
* **Xác thực luồng & Định dạng MP4 chuẩn nguyên bản**:
  * Luôn truyền cờ `--referer "https://www.o9o.net/"` và `--user-agent` cho `yt-dlp`.
  * **BẮT BUỘC CHUYỂN ĐỔI CHUẨN MP4**: Luôn truyền cờ `--remux-video mp4` cho `yt-dlp` để `ffmpeg` tự động chuyển đổi luồng MPEG-TS (`.ts`) thành tệp MP4 chuẩn nguyên bản (MPEG-4 / H.264), đảm bảo tất cả file video trên Google Drive 100% là chuẩn MP4 phát được trên trình duyệt, Google Drive Web Previewer, iOS và Android.

### 🔹 BƯỚC 1.2: CÀO THEO GRADE & NGÀY HỌC CHỈ ĐỊNH (Step 1.2)
* Xem chi tiết file hướng dẫn: [`step1.2/huongdanstep12.md`](file:///media/vpsg24gb/DATA1/o9o/step1.2/huongdanstep12.md).
* Khi cần cào nhanh hoặc bổ sung 1 Ngày học bất kỳ của 1 Grade:
  ```bash
  python3 /media/vpsg24gb/DATA1/o9o/step1.2/step1_2_date_scraper.py --grade "<GRADE>" --day <DAY>
  ```

### 🔹 BƯỚC 2: TẠO CHỈ MỤC & ĐỒNG BỘ DASHBOARD ONLINE (Step 2 & Upload)
* Sau khi cào xong bài học:
  1. Chạy `scripts/step2_link_database.py` để quét lại toàn bộ file ID trên Google Drive (bao gồm **tất cả các Lớp**, kể cả những Lớp đã 100% như Grade 2 & Grade 5) để biên dịch lại tệp `index_songsong.html` đầy đủ chứa link phát video trực tuyến cho toàn bộ học sinh.
  2. Chạy `scripts/upload_to_gdrive.py` để upload đè file `index_songsong.html` lên Google Drive File ID `17-iAoi4fK8DuxX7ucDBEvJbtLj4Q2rkX`.

### 🔹 BƯỚC 3: GHI LOG GOOGLE DOC & ĐỒNG BỘ GITHUB (Step 3 & Git)
* **Ghi log vào Google Doc (`1Ew8UPThE2yN9S7EEzeeToUxZCMNpWbkNqhOfpsqXPBw`)**:
  * Định dạng dòng log: `YYYY-MM-DD HH:MM:SS: Hoàn thành [Lớp], [Ngày], [Môn]` hoặc `[Lỗi cào...]`.
  * **BẮT BUỘC MÚI GIỜ GMT+7 (Giờ Việt Nam)**: Sử dụng `datetime.now(timezone(timedelta(hours=7)))`.
  * Chuẩn hóa khóa private key (`replace("\\n", "\n")`) để không bao giờ bị lỗi `Invalid JWT Signature`.
* **Đồng bộ GitHub**: Commit & Push toàn bộ mã nguồn và tệp `index_songsong.html` mới nhất về nhánh `main` của repository GitHub `naadld/caoo9onet`.

---

## 🔒 2. Quy Tắc An Toàn Hệ Thống Tuyệt Đối (Strict Safety Rules)

1. **KHÔNG DÙNG LỆNH `rclone move`**: Tất cả các thao tác đẩy dữ liệu sang Google Drive đều **chỉ được phép dùng `rclone copy` hoặc `rclone copyto`** để tránh tuyệt đối việc xóa nhầm thư mục có sẵn của người dùng thành rác.
2. **CÔ LẬP TỆP TẠM (UUID)**: Mỗi bài học khi tải tạm phải dùng một thư mục chứa tạm riêng biệt bằng mã UUID (`.tmp_stream/{uuid}/`) cùng tham số `--paths` cho `yt-dlp` để tránh xung đột file `--Frag2` khi chạy song song.
3. **CHẠY TRÊN GITHUB CLOUD**: Quá trình cào chính thức chạy trên GitHub Actions Cloud (`.github/workflows/1_scraper_stream.yml`), không chiếm dụng CPU/RAM của máy VPS local.
4. **THỰC TẾ TRƯỚC, BÁO CÁO SAU**: Chỉ báo cáo hoàn thành khi đã verified empirical size của tệp video trên Google Drive (> 0 MB).

---

## 🛠️ 3. Lệnh Tắt Kích Hoạt Nhanh Qua Terminus / SSH

* **Kích hoạt lượt cào trên GitHub Cloud**:
  ```bash
  curl -s -X POST -H "Accept: application/vnd.github+json" -H "Authorization: Bearer YOUR_GITHUB_PAT" https://api.github.com/repos/naadld/caoo9onet/actions/workflows/1_scraper_stream.yml/dispatches -d '{"ref":"main"}'
  ```
* **Chạy script trigger có sẵn**:
  ```bash
  bash /media/vpsg24gb/DATA1/o9o/trigger_download.sh
  ```
