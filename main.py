from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import os, json

# ------------------ SETUP ------------------

load_dotenv()
app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ------------------ LOAD PROMPT ------------------

with open("mega_prompt.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# ------------------ PRODUCT CATALOG (FACTS ONLY) ------------------

PRODUCT_CATALOG = {
    "wired_earphones": {
        "name": "Wired Earphones",
        "cost_price": 150,
        "selling_range": [180, 220],
        "margin_level": "low",
        "demand": "medium",
        "use_cases": ["calls", "basic music"],
        "pairable": True
    },
    "bluetooth_earphones": {
        "name": "Bluetooth Earphones",
        "cost_price": 500,
        "selling_range": [650, 800],
        "margin_level": "medium",
        "demand": "high",
        "use_cases": ["daily use", "travel", "office"],
        "pairable": False
    },
    "headphones": {
        "name": "Headphones",
        "cost_price": 1200,
        "selling_range": [1600, 2200],
        "margin_level": "high",
        "demand": "medium",
        "use_cases": ["long listening", "quality music"],
        "pairable": False
    },
    "bluetooth_speaker": {
        "name": "Bluetooth Speaker",
        "cost_price": 900,
        "selling_range": [1200, 1600],
        "margin_level": "medium-high",
        "demand": "high",
        "use_cases": ["room", "party", "group"],
        "pairable": True
    }
}

# ------------------ MEMORY ------------------

session_messages = []

# ------------------ INPUT MODEL ------------------

class UserInput(BaseModel):
    message: str
    gender: str
    age_group: str

# ------------------ CHAT ENDPOINT ------------------

@app.post("/chat")
def chat(user_input: UserInput):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": f"""
CUSTOMER PROFILE:
Gender: {user_input.gender}
Age Group: {user_input.age_group}

PRODUCT CATALOG (BUSINESS FACTS):
{json.dumps(PRODUCT_CATALOG, indent=2)}
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
    session_messages[:] = session_messages[-12:]

    return {"response": reply}

# ------------------ SIMPLE UI ------------------

@app.get("/dom", response_class=HTMLResponse)
def dom():
    return """
<!DOCTYPE html>
<html>
<head><title>Expert Shopkeeper Demo</title></head>
<body>

<h3>Bangalore Shopkeeper (Prompt-Driven)</h3>

Gender:
<select id="gender">
  <option value="male">Male</option>
  <option value="female">Female</option>
</select>

Age Group:
<select id="age">
  <option value="child">Child</option>
  <option value="young">Young</option>
  <option value="adult">Adult</option>
  <option value="mid-aged">Mid-aged</option>
  <option value="elderly">Elderly</option>
</select>

<br><br>

<input id="msg" placeholder="Speak..." />
<button onclick="send()">Send</button>

<div id="chat"></div>

<script>
async function send() {
  const msg = document.getElementById("msg").value;
  const gender = document.getElementById("gender").value;
  const age = document.getElementById("age").value;

  chat.innerHTML += `<p><b>You:</b> ${msg}</p>`;
  document.getElementById("msg").value = "";

  const res = await fetch("/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ message: msg, gender: gender, age_group: age })
  });

  const data = await res.json();
  chat.innerHTML += `<p><b>Shopkeeper:</b> ${data.response}</p>`;
}
</script>

</body>
</html>
"""
