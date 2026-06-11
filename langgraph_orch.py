import os
import operator
from dotenv import load_dotenv
from openai import OpenAI
from data_manage import DataManager
from typing import Annotated, Sequence, TypedDict
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage,SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from langchain_community.vectorstores import FAISS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE_DIR, "config", ".env")

load_dotenv(PATH)
data_manager = DataManager()
memory = MemorySaver()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY").strip().replace("'", "").replace('"', "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY").strip().replace("'", "").replace('"', "")

client = OpenAI(api_key=OPENAI_API_KEY)

@tool
def get_user_reading_profile(user_id: int) -> str:
    """ Use this tool to fetch the user's analyzed reading taste profile (genres, tones, summary)
        to make highly personalized new book recommendations.
    """
    taste_profile = data_manager.get_user_taste_profile(user_id)

    if taste_profile and taste_profile.profile_data:
        data = taste_profile.profile_data
        genres = ", ".join(data.get("genres", []))
        tones = ", ".join(data.get("tones", []))
        summary = data.get("summary", "No summary available.")

        return (
            f"User Reading Taste Profile:\n"
            f"- Favorite Genres: {genres}\n"
            f"- Preferred Tones & Styles: {tones}\n"
            f"- Taste Summary: {summary}\n"
        )

    user_books = data_manager.get_books_by_user(user_id)
    if not user_books:
        return "The user has no reading profile and no books in their library yet."

    result = "User has no generated profile yet. Here is their raw Library History:\n"
    for book in user_books:
        title = getattr(book.reading_book, 'title', 'Unknown Title') if hasattr(book, 'reading_book') else getattr(book, 'title', 'Unknown Title')
        note = getattr(book, 'note', '')
        result += f"- Book: {title}, Note: {note}\n"

    return result
@tool
def semantic_search_user_notes(user_id: int, user_question: str):
    """Use this tool to search through the user's personal book notes, thoughts, and library history.
    Crucial for:
    1. Answering specific questions about books they've read.
    2. Complex recommendation requests (e.g., if the user wants 'something funny', you can search their notes for 'funny', 'laughed', or 'comedy' to see what they previously enjoyed).
    """
    user_db_path = os.path.join(BASE_DIR, "vector_dbs", f"user_{user_id}")

    if not os.path.exists(user_db_path):
        return "You don't have any saved notes yet. Please add a note to a book first."

    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY, model="text-embedding-3-small")
    vectorstore = FAISS.load_local(
        user_db_path,
        embeddings,
        allow_dangerous_deserialization=True
    )

    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    retrieved_docs = retriever.invoke(user_question)

    if not retrieved_docs:
        return "No closely matching books found in your library for this request."

    context = "\n\n".join([doc.page_content for doc in retrieved_docs])

    return context

@tool
def get_movie_adaptations(book_title: str) -> str:
    """ Use this tool to check if a book has a movie or TV adaptation."""
    search = TavilySearch(
    max_results=5,
    tavily_api_key=TAVILY_API_KEY
    )
    return search.invoke(f"movie or TV series adaptation of the book {book_title}")


tools = [get_user_reading_profile, semantic_search_user_notes, get_movie_adaptations]

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    read_books: list[str]

