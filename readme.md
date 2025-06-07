# 📄 AgilTech PDF Service API

A FastAPI-based backend application for managing PDF operations including:

- 📥 Downloading files from an SFTP server
- 📎 Merging multiple PDF files
- 📦 Compressing a PDF using Ghostscript
- 🔄 Merging and then compressing PDFs

---

## 🚀 Features

- **SFTP Integration**: Downloads files from a remote SFTP directory.
- **PDF Merging**: Combines multiple PDF files into one.
- **PDF Compression**: Compresses PDFs using Ghostscript with aggressive downsampling.
- **Merge & Compress**: Efficient two-step PDF processing in a single endpoint.

---

## 🧰 Tech Stack

- **Python 3.8+**
- [FastAPI](https://fastapi.tiangolo.com/) – Web framework
- [Pydantic](https://docs.pydantic.dev/) – Data validation
- `Ghostscript` – External dependency for PDF compression

---

## 📂 Project Structure

```

agiltech-python-project/
├── main.py
├── services/
│   ├── sftp\_service.py
│   ├── merge\_pdf.py
│   ├── compress\_pdf.py
│   └── mergencompress.py
├── downloads/
├── requirements.txt
└── README.md

````

---

## ⚙️ Installation & Usage

### 1. Clone the repository

```bash
git clone https://github.com/ignacioelizeche/agiltech-python-project.git
cd agiltech-python-project
````

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Ghostscript

> Required for PDF compression to work.

* **Ubuntu/Debian**:

  ```bash
  sudo apt update && sudo apt install ghostscript
  ```

* **macOS**:

  ```bash
  brew install ghostscript
  ```

* **Windows**:

  * Download from: [https://www.ghostscript.com/download/gsdnld.html](https://www.ghostscript.com/download/gsdnld.html)
  * Add `gswin64c.exe` or `gswin32c.exe` to your system PATH.

### 4. Run the application

```bash
uvicorn main:app --reload
```

Then visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the auto-generated Swagger UI.

---

## 🧪 API Endpoints

### 📥 `POST /sftpcopy`

Downloads files from a remote SFTP directory.

```json
{
  "host": "sftp.example.com",
  "username": "user",
  "password": "pass",
  "directory": "/remote/path"
}
```

### 📎 `POST /mergepdf`

Merges multiple PDF files (present in `./downloads/`).

```json
["file1.pdf", "file2.pdf"]
```

Returns: Merged PDF file.

---

### 📦 `POST /compresspdf`

Compresses a base64-encoded PDF file using Ghostscript.

```json
{
  "file": "BASE64_ENCODED_PDF"
}
```

Returns: Compressed PDF as file download.

---

### 🔄 `POST /merge-compress`

Merges a list of files from disk and returns a **compressed base64 string**.

```json
{
  "files": ["file1.pdf", "file2.pdf"]
}
```

Returns:

```json
{
  "compressed_pdf_base64": "JVBERi0xLjQKJ..."  // shortened
}
```

---

## 🧹 File Cleanup

* Temporary files are created in `/tmp` or `./downloads`.
* Compression deletes the original uncompressed file after processing.

---

## 📄 License

MIT License. See `LICENSE` for details.

---

## 🤝 Contributing

Feel free to open issues or submit pull requests.
For major changes, please open an issue first to discuss your ideas.

---

## 👤 Author

Created by [Ignacio Elizeche](https://github.com/ignacioelizeche)

