# K-Audio

K-Audio là ứng dụng desktop Python/PySide6 hỗ trợ quy trình làm truyện nói và video: tải truyện, tách/làm sạch chương, tổng hợp giọng nói, clone giọng, xử lý nhiều người nói, tạo phụ đề và dựng video.

> Repository chỉ chứa mã nguồn. Model AI, giọng mẫu, API key, nội dung truyện và file xuất **không được đưa lên GitHub**.

## Tính năng chính

- Crawl truyện từ các website được hỗ trợ và lưu thành chương.
- Đọc TXT, EPUB, DOCX và PDF; tách và làm sạch chương.
- TTS bằng Edge TTS, gTTS và OmniVoice; xuất WAV và SRT.
- Quản lý/clone giọng, phân tích nhiều người nói bằng Whisper và pyannote.
- Tạo/chỉnh SRT, VTT và style phụ đề.
- Story Maker và dựng video bằng FFmpeg với transition, Ken Burns và overlay.
- Cấu hình API cho các dịch vụ AI tùy chọn.

Chỉ sử dụng nội dung và giọng nói mà bạn sở hữu hoặc có quyền sử dụng. Không dùng voice cloning để mạo danh, lừa đảo hoặc xâm phạm quyền riêng tư.

## Yêu cầu

- Windows 10/11 64-bit.
- Python 3.11 hoặc 3.12 được khuyến nghị. Dự án đã được kiểm tra cú pháp và UI trên Python 3.14, nhưng một số gói AI tùy chọn có thể chưa hỗ trợ 3.14.
- FFmpeg và `ffprobe` có trong biến môi trường `PATH` nếu dùng ghép âm thanh, phụ đề hoặc video.
- GPU NVIDIA/CUDA được khuyến nghị cho OmniVoice và nhận dạng giọng nói; CPU vẫn dùng được nhưng chậm.
- Khoảng 5–8 GB dung lượng trống cho môi trường Python và model OmniVoice.

## Cài đặt

Mở PowerShell tại thư mục dự án:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Nếu dùng GPU NVIDIA, nên cài `torch` và `torchaudio` đúng phiên bản CUDA theo hướng dẫn chính thức của PyTorch trước khi cài `requirements.txt`.

Tính năng phân tách người nói là tùy chọn:

```powershell
pip install "pyannote.audio>=3.1"
```

Sau đó nhập Hugging Face token trong **Cài đặt**. Tài khoản/token cần được cấp quyền với model pyannote mà ứng dụng sử dụng.

### Cài FFmpeg

Cài FFmpeg cho Windows, thêm thư mục chứa `ffmpeg.exe` và `ffprobe.exe` vào `PATH`, rồi kiểm tra:

```powershell
ffmpeg -version
ffprobe -version
```

### Cài model OmniVoice

Không commit model vào Git. Model chính khoảng 3,1 GB và ứng dụng tìm model tại:

```text
data/models/models--k2-fsa--OmniVoice/
```

Cách được khuyến nghị là tải trực tiếp từ nguồn chính thức:

```powershell
pip install -U huggingface_hub
hf download k2-fsa/OmniVoice --local-dir "data/models/models--k2-fsa--OmniVoice"
```

Bạn cũng có thể mở màn hình **OmniVoice** và dùng chức năng tải model của ứng dụng khi đang online. Sau khi tải xong, bật **Offline mode** trong Cài đặt nếu không muốn ứng dụng truy cập mạng cho model.

Lưu ý giấy phép: mã OmniVoice là Apache-2.0, nhưng model pretrained hiện được tác giả công bố theo **CC-BY-NC**; audio tokenizer đi kèm còn chịu Boson Higgs Audio 2 Community License. Vì vậy không mặc định dùng model cho mục đích thương mại và không phân phối lại weights nếu chưa tự kiểm tra đầy đủ điều khoản.

### Thêm giọng mẫu

Đặt dữ liệu giọng do bạn sở hữu quyền sử dụng trong `data/voices/`. Mỗi giọng thường gồm:

```text
Ten_Giong.wav   # audio tham chiếu sạch
Ten_Giong.txt   # lời đọc tương ứng
Ten_Giong.json  # metadata của giọng
```

Không đưa thư mục này lên GitHub. Chỉ clone giọng khi có sự đồng ý rõ ràng của người nói.

