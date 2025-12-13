from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
import re
from dotenv import load_dotenv
from openai import OpenAI

# ------------------ SETUP ------------------

load_dotenv()

app = FastAPI()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not found")

client = OpenAI(api_key=api_key)

# ------------------ NEGOTIATION STATE (DEMO LEVEL) ------------------

START_PRICE = 150
ABSOLUTE_MIN = 100

current_price = START_PRICE
has_countered = False
deal_closed = False

# ------------------ HELPERS ------------------

def extract_offer(text: str):
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None

# ------------------ MODELS ------------------

class UserInput(BaseModel):
    message: str

# ------------------ ROUTES ------------------

@app.get("/")
def root():
    return {
        "message": "I am selling a Bluetooth speaker for 150. Let's negotiate."
    }

@app.post("/negotiate")
def negotiate(user_input: UserInput):
    global current_price, has_countered, deal_closed

    text = user_input.message.lower()
    offer = extract_offer(text)

    # Deal already closed
    if deal_closed:
        return {"response": "Deal done sir 🤝 Next customer please."}

    # No price mentioned → fallback to AI
    if offer is None:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an Indian shopkeeper in Bengaluru selling a Bluetooth speaker. "
                        "Speak casually with Kannada-English mix. "
                        "Be polite but firm."
                    ),
                },
                {"role": "user", "content": user_input.message},
            ],
        )
        return {"response": response.choices[0].message.content}

    # Lowball immediately
    if offer < ABSOLUTE_MIN:
        return {"response": "Illa sir, idu too less. Serious offer maadi."}

    # First serious offer → fight
    if not has_countered:
        counter = max(offer + 10, 130)
        current_price = counter
        has_countered = True
        return {
            "response": f"{counter} last price sir. Quality item idu."
        }

    # After counter → close deal if close enough
    if offer >= current_price - 10:
        deal_closed = True
        return {
            "response": f"Okay sir, {offer} final. Deal done 🤝"
        }

    # User drops after counter
    return {
        "response": "Sir, already best rate idu. Please understand."
    }

# ------------------ SIMPLE UI ------------------

@app.get("/dom", response_class=HTMLResponse)
def dom():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>BargainBot</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: auto; }
        #chat { border: 1px solid #ccc; height: 300px; overflow-y: auto; padding: 10px; }
        .user { text-align: right; color: blue; }
        .bot { text-align: left; color: green; }
    </style>
</head>
<body>
    <h2>BargainBot – Shopkeeper Negotiation</h2>
    <div id="chat"></div>
    <input id="msg" placeholder="Type your offer..." />
    <button onclick="send()">Send</button>

    <script>
        async function send() {
            const msg = document.getElementById("msg").value;
            if (!msg) return;

            document.getElementById("chat").innerHTML +=
                `<div class="user">You: ${msg}</div>`;

            document.getElementById("msg").value = "";

            const res = await fetch("/negotiate", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({message: msg})
            });

            const data = await res.json();
            document.getElementById("chat").innerHTML +=
                `<div class="bot">Bot: ${data.response}</div>`;
        }
    </script>
</body>
</html>
"""
