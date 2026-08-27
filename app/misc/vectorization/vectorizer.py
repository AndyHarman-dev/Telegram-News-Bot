import asyncio
from sentence_transformers import SentenceTransformer


class Vectorizer:
    _instance = None
    _lock = asyncio.Lock()
    model = None

    def __new__(cls):
        return cls.get_instance()

    @classmethod
    async def get_instance(cls) -> 'Vectorizer':
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    await cls._instance.__initialize()
        return cls._instance

    async def __initialize(self):
        self.model = await asyncio.to_thread(SentenceTransformer, 'distilbert-base-nli-mean-tokens')

    async def get_vector_for(self, text: str | list[str]):
        sentences = [text] if isinstance(text, str) else text
        return await asyncio.to_thread(self.model.encode, sentences)


async def main():
    vectorizer = await Vectorizer.get_instance()
    vec = await vectorizer.get_vector_for('Elephants, giraffes, crocodiles')
    print(vec)


if __name__ == '__main__':
    asyncio.run(main())
