import openai
from dotenv import load_dotenv
import requests
import os


# Инициализация ключа API
def initialize_llm_api():
    load_dotenv()
    openai.api_key = os.getenv('OPENAI_API_KEY')
    #another APis




def summarize_content_with_openai(link):
    try:
        response = requests.get(link)
        print( len(response.text) )
        article_content = response.text[:100000]  # get only the first 4000 characters
 #       print("Original Article Content (limited to 200000 chars):")
 #       print(article_content)  # Displaying the truncated content
        print("\n\n")  # some space
    except:
        print(f"Error fetching content for {link}")
        return ""

    # extract text out of HTML
    soup = BeautifulSoup(article_content, "html.parser")
    plain_text = soup.get_text()[:2000]

    print(plain_text)

    response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
     #   {"role": "system", "content": "Summarize text, add your comments, write in funny neformal style"},
        {"role": "system", "content": "Summarize text, add your comments, and remarks, write in professional style"},
        {"role": "user", "content": plain_text}
    ],
    max_tokens=500  # Adjust the max tokens based on your needs
    )
    print("response from GPT:")
    print( response.choices[0].message['content'].strip() )
    return response.choices[0].message['content'].strip()


# Пример использования функции
if __name__ == "__main__":
    initialize_llm_api()
    sample_content = "Here is some sample posts content to rate."
    print(llm_rate_posts(sample_content))
