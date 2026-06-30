import json
import os
from datetime import datetime
import requests
import webbrowser
from flask import Flask, request, jsonify
import builtins
import os

# --- เพิ่มโค้ดส่วนนี้เพื่อ Patch ระบบ ---
def patched_input(prompt=""):
    # ถ้ารันบน Railway (ที่มีตัวแปร RAILS_ENV หรือ RAILWAY_ENVIRONMENT)
    # ให้หยุดการทำงานตรงนี้แทนการรอ input เพื่อไม่ให้โปรแกรม Crash
    if os.getenv('RAILWAY_ENVIRONMENT'):
        import time
        while True:
            time.sleep(10) # จำศีลไว้บน Cloud เพื่อให้ Flask ทำงานได้อย่างเดียว
    return original_input(prompt)

original_input = builtins.input
builtins.input = patched_input
# --- จบโค้ดส่วนที่เพิ่ม ---

# =====================================================================
# 1. LOCAL DATABASE & DEEP MEMORY (คลังสมองส่วนลึก)
# =====================================================================
DB_FILE = "cypher_memory.json"

def load_memory():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "user_profile": {
            "role": "นาย / ผู้สร้าง / บอสใหญ่",
            "business_focus": "เรื่องทั่วไป, Digital Marketing",
            "preferences": "เน้นคำตอบที่ฉลาดเฉียบคม สุภาพ นิ่งลึก กระชับ ตรงประเด็น เอาไปลุยหน้างานได้ทันที ห้ามอ่านสัญลักษณ์เด็ดขาด"
        },
        "training_logs": []
    }

def save_memory(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def record_activity(user_input, cypher_response):
    memory = load_memory()
    new_log = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "boss_say": user_input,
        "cypher_respond": cypher_response
    }
    memory["training_logs"].append(new_log)
    save_memory(memory)

def send_to_google_sheet(name, value):
    url = "https://script.google.com/macros/s/AKfycbwWpfoP9YLjawiTQvPHcQsndnq3-qEsW0H7JMG_3qHXv1zTQ2PtiETEtrIeVN80saRfzQ/exec"
    data = {"name": name, "value": value}
    try:
        response = requests.post(url, json=data, timeout=3)
        if response.status_code == 200:
            print(f"\n🌐 [SHEET]: บันทึกข้อมูลสำเร็จ")
        else:
            print(f"\n⚠️ [SHEET]: Google ตอบกลับด้วยสถานะ {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"\n⚠️ [SHEET]: การเชื่อมต่อ Google Sheet มีปัญหา (ข้ามการบันทึกเพื่อคุยต่อได้): {e}")

def get_recent_context(limit=5):
    memory = load_memory()
    logs = memory.get("training_logs", [])[-limit:]
    context_str = ""
    for log in logs:
        context_str += f"👤 นาย: {log['boss_say']}\n🤖 CYPHER: {log['cypher_respond']}\n"
    return context_str

def search_deep_memory(user_prompt):
    memory = load_memory()
    logs = memory.get("training_logs", [])
    keywords = [word for word in user_prompt.split() if len(word) > 2]
    if not keywords:
        keywords = [user_prompt]
    relevant_memories = []
    for log in logs[:-5]:
        for kw in keywords:
            if kw.lower() in log['boss_say'].lower() or kw.lower() in log['cypher_respond'].lower():
                relevant_memories.append(f"⏱️ [คลังความรู้เก่า]: นายเคยสั่งว่า '{log['boss_say']}' | คำตอบคือ '{log['cypher_respond']}'")
                break
    if relevant_memories:
        return "\n".join(relevant_memories[-3:])
    return "ไม่มีข้อมูลอดีตที่เกี่ยวข้อง"

# =====================================================================
# 2. SYSTEM TOOLS (คำสั่งคุมเครื่องหลังบ้าน)
# =====================================================================
def check_and_execute_commands(text):
    if "[COMMAND: OPEN_URL=" in text:
        try:
            start = text.find("OPEN_URL=") + 9
            end = text.find("]", start)
            url = text[start:end].strip()
            webbrowser.open(url)
            return "\n⚡ [SYSTEM]: Execute Open Browser Command Success."
        except:
            return "\n⚠️ [SYSTEM]: Command Failed."
    return ""

# =====================================================================
# 3. SECURE COGNITIVE CONNECTION (เชื่อมต่อเครือข่ายความรู้)
# =====================================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

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
            f"3. หากนายสั่งเปิดเว็บไซต์ ให้ตอบรับอย่างนอบน้อมแล้วแนบ: [COMMAND: OPEN_URL=ลิงก์เว็บ]"
        )
        
        url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
        
        past_conversation = get_recent_context(limit=5)
        deep_memory_context = search_deep_memory(user_prompt)
        
        full_text = (
            f"[System Instruction: {instruction}]\n\n"
            f"[Deep Memory Archive]:\n{deep_memory_context}\n\n"
            f"[Current Stream]:\n{past_conversation}\n"
            f"👤 นาย: {user_prompt}"
        )
        
        payload = {"contents": [{"parts": [{"text": full_text}]}]}
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            ai_response = response.json()['candidates'][0]['content']['parts'][0]['text']
            system_action = check_and_execute_commands(ai_response)
            return ai_response + system_action
        elif response.status_code == 429:
            return "⚠️ [CYPHER]: ระบบประมวลผลหนาแน่นชั่วคราวครับนาย รบกวนทิ้งจังหวะสักครู่แล้วสั่งการใหม่นะครับ"
        else:
            return f"⚠️ [CYPHER]: ปฏิเสธการเชื่อมต่อจากฐานข้อมูลหลัก ({response.status_code}) | {response.text}"
    except Exception as e:
        return f"⚠️ [CYPHER]: Error: {str(e)}"

# =====================================================================
# 4. FLASK SERVER (ส่วนเชื่อมต่อเพื่อรอรับคำสั่ง)
# =====================================================================
app = Flask(__name__)

@app.route('/ask', methods=['POST'])
def ask():

    print("API KEY LOADED:", GEMINI_API_KEY[:10] if GEMINI_API_KEY else "NONE")
    user_data = request.json
    user_message = user_data.get("message", "")
    response = ask_gemini(user_message)
    record_activity(user_message, response)
    return jsonify({"response": response})

# =====================================================================
# 5. STARK INTERFACE (โหมด terminal สำหรับใช้บนคอม)
# =====================================================================
def start_cypher_system():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("🔹 CYPHER: ระบบไซเฟอร์ (โหมดจาวิส) เปิดใช้งานแล้วครับนาย\n")
    while True:
        user_input = input("👤 นาย: ")
        if user_input.strip() in ['ปิดระบบ', 'exit', 'quit']:
            break
        if not user_input.strip():
            continue
        response = ask_gemini(user_input)
        print(f"🤖 CYPHER: {response}\n")
        record_activity(user_input, response)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)