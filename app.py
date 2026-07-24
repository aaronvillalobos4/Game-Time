import os
import chainlit as cl
from chainlit.server import app
from starlette.responses import HTMLResponse
from dotenv import load_dotenv
from agents import TravelCrew

load_dotenv()

# Read the custom head HTML snippet if it exists
HEAD_FILE_PATH = os.path.join(".chainlit", "head.html")
CUSTOM_HEAD_HTML = ""
if os.path.exists(HEAD_FILE_PATH):
    with open(HEAD_FILE_PATH, "r", encoding="utf-8") as f:
        CUSTOM_HEAD_HTML = f.read()

# FastAPI / Starlette middleware to inject <script> into the <head>
@app.middleware("http")
async def inject_partnerize_script(request, call_next):
    response = await call_next(request)
    
    # Only modify root HTML page requests
    if request.url.path in ["/", "/index.html"] and "text/html" in response.headers.get("content-type", ""):
        body = [chunk async for chunk in response.body_iterator]
        html_content = b"".join(body).decode("utf-8")
        
        if "</head>" in html_content and CUSTOM_HEAD_HTML:
            html_content = html_content.replace("</head>", f"{CUSTOM_HEAD_HTML}\n</head>")
            
        return HTMLResponse(content=html_content, status_code=response.status_code, headers=dict(response.headers))
        
    return response


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

    await cl.Message(
        content=f"🔄 Gathering options for **{session_data['game']}**... My specialist sub-agents are searching tickets, flights, and hotels using Google Search right now! Please wait a moment..."
    ).send()
    
    planner = TravelCrew(inputs=session_data)
    final_itinerary = await planner.run()
    
    await cl.Message(
        content=f"### 📋 Your Custom Sports Trip Itinerary\n\n{final_itinerary}"
    ).send()