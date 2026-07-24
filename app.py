import os
import chainlit as cl
from dotenv import load_dotenv
from agents import TravelCrew
from chainlit.server import app
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class InjectMetaTagMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Only modify HTML responses for the root / page
        if request.url.path == "/" and "text/html" in response.headers.get("content-type", ""):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            meta_tag = b'<meta name="impact-site-verification" value="1b0abe48-699c-47a5-afd2-96fe2538979b">'
            # Inject meta tag right before </head>
            if b"</head>" in body:
                body = body.replace(b"</head>", meta_tag + b"</head>")
            elif b"<head>" in body:
                body = body.replace(b"<head>", b"<head>" + meta_tag)
                
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
        return response

app.add_middleware(InjectMetaTagMiddleware)

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

    await cl.Message(
        content=f"🔄 Gathering options for **{session_data['game']}**... My specialist sub-agents are searching tickets, flights, and hotels using Google Search right now! Please wait a moment..."
    ).send()
    
    planner = TravelCrew(inputs=session_data)
    final_itinerary = await planner.run()
    
    await cl.Message(
        content=f"### 📋 Your Custom Sports Trip Itinerary\n\n{final_itinerary}"
    ).send()