"""
TOR AI — FastAPI Backend
เชื่อมต่อกับ OpenTyphoon API (https://opentyphoon.ai)
รัน: python backend.py
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List
import os, json, io
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

class TorSection(BaseModel):
    num: int
    title: str
    content: str

class ExportRequest(BaseModel):
    title: str
    agency: str = "หน่วยงาน"
    budget: str = ""
    project_type: str = ""
    criteria: str = ""
    created_at: str = ""
    sections: List[TorSection]

# ── Routes ───────────────────────────────────────────────────────
@app.get("/")
def serve_frontend():
    """เสิร์ฟหน้า HTML หลัก"""
    html_path = os.path.join(os.path.dirname(__file__), "tor_generator.html")
    return FileResponse(html_path)

@app.post("/api/export/docx")
def export_docx(req: ExportRequest):
    """สร้างไฟล์ Word (.docx) จาก TOR ทั้ง 10 ข้อ"""
    try:
        from docx import Document as DocxDocument
        from docx.shared import Pt, Cm, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
    except ImportError:
        raise HTTPException(status_code=500, detail="กรุณาติดตั้ง python-docx ก่อน: pip install python-docx")

    try:
        doc = DocxDocument()

        # ── ตั้งค่าหน้ากระดาษ A4 มาตรฐานราชการไทย ──
        sec = doc.sections[0]
        sec.page_width    = Cm(21)
        sec.page_height   = Cm(29.7)
        sec.left_margin   = Cm(3)
        sec.right_margin  = Cm(2)
        sec.top_margin    = Cm(2.5)
        sec.bottom_margin = Cm(2.5)

        FONT = "TH Sarabun New"

        def set_font(run, size=16, bold=False):
            run.bold = bold
            run.font.size = Pt(size)
            rPr = run._element.get_or_add_rPr()
            rFonts = rPr.find(qn('w:rFonts'))
            if rFonts is None:
                rFonts = OxmlElement('w:rFonts')
                rPr.insert(0, rFonts)
            for attr in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
                rFonts.set(qn(attr), FONT)

        def add_text(para, text, bold=False, size=16, align=None):
            run = para.add_run(text)
            set_font(run, size=size, bold=bold)
            if align:
                para.alignment = align
            return run

        # ── หัวเรื่อง ──
        p = doc.add_paragraph()
        add_text(p, "ร่างขอบเขตของงาน (Terms of Reference)", bold=True, size=20,
                 align=WD_ALIGN_PARAGRAPH.CENTER)
        p = doc.add_paragraph()
        add_text(p, req.title, bold=True, size=18, align=WD_ALIGN_PARAGRAPH.CENTER)
        doc.add_paragraph()

        # ── ข้อมูลโครงการ ──
        meta = [
            ("อ้างอิง",        "หนังสือเวียน กค (กวจ) 0405.4/ว 159 ลงวันที่ 20 มีนาคม 2566"),
            ("หน่วยงาน",       req.agency),
            ("ประเภทงาน",      req.project_type),
            ("วงเงินงบประมาณ", f"{req.budget} บาท" if req.budget else "-"),
            ("หลักเกณฑ์",      req.criteria),
            ("วันที่สร้าง",     req.created_at),
        ]
        for label, value in meta:
            if value and value.strip():
                p = doc.add_paragraph()
                add_text(p, f"{label}: ", bold=True, size=16)
                add_text(p, value, bold=False, size=16)
        doc.add_paragraph()

        # ── 10 หัวข้อ TOR ──
        import re
        for s in req.sections:
            p = doc.add_paragraph()
            add_text(p, f"ข้อ {s.num}  {s.title}", bold=True, size=16)
            for line in s.content.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                # ข้ามบรรทัดที่เป็นหัวข้อซ้ำ
                line_no_num = re.sub(r'^(ข้อ\s*)?\d+[\.\s]*', '', line).strip()
                title_words = set(re.sub(r'[/\-]', ' ', s.title).split())
                line_words  = set(re.sub(r'[/\-]', ' ', line_no_num).split())
                # ถ้าคำในบรรทัดทับซ้อนกับชื่อหัวข้อ >= 60% และสั้นกว่า 60 ตัว → ข้าม
                if title_words and line_words:
                    overlap = len(title_words & line_words) / len(line_words)
                    if overlap >= 0.6 and len(line_no_num) < 60:
                        continue
                # ลดช่องว่างซ้ำซ้อนในเนื้อหา
                line = re.sub(r'[ \t]+', ' ', line).strip()
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.left_indent = Cm(1)
                p.paragraph_format.space_after = Pt(4)
                add_text(p, line, size=16)
            doc.add_paragraph()

        # ── หมายเหตุท้ายเอกสาร ──
        p = doc.add_paragraph()
        add_text(p, "หมายเหตุ: ", bold=True, size=14)
        add_text(p, "โครงร่างนี้เป็นแนวทางเบื้องต้น เจ้าหน้าที่ผู้รับผิดชอบต้องตรวจสอบและแก้ไขก่อนนำไปใช้งาน", size=14)

        # ── บันทึกและส่งกลับ ──
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        from urllib.parse import quote
        safe_title = req.title[:40].strip()
        encoded = quote(safe_title, safe='')
        filename_ascii = f"TOR_{encoded}.docx"
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=\"TOR.docx\"; filename*=UTF-8''{filename_ascii}"}
        )
    except Exception as e:
        print(f"[export error] {e}")
        raise HTTPException(status_code=500, detail=f"สร้างไฟล์ไม่สำเร็จ: {str(e)}")


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
                            "เนื้อหาในแต่ละข้อต้องสอดคล้องและสัมพันธ์กัน "
                            "ตอบเฉพาะเนื้อหาที่ถามโดยตรง ไม่ต้องมีคำนำหรือคำลงท้ายที่ไม่จำเป็น "
                            "ห้ามใช้อักขระภาษาจีน ญี่ปุ่น เกาหลี หรืออักขระพิเศษจากภาษาอื่นโดยเด็ดขาด "
                            "ใช้ตัวเลขอารบิก (1, 2, 3, 4, 5) เท่านั้น ห้ามใช้เลขไทย (๑, ๒, ๓, ๔, ๕) ในทุกกรณี "
                            "เมื่อเขียนรายการข้อย่อย ให้เริ่มต้นที่ข้อ 1 เสมอ "
                            "ห้ามแปลเนื้อหาเป็นภาษาอังกฤษโดยเด็ดขาด ห้ามมี paragraph หรือบรรทัดที่เป็นภาษาอังกฤษล้วน "
                            "ตอบเป็นภาษาไทยเท่านั้น คำศัพท์เทคนิคอาจมีภาษาอังกฤษแทรกในวงเล็บได้เท่านั้น"
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