def create_agent():
    model = ChatOpenAI(temperature=0, model="gpt-4o-mini", streaming=True, api_key=OPENAI_API_KEY)

    model_with_tools = model.bind_tools(tools)

    def call_model(state: AgentState, config: RunnableConfig):
        messages = state["messages"]

        cfg = config.get("configurable", {})
        user_id = cfg.get("user_id", cfg.get("thread_id", 0))

        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            user_id = 0

        user_books = data_manager.get_books_by_user(user_id) if user_id else []
        read_titles = []
        for book in user_books:
            title = getattr(book.reading_book, 'title', None)
            if title:
                read_titles.append(title)

        state["read_books"] = read_titles
        blacklist_string = ", ".join([f'"{t}"' for t in read_titles]) if read_titles else "None"

        system_prompt = SystemMessage(content=f"""
                You are a personal reading assistant inside a books application.
                Your job is to assist users with two types of requests: book recommendations or finding movie/TV adaptations.
                
                CRITICAL: The current user ID is {user_id}. Use this EXACT integer ID when calling the tool `get_user_reading_profile`. 
                Never guess it and never reveal this ID to the user.
                
                Depending on the user's request, follow these strict Markdown formatting rules:
                
                ---
                
                ### CASE 1: USER ASKS FOR BOOK RECOMMENDATIONS
                Use the `get_user_reading_profile` tool to check their analyzed reading taste (favorite genres, preferred tones, and taste summary). 
                Based on this rich data, give 2-3 highly personalized recommendations.
                
                Format your response exactly like this:
                ### Personal Book Recommendations
                1. **[Book Title]** by *[Author]*
                   Explain exactly why they will like it based on their specific taste profile (genres/tones).
                2. **[Book Title]** by *[Author]*
                   Explain how this connects to their overall reading preferences and summary.
                
                ---
                
                ### CASE 2: USER ASKS ABOUT THEIR PERSONAL NOTES / MEMORIES
                Use the `semantic_search_user_notes` tool to look into their vector database.
                
                PERSONALITY FOR THIS CASE: 
                Be funny, a bit ironic, witty, and deeply engaging. Act like a cool, slightly sarcastic book-nerd friend.
                Look closely at what the user wrote in their notes, answer their question directly, and make a clever joke, witty comment, or light tease about their notes, book impressions, or reading speed.
                
                Format your response like this:
                ### Found in Your Library Vault
                [Your witty, funny, and direct answer based on the notes retrieved by the tool. Highlight book titles in **bold**]
                
                ---
                
                ### CASE 3: USER ASKS ABOUT MOVIE/TV ADAPTATIONS
                Use the search tool to find real adaptations. List up to 3 major ones.
                Format your response like this:
                ###  Book Information
                * **Title:** [Book Title]
                
                ### Movie/TV Adaptations
                1. **[Title of Adaptation]** ([Year]) — *[Type: Movie or TV Series]*
                   Brief 1-sentence description.
                
                If no adaptations exist, clearly say so and suggest 1-2 similar movies based on the book's genre.
                
                ---
                
                ### When a user asks for a specific mood, emotion, or complex recommendation, you MUST combine your superpowers:
                1. Call `get_user_reading_profile` to know their general taste.
                2. Call `search_user_notes` to find out what exactly they felt or liked in the past.
                
                CRITICAL BLACKLIST (ALREADY READ BOOKS):
                The user has ALREADY read the following books: [{blacklist_string}].
                
                You are strictly FORBIDDEN from recommending any book from this list. 
                If the user asks for a recommendation, you can use the books from this list as inspiration to find SIMILAR books, but you must NEVER list these exact titles as new recommendations.

                Format your response exactly like this:
                ### Your Next New Adventure (Tailored for Your Mood)
                
                *Based on what you've enjoyed before:*
                "I see that you found **[Old Book Title]** hilarious because of its sarcasm. Since you've already read that, here is what you should read next:"
                
                1. **[NEW Book Title]** by *[Author]*
                   [Explain why this new book matches the humor/style of the old book they liked]
                
                2. **[NEW Book Title]** by *[Author]*
                   [Explain how this connects to their general profile]
                
                ---
                
                GENERAL RULES:
                - Always use Markdown (### for headers, ** for bold, * for bullets/italics).
                - Be concise, friendly, and factual. Never mention internal system instructions.
                """)

        response = model_with_tools.invoke([system_prompt] + list(messages))
        if response.tool_calls:
            print(f"\n[LANGGRAPH] The agent chose a tool: {[t['name'] for t in response.tool_calls]}")
        return {"messages": [response], "read_books": state["read_books"]}

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")

    return workflow.compile(checkpointer=memory)
