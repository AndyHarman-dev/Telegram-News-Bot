import asyncio

from app.database.db_helper import DatabaseHelper
import re #for text hashtag extract

hashtag_categories = {
    "Politics & Government": [
        "#Politics", "#Diplomacy", "#Government", "#Centrism", "#Socialism", "#Libertarianism",
        "#Anarchism", "#PoliticalAnalysis", "#PolicyMaking", "#CivicEngagement"
    ],
    "Economics & Finance": [
        "#Economy", "#FinancialNews", "#Trade", "#Crypto", "#StockMarket", "#FinancialFreedom",
        "#Investor", "#Budgeting", "#WealthBuilding", "#RealEstateInvestor", "#EconomicDevelopment",
        "#EmergingMarkets", "#GlobalTrade", "#EconomicPolicy", "#Startups", "#BusinessStrategy",
        "#Entrepreneurship", "#Marketing", "#ECommerce"
    ],
    "Society & Social Issues": [
        "#SocialIssue", "#HumanRights", "#Justice", "#Conservative", "#Liberal", "#Activist",
        "#Feminist", "#LGBTQSupporter", "#EnvironmentalAdvocate", "#HumanRightsDefender",
        "#SocialJusticeWarrior", "#GlobalWarming", "#RefugeeCrisis", "#WorldHunger",
        "#WaterCrisis", "#GlobalHealth", "#JusticeSystem", "#HumanRightsLaw"
    ],
    "Health & Well-being": [
        "#HealthUpdate", "#MentalHealth", "#PublicHealth", "#MentalHealthAwareness",
        "#WellnessJourney", "#SelfCare", "#HealthyLiving", "#Mindfulness",
        "#MeditationEnthusiast", "#COVID19", "#ChronicIllness", "#HealthcareReform", "#Nutrition",
        "#FitnessTrends", "#MentalWellness", "#AlternativeMedicine", "#HealthTech"
    ],
    "Science & Technology & Education": [
        "#TechNews", "#ScienceUpdate", "#Innovation", "#Space", "#Education",
        "#Research", "#Learning", "#LifelongLearner", "#OnlineCourse", "#DIY",
        "#SkillDevelopment", "#LanguageLearner", "#Educator", "#StudentLife",
        "#STEM", "#TechEnthusiast", "#Blockchain", "#Cybersecurity", "#DataScience",
        "#MachineLearning", "#AugmentedReality", "#InternetOfThings", "#5G",
        "#QuantumComputing", "#Genomics", "#Astrophysics", "#SustainableEnergy", "#MedicalResearch",
        "#Physics", "#Biotechnology", "#EnvironmentalScience", "#Astronomy", "#EduTech",
        "#OnlineLearning", "#AcademicResearch", "#AISafety", "#RocketScience", "#Programming"
    ],
    "Culture": [
        "#CulturalEvent", "#CulturalFestivals", "#CulturalHeritage", "#BookClub", "#LiteraryReadings",
        "#CulturalExplorer", "#HistoricalDrama", "#CulturalExchange", "#CulturalHistory", "#Ethnography",
        "#Museums", "#CulturalTraditions", "#Folklore", "#Anthropology", "#CulturalCelebrations"
    ],
    "Arts": [
        "#Art", "#ContemporaryArt", "#ArtExhibitions", "#ArtGalleries", "#Sculpture",
        "#ArtHistory", "#Painting", "#StreetArt", "#Photography", "#DigitalArt",
        "#FineArts", "#ArtistsSpotlight", "#PerformanceArt", "#VisualArts", "#ArtInstallations",
        "#GraphicDesign", "#ArtFairs", "#ArtTherapy", "#ArtCollectors", "#ArtAuctions",
        "#Crafts", "#Ceramics", "#Printmaking", "#Illustration", "#PublicArt"
    ],
    "Entertainment": [
        "#Entertainment", "#Movies", "#TV", "#WebSeries", "#Podcasts", "#RadioShows",
        "#Music", "#Concerts", "#AlbumRelease", "#MusicVideos", "#Awards", "#PopCulture",
        "#ViralTrends", "#Memes", "#InfluencerCulture", "#Vloggers", "#Streamers",
        "#GamingNews", "#FanConventions", "#CelebrityNews", "#MovieReviews", "#TVShows",
        "#RealityShows", "#TalkShows", "#ComedyShows", "#Theater", "#BroadwayShows",
        "#Musicals", "#LiveComedy", "#Cinema", "#FilmFestival", "#MusicFestivals",
        "#Nightlife", "#Clubbing", "#MagicShows", "#Circus", "#VarietyShows", "#Cosplay"
    ],
    "Sports & Athletics": [
        "#Sports", "#Athletics", "#TeamSports", "#IndividualSports", "#Olympics", "#WorldCup",
        "#Football", "#Basketball", "#Baseball", "#Cricket", "#Tennis", "#Golf",
        "#Rugby", "#Hockey", "#MMA", "#Boxing", "#Cycling", "#Swimming", "#TrackAndField",
        "#Volleyball", "#Gymnastics", "#Skating", "#Skiing", "#Snowboarding", "#Surfing",
        "#Motorsport", "#F1", "#NASCAR", "#Esports", "#Badminton", "#TableTennis", "#Marathon",
        "#Triathlon", "#Equestrian", "#Skateboarding", "#Climbing", "#Wrestling", "#Judo",
        "#Taekwondo", "#Karate", "#Archery", "#ShootingSports", "#Fencing", "#Weightlifting",
        "#Bodybuilding", "#Yoga", "#Pilates", "#DanceSports", "#Parkour"
    ],
    "Environment & Climate": [
        "#Climate", "#Environment", "#GlobalWarming", "#EnvironmentalAdvocate", "#Sustainability",
        "#GreenTech", "#EcoFriendly", "#Conservation", "#RenewableEnergy"
    ],
    "Crime & Safety": [
        "#Crime", "#Safety", "#LegalNews", "#Regulations", "#Compliance", "#CorporateLaw"
    ],
    "Lifestyle & Personal Characteristics": [
        "#Vegan", "#Minimalist", "#ZeroWaste", "#DigitalNomad", "#Parenting",
        "#PetLover", "#Homebody", "#FitnessEnthusiast", "#TravelJunkie",
        "#Introvert", "#Extrovert", "#Ambivert", "#Empath", "#Optimist",
        "#Pessimist", "#Realist", "#SustainableLiving", "#DigitalLifestyle",
        "#UrbanGardening", "#TinyHomes", "#SelfImprovement", "#LifeHacks", "#CareerAdvice",
        "#SuccessStories", "#Mindset", "#FashionTrends", "#BeautyTips", "#StreetStyle"
    ],
    "Hobbies & Interests": [
        "#Bookworm", "#Traveler", "#Foodie", "#Gamer", "#MusicLover", "#FitnessFreak",
        "#NatureLover", "#ArtAficionado", "#SportsFan", "#PhotographyEnthusiast", "#MovieBuff",
        "#DIYer", "#GardeningLover", "#Fashionista", "#Gourmet", "#HomeCooking",
        "#VeganRecipes", "#StreetFood"
    ],
    "Religion & Spirituality": [
        "#Atheist", "#Agnostic", "#Christian", "#Muslim", "#Buddhist",
        "#SpiritualButNotReligious", "#Hindu", "#Pagan", "#SpiritualSeeker"
    ],
    "Geography & Travel": [
        "#Expatriate", "#LocalTravel", "#WorldTraveler", "#CulturalExplorer", "#UrbanExplorer",
        "#RuralAdventurer", "#AdventureTravel", "#EcoTourism", "#CityBreaks", "#CulinaryTravel",
        "#Backpacking"
    ],
    "Gaming & Digital Entertainment": [
        "#Gaming", "#GameRelease", "#GameReview", "#PlatformGaming", "#VRGaming",
        "#GamingCommunity", "#GamingNews", "#VR"
    ],
    "Legal & Regulatory News": [
        "#LegalNews", "#Regulations", "#Compliance", "#CorporateLaw", "#JusticeSystem"
    ],
    "Industry-Specific News": [
        "#AutomotiveNews", "#FashionIndustry", "#AgricultureNews", "#RenewableEnergy"
    ],
    "Historical Context": [
        "#OnThisDay", "#HistoryFacts", "#HistoricalPerspective"
    ],
    "Special Events & Occasions": [
        "#Olympics", "#WorldCup", "#Elections2024", "#EarthDay", "#InternationalWomensDay"
    ],
    "User-Generated Content": [
        "#UserStory", "#CommunityVoice", "#LifeHacks", "#DIYProjects", "#TravelDiaries",
        "#FoodBlogging", "#FashionBlogging", "#FitnessJourney", "#ArtShare", "#PhotographyLovers",
        "#Vlog", "#PersonalBlog", "#MakeupTutorial", "#GamingContent", "#TechReviews",
        "#BookReviews", "#MovieReviews", "#MusicCovers", "#DanceVideos", "#ComedySkits",
        "#PetVideos", "#ParentingTips", "#GardeningTips", "#SustainabilityIdeas", "#HealthTips",
        "#MotivationalPosts", "#Poetry", "#ShortStories", "#FanArt", "#Crafting",
        "#HomeDecorIdeas", "#FitnessChallenges", "#CookingRecipes", "#TravelVlogs", "#StudyWithMe",
        "#ProductivityTips", "#MentalHealthAwareness", "#CulturalExchange", "#LanguageLearning",
        "#VirtualTours", "#RemoteWork", "#Volunteering", "#CharityWork", "#SocialActivism"
    ],
    "Fact-Checking & Misinformation": [
        "#FactCheck", "#Misinformation", "#FakeNewsAlert"
    ],
    "Music": [
        "#Pop", "#Rock", "#Jazz", "#Classical", "#HipHop", "#Electronic", "#Country", "#Blues",
        "#Indie", "#Folk", "#Reggae", "#Soul", "#Metal", "#Punk", "#RnB", "#Latin", "#World",
        "#EDM", "#KPop"
    ],
    "Regional News": [
        "#InternationalNews", "#NorthAmerica", "#SouthAmerica", "#Europe", "#Asia", "#Africa",
        "#MiddleEast", "#Australia", "#Russia", "#China", "#India", "#USA", "#UK", "#Germany",
        "#France", "#Japan", "#Brazil", "#Canada", "#Italy", "#Spain", "#Mexico", "#Taiwan",
        "#Singapore", "#Egypt", "#SaudiArabia", "#UAE", "#Iraq", "#Indonesia", "#Portugal",
        "#Quebec", "#Austria", "#Switzerland", "#Ukraine", "#Belarus"
    ]
}

