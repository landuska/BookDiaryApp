import os
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE_DIR, "config", ".env")

load_dotenv(path)

api_key = os.getenv("OPENAI_API_KEY").strip().strip("'").strip('"')

client = OpenAI(api_key=api_key)

def get_ai_summary(title: str, author: str):

        user_prompt = (
            f"Write a short summary for the book {title} by {author}"
            f"Highlight the main idea, key themes, and explain who would benefit from reading this book. "
            f"Make the response structured, clear, not complicated, in max 3-4 sentences. "
            f"Do not use markdown formatting like '**' or '#', write as plain text with paragraphs."
        )

        system_prompt = "You are a reading assistant, who get a summary about books simply and clearly."

        try:
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
                temperature=0.7
            )

            ai_response = response.output_text
            return ai_response

        except Exception as e:
            return f"OpenAI Error: {e}"
