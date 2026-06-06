"""
TOR AI — FastAPI Backend
เชื่อมต่อกับ OpenTyphoon API (https://opentyphoon.ai)
รัน: python backend.py
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os, json
from openai import OpenAI

# ── Config ──────────────────────────────────────────────────────
# API_KEY   = os.environ.get("TYPHOON_API_KEY", "YOUR_API_KEY_HERE")
API_KEY = os.environ.get("TYPHOON_API_KEY")
BASE_URL  = "https://api.opentyphoon.ai/v1"
MODEL     = "typhoon-v2.5-30b-a3b-instruct"
PORT      = 8000

# ── FastAPI ──────────────────────────────────────────────────────
app = FastAPI(title="TOR AI Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # รับจาก file:// และทุก origin
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ── Models ───────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    prompt: str
    stream: bool = True
    temperature: float = 0.7
    max_tokens: int = 1500

# ── Routes ───────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    """ตรวจสอบว่า backend + API key พร้อมใช้งาน"""
    if API_KEY == "YOUR_API_KEY_HERE":
        raise HTTPException(status_code=401, detail="ยังไม่ได้ตั้ง TYPHOON_API_KEY")
    return {"status": "ok", "model": MODEL, "provider": "OpenTyphoon"}


@app.post("/api/generate")
def generate(req: GenerateRequest):
    """รับ prompt แล้วส่งไปที่ OpenTyphoon API พร้อม streaming"""
    if API_KEY == "YOUR_API_KEY_HERE":
        raise HTTPException(status_code=401, detail="ยังไม่ได้ตั้ง TYPHOON_API_KEY")

    def stream_generator():
        try:
            stream = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "คุณคือผู้เชี่ยวชาญด้านการจัดซื้อจัดจ้างภาครัฐไทย "
                            "ที่มีความเชี่ยวชาญในการร่างขอบเขตของงาน (TOR) "
                            "ตามมาตรฐานหนังสือเวียน กค (กวจ) 0405.4/ว 159 "
                            "ของกรมบัญชีกลาง "
                            "ตอบเป็นภาษาราชการไทยที่ถูกต้องและเป็นทางการ "
                            "ห้ามระบุยี่ห้อหรือรุ่นของสินค้าโดยตรง ให้ใช้ Functional Specification แทน "
                            "เนื้อหาในแต่ละข้อต้องสอดคล้องและสัมพันธ์กัน"
                            "ตอบเฉพาะเนื้อหาที่ถามโดยตรง ไม่ต้องมีคำนำหรือคำลงท้ายที่ไม่จำเป็น"
                        )
                    },
                    {"role": "user", "content": req.prompt}
                ],
                temperature=req.temperature,
                max_completion_tokens=req.max_tokens,
                top_p=0.6,
                frequency_penalty=0,
                stream=True,
            )
            token_count = 0
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content is not None and delta.content != "":
                    token_count += 1
                    yield json.dumps({"response": delta.content}) + "\n"
            print(f"[stream] ส่ง {token_count} tokens")
            yield json.dumps({"response": "", "done": True}) + "\n"  # sentinel
        except Exception as e:
            print(f"[stream error] {e}")
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(
        stream_generator(),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
    )


@app.get("/api/models")
def list_models():
    """ดูว่า API key นี้ใช้ model อะไรได้บ้าง"""
    if API_KEY == "YOUR_API_KEY_HERE":
        raise HTTPException(status_code=401, detail="ยังไม่ได้ตั้ง TYPHOON_API_KEY")
    try:
        models = client.models.list()
        return {"models": [m.id for m in models.data]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test")
def test_api():
    """ทดสอบ OpenTyphoon API ตรงๆ แบบไม่ stream"""
    if API_KEY == "YOUR_API_KEY_HERE":
        raise HTTPException(status_code=401, detail="ยังไม่ได้ตั้ง TYPHOON_API_KEY")
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "คุณคือผู้เชี่ยวชาญด้านการจัดซื้อจัดจ้างภาครัฐไทย"},
                {"role": "user", "content": "ตอบว่า 'ทดสอบสำเร็จ' เท่านั้น"}
            ],
            max_completion_tokens=20,
            temperature=0.6,
            top_p=0.6,
            stream=False,
        )
        content = resp.choices[0].message.content
        return {"status": "ok", "response": content, "model": MODEL}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/simple")
def generate_simple(req: GenerateRequest):
    """สำหรับทดสอบ — ไม่ stream คืน text เต็มทันที"""
    if API_KEY == "YOUR_API_KEY_HERE":
        raise HTTPException(status_code=401, detail="ยังไม่ได้ตั้ง TYPHOON_API_KEY")
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": req.prompt}],
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            stream=False,
        )
        return {"response": resp.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Run ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn, sys

    key = os.environ.get("TYPHOON_API_KEY", "")
    if not key or key == "YOUR_API_KEY_HERE":
        print("\n" + "="*55)
        print("  ⚠️  กรุณาตั้งค่า API Key ก่อนรัน backend")
        print("="*55)
        print("\n  วิธีที่ 1 — ตั้งค่าผ่าน environment variable:")
        print("    Windows CMD:")
        print("      set TYPHOON_API_KEY=sk-xxxxxxxxxxxx")
        print("      python backend.py")
        print("\n  วิธีที่ 2 — แก้ในไฟล์ backend.py บรรทัด:")
        print('      API_KEY = "sk-xxxxxxxxxxxx"')
        print("\n  สมัครรับ API Key ฟรีที่: https://opentyphoon.ai")
        print("="*55 + "\n")

        ans = input("มี API Key แล้ว? กรอกได้เลย (หรือ Enter เพื่อออก): ").strip()
        if ans:
            os.environ["TYPHOON_API_KEY"] = ans
            client = OpenAI(api_key=ans, base_url=BASE_URL)
            print(f"✅ ตั้งค่า key เรียบร้อย\n")
        else:
            sys.exit(0)

    print(f"\n🚀 TOR AI Backend รันที่ http://localhost:{PORT}")
    print(f"   Model  : {MODEL}")
    print(f"   Docs   : http://localhost:{PORT}/docs")
    print(f"   Health : http://localhost:{PORT}/api/health\n")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