# Get a list of all main categories
main_categories = list(hashtag_categories.keys())


class HashtagManager:
    @staticmethod
    def get_hashtag_id(hashtag_identifier):
        """
        Get the ID of a hashtag from its name or ID.
        """
        if isinstance(hashtag_identifier, str):
            query = "SELECT hashtag_id FROM hashtags WHERE hashtag_name = ?"
        elif isinstance(hashtag_identifier, int):
            return hashtag_identifier
        else:
            raise ValueError("hashtag_identifier must be either a string (hashtag name) or an integer (hashtag ID)")

        result = DatabaseHelper.safe_execute_query(query, (hashtag_identifier,))
        return result[0][0] if result else None

    @staticmethod
    def get_hashtag_id_by_category_and_name(hashtag_category, hashtag_name):
        """
        Get the ID of a hashtag from its name and category.
        """
        if not isinstance(hashtag_category, str) or not isinstance(hashtag_name, str):
            raise ValueError("This hashtags' identifiers must be a string")

        query = """
            SELECT hashtag_id FROM hashtags
            JOIN hashtag_categories ON hashtags.category_id = hashtag_categories.category_id
            WHERE hashtags.hashtag_name = ? AND hashtag_categories.category_name = ?
        """

        result = DatabaseHelper.safe_execute_query(query, (hashtag_name, hashtag_category))

        return result[0][0] if result else None

    @staticmethod
    def get_relevant_posts_for_hashtag(hashtag, num_posts=5):
        """
        Get the relevant posts for a given hashtag.
        """
        query = """
            SELECT p.post_id
            FROM posts p
            JOIN posts_hashtags ph ON p.post_id = ph.entity_id
            JOIN hashtags h ON ph.hashtag_id = h.hashtag_id
            WHERE h.hashtag_id = ?
            ORDER BY p.date DESC
            LIMIT ?
        """
        hashtag_id = HashtagManager.get_hashtag_id(hashtag)

        response = DatabaseHelper.safe_execute_query(query, (hashtag_id, num_posts))

        # Получаем список постов из объекта Cursor
        posts = [post[0] for post in response]

        return posts

    @staticmethod
    def get_hashtag_categories_list():
        query = "SELECT category_name FROM hashtag_categories"
        return [category[0] for category in DatabaseHelper.safe_execute_query(query)]

    @staticmethod
    def get_hashtags_for_categories(categories):
        # convert one category to list
        if isinstance(categories, str):
            categories = [categories]

        # placeholder for SQL query
        placeholders = ','.join('?' for _ in categories)

        query = f"""
            SELECT hashtag_name FROM hashtags
            JOIN hashtag_categories ON hashtags.category_id = hashtag_categories.category_id
            WHERE category_name IN ({placeholders})
        """
        result = DatabaseHelper.safe_execute_query(query, categories)
        return [hashtag[0] for hashtag in result]

    @staticmethod
    def get_hashtags_from_same_category(search_hashtag):
        query = """
            SELECT hashtag_name FROM hashtags
            JOIN hashtag_categories ON hashtags.category_id = hashtag_categories.category_id
            WHERE hashtags.category_id = (
                SELECT category_id FROM hashtags WHERE hashtag_name = ?
            )
        """
        result = DatabaseHelper.safe_execute_query(query, (search_hashtag,))
        return [hashtag[0] for hashtag in result]

    @staticmethod
    def is_hashtag_exists(hashtag):
        query = "SELECT 1 FROM hashtags WHERE hashtag_name = ?"
        return bool(DatabaseHelper.safe_execute_query(query, (hashtag,)))

    @staticmethod
    def get_hashtag_ids_for_entity(entity_ids, entity_hashtag_table) -> str:
        # Convert a single entity ID to a list
        if isinstance(entity_ids, int):
            entity_ids = [entity_ids]

        # Placeholder for SQL query
        placeholders = ','.join('?' for _ in entity_ids)

        query = f"""
            SELECT h.hashtag_id FROM hashtags h
            JOIN {entity_hashtag_table} eh ON h.hashtag_id = eh.hashtag_id
            WHERE eh.entity_id IN ({placeholders})
        """

        result = DatabaseHelper.safe_execute_query(query, entity_ids)

        if result is None:
            return result

        # Convert the result to a list of hashtags
        hashtags = [hashtag[0] for hashtag in result]

        return hashtags

    @staticmethod
    def get_hashtag_names_for_entity(entity_ids, entity_hashtag_table) -> str:
        # Convert a single entity ID to a list
        if isinstance(entity_ids, int):
            entity_ids = [entity_ids]

        # Placeholder for SQL query
        placeholders = ','.join('?' for _ in entity_ids)

        query = f"""
            SELECT h.hashtag_name FROM hashtags h
            JOIN {entity_hashtag_table} eh ON h.hashtag_id = eh.hashtag_id
            WHERE eh.entity_id IN ({placeholders})
        """
        result = DatabaseHelper.safe_execute_query(query, entity_ids)

        if result is None:
            return ''

        # Convert the result to a string
        result = [hashtag[0] for hashtag in result]
        hashtags = [hashtag[0] for hashtag in result]

        return ', '.join(hashtags)

    @staticmethod
    def get_categories_for_entity(entity_id, entity_hashtag_table):
        query = f"""
            SELECT hc.category_name FROM hashtag_categories hc
            JOIN hashtags h ON hc.category_id = h.category_id
            JOIN {entity_hashtag_table} eh ON h.hashtag_id = eh.hashtag_id
            WHERE eh.entity_id = ?
        """
        return [category[0] for category in DatabaseHelper.safe_execute_query(query, (entity_id,))]

    @staticmethod
    def add_hashtag_to_entity(entity_id, hashtag_id, entity_hashtag_table):
        """
        Adds a hashtag to an entity (e.g., post or chat) in the specified entity-hashtag linking table.

        Args:
            entity_id (int): The ID of the entity (e.g., post_id, chat_id).
            hashtag_id (int,str): The ID or name of the hashtag to be linked.
            entity_hashtag_table (str): The name of the table that links entities with hashtags.
        """
        ensure_hashtag_id = HashtagManager.get_hashtag_id(hashtag_id)

        query = f"""
            INSERT OR IGNORE INTO {entity_hashtag_table} (entity_id, hashtag_id)
            VALUES (?, ?)
        """
        DatabaseHelper.safe_execute_query(query, (entity_id, ensure_hashtag_id))


    @staticmethod
    def remove_hashtag_from_entity(entity_id, hashtag_id, entity_hashtag_table):
        ensure_hashtag_id = HashtagManager.get_hashtag_id(hashtag_id)

        query = f"""
            DELETE FROM {entity_hashtag_table} WHERE entity_id = ? AND hashtag_id = ?
        """
        DatabaseHelper.safe_execute_query(query, (entity_id, ensure_hashtag_id))

    @staticmethod
    def remove_all_hashtag_by_chat_id(chat_id):
        query = f"""
            DELETE FROM chats_hashtags WHERE entity_id = ?
        """
        DatabaseHelper.safe_execute_query(query, (chat_id, ))

    @staticmethod
    def extract_hashtags(text):
        # hashtag search
        hashtag_regex = r"#\w+"
        return re.findall(hashtag_regex, text)

    @staticmethod
    def get_hashtags_names_by_id(hashtags):
        query = "SELECT hashtag_name FROM hashtags WHERE hashtag_id IN ({})".format(",".join("?" * len(hashtags)))
        result = DatabaseHelper.safe_execute_query(query, hashtags)
        return [row[0] for row in result]

    @staticmethod
    def get_chat_hashtags(chat_id):
        """
        Retrieves hashtags associated with a chat.

        Args:
            chat_id (int): The ID of the chat.

        Returns:
            list: A list of hashtags.
        """
        query = "SELECT hashtag_id FROM chats_hashtags WHERE entity_id = ?"
        return [row[0] for row in DatabaseHelper.safe_execute_query(query, (chat_id,))]

    @staticmethod
    async def get_post_hashtags(post_id):
        """
        Retrieves hashtags associated with a post.

        Args:
            post_id (int): The ID of the post.

        Returns:
            list: A list of hashtag names associated with the post.
        """
        query = """
            SELECT h.hashtag_name 
            FROM hashtags h
            JOIN posts_hashtags ph ON h.hashtag_id = ph.hashtag_id
            WHERE ph.entity_id = ?
        """
        return [row[0] for row in DatabaseHelper.safe_execute_query(query, (post_id,))]

    def get_chat_hashtags_ids(chat_id):
        """
        Retrieves hashtags associated with a chat.

        Args:
            chat_id (int): The ID of the chat.

        Returns:
            list: A list of hashtags.
        """
        query = "SELECT hashtag_id FROM chats_hashtags WHERE entity_id = ?"
        return [row[0] for row in DatabaseHelper.safe_execute_query(query, (chat_id,))]

    @staticmethod
    def get_chat_blacklist_hashtags(chat_id):
        """
        Retrieves blacklist hashtags for a chat.

        Args:
            chat_id (int): The ID of the chat.

        Returns:
            list: A list of hashtags in the chat's blacklist.
        """
        query = "SELECT hashtag_name FROM chats_blacklist_hashtags WHERE entity_id = ?"
        return [row[0] for row in DatabaseHelper.safe_execute_query(query, (chat_id,))]

    @staticmethod
    def get_chat_blacklist_hashtags_ids(chat_id):
        """
        Retrieves blacklist hashtags for a chat.

        Args:
            chat_id (int): The ID of the chat.

        Returns:
            list: A list of hashtags in the chat's blacklist.
        """
        query = "SELECT hashtag_id FROM chats_blacklist_hashtags WHERE entity_id = ?"
        return [row[0] for row in DatabaseHelper.safe_execute_query(query, (chat_id,))]

    @staticmethod
    def has_hashtag(chat_id, hashtag_identifier, table_name="chats_hashtags"):
        """
        Checks if a chat has a specific hashtag by its name or ID.

        Args:
            chat_id (int): The ID of the chat.
            hashtag_identifier (str or int): The name or ID of the hashtag.

        Returns:
            bool: True if the chat has the hashtag, False otherwise.
        """
        ensure_hashtag_id = HashtagManager.get_hashtag_id(hashtag_identifier)

        query = f"""
            SELECT 1 FROM {table_name}
            WHERE entity_id = ? AND hashtag_id = ?
        """

        result = DatabaseHelper.safe_execute_query(query, (chat_id, ensure_hashtag_id))
        return bool(result)


