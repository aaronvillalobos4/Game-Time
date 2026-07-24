import os
import chainlit as cl
from dotenv import load_dotenv
from agents import TravelCrew
from flask import Flask, render_template
import chainlit as cl
from chainlit.server import app
from starlette.responses import HTMLResponse

PARTNERIZE_SCRIPT = """
<script>
  (function () {
      var pztt = 3;
      var pztp = {"p":"pzt","mi":0,"ma":99,"e":[]};
      var tid = 'c7b6e1e8-98ca-4d8c-acd9-c2d6c30fc6bd';
      // ... your Partnerize script ...
  })();
</script>
"""

@app.middleware("http")
async def inject_partnerize_tag(request, call_next):
    response = await call_next(request)
    
    # Only modify root HTML page requests
    if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
        body = [chunk async for chunk in response.body_iterator]
        html_content = b"".join(body).decode("utf-8")
        
        if "</head>" in html_content and PARTNERIZE_SCRIPT not in html_content:
            html_content = html_content.replace("</head>", f"{PARTNERIZE_SCRIPT}\n</head>")
            
        return HTMLResponse(content=html_content, status_code=response.status_code)
        
    return response

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")

# Load environment keys from our secret .env file
load_dotenv()

@cl.on_chat_start
async def start():
    await cl.Message(
        content="🏆 **Welcome to Game Time!**\n"
                "I will help you plan your entire sports trip. To get started, please tell me your criteria in this exact format:\n\n"
                "`Game, Date, Departure City, Total Budget`\n\n"
                "Example: `Mavericks @ Celtics, March 14, Austin, $1200`"
    ).send()

@cl.on_message
async def main(message: cl.Message):
    session_data = cl.user_session.get("trip_details", {})

    if not session_data:
        try:
            parts = [p.strip() for p in message.content.split(",")]
            if len(parts) < 4:
                raise ValueError("Incomplete parameters")
                
            session_data = {
                "game": parts[0],
                "date": parts[1],
                "origin": parts[2],
                "budget": parts[3]
            }
            cl.user_session.set("trip_details", session_data)
        except Exception:
            await cl.Message(
                content="Oops! Please provide the details in this exact format:\n"
                        "`Game, Date, Departure City, Budget`\n\n"
                        "Example: `Mavericks @ Celtics, March 14, Austin, $1200`"
            ).send()
            return

    await cl.Message(content=f"🔄 Gathering options for **{session_data['game']}**... My specialist sub-agents are searching tickets, flights, and hotels using Google Search right now! Please wait a moment...").send()
    
    # Run our background Crew
    planner = TravelCrew(inputs=session_data)
    
    # Add 'await' right here to match our new async function
    final_itinerary = await planner.run()
    
    await cl.Message(
        content=f"### 📋 Your Custom Sports Trip Itinerary\n\n{final_itinerary}"
    ).send()