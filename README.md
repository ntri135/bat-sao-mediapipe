# Bắt Sao — trò chơi điều khiển bằng tay

Ứng dụng dùng webcam và MediaPipe Hand Landmarker để theo dõi đầu ngón trỏ. Người chơi di chuyển ngón tay để điều khiển khay hứng sao trong 60 giây.

## Yêu cầu

- Windows 10/11, macOS hoặc Linux
- Python 3.11, 3.12 hoặc 3.13 64-bit (khuyến nghị 3.13). Python 3.15 hiện chưa phù hợp với bộ wheel NumPy/OpenCV được ghim trong project.
- Webcam và quyền truy cập camera
- Internet ở lần chạy đầu để tải model Hand Landmarker

## Cài đặt và chạy

Nếu đã tạo môi trường ảo bằng Python 3.15, hãy thoát môi trường đó và xóa thư mục môi trường cũ trước khi tạo lại bằng Python 3.13:

~~~powershell
deactivate
Remove-Item -Recurse -Force .venv
~~~

Windows PowerShell (dùng Python 3.13):

~~~powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
~~~

macOS/Linux, nếu lệnh python trỏ tới Python 3.11–3.13:

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
~~~

Lần đầu chạy, ứng dụng tải model vào models/hand_landmarker.task. Nếu camera mặc định không mở được, thử:

~~~bash
python app.py --camera 1
~~~

Bạn cũng có thể tự cung cấp model:

~~~bash
python app.py --model "C:/duong-dan/hand_landmarker.task"
~~~

Model chính thức: [Hand Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker) · Tệp model được lấy từ [Google MediaPipe model storage](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task).

## Cách chơi

1. Đứng sao cho bàn tay nằm trong khung hình, đủ sáng và cách camera khoảng 0,5–1,5 m.
2. Nhấn SPACE để bắt đầu. Di chuyển đầu ngón trỏ sang trái/phải để điều khiển khay.
3. Mỗi sao bắt được cộng 10 điểm. Sao rơi khỏi màn hình làm mất một mạng. Ván chơi kết thúc khi hết 60 giây hoặc hết 3 mạng.
4. SPACE: tạm dừng/tiếp tục; R: chơi lại; Q hoặc ESC: thoát.

## Logic chính

- MediaPipe trả về các landmark bàn tay đã chuẩn hóa theo chiều rộng và chiều cao khung hình.
- Ứng dụng lấy landmark số 8 (đầu ngón trỏ), đổi tọa độ x thành pixel và dùng nó làm vị trí đích của khay.
- Khay theo vị trí đích bằng bộ lọc trung bình mũ: x_khay ← x_khay + 0,32 × (x_đích − x_khay).
- Mỗi sao được sinh với vị trí ngang, vận tốc rơi và bán kính ngẫu nhiên. Va chạm xảy ra khi sao đến vùng khay và khoảng cách ngang không vượt quá nửa chiều rộng khay cộng bán kính sao.
- Bắt sao: điểm += 10; để sao rơi: mạng -= 1.

## Cấu trúc

~~~text
app.py           Ứng dụng webcam, MediaPipe và luật chơi
requirements.txt Thư viện Python
README.md        Cài đặt, chạy và hướng dẫn chơi
DEMO.md          Kịch bản quay demo ngắn
report.pdf       Báo cáo assignment
report.md        Bản văn bản có thể chỉnh sửa của báo cáo
assets/          Hình minh họa luồng xử lý và giao diện
~~~

## Đóng góp và giới hạn

Phần nhận diện landmark được MediaPipe cung cấp; ánh xạ đầu ngón tay sang khay, lọc chuyển động, sinh vật thể, phát hiện va chạm, tính điểm, mất mạng và kết thúc ván là logic của ứng dụng. Kết quả còn phụ thuộc ánh sáng, vị trí tay, webcam và hiệu năng máy. Bài nộp cần kèm video quay ứng dụng chạy thực tế; README và báo cáo không thay thế video đó.

## Tạo repository để nộp

Trong thư mục project:

~~~bash
git init
git add app.py README.md requirements.txt DEMO.md report.md report.pdf assets
git commit -m "Build MediaPipe hand-controlled catch game"
~~~

Sau đó tạo repository GitHub và thêm remote theo URL do GitHub cung cấp.