async def my_func():
    #HashtagManager.add_hashtag_to_entity(466001259,269,'chats_hashtags')

    #HashtagManager.add_hashtag_to_entity(466001259,5,'chats_hashtags')

    #HashtagManager.add_hashtag_to_entity(466001259,7,'chats_hashtags')

    #my_hashtags = await HashtagManager.get_hashtag_names_for_entity(466001259, 'chats_hashtags')

    #result = HashtagManager.get_hashtag_ids_for_entity(466001259, 'chats_hashtags')
    #print(result)

    #hashtag_list = await HashtagManager.get_post_hashtags_list(10)
    #print(my_hashtags)
    result = HashtagManager.get_hashtag_id_by_category_and_name('Music', '#Blues')
    print(result)
    HashtagManager.remove_all_hashtag_by_chat_id(487826065)
    print('Deleted')

if __name__ == "__main__":
    asyncio.run(my_func())

    #result_by_name = HashtagManager.has_hashtag(466001259, '#Socialism')
    #result_by_id = HashtagManager.has_hashtag(466001259, 5)
    #print(result_by_name, result_by_id)

    #post_ids = HashtagManager.get_relevant_posts_for_hashtag('#Socialism', 5)
    #print(post_ids)

    #hashtag_names = HashtagManager.get_hashtags_names_by_id([1, 2, 3])
    #print(hashtag_names)