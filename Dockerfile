# ── AudiToR (TOR AI) — Dockerfile ──────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# ติดตั้ง dependency ก่อน (cache layer ให้ build เร็วขึ้นรอบถัดไป)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกโค้ดแอป (backend.py + tor_generator.html)
COPY . .

# พอร์ตที่ backend.py รันอยู่ (uvicorn host=0.0.0.0 port=8000)
EXPOSE 8000

# ตัวแปร ENV จะถูกส่งเข้ามาตอน docker run (ดู checklist ข้อ 5)
# TYPHOON_API_KEY, TYPHOON_OCR_API_KEY

CMD ["python", "backend.py"]