## Chạy ứng dụng

Sau khi đã kích hoạt môi trường ảo:

```powershell
python main.py
```

Hoặc chạy `run.bat`. Script này kiểm tra Python, cài dependency trong `requirements.txt`, tạo các thư mục cần thiết rồi mở K-Audio.

Quy trình ngắn:

1. Vào **Cài đặt**, chọn thiết bị, thư mục output và nhập API key nếu cần.
2. Dùng **Crawl** hoặc **Tách chương** để chuẩn bị văn bản.
3. Dùng **Làm sạch** và kiểm tra bản xem trước trước khi ghi kết quả.
4. Chọn **TTS Cơ bản**, **OmniVoice**, **Voice Clone** hoặc **Multi-Speaker** để tạo audio.
5. Dùng **Style Sub** và **Story Maker** nếu cần phụ đề/video.

API key được lưu cục bộ trong `config/settings.json`. File này đã bị `.gitignore` loại khỏi Git. Có thể sao chép `config/settings.example.json` thành `config/settings.json` rồi nhập giá trị qua giao diện; tuyệt đối không commit file thật.

## Kiểm tra

```powershell
python -m unittest discover -s tests -v
```

Một bài kiểm tra pass không bảo đảm các dịch vụ online, model lớn, GPU hoặc website crawl vẫn hoạt động; các phần đó cần được kiểm tra trong chính môi trường sử dụng.

## Những gì được đưa lên GitHub

| Nhóm | Đưa lên | Ghi chú |
|---|---:|---|
| `app/`, `process/`, `tests/`, `main.py` | Có | Mã ứng dụng và kiểm thử |
| `omnivoice/` | Có điều kiện | Mã upstream Apache-2.0; phải giữ license/attribution |
| `requirements.txt`, `run.bat` | Có | Cài đặt và khởi chạy |
| `assets/` rỗng hoặc asset tự sở hữu | Có | Chỉ commit icon/font/media có quyền phân phối |
| `data/models/` | Không | Hơn 3 GB; model có giấy phép riêng, dùng local |
| `data/voices/` | Không | Dữ liệu giọng riêng tư và quyền nhân thân |
| `config/*.json` | Không | Có API key, token, đường dẫn và session người dùng |
| `config/settings.example.json` | Có | Mẫu rỗng, không chứa credential |
| Audio, video, SRT/VTT và output | Không | Nội dung người dùng/file sinh ra |
| `__pycache__`, `.pyc`, venv, log, temp | Không | File máy cục bộ/file sinh tự động |
| `_debug_clean.py`, `hemtruyen_chapter.html`, `0711.srt` | Không | Artifact debug/mẫu cục bộ chưa xác minh bản quyền |

Các quy tắc trên đã được cấu hình trong `.gitignore`. Trước mỗi lần push nên chạy:

```powershell
git status --short
git ls-files | Select-String -Pattern "config/.*\.json|data/models|data/voices|\.(wav|mp3|mp4|srt)$"
```

## Bản quyền và giấy phép

- Phần mã K-Audio chưa có nguồn gốc bên thứ ba được xác minh: xem `LICENSE`. Không có quyền tái sử dụng mặc định ngoài quyền xem/fork do GitHub cung cấp.
- Mã vendored trong `omnivoice/`: Apache License 2.0, bản quyền các tác giả/upstream tương ứng.
- Model `k2-fsa/OmniVoice`: model card hiện ghi CC-BY-NC; không nằm trong repository này.
- Audio tokenizer: Boson Higgs Audio 2 Community License; không nằm trong repository này.
- Edge TTS, Google TTS, FFmpeg, PyTorch, Hugging Face, pyannote và các dependency khác là dự án/dịch vụ độc lập với điều khoản riêng.

Người đóng góp phải bảo đảm họ có quyền với code, truyện, hình, nhạc, font, giọng và dataset đã thêm. README này không phải tư vấn pháp lý; trước khi thương mại hóa cần tự rà soát điều khoản hiện hành của từng model và dịch vụ.

## Trạng thái

K-Audio đang trong giai đoạn hoàn thiện. Hãy sao lưu dữ liệu trước khi xử lý hàng loạt và kiểm tra output trước khi xuất bản.

