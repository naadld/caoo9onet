# HƯỚNG DẪN VẬN HÀNH STEP 1.2: CÀO THEO GRADE VÀ NGÀY CỤ THỂ (huongdanstep12.md)

Tệp này lưu trữ **Quy trình chuẩn (SOP)** cho **AI Agent (Antigravity)** mỗi khi người dùng gọi file hướng dẫn này kèm thông tin **Grade (Lớp)** và **Ngày (Day)**.

---

## 🎯 1. Mục Đích Của Step 1.2

- **Giải quyết bài học bị thiếu**: Tải bổ sung chính xác Ngày học của Lớp bị thiếu bài mà không cần phải cào lại toàn bộ danh sách.
- **Tải nhanh theo yêu cầu**: Cho phép tải tức thì 1 ngày học bất kỳ của bất kỳ Lớp nào (K4, K5, Grade 1 đến Grade 12).
- **Ghi đè khắc phục tệp lỗi**: Hỗ trợ cờ `--force` để tải lại và thay thế video bị lỗi hoặc thiếu dung lượng trên Google Drive.

---

## 🤖 2. Quy Trình Xử Lý Của AI Agent (Antigravity) Khi Nhận Yêu Cầu

Khi người dùng cung cấp lệnh/tin nhắn chứa `huongdanstep12.md` + **Grade** + **Ngày** (Ví dụ: *"chạy huongdanstep12.md Grade 4 Ngày 15"*, *"huongdanstep12.md g2 120"*, *"huongdanstep12.md K4 day 5"*), Agent **Antigravity** sẽ lập tức thực hiện các bước sau:

### 🔹 Bước 1: Chuẩn Hóa Tham Số Đầu Vào
Agent tự động nhận diện và chuẩn hóa tên Lớp và Số Ngày:
- **Tên Lớp (Grade)**:
  - `k4`, `K4`, `0` ➔ `K4`
  - `k5`, `K5` ➔ `K5`
  - `g1`, `1`, `01`, `grade 1` ➔ `Grade 1`
  - `g4`, `4`, `04`, `grade 4` ➔ `Grade 4`
  - `g12`, `12`, `grade 12` ➔ `Grade 12`
- **Số Ngày (Day)**: Nhận diện các giá trị số từ `1` đến `170` (Ví dụ: `15`, `015`, `120`).

### 🔹 Bước 2: Thực Thi Lệnh Scraper Step 1.2
Agent chạy lệnh Python trực tiếp trong thư mục dự án `/media/vpsg24gb/DATA1/o9o`:

```bash
python3 /media/vpsg24gb/DATA1/o9o/step1.2/step1_2_date_scraper.py --grade "<GRADE_CHUAN_HOA>" --day <SO_NGAY>
```

#### Các ví dụ câu lệnh chạy thực tế:
1. **Chạy Lớp 4, Ngày 15 (Chế độ thường - bỏ qua bài đã có)**:
   ```bash
   python3 /media/vpsg24gb/DATA1/o9o/step1.2/step1_2_date_scraper.py --grade "Grade 4" --day 15
   ```

2. **Chạy Lớp 2, Ngày 120 (Chế độ Ép tải / Ghi đè file cũ)**:
   ```bash
   python3 /media/vpsg24gb/DATA1/o9o/step1.2/step1_2_date_scraper.py --grade "Grade 2" --day 120 --force
   ```

3. **Chạy K4, Ngày 5**:
   ```bash
   python3 /media/vpsg24gb/DATA1/o9o/step1.2/step1_2_date_scraper.py --grade "K4" --day 5
   ```

---

## ⚙️ 3. Quy Trình Tự Động Hoàn Chỉnh Của Script Step 1.2

Khi tệp `step1_2_date_scraper.py` khởi chạy, hệ thống sẽ tự động thực hiện trọn gói quy trình 5 bước sau:

1. **Khóa chống trùng lặp (Grade-Day Lock)**: Khởi tạo tệp `.lock` riêng cho từng cặp `Grade_Day` để tránh xung đột khi chạy song song.
2. **Cào & Tải nguyên tử (Atomic Stream & Upload)**:
   - Tải video từ `o9o.net` về thư mục tạm `.tmp_stream/{uuid}/` và chuyển đổi sang MP4 chuẩn nguyên bản (`--remux-video mp4`).
   - Kiểm tra dung lượng tệp (> 100 KB).
   - Đẩy trực tiếp sang Google Drive (`vpsg24gb.aleron:`) bằng `rclone copyto`.
3. **Cập nhật Cơ sở dữ liệu (Database)**: Cập nhật tệp `database_{Grade}.json`.
4. **Nhật ký & Thông báo**:
   - Ghi log thời gian thực GMT+7 vào Google Doc (`1Ew8UPThE2yN9S7EEzeeToUxZCMNpWbkNqhOfpsqXPBw`).
   - Gửi thông báo bắt đầu và kết thúc qua Telegram Bot.
5. **Đồng bộ Web Dashboard & GitHub**:
   - Tự động quét lại ID Google Drive (`step2_link_database.py`).
   - Tự động đẩy file `index_songsong.html` lên Google Drive (`upload_to_gdrive.py`).
   - Tự động `git commit` và `git push` về repository GitHub `naadld/caoo9onet`.

---

## 💡 4. Gợi Ý Sử Dụng Cho Người Dùng

Chỉ cần gọi Antigravity agent theo cú pháp ngắn gọn:
> *"Em chạy cho anh file huongdanstep12.md với Grade 4 Ngày 15"*  
> *"huongdanstep12.md K5 010"*  
> *"huongdanstep12.md g3 day 50 --force"*  

Agent Antigravity sẽ tự động đọc tệp hướng dẫn này, kích hoạt `step1_2_date_scraper.py` và báo cáo kết quả hoàn tất cho bạn!
