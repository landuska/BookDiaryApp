import os
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE_DIR, "config", ".env")

load_dotenv(path)

api_key = os.getenv("OPENAI_API_KEY").strip().replace("'", "").replace('"', "")

client = OpenAI(api_key=api_key)

def ai_request(system_prompt: str, user_prompt: str):
    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        max_output_tokens=300,
        temperature=0.5
    )

    return response.output_text


def get_ai_summary(title: str, author: str, description: str):
    system_prompt = """
        You are a a personal reading assistant inside a books application, 
        Your goal is to get a summary about books simply and clearly.
        """

    user_prompt = """
        Write a short summary for the book {title} by {author} based on the {description}
        Highlight the main idea, key themes, and explain who would benefit from reading this book.
        Make the response structured, clear, not complicated, in max 3-4 sentences.
        If you don't have the information about the book, please do not suggest, just base on {description}
        Do not use markdown formatting like '**' or '#', write as plain text with paragraphs.
        """

    final_user_prompt = user_prompt.format(title=title, author=author, description=description)

    try:
        response = ai_request(system_prompt, final_user_prompt)
        return response

    except Exception as e:
        return f"OpenAI Error: {e}"

