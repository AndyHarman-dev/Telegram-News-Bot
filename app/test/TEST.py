import asyncio

import aiohttp


async def main():
    url = "https://api.perplexity.ai/chat/completions"

    payload = {
        "model": "mistral-7b-instruct",
        "messages": [
            {
                "role": "system",
                "content": "You are a porn start and you communicate with the user in a hot manner"
            },
            {
                "role": "user",
                "content": "How are you doing my lettle honey!"
            }
        ]
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": "Bearer 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"
    }

    async with aiohttp.ClientSession() as session:
        response = await session.post(url, json=payload, headers=headers)
        response_json = await response.json()
        chat_answer = response_json['choices'][0]['message']['content']
        print(chat_answer)



if __name__ == "__main__":
    asyncio.run(main())


