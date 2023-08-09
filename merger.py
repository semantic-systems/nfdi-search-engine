from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def deduplicate_search_results(search_results):
    publications = search_results['publications']
    threshold = 0.5
    unique_articles = get_unique_similar_articles(publications, threshold)
    return unique_articles


def calculate_similarity(text_list):
    vectorizer = CountVectorizer().fit_transform(text_list)
    vectors = vectorizer.toarray()
    similarity_matrix = cosine_similarity(vectors)
    return similarity_matrix


def get_unique_similar_articles(data, threshold):
    unique_articles = []
    similarity_matrix = calculate_similarity(
        [article.name + ' '.join([author.name for author in article.author]) for article in data])

    for i in range(len(data)):
        is_unique = True
        for j in range(i + 1, len(data)):
            if similarity_matrix[i, j] >= threshold:
                is_unique = False
                break
        if is_unique:
            unique_articles.append(data[i])

    return unique_articles
