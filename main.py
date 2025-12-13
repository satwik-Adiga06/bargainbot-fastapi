from fastapi import FastAPI
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
deal_closed = False
counter_attempts = 0
has_greeted = False

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
    return {"message": "BargainBot running"}

@app.post("/negotiate")
def negotiate(user_input: UserInput):
    global current_price, deal_closed, counter_attempts, has_greeted

    text = user_input.message.lower()
    offer = extract_offer(text)

    # --------- GREETING (ONLY ONCE) ---------
    if not has_greeted:
        has_greeted = True
        return {
            "response": (
                "Namaskara sir 🙂 Bluetooth speaker ide. "
                "Starting price 150. Bargain maadbahudu."
            )
        }

    # --------- DEAL ALREADY CLOSED ---------
    if deal_closed:
        return {"response": "Deal done sir 🤝 Next customer please."}

    # --------- NO PRICE MENTIONED → AI RESPONSE ---------
    if offer is None:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an Indian shopkeeper in Bengaluru. "
                        "Do NOT greet again. "
                        "Do NOT change the product or price. "
                        "You are selling ONE Bluetooth speaker. "
                        "Speak casually in Kannada-English mix."
                    ),
                },
                {"role": "user", "content": user_input.message},
            ],
        )
        return {"response": response.choices[0].message.content}

    # --------- TOO LOW (HARD REJECT) ---------
    if offer < 110:
        return {
            "response": "Sir idu too low. Naanu loss alli sell maadakke agalla."
        }

    # --------- FIRST SERIOUS OFFER (FIGHT STARTS) ---------
    if counter_attempts == 0:
        counter_attempts += 1
        current_price = max(offer + 15, 135)
        return {
            "response": f"{current_price} sir. Idu already tight price."
        }

    # --------- SECOND ROUND (HARD BARGAIN ZONE) ---------
    if counter_attempts == 1:
        counter_attempts += 1

        if offer >= 120:
            deal_closed = True
            return {
                "response": f"Okay sir… {offer} final. Regular customer antha 🤝"
            }

        if 110 <= offer < 120:
            return {
                "response": (
                    "Sir swalpa adjust maadi. 125 kodbeku. "
                    "Naanu already loss alli idini."
                )
            }

    # --------- FINAL ROUND (CLOSE OR WALK AWAY) ---------
    if counter_attempts >= 2:
        if offer >= 120:
            deal_closed = True
            return {
                "response": f"Okay sir, {offer}. Final deal 🤝"
            }

        if offer >= 115:
            deal_closed = True
            return {
                "response": "Hmm… sari sir. 115 final. Last price 🤝"
            }

        return {
            "response": "Illa sir. Ee price ge agalla."
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
    <input id="msg" placeholder="Type your message..." />
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
