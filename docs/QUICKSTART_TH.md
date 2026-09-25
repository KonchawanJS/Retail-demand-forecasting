# เริ่มใช้งาน Stockwise

โปรเจกต์นี้มีโมเดลพยากรณ์ยอดขาย ระบบแนะนำสั่งซื้อ API และ dashboard พร้อมนำขึ้น GitHub ได้

## 1. ติดตั้ง

ติดตั้ง Python 3.12 และแตกไฟล์ ZIP จากนั้นเปิด Terminal ในโฟลเดอร์ `retail-demand-forecasting`

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
```

ถ้า PowerShell เปิด virtual environment ไม่ได้ ใช้ `.venv\Scripts\python.exe` แทน `python` ในทุกคำสั่งได้โดยไม่ต้องเปลี่ยนนโยบายของเครื่อง

macOS/Linux ใช้ `source .venv/bin/activate`

## 2. สร้างผลพยากรณ์และเปิดแอป

```bash
python -m retail.cli demo
python -m streamlit run app/dashboard.py
```

เปิด http://localhost:8501 เลือกสินค้า ปรับสต็อกคงเหลือ เวลารอสินค้า และรอบตรวจสต็อก

ข้อมูลเริ่มต้นเป็นข้อมูลจำลอง 20 สินค้า 420 วัน ไม่ใช่ยอดขายจริงของธุรกิจ ตัวแอปแสดงวันสุดท้ายของข้อมูลเสมอ ผลพยากรณ์จึงเป็นการสาธิตย้อนหลัง ไม่ใช่ยอดขาย ณ วันนี้

## 3. เปิด API

เปิดอีก Terminal ใช้ environment เดิมและอยู่ในโฟลเดอร์โปรเจกต์:

```bash
python -m uvicorn retail.api:app --host 127.0.0.1 --port 8000
```

เปิด http://localhost:8000/docs แล้วลอง `GET /forecast/{sku}` กับ `POST /inventory/recommend`

## 4. ใช้ข้อมูลจริง

อ่านหัวข้อ UCI ใน README แล้วดาวน์โหลด workbook จากแหล่งต้นฉบับ:

```bash
python -m retail.cli import-uci --input data/raw/online_retail_II.xlsx --top-n 20
python -m retail.cli train --csv data/processed/daily_sales.csv
```

หรือใช้ CSV ของตัวเองที่มี `date,sku,quantity` อย่างน้อย 180 วันต่อสินค้า แต่ละสินค้าต้องมีวันครบและช่วงเวลาเดียวกัน รวมธุรกรรมต่อวันก่อนนำเข้า และไม่ใส่ข้อมูลส่วนบุคคลลง GitHub

หลังฝึกใหม่ให้ restart API แอปโหลดผลใหม่เมื่อ rerun ไม่ควรฝึกทับโฟลเดอร์ที่กำลังให้บริการจริง

## 5. ทำความเข้าใจสิ่งที่จะพูดตอนสัมภาษณ์

- ทำไมแบ่งตามเวลาแทนสุ่ม train/test?
- ทำไมต้องเทียบยอดขายวันเดียวกันของสัปดาห์ก่อน?
- โมเดลใช้ข้อมูลอะไรที่รู้ได้จริง ณ วันที่พยากรณ์?
- โมเดลมี bias ไปทางทำนายต่ำหรือสูง และส่งผลต่อสต็อกอย่างไร?
- ยอดขายที่บันทึกได้ต่างจากความต้องการจริงอย่างไรเมื่อสินค้าหมด?
- ทำไมผลจำลองต้นทุนยังเรียกว่าผลประหยัดจริงไม่ได้?

อ่าน `docs/METHODOLOGY.md` และ `docs/MODEL_CARD.md` ก่อนนำไปอธิบาย ปรับโค้ด/ทดลองเพิ่มเติมด้วยตัวเองและอธิบายบทบาทการใช้ AI อย่างตรงไปตรงมา

## 6. ทดสอบและเตรียมพอร์ต

```bash
python -m ruff check .
python -m pytest -q
```

ดูผลใน `reports/` อัด demo 2–3 นาที: โจทย์ธุรกิจ → ผลพยากรณ์ → ปรับเงื่อนไขสั่งซื้อ → ผลประเมิน → ข้อจำกัด แล้วทำตาม `docs/GITHUB.md` เพื่ออัปโหลด

โปรเจกต์มี Docker Compose ให้ แต่การตรวจในรอบสร้างนี้ใช้ Python โดยตรง เนื่องจากสภาพแวดล้อมไม่มี Docker และยังไม่ได้ deploy หรือสร้าง repository ในบัญชี GitHub ของคุณ
