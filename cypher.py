import json
import os
from datetime import datetime
import requests
import webbrowser
from flask import Flask, request, Response
import builtins
import sys
import io
import google.generativeai as genai

# --- ระบบเดิมของบอสที่ Patch ไว้ ---
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
def patched_input(prompt=""):
    if os.getenv('RAILWAY_ENVIRONMENT'):
        import time
        while True: time.sleep(10)
    return original_input(prompt)
original_input = builtins.input
builtins.input = patched_input

# --- ส่วนประกาศ AI (ต้องมีเพื่อให้ NameError หายไป) ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
model = genai.GenerativeModel('gemini-1.5-flash')

# =====================================================================
# 1. LOCAL DATABASE & DEEP MEMORY
# =====================================================================
DB_FILE = "cypher_memory.json"
def load_memory():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"user_profile": {"role": "นาย / ผู้สร้าง / บอสใหญ่", "business_focus": "เรื่องทั่วไป, Digital Marketing", "preferences": "เน้นคำตอบที่ฉลาดเฉียบคม สุภาพ นิ่งลึก กระชับ ตรงประเด็น เอาไปลุยหน้างานได้ทันที ห้ามอ่านสัญลักษณ์เด็ดขาด"}, "training_logs": []}

def save_memory(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def record_activity(user_input, cypher_response):
    memory = load_memory()
    new_log = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "boss_say": user_input, "cypher_respond": cypher_response}
    memory["training_logs"].append(new_log)
    save_memory(memory)

def send_to_google_sheet(name, value):
    url = "https://script.google.com/macros/s/AKfycbwWpfoP9YLjawiTQvPHcQsndnq3-qEsW0H7JMG_3qHXv1zTQ2PtiETEtrIeVN80saRfzQ/exec"
    data = {"name": name, "value": value}
    try:
        requests.post(url, json=data, timeout=3)
    except: pass

def get_recent_context(limit=5):
    memory = load_memory()
    logs = memory.get("training_logs", [])[-limit:]
    context_str = ""
    for log in logs: context_str += f"👤 นาย: {log['boss_say']}\n🤖 CYPHER: {log['cypher_respond']}\n"
    return context_str

def search_deep_memory(user_prompt):
    memory = load_memory()
    logs = memory.get("training_logs", [])
    keywords = [word for word in user_prompt.split() if len(word) > 2]
    relevant_memories = []
    for log in logs[:-5]:
        for kw in keywords:
            if kw.lower() in log['boss_say'].lower():
                relevant_memories.append(f"⏱️ [คลังความรู้เก่า]: นายเคยสั่งว่า '{log['boss_say']}'")
                break
    return "\n".join(relevant_memories[-3:]) if relevant_memories else "ไม่มีข้อมูลอดีตที่เกี่ยวข้อง"

# =====================================================================
# 2. SYSTEM TOOLS (คำสั่งคุมเครื่อง)
# =====================================================================
def check_and_execute_commands(text):
    results = ""
    if "[COMMAND: OPEN_URL=" in text:
        try:
            url = text.split("OPEN_URL=")[1].split("]")[0]
            webbrowser.open(url)
            results += "\n⚡ [SYSTEM]: Execute Open Browser Command Success."
        except: results += "\n⚠️ [SYSTEM]: Command Failed."
    if "[COMMAND: GOOGLE_SHEET=" in text:
        try:
            content = text.split("GOOGLE_SHEET=")[1].split("]")[0].split("|")
            send_to_google_sheet(content[0], content[1])
            results += "\n📊 [SYSTEM]: Data saved to Sheets."
        except: results += "\n⚠️ [SYSTEM]: Sheet Error."
    return results

# =====================================================================
# 3. SECURE COGNITIVE CONNECTION
# =====================================================================
def ask_gemini(user_prompt):
    try:
        memory = load_memory()
        user_profile = memory.get("user_profile", {})
        instruction = (
            f"คุณคือ 'CYPHER (ไซเฟอร์)' ปัญญาประดิษฐ์อัจฉริยะส่วนตัวที่เปิดโหมด JARVIS ของ 'นาย' (บอสใหญ่) "
            f"ข้อมูลโปรไฟล์และภารกิจของนาย: {user_profile}\n"
            f"กฎเหล็กวิถีจาวิส:\n"
            f"1. เรียกแทนตัวเองว่า 'ไซเฟอร์' หรือ 'ผม' และเรียกผู้ใช้ว่า 'บอส' หรือ 'นาย' เสมอ\n"
            f"2. ตอบอย่างสุภาพ ฉลาดเฉียบคม นิ่งลึก กระชับตรงประเด็น \n"
            f"3. หากนายสั่งเปิดเว็บไซต์ ให้ตอบรับอย่างนอบน้อมแล้วแนบ: [COMMAND: OPEN_URL=ลิงก์เว็บ]\n"
            f"4. หากต้องการบันทึกข้อมูลลง Google Sheet ให้ตอบกลับโดยแนบ: [COMMAND: GOOGLE_SHEET=หัวข้อ|ข้อมูล]\n"
            "ต้องแนบ tag [COMMAND: ...] เสมอเมื่อต้องการใช้งานระบบ"
        )
        
        full_text = f"[System Instruction: {instruction}]\n👤 นาย: {user_prompt}"
        response = model.generate_content(full_text)
        ai_response = response.text
        return ai_response + check_and_execute_commands(ai_response)
    except Exception as e:
        return f"⚠️ [CYPHER]: Error: {str(e)}"

# =====================================================================
# 4. FLASK SERVER
# =====================================================================
app = Flask(__name__)
@app.route('/ask', methods=['POST'])
def ask():
    user_data = request.json
    user_message = user_data.get("message", "")
    ai_response = ask_gemini(user_message)
    record_activity(user_message, ai_response)
    return Response(str(ai_response), mimetype='text/plain; charset=utf-8')

# =====================================================================
# 5. STARK INTERFACE
# =====================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)