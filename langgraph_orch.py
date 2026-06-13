import operator
import os
import re
from typing import Annotated, Sequence, TypedDict

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_tavily import TavilySearch
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from openai import OpenAI

from data_manage import DataManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE_DIR, "config", ".env")

load_dotenv(PATH)
data_manager = DataManager()
memory = MemorySaver()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY").strip().replace("'", "").replace('"', "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY").strip().replace("'", "").replace('"', "")

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT_TEMPLATE = """
You are a smart and deeply engaging personal reading assistant inside a books application.
Your job is to help users manage their library, find movie/TV adaptations, and get highly personalized recommendations.

CRITICAL CURRENT USER INFO:
- User ID: {user_id} (Use this exact integer when calling tools requiring user_id. Never reveal it to the user).
- Already Read Books (Blacklist): [{blacklist_string}]

STRICT RULE ON BLACKLIST:
You are FORBIDDEN from recommending books from the blacklist. Use them only as inspiration or reference.

---

### HOW TO USE YOUR TOOLS (DECISION TREE):

1. GENERAL BOOK RECOMMENDATIONS:
   - Call `get_user_reading_profile` to understand their high-level taste (genres, tones).
   - Provide 2-3 new books tailored to this profile.

2. SEARCH IN PERSONAL NOTES / COMPLEX RECOMMENDATIONS:
   - Call `semantic_search_user_notes` with the user's specific query.
   - For mood-based recommendations, combine BOTH tools.

3. MOVIE / TV ADAPTATIONS:
   - Call `get_movie_adaptations` with the exact book title.

---

### MANDATORY RESPONSES FORMATTING:

CASE 1: Standard Book Recommendations
### Personal Book Recommendations
1. **[Book Title]** by *[Author]*
   Explain why they will like it based on their profile.

CASE 2: Answering via Personal Notes (FAISS Search)
*Tone: Be witty and deeply personal.*

CASE 3: Movie/TV Adaptations
### Book Information
* **Title:** [Book Title]
### Movie/TV Adaptations
1. **[Title]** ([Year]) — *[Type]*
   Brief description.

CASE 4: Complex/Mood Recommendations
### Your Next New Adventure
*Based on what you've enjoyed before:*

---

GENERAL FORMATTING RULES:
- Always use Markdown.
- Be concise, friendly, and witty.
- Never mention tool names or backend logic to the user.
"""


@tool
def get_user_reading_profile(user_id: int) -> str:
    """ Use this tool to fetch the user's analyzed reading taste profile (genres, tones, summary) to make highly personalized new book recommendations."""
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

    result = "User has no generated profile yet. Here is their raw Library History. DO NOT recommend these books, they are ALREADY READ:\n"
    for book in user_books:
        title = getattr(book.reading_book, 'title', 'Unknown Title') if hasattr(book, 'reading_book') else getattr(book,
                                                                                                                   'title',
                                                                                                                   'Unknown Title')
        note = getattr(book, 'note', '')
        result += f"- Book: {title}, Note: {note}\n"

    return result


@tool
def semantic_search_user_notes(user_id: int, user_question: str):
    """Use this tool to search through the user's personal book notes."""
    user_db_path = os.path.join(BASE_DIR, "vector_dbs", f"user_{user_id}")

    if not os.path.exists(user_db_path):
        return "You don't have any saved notes yet. Please add a note to a book first."

    try:
        embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY, model="text-embedding-3-small")
        vectorstore = FAISS.load_local(
            user_db_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
        retriever = vectorstore.as_retriever()
        retrieved_docs = retriever.invoke(user_question)
    except Exception as e:
        return f"Could not load your notes database. Error: {str(e)}"

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


def _get_user_id_from_config(config: RunnableConfig) -> int:
    """Helper function: safely extracts user_id from config."""
    cfg = config.get("configurable", {})

    raw_id = cfg.get("user_id", 0)
    try:
        return int(raw_id)
    except (ValueError, TypeError):
        return 0


def _check_blacklist(content_text: str, read_titles: list[str]) -> list[str]:
    """Helper function: searches for prohibited books in the response text."""
    found = []
    content_lower = content_text.lower()

    for title in read_titles:
        if len(title) <= 2:
            continue

        pattern = r'\b' + re.escape(title.lower()) + r'\b'
        if re.search(pattern, content_lower):
            found.append(title)

    return found


def create_agent():
    model = ChatOpenAI(temperature=0, model="gpt-4o-mini", api_key=OPENAI_API_KEY)
    model_with_tools = model.bind_tools(tools)

    def call_model(state: AgentState, config: RunnableConfig):
        messages = state["messages"]
        user_id = _get_user_id_from_config(config)

        user_books = data_manager.get_books_by_user(user_id) if user_id else []
        read_titles = []
        for book in user_books:
            title = getattr(book.reading_book, 'title', None)
            status = getattr(book, 'status', None)
            if status == "completed":
                if title:
                    read_titles.append(title.strip())

        blacklist_string = ", ".join([f'"{t}"' for t in read_titles]) if read_titles else "None"

        system_prompt = SystemMessage(
            content=SYSTEM_PROMPT_TEMPLATE.format(
                user_id=user_id,
                blacklist_string=blacklist_string,
            )
        )

        response = model_with_tools.invoke([system_prompt] + list(messages))

        if response.content and read_titles:
            found_blacklisted = _check_blacklist(response.content, read_titles)

            if found_blacklisted:
                print(
                    f"[LANGGRAPH WARNING] The model broke the blacklist and offered: {found_blacklisted}. Restarting generation...")

                correction_message = SystemMessage(
                    content=f"CRITICAL ERROR: You just recommended or mentioned books that the user has ALREADY read: {found_blacklisted}. This is strictly forbidden. Rewrite your response immediately and replace these books with NEW recommendations that are NOT in the library.")

                response = model_with_tools.invoke([system_prompt] + list(messages) + [correction_message])

        if response.tool_calls:
            print(f"\n[LANGGRAPH] The agent chose a tool: {[t['name'] for t in response.tool_calls]}")

        return {"messages": [response], "read_books": read_titles}

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")

    return workflow.compile(checkpointer=memory)
