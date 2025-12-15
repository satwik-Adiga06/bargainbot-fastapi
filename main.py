from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import os, re

# ------------------ SETUP ------------------

load_dotenv()
app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ------------------ PRODUCT DATA ------------------

PRODUCT = {
    "name": "Bluetooth Speaker",
    "base_price": 150,
    "min_price": 110,
    "cost": 90,
    "margin": "medium",
    "demand": "high",
    "bulk_allowed": False
}

# ------------------ LOAD MEGA PROMPT ------------------

with open("mega_prompt.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# ------------------ SESSION MEMORY ------------------

session_messages = []

# ------------------ HELPERS ------------------

def extract_offer(text):
    match = re.search(r"\b\d+\b", text)
    return int(match.group()) if match else None

# ------------------ MODEL ------------------

class UserInput(BaseModel):
    message: str

# ------------------ CHAT ROUTE ------------------

@app.post("/chat")
def chat(user_input: UserInput):
    try:
        text = user_input.message.lower()
        offer = extract_offer(text)

        # 🔒 HARD PRICE GUARDRAIL
        if offer is not None and offer < PRODUCT["min_price"]:
            return {
                "response": "Illa sir, idu too low. Loss alli sell maadakke agalla."
            }

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": f"""
PRODUCT DETAILS:
Name: {PRODUCT['name']}
Base Price: {PRODUCT['base_price']}
Minimum Price: {PRODUCT['min_price']}
Cost Price: {PRODUCT['cost']}
Margin: {PRODUCT['margin']}
Demand: {PRODUCT['demand']}
Bulk Allowed: {PRODUCT['bulk_allowed']}
"""
            }
        ]

        messages.extend(session_messages)
        messages.append({"role": "user", "content": user_input.message})

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages
        )

        reply = response.choices[0].message.content

        session_messages.append({"role": "user", "content": user_input.message})
        session_messages.append({"role": "assistant", "content": reply})

        return {"response": reply}

    except Exception as e:
        print("🔥 ERROR:", e)
        return {"response": "Internal error. Check server logs."}

# ------------------ SIMPLE UI ------------------

@app.get("/dom", response_class=HTMLResponse)
def dom():
    return """
<!DOCTYPE html>
<html>
<head>
<title>Bangalore Shopkeeper Bot</title>
<style>
body { font-family: sans-serif; max-width: 600px; margin: auto; }
#chat { border: 1px solid #ccc; height: 300px; overflow-y: auto; padding: 10px; }
.user { text-align: right; color: blue; }
.bot { text-align: left; color: green; }
</style>
</head>
<body>
<h2>Bangalore Shopkeeper Bot</h2>
<div id="chat"></div>
<input id="msg" placeholder="Type message..." />
<button onclick="send()">Send</button>
<script>
async function send() {
  const msg = document.getElementById("msg").value;
  if (!msg) return;
  chat.innerHTML += `<div class="user">You: ${msg}</div>`;
  document.getElementById("msg").value = "";
  const res = await fetch("/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({message: msg})
  });
  const data = await res.json();
  chat.innerHTML += `<div class="bot">Bot: ${data.response}</div>`;
}
</script>
</body>
</html>
"""
