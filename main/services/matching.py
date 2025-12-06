import math

from django.utils import timezone

from main.models import MatchHistory, User

# Talk duration settings (in seconds)
MIN_TALK_MINUTES = 7
MAX_TALK_MINUTES = 15

# Half-life for time decay (in days)
# After 1 year, weight becomes 0.5; after 2 years, 0.25
HALF_LIFE_DAYS = 365


def calculate_time_decay_weight(pushed_at):
    """
    Calculate time decay weight using half-life model.
    Returns a float between 0 and 1.
    """
    if not pushed_at:
        return 0.1  # Minimum weight for repos without push date

    now = timezone.now()
    days_since_push = (now - pushed_at).days
    if days_since_push < 0:
        days_since_push = 0

    # Half-life decay: weight = 0.5 ^ (days / half_life)
    weight = 0.5 ** (days_since_push / HALF_LIFE_DAYS)
    return weight


def get_language_vector(user):
    """
    Generate a language vector for a user based on their repositories.
    Uses time decay weighting based on pushed_at date.
    Returns a dict: {language_name: weighted_score}
    """
    language_weights = {}
    for repo in user.repositories.select_related("language").all():
        if repo.language:
            lang_name = repo.language.name
            weight = calculate_time_decay_weight(repo.pushed_at)
            language_weights[lang_name] = language_weights.get(lang_name, 0) + weight
    return language_weights


def normalize_vector(vec):
    """Normalize a vector to proportions (sum to 1.0)."""
    if not vec:
        return {}
    total = sum(vec.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in vec.items()}


def calculate_euclidean_distance(vec1, vec2):
    """
    Calculate Euclidean distance between two language vectors.
    Returns a float >= 0.
    """
    all_languages = set(vec1.keys()) | set(vec2.keys())
    squared_sum = 0.0
    for lang in all_languages:
        v1 = vec1.get(lang, 0)
        v2 = vec2.get(lang, 0)
        squared_sum += (v1 - v2) ** 2
    return math.sqrt(squared_sum)


def calculate_similarity(vec1, vec2):
    """
    Calculate similarity between two language vectors.
    Combines cosine similarity (direction) with inverse Euclidean distance (magnitude).
    Returns a float between 0.0 and 1.0.
    """
    if not vec1 or not vec2:
        return 0.0

    # Get all unique languages
    all_languages = set(vec1.keys()) | set(vec2.keys())

    # Calculate dot product and magnitudes for cosine similarity
    dot_product = 0.0
    magnitude1 = 0.0
    magnitude2 = 0.0

    for lang in all_languages:
        v1 = vec1.get(lang, 0)
        v2 = vec2.get(lang, 0)
        dot_product += v1 * v2
        magnitude1 += v1 * v1
        magnitude2 += v2 * v2

    magnitude1 = math.sqrt(magnitude1)
    magnitude2 = math.sqrt(magnitude2)

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    # Cosine similarity (0 to 1)
    cosine_sim = dot_product / (magnitude1 * magnitude2)

    # Inverse Euclidean distance (0 to 1)
    euclidean_dist = calculate_euclidean_distance(vec1, vec2)
    inverse_euclidean = 1 / (1 + euclidean_dist)

    # Geometric mean of both metrics (keeps result in 0-1 range)
    similarity = math.sqrt(cosine_sim * inverse_euclidean)

    return similarity


def get_talk_duration(similarity_score):
    """
    Convert similarity score to talk duration in seconds.
    0.0 -> MIN_TALK_MINUTES minutes
    1.0 -> MAX_TALK_MINUTES minutes
    """
    minutes = MIN_TALK_MINUTES + (similarity_score * (MAX_TALK_MINUTES - MIN_TALK_MINUTES))
    return int(minutes * 60)  # Convert to seconds


def find_best_match(user):
    """
    Find the best matching partner for a user.
    Returns (partner_user, similarity_score) or (None, 0.0) if no match found.
    """
    # Get users who have been matched with today (to exclude)
    today_matched_ids = MatchHistory.objects.get_today_matched_users(user)

    # Get free users (excluding current user and already matched users)
    free_users = MatchHistory.objects.get_free_users(exclude_user=user)
    free_users = free_users.exclude(id__in=today_matched_ids)

    if not free_users.exists():
        return None, 0.0

    # Get current user's language vector
    user_vector = get_language_vector(user)

    if not user_vector:
        # User has no language data, return first available user with 0 similarity
        return free_users.first(), 0.0

    # Find the best match
    best_match = None
    best_similarity = -1.0

    for candidate in free_users:
        candidate_vector = get_language_vector(candidate)
        similarity = calculate_similarity(user_vector, candidate_vector)

        if similarity > best_similarity:
            best_similarity = similarity
            best_match = candidate

    return best_match, max(best_similarity, 0.0)


def get_matched_languages(user1, user2):
    """
    Get the common languages between two users with icon URLs.
    Returns a list of dicts: [{"name": "Python", "icon_url": "..."}]
    """
    from main.models import Language

    vec1 = get_language_vector(user1)
    vec2 = get_language_vector(user2)

    # Find common languages
    common_langs = set(vec1.keys()) & set(vec2.keys())

    result = []
    for lang_name in common_langs:
        try:
            language = Language.objects.get(name=lang_name)
            icon_url = language.icon_url
        except Language.DoesNotExist:
            icon_url = Language.get_devicon_url(lang_name)

        result.append(
            {
                "name": lang_name,
                "icon_url": icon_url,
            }
        )

    # Sort by name
    result.sort(key=lambda x: x["name"])
    return result


def create_match(user):
    """
    Create a new match for the user.
    Returns the MatchHistory object or None if no match possible.
    """
    # Check if user already has an active match
    existing_match = MatchHistory.objects.get_active_match(user)
    if existing_match:
        return existing_match

    # Find the best match
    partner, similarity_score = find_best_match(user)

    if not partner:
        return None

    # Calculate talk duration
    talk_duration = get_talk_duration(similarity_score)

    # Create match
    match = MatchHistory.objects.create(
        user1=user,
        user2=partner,
        similarity_score=similarity_score,
        talk_duration=talk_duration,
        event_date=timezone.now().date(),
    )

    return match
