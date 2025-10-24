from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from debug_toolbar.middleware import DebugToolbarMiddleware
from pydantic import BaseModel
import os
import random

class Joke(BaseModel):
    setup: str
    punchline: str
    category: str

# Read the root path from an environment variable, defaulting to "" if not set
root_path = os.getenv("ROOT_PATH", "")

app = FastAPI(debug=True, root_path=root_path)

# Mount the middleware
app.add_middleware(DebugToolbarMiddleware)

# This example uses Jinja2 so we have an HTML page to inject the toolbar into
templates = Jinja2Templates(directory="templates")

# Configure to bind to all interfaces for code-server access
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

JOKES = [
    Joke(setup="Why don't scientists trust atoms?", punchline="Because they make up everything!", category="science"),
    Joke(setup="What do you call a fake noodle?", punchline="An impasta!", category="food"),
    Joke(setup="Why did the scarecrow win an award?", punchline="He was outstanding in his field!", category="general"),
    Joke(setup="What do you call a bear with no teeth?", punchline="A gummy bear!", category="animals"),
    Joke(setup="Why don't eggs tell jokes?", punchline="They'd crack each other up!", category="food"),
    Joke(setup="What's the best thing about Switzerland?", punchline="I don't know, but the flag is a big plus!", category="geography"),
    Joke(setup="Why did the math book look so sad?", punchline="Because it had too many problems!", category="education"),
    Joke(setup="What do you call a sleeping bull?", punchline="A bulldozer!", category="animals"),
    Joke(setup="Why can't a bicycle stand up by itself?", punchline="It's two tired!", category="general"),
    Joke(setup="What do you call a fish wearing a bowtie?", punchline="Sofishticated!", category="animals")
]

@app.get("/")
def home(request: Request):
    """
    An example route that renders an HTML template.
    The debug toolbar will appear on this page.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/help")
def root():
    return {"message": "Joke API"}

@app.get("/joke", response_model=Joke)
def get_random_joke():
    return random.choice(JOKES)

@app.get("/jokes", response_model=list[Joke])
def get_all_jokes():
    return JOKES
    