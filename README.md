# K-Audio

K-Audio là ứng dụng desktop mã nguồn mở dành cho quy trình sản xuất truyện nói, audiobook, phụ đề và video. Ứng dụng được viết bằng Python/PySide6, tập trung vào thao tác trực quan, xử lý hàng loạt và khả năng chạy AI cục bộ.

## Tính năng

- Crawl truyện từ nhiều website được hỗ trợ.
- Đọc TXT, EPUB, DOCX và PDF; tách và làm sạch chương.
- TTS bằng Edge TTS, Google TTS và OmniVoice.
- Quản lý giọng mẫu, voice cloning và điều chỉnh audio.
- Nhận dạng giọng nói, diarization và xử lý nhiều nhân vật.
- Tạo, chỉnh sửa và style phụ đề SRT/VTT.
- Story Maker, chia cảnh và dựng video bằng FFmpeg.
- Chạy offline sau khi model đã được tải.

## Yêu cầu

- Windows 10/11 64-bit.
- Python 3.11 hoặc 3.12 được khuyến nghị.
- FFmpeg nếu sử dụng audio, phụ đề hoặc video.
- GPU NVIDIA/CUDA được khuyến nghị cho OmniVoice, Whisper và diarization.
- Khoảng 5–8 GB dung lượng trống nếu cài model AI cục bộ.

K-Audio có thể chạy trên CPU, nhưng những tác vụ AI lớn sẽ chậm hơn đáng kể.

## Cài đặt

### 1. Tải mã nguồn

```powershell
git clone https://github.com/trungkien2002/K-Audio.git
cd K-Audio
```

### 2. Tạo môi trường Python

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Nếu dùng GPU NVIDIA, hãy cài `torch` và `torchaudio` phù hợp với phiên bản CUDA theo hướng dẫn của PyTorch trước khi cài các dependency còn lại.

### 3. Cài FFmpeg

Cài FFmpeg, thêm thư mục chứa `ffmpeg.exe` và `ffprobe.exe` vào biến môi trường `PATH`, sau đó kiểm tra:

```powershell
ffmpeg -version
ffprobe -version
```

### 4. Tạo cấu hình cá nhân

```powershell
Copy-Item config/settings.example.json config/settings.json
```

API key và thiết lập có thể nhập trong màn hình **Cài đặt**. `config/settings.json` chỉ được lưu cục bộ và đã bị loại khỏi Git.

## Cài model OmniVoice

Model không được đóng gói trong repository vì có dung lượng lớn và giấy phép riêng.

```powershell
pip install -U huggingface_hub
hf download k2-fsa/OmniVoice --local-dir "data/models/models--k2-fsa--OmniVoice"
```

Bạn cũng có thể tải model từ màn hình **OmniVoice**. Sau khi tải xong, có thể bật **Offline mode** trong Cài đặt.

> Mã OmniVoice sử dụng Apache-2.0, nhưng model pretrained hiện được phát hành theo CC-BY-NC. Audio tokenizer đi kèm có Boson Higgs Audio 2 Community License. Hãy đọc điều khoản hiện hành trước khi sử dụng thương mại hoặc phân phối lại.

## Diarization nhiều người nói

Đây là dependency tùy chọn:

```powershell
pip install "pyannote.audio>=3.1"
```

Nhập Hugging Face token trong **Cài đặt**. Tài khoản của bạn phải được cấp quyền truy cập model pyannote tương ứng.

## Thêm giọng tham chiếu

Tạo `data/voices` và đặt mỗi giọng theo cấu trúc:

```text
data/voices/
├── Ten_Giong.wav
├── Ten_Giong.txt
└── Ten_Giong.json
```

- `.wav`: audio tham chiếu sạch.
- `.txt`: nội dung được đọc trong audio.
- `.json`: metadata của giọng.

Chỉ sử dụng giọng của chính bạn hoặc giọng đã được cho phép. Dữ liệu trong `data/voices` không được Git theo dõi.

## Chạy ứng dụng

```powershell
.\run.bat
```

Hoặc chạy trong môi trường Python đã cài dependency:

```powershell
python main.py
```

## Sử dụng nhanh

1. Mở **Cài đặt** để chọn thiết bị, thư mục output và API provider.
2. Dùng **Crawl** hoặc **Tách chương** để chuẩn bị văn bản.
3. Mở **Làm sạch**, chọn quy tắc và xem bản so sánh trước khi ghi file.
4. Tạo audio bằng **TTS Cơ bản**, **OmniVoice**, **Voice Clone** hoặc **Multi-Speaker**.
5. Chỉnh phụ đề trong **Style Sub**.
6. Dùng **Story Maker** để chia cảnh và dựng video.

Nên thử một chương ngắn trước khi chạy hàng loạt.

## Kiểm thử

```powershell
python -m unittest discover -s tests -v
```

Test tự động không bao phủ toàn bộ dịch vụ online, website, GPU hoặc model lớn. Khi đóng góp cho những phần này, hãy ghi rõ môi trường và cách kiểm tra thủ công trong pull request.

## Cấu trúc dự án

```text
K-Audio/
├── app/                 # Giao diện PySide6
├── process/             # Crawl, cleaner, TTS, STT, phụ đề và video
├── omnivoice/           # Mã OmniVoice được tích hợp
├── tests/               # Kiểm thử tự động
├── config/              # Cấu hình mẫu
├── assets/              # Icon, font và media tùy chọn
├── main.py              # Entrypoint
├── requirements.txt
└── run.bat
```

Model, voice, API key, nội dung người dùng và output không nằm trong repository.

## Đóng góp

Issue và pull request đều được hoan nghênh.

1. Fork repository và tạo branch từ `main`.
2. Giữ thay đổi tập trung vào một vấn đề cụ thể.
3. Không commit API key, model weights, voice cá nhân hoặc nội dung có bản quyền.
4. Thêm hoặc cập nhật test khi thay đổi logic.
5. Chạy toàn bộ test trước khi gửi pull request.
6. Mô tả rõ phần đã kiểm tra runtime và phần chỉ được kiểm tra tĩnh.

## Sử dụng có trách nhiệm

- Không dùng voice cloning để mạo danh, lừa đảo hoặc gây nhầm lẫn.
- Không crawl, sao chép hoặc xuất bản nội dung khi chưa có quyền.
- Không chia sẻ API key, Hugging Face token hoặc dữ liệu giọng cá nhân.
- Tuân thủ điều khoản của website, model, API provider và pháp luật áp dụng.

## Giấy phép

Mã nguồn K-Audio được phát hành theo [Apache License 2.0](LICENSE).

Model, model weights, tokenizer, voice, nội dung người dùng và dịch vụ bên thứ ba không tự động thuộc giấy phép K-Audio. Xem [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) để biết chi tiết.
