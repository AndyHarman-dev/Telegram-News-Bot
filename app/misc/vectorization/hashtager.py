from app.database.db_hashtag import hashtag_categories
from app.misc.vectorization.vectorizer import Vectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import asyncio
import json


class Hashtager:
    _instance = None
    _lock: asyncio.Lock = asyncio.Lock()
    __vectorizer = None
    __hashtags_list: list[str] = None
    __hashtags_path: dict = None
    __hashtags_vector: np.ndarray = None
    __MIN_HASHTAGS_COUNT = 5
    __MAX_HASHTAGS_COUNT = 25
    __MIN_SIM_VALUE = 0.5
    __ACCEPT_PERCENT_MAX_SIM_V = 0.8

    def __new__(cls):
        return cls.get_instance()

    @classmethod
    async def get_instance(cls) -> 'Hashtager':
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    await cls._instance.__init_hashtags_vec()
        return cls._instance

    async def __init_hashtags_vec(self):
        self.__vectorizer = await Vectorizer.get_instance()
        self.__hashtags_list, self.__hashtags_path = self.creating_hashtags_list()
        self.__hashtags_vector = await self.__vectorizer.get_vector_for(self.__hashtags_list)

    async def hashtagization(self, user_preferences: str):
        vector_preferences: np.ndarray = await self.__vectorizer.get_vector_for(user_preferences)
        similarities: np.ndarray = cosine_similarity(self.__hashtags_vector, vector_preferences)
        optimal_count = self.get_optimal_hashtags_count(similarities)
        top_indices = similarities.transpose()[0].argsort()[-optimal_count:][::-1]
        return [(self.__hashtags_list[i], similarities[i][0]) for i in top_indices]

    async def choosing_hashtags_for(self, user_preferences: str):
        similarities = await self.hashtagization(user_preferences)
        return {hashtag: self.__hashtags_path[hashtag] for hashtag, _ in similarities}

    @staticmethod
    def get_optimal_hashtags_count(similarities: np.ndarray):
        sorted_similarities = sorted(similarities.transpose()[0], reverse=True)
        min_ind = Hashtager.__MIN_HASHTAGS_COUNT - 1
        max_ind = Hashtager.__MAX_HASHTAGS_COUNT - 1
        min_val = Hashtager.__MIN_SIM_VALUE
        accepted_val = Hashtager.__ACCEPT_PERCENT_MAX_SIM_V * sorted_similarities[0]
        if sorted_similarities[min_ind] < min_val or sorted_similarities[min_ind] < accepted_val:
            return Hashtager.__MIN_HASHTAGS_COUNT
        if sorted_similarities[max_ind] >= min_val and sorted_similarities[max_ind] >= accepted_val:
            return Hashtager.__MAX_HASHTAGS_COUNT
        optimal_ind = min_ind
        while optimal_ind < max_ind and sorted_similarities[optimal_ind + 1] >= min_val and sorted_similarities[optimal_ind + 1] >= accepted_val:
            optimal_ind += 1
        return optimal_ind + 1

    @staticmethod
    def creating_hashtags_list() -> tuple[list, dict]:
        all_hashtags_info = sorted(list(
            [f'{category.lower()}: {Hashtager._into_words(hashtag)}', category, hashtag]
            for category, hashtags in hashtag_categories.items()
            for hashtag in hashtags
        ), key=lambda x: x[0])
        hashtags_list = [hashtag for hashtag, _, _ in all_hashtags_info]
        hashtags_path = {hashtag: (category_name, hashtag_name)
                         for hashtag, category_name, hashtag_name in all_hashtags_info}
        return hashtags_list, hashtags_path

    @staticmethod
    def _into_words(hashtag: str) -> str:
        if hashtag[0] != '#':
            raise ValueError('Incorrect hashtag')
        s = hashtag[1:]
        if len(s) < 2:
            raise ValueError('The string is too short')
        if len(s) == 2:
            return s.lower()
        output_string = s[0]
        for i in range(1, len(s) - 2):
            output_string += s[i]
            if s[i + 1].isupper() and s[i + 2].islower():
                output_string += ' '
        output_string += s[-2:]
        return output_string.lower()


async def process_preferences(pref_examples):
    h = await Hashtager.get_instance()
    results = []

    for pref_example in pref_examples:
        result = await h.hashtagization(pref_example)
        pref_result = {
            "preference": pref_example,
            "hashtags": [{
                "hashtag": hashtag,
                "similarity": float(similarity)
            } for hashtag, similarity in result]
        }
        results.append(pref_result)

    return results


async def path_for_preferences(pref_examples):
    h = await Hashtager.get_instance()
    results = []

    for pref_example in pref_examples:
        result = await h.choosing_hashtags_for(pref_example)
        pref_result = {
            "preference": pref_example,
            "hashtags": [{
                "hashtag": hashtag,
                "path": f"{path[0]}->{path[1]}"
            } for hashtag, path in result.items()]
        }
        results.append(pref_result)

    return results


def write_results_to_file(results, filename="preference_results.json"):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


async def main():
    pref_examples = [
        'Elephants, giraffes, crocodiles',
        'Rock painting, graffiti; political analysis, debate',
        'Reggae, jazz, blues',
        'Artificial intelligence, machine learning, robotics',
        'Climate change, renewable energy, sustainable living',
        'Space exploration, astronomy, astrophysics',
        'Healthy recipes, nutrition tips, organic food',
        'Cryptocurrency, blockchain technology, fintech innovations',
        'Yoga, meditation, mindfulness practices',
        'Virtual reality, augmented reality, gaming industry news',
        'Classic literature, poetry, book reviews',
        'Architectural design, urban planning, sustainable cities',
        'Fashion trends, sustainable clothing, ethical fashion brands',
        'Mental health awareness, psychology research, self-care tips',
        'Electric vehicles, autonomous driving technology, future of transportation',
        'Biodiversity conservation, wildlife protection, endangered species',
        'Quantum computing, nanotechnology, emerging scientific breakthroughs',
        'Ancient civilizations, archaeology, historical discoveries',
        'Indie films, international cinema, film festival coverage',
        'Artificial intelligence in healthcare, medical research breakthroughs, telemedicine',
        'Renewable energy sources, solar power innovations, wind turbine technology',
        'Cybersecurity, data privacy, ethical hacking',
        'Genetic engineering, CRISPR technology, bioethics debates',
        'Minimalism, decluttering techniques, simple living philosophy',
        'Extreme sports, adventure travel, outdoor survival skills',
        'Graphic design trends, typography, branding strategies',
        'Sustainable agriculture, vertical farming, permaculture practices',
        'Neuroscience advancements, brain-computer interfaces, cognitive enhancement',
        'Classical music, opera performances, symphony orchestra news',
        'DIY home improvement, woodworking projects, upcycling ideas'
    ]
    results = await path_for_preferences(pref_examples)  # results = await process_preferences(pref_examples)
    write_results_to_file(results)
    print(f"Results have been written to preference_results.json")


if __name__ == "__main__":
    asyncio.run(main())
