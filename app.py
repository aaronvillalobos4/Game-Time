import os
import chainlit as cl
from dotenv import load_dotenv
from agents import TravelCrew

# Load environment keys from secret .env file
load_dotenv()


@cl.on_chat_start
async def start():
    # Send welcome message when a user starts a chat session
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
    
    # Run background Crew
    planner = TravelCrew(inputs=session_data)
    final_itinerary = await planner.run()
    
    await cl.Message(
        content=f"### 📋 Your Custom Sports Trip Itinerary\n\n{final_itinerary}"
    ).send()