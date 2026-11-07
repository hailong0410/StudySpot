# ICA14 — Bài đã được đẩy lên GitHub

## Link để nộp Brightspace

https://github.com/hailong0410/StudySpot/tree/refactor/ica14-pricing

Nhánh này có code ICA14, 24 test gốc không đổi, lịch sử commit từng bước và REFACTOR_NOTES.md ở ngoài cùng repository. Bạn chỉ cần sao chép link nhánh để nộp theo yêu cầu đề. Không cần tự tạo nhánh hay push lại. Việc nộp Brightspace vẫn cần bạn thực hiện.

## Xem bài

- REFACTOR_NOTES.md ở ngoài cùng: ba worksheet, số đo, log và đánh đổi.
- ICA14/legacy_pricing.py: code đã refactor.
- ICA14/test_legacy_pricing.py: test gốc.
- ICA14/evidence/: kết quả kiểm tra và bản code gốc để đối chiếu.

Bài này là bài tập độc lập đặt trong repository StudySpot. Module pricing không được tích hợp vào ứng dụng StudySpot.

## Chạy trên Windows

Sau khi clone repository và chuyển sang nhánh refactor/ica14-pricing, mở Terminal tại thư mục gốc:

```powershell
cd ICA14
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe verify_behavior.py
.venv\Scripts\python.exe -m radon cc -s -a legacy_pricing.py
.venv\Scripts\python.exe -m radon mi -s legacy_pricing.py
```

Kết quả: 24 passed; 27,000 cases matched; calc CC 3, hàm cao nhất CC 9, MI 49.77.

## Nắm cách tính giá

Giá gốc × số lượng → giảm theo người dùng → giảm số lượng → coupon → phụ phí waitlist → chặn số âm → phí dịch vụ → làm tròn.

Ví dụ 5 lecture cho sinh viên verified với HALFOFF: 25 → 20 → 15 → 7.5 → cộng phí 1 = 8.50 USD.

CC của calc giảm 31 xuống 3 nhờ tách hàm. MI giảm nhẹ từ 53.94 xuống 49.77, vẫn hạng A; báo cáo ghi rõ đánh đổi. Bài được chuẩn bị với AI; hãy đọc code và chạy lại để giải thích được khi thầy hỏi.
