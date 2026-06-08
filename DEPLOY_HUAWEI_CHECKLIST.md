# Checklist: Deploy AudiToR ขึ้น Huawei Cloud (Flexus L Instance)

ใช้สำหรับเปิดลิงก์ทดลองใช้งาน ~7 วัน บน free package ของ Huawei Cloud

---

## ขั้นที่ 1 — สมัครแพ็กเกจฟรี
1. เข้า https://activity.huaweicloud.com/intl/th-th/free_packages/index.html
2. หาการ์ด **"Huawei Cloud Flexus L Instance"** (2 vCPU, 4 GiB, ดิสก์ 80 GB) → กด "ลองเลย"
3. เลือก Region เป็น **AP-Singapore** (ใกล้ไทย เน็ตเร็วกว่า Hong Kong สำหรับผู้ใช้ในไทย)
4. เลือก OS เป็น **Ubuntu 22.04** (หรือเวอร์ชันใกล้เคียงที่มีให้)
5. ตั้งรหัสผ่าน/คีย์ SSH เก็บไว้ให้ดี แล้วกดสร้างเครื่อง รอจนสถานะ "Running"

## ขั้นที่ 2 — เปิด Security Group (firewall)
1. ไปที่หน้า instance → แท็บ Security Groups
2. เพิ่ม Inbound rule:
   - Port 22 (SSH) — source: IP ของคุณ (ปลอดภัยกว่า 0.0.0.0/0)
   - Port 8000 (แอป) — source: 0.0.0.0/0 (ให้ทุกคนเข้าได้ชั่วคราว 7 วัน)
3. บันทึก แล้วจด Public IP ของเครื่องไว้

## ขั้นที่ 3 — SSH เข้าเครื่อง
```
ssh root@<PUBLIC_IP>
```
(ใช้ PuTTY บน Windows ถ้าไม่มี ssh client)

## ขั้นที่ 4 — ติดตั้ง Docker
```bash
apt update && apt install -y docker.io
systemctl enable --now docker
docker --version
```

## ขั้นที่ 5 — อัปโหลดโค้ด
จากเครื่องคุณ (Windows, ใช้ scp หรือ WinSCP):
```
scp -r D:\TOR_AI\Program root@<PUBLIC_IP>:/root/audiTOR
```
(หรือ git clone จาก repo ที่ push ไว้แล้ว)

## ขั้นที่ 6 — Build และรัน container
บนเครื่อง Huawei Cloud (ผ่าน SSH):
```bash
cd /root/audiTOR
docker build -t auditor-app .

docker run -d \
  --name auditor \
  -p 8000:8000 \
  -e TYPHOON_API_KEY="sk-xxxxxxxxxxxx" \
  -e TYPHOON_OCR_API_KEY="sk-xxxxxxxxxxxx" \
  --restart unless-stopped \
  auditor-app
```
> แทนที่ `sk-xxxx` ด้วยคีย์จริงของคุณ — **ห้ามใส่คีย์ลงในโค้ดที่ push ขึ้น public repo**

## ขั้นที่ 7 — ทดสอบ
1. เปิดเบราว์เซอร์ไปที่ `http://<PUBLIC_IP>:8000`
2. ตรวจว่าโหลดหน้า AudiToR ขึ้น และสถานะ Backend แสดง "พร้อมใช้งาน"
3. ลองใช้งานแต่ละแท็บ (เจนโครงร่าง / วิเคราะห์สเปค / ตรวจสอบ ToR)

## ขั้นที่ 8 — แชร์ลิงก์ และตั้งเตือนปิดระบบ
1. ส่งลิงก์ `http://<PUBLIC_IP>:8000` ให้ผู้ใช้ทดลอง
2. ตั้งเตือนตัวเองล่วงหน้าก่อนครบ 7 วัน เพื่อ:
   - ปิด/ลบ instance ก่อนแพ็กเกจฟรีหมดอายุ (กันถูกเรียกเก็บเงินอัตโนมัติ)
   - หรือถอด/หมุนเวียน API key ของ OpenTyphoon ถ้าจะไม่ใช้ลิงก์นี้ต่อ

## คำสั่งที่มีประโยชน์ระหว่างใช้งาน
```bash
docker logs -f auditor        # ดู log แบบ real-time
docker restart auditor        # รีสตาร์ทแอป
docker stop auditor           # หยุดชั่วคราว
docker rm -f auditor          # ลบ container ทิ้ง
```

---
### หมายเหตุความปลอดภัย
- คีย์ `TYPHOON_API_KEY` / `TYPHOON_OCR_API_KEY` ส่งผ่าน environment variable เท่านั้น ไม่ baked เข้าไปใน Docker image
- ToR ที่ผู้ใช้อัปโหลดจะถูกส่งออกไปยัง OpenTyphoon API (ไม่ใช่ local 100% อีกต่อไปเมื่อ deploy บน cloud) — ควรแจ้งผู้ทดลองใช้ให้ทราบ และเลี่ยงอัปโหลดเอกสารที่มีข้อมูลอ่อนไหวจริง
