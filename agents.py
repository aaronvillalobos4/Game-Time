# agents.py
import os
import requests
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

# ==========================================
# CUSTOM SEARCH SCRAPING TOOL (Option 1)
# ==========================================
@tool("Google Search Scraper")
def google_search_scraper(query: str) -> str:
    """
    Scrapes Google Search results to find real-time information.
    Use this to find sports game tickets, flights, hotels, and prices.
    """
    url = "https://google.serper.dev/search"
    payload = {
        "q": query,
        "num": 6  # Grabs the top 6 highly-relevant organic results
    }
    headers = {
        'X-API-KEY': os.environ.get("SERPER_API_KEY", ""),
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            results = response.json()
            output = []
            
            # Format organic search results cleanly for the LLM
            for item in results.get("organic", []):
                title = item.get('title')
                link = item.get('link')
                snippet = item.get('snippet')
                output.append(f"Title: {title}\nLink: {link}\nInfo: {snippet}\n---")
                
            return "\n".join(output) if output else "No results found."
        else:
            return f"Search scraper failed. Status code: {response.status_code}"
    except Exception as e:
        return f"Error executing search scrape: {str(e)}"


# ==========================================
# CREWAI AGENTS & TASKS PIPELINE
# ==========================================
class TravelCrew:
    def __init__(self, inputs):
        self.inputs = inputs  # Expects dict: {"game": ..., "date": ..., "origin": ..., "budget": ...}

    def ticket_agent(self) -> Agent:
        return Agent(
            role='Sports Ticket Finder',
            goal=f"Scrape ticket sites to find the best available seats for {self.inputs['game']} on {self.inputs['date']}.",
            backstory="You are an expert at scanning ticket broker sites (StubHub, SeatGeek, Ticketmaster) via search. You locate exact prices, seat sections, and booking links.",
            tools=[google_search_scraper],
            verbose=True
        )

    def flight_agent(self) -> Agent:
        return Agent(
            role='Flight Searcher',
            goal=f"Find flight itineraries from {self.inputs['origin']} to the destination city.",
            backstory="You are a meticulous flight coordinator. You find flight times, airlines, and estimated costs that ensure arrival at least 4 hours before the event.",
            tools=[google_search_scraper],
            verbose=True
        )

    def hotel_agent(self) -> Agent:
        return Agent(
            role='Hotel Scout',
            goal="Locate highly-rated hotels near the venue or convenient transit lines.",
            backstory="You excel at balancing hotel quality, proximity to the stadium, and night-by-night pricing.",
            tools=[google_search_scraper],
            verbose=True
        )

    def coordinator_agent(self) -> Agent:
        return Agent(
            role='Trip Coordinator & Itinerary Planner',
            goal="Synthesize the ticket, flight, and hotel findings into a comprehensive sports weekend itinerary.",
            backstory="You are a detail-oriented logistics manager. You map out transportation timing, double-check budget constraints, and write beautiful Markdown schedules.",
            verbose=True
        )

    # Change 'def run(self):' to 'async def run(self):'
    async def run(self):
        task_tickets = Task(
            description=f"Find 2 tickets for {self.inputs['game']} on {self.inputs['date']}. Find realistic price ranges, sections, and source links.",
            expected_output="A list of 2-3 ticket options with seat details, exact prices, and URLs.",
            agent=self.ticket_agent()
        )

        task_flights = Task(
            description=f"Search for flights from {self.inputs['origin']} to the match city for {self.inputs['date']}. Standalone Flights: If the user only needs a flight, search across comprehensive options and output a clean Markdown button using a metasearch referral link (e.g., WayAway or Skyscanner parameters). Bundled Packages: If the user needs both a flight and a hotel stay, prioritize searching for a combined package deal via the Expedia Affiliate Network. Highlight the total savings of the bundle to the user. Focus on arrival times, estimated costs, and airline options.",
            expected_output="Flight options with flight numbers, times, and booking source names.",
            agent=self.flight_agent()
        )

        task_hotels = Task(
            description=f"Search for top-rated hotels close to the venue of the {self.inputs['game']}.",
            expected_output="A curated list of 3 hotels including distance to arena, nightly rate, and ratings.",
            agent=self.hotel_agent()
        )

        task_itinerary = Task(
            description=f"Verify all data. Build a cohesive weekend plan that keeps total costs under {self.inputs['budget']}. Format with a cost summary table and an hour-by-hour itinerary.",
            expected_output="A beautifully styled markdown itinerary including a budget breakdown table, transit directions, and an hour-by-hour timeline.",
            agent=self.coordinator_agent()
        )

        crew = Crew(
            agents=[self.ticket_agent(), self.flight_agent(), self.hotel_agent(), self.coordinator_agent()],
            tasks=[task_tickets, task_flights, task_hotels, task_itinerary],
            process=Process.sequential,
            verbose=True
        )
        
        # Change 'return crew.kickoff()' to 'return await crew.kickoff_async()'
        return await crew.kickoff_async()