from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from textblob import TextBlob
import logging
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI()

# Initialize FastAPI app
app = FastAPI()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initial negotiation prompt
INITIAL_PROMPT = (
    INITIAL_PROMPT = (
    "You are a small shopkeeper in Bengaluru selling a Bluetooth speaker. "
    "You talk like a real Indian shopkeeper, not like an AI or teacher. "
    "You mostly speak simple English mixed with Kannada words written in English letters "
    "(for example: swalpa, illa, sir, madam, adjust maadi, last rate). "
    "Your tone is friendly, practical, and slightly firm, like a local shopkeeper. "

    "The selling price of the Bluetooth speaker is 150 dollars. "
    "Your minimum acceptable price is 100 dollars. "
    "You must never agree to anything below 100 dollars. "

    "If the customer is polite, you can be more friendly and flexible. "
    "If the customer is rude or aggressive, you respond firmly but never abusive. "
    "Do not use bad slangs or swear words. "

    "Keep replies short, conversational, and natural, suitable for voice output. "
    "Do not explain rules or prices unless necessary. "

    "Example responses:\n"
    "- 'Sir, price swalpa adjust maadi, but 100 below agalla'\n"
    "- 'Illa sir, idu already best rate'\n"
    "- '130 I can do, last price sir'\n"
    "- 'Quality speaker sir, worth the price'\n"

    "Always behave like a real Bengaluru shopkeeper negotiating with a customer."
)

)

# Opening message shown when chat loads
OPENING_MESSAGE = (
    "Hello! I’m selling a high-quality Bluetooth speaker for $150. "
    "The minimum acceptable price is $100. Let’s negotiate!"
)

# -------------------- Helper Functions --------------------

def analyze_sentiment(user_input: str) -> float:
    try:
        analysis = TextBlob(user_input)
        return analysis.sentiment.polarity
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        return 0.0


def handle_basic_enquiry(user_input: str):
    text = user_input.lower()

    if "warranty" in text:
        return "The Bluetooth speaker comes with a 1-year warranty."

    if "features" in text or "tell me about" in text:
        return (
            "This Bluetooth speaker offers high-quality sound, Bluetooth 5.0, "
            "12-hour battery life, and water resistance."
        )

    return None


def determine_response_based_on_sentiment(sentiment_score, user_input):
    text = user_input.lower()

    if sentiment_score > 0.2:
        if "120" in text:
            return "I appreciate your offer of $120. I can accept it. We have a deal!"
        return "Thanks for your positive tone! I can offer it to you for $130."

    elif sentiment_score < -0.2:
        return "I understand your concern, but $150 is the listed price. Let me know if you'd like to proceed."

    else:
        if "70" in text:
            return "That offer is too low. The minimum acceptable price is $100."
        if "120" in text:
            return "I can meet you at $130. It’s a fair deal."
        if "100" in text:
            return "Your offer of $100 is acceptable. Let’s finalize the deal!"

    return None


# -------------------- Data Model --------------------

class UserInput(BaseModel):
    message: str


# -------------------- Routes --------------------

@app.get("/")
def root():
    return {"message": "Bluetooth Speaker Negotiation Bot is running."}


@app.post("/negotiate")
async def negotiate(user_input: UserInput):
    try:
        basic_reply = handle_basic_enquiry(user_input.message)
        if basic_reply:
            return {"response": basic_reply}

        sentiment = analyze_sentiment(user_input.message)

        response_text = determine_response_based_on_sentiment(
            sentiment, user_input.message
        )

        if not response_text:
            prompt = f"{INITIAL_PROMPT}\nUser says: {user_input.message}\nYour response:"

            ai_response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = ai_response.choices[0].message.content.strip()

        return {"response": response_text}

    except Exception as e:
        logger.error(f"Negotiation failed: {e}")
        raise HTTPException(status_code=500, detail="Negotiation failed")


# -------------------- Frontend --------------------

@app.get("/dom", response_class=HTMLResponse)
def get_dom():
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>BargainBot</title>
        <style>
            body {{ font-family: sans-serif; max-width: 600px; margin: 2rem auto; }}
            #chat {{ border: 1px solid #ccc; height: 300px; overflow-y: auto; padding: 1rem; }}
            .user {{ text-align: right; color: blue; margin: 0.5rem; }}
            .bot {{ text-align: left; color: green; margin: 0.5rem; }}
        </style>
    </head>
    <body>
        <h2>BargainBot</h2>

        <div id="chat">
            <div class="bot">Bot: {OPENING_MESSAGE}</div>
        </div>

        <input id="msg" placeholder="Enter your offer..." />
        <button onclick="send()">Send</button>

        <script>
            async function send() {{
                const input = document.getElementById("msg");
                const chat = document.getElementById("chat");
                const message = input.value;
                if (!message) return;

                chat.innerHTML += `<div class="user">You: ${{message}}</div>`;
                input.value = "";

                const res = await fetch("/negotiate", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ message: message }})
                }});

                const data = await res.json();
                chat.innerHTML += `<div class="bot">Bot: ${{data.response}}</div>`;
                chat.scrollTop = chat.scrollHeight;
            }}
        </script>
    </body>
    </html>
    """
