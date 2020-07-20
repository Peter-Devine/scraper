import os
import pandas as pd
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import nltk
import json
from matplotlib import pyplot as plt
nltk.download('vader_lexicon')

# Create directory to output results to
results_path = os.path.join(".", "results")
if not os.path.exists(results_path):
    os.mkdir(results_path)

# Iterate through all posts of all pages (datasets) that have been downloaded, saving the downloaded posts to a dict
data_path = os.path.join(".", "data")
all_data = {}
# Iterate through pages
for dataset in os.listdir(data_path):
    all_data[dataset] = []
    # Iterate through posts
    dataset_data_dir = os.path.join(data_path, dataset)
    for file in os.listdir(dataset_data_dir):
        post_data_dir = os.path.join(dataset_data_dir, file)

        # Do not look at post_links
        if not os.path.isfile(post_data_dir) or "post_links" in file:
            continue

        file_path = os.path.join(data_path, dataset, file)
        with open(file_path, "rb") as f:
            data = json.load(f)

        all_data[dataset].append(data)

# We get a simple list of comments for each page
per_dataset_text = {}
for dataset_name, all_dataset_posts in all_data.items():
    per_dataset_text[dataset_name] = []
    for post in all_dataset_posts:
        for comment in post["comment_data"]:
            # We want to leave out all comments written by the page themselves
            if comment["commenter_name"] == post["page_name"]:
                continue

            per_dataset_text[dataset_name].append(comment)

            for reply in comment["replies"]:
                per_dataset_text[dataset_name].append(reply)

# We find the sentiment for each individual post
def get_sentiment_df(list_of_comments):

    list_of_comments = [x for x in list_of_comments if x["comment_text"] is not None]

    sid = SentimentIntensityAnalyzer()
    sentences = [x["comment_text"] for x in list_of_comments]
    sentiments = [sid.polarity_scores(sentence)["compound"] for sentence in sentences]

    df = pd.DataFrame(list_of_comments)
    df["sentiment"] = sentiments
    df["text"] = df.comment_text

    return df

def get_top_k_words_from_n_topics(df, k, n):
    # Make list of comments into BOW
    vectorizer = CountVectorizer()
    bow_embed = vectorizer.fit_transform(df.text.str.lower())

    # Do LDA over BOW
    lda = LatentDirichletAllocation(n_components=n, max_iter=10, learning_method='online', learning_offset=50., random_state=111)
    embeddings = lda.fit_transform(bow_embed)
    reversed_vocab = {v:k for k,v in vectorizer.vocabulary_.items()}

    topic_word_lists = []

    for i, component in enumerate(lda.components_ / lda.components_.sum(axis=1)[:, np.newaxis]):
        topic_word_list = []

        idx_of_highest_vals = component.argsort()[-k:][::-1]

        for idx in idx_of_highest_vals:
            topic_word_list.append(reversed_vocab[idx])

        topic_word_lists.append({f"Topic {i} words": topic_word_list})

    return pd.DataFrame(topic_word_lists)

dataset_dfs = {}
for dataset_name, comment_list in per_dataset_text.items():
    sent_df = get_sentiment_df(comment_list)
    # Save the sentiment of each comment
    sent_df.to_csv(os.path.join(results_path, f"{dataset_name}_full_sent_df.csv"))

    print(f"{dataset_name} average sentiment {sent_df.sentiment.mean()}")
    # We plot the sentiment as a histogram
    sent_df.sentiment.plot.hist(density=True, bins=50, alpha=0.5)

    # We save the top and bottom k comments in terms of sentiment
    top_k_comments = 20
    sent_df.sort_values("sentiment", ascending=False).iloc[:top_k_comments].to_csv(os.path.join(results_path, f"{dataset_name}_top_{top_k_comments}_comments.csv"))
    sent_df.sort_values("sentiment", ascending=True).iloc[:top_k_comments].to_csv(os.path.join(results_path, f"{dataset_name}_bottom_{top_k_comments}_comments.csv"))

    # Get the top K most common commenters
    top_k_commenters = 20
    sent_df["commenter_name"].value_counts()[:top_k_commenters].to_csv(os.path.join(results_path, f"{dataset_name}_top_{top_k_commenters}_commenters.csv"))

    # Do LDA on text list
    topic_word_df = get_top_k_words_from_n_topics(sent_df, k=5, n=10)
    topic_word_df.to_csv(os.path.join(results_path, f"{dataset_name}_characteristic_topic_words.csv"))

    dataset_dfs[dataset_name] = sent_df

# Save the plots of all pages overlaid against one another
plt.savefig(os.path.join(results_path, "sentiments.png"))

done_first_datasets = []

# Compare each pair of pages, to see the most stereotypical words when comparing them.
for dataset_name_1, sent_df_1 in dataset_dfs.items():
    done_first_datasets.append(dataset_name_1)

    for dataset_name_2, sent_df_2 in dataset_dfs.items():
        if dataset_name_2 not in done_first_datasets:
            words_1 = sent_df_1.text.apply(lambda x: nltk.word_tokenize(x.lower())).apply(pd.Series).stack().reset_index(drop=True)
            words_2 = sent_df_2.text.apply(lambda x: nltk.word_tokenize(x.lower())).apply(pd.Series).stack().reset_index(drop=True)

            vc_1 = words_1.value_counts()
            vc_2 = words_2.value_counts()

            # Find the top k words for each page
            top_k_words = 500
            vc_1 = vc_1[:top_k_words]
            vc_2 = vc_2[:top_k_words]

            # Combine the top k words from each page to get a union list of top words
            all_words = vc_1.index.append(vc_2.index).unique()

            # Get the rank of each word in each dataset (E.g. rank 1 is the most common word on a page, 2 is 2nd most common)
            indices_1 = [vc_1.index.get_loc(i) if i in vc_1.index else len(vc_1.index) for i in all_words]
            indices_2 = [vc_2.index.get_loc(i) if i in vc_2.index else len(vc_2.index) for i in all_words]

            # Find the difference in rank for each word. Large positive numbers mean that this word is used much more in dataset 1 than 2 and vice versa.
            differences = pd.Series({word: wi - gi for word, wi, gi in zip(all_words, indices_1, indices_2)}).sort_values()

            # Output these differences to disc
            differences.to_csv(os.path.join(results_path, f"{dataset_name_1}_vs_{dataset_name_2}_most_popular_{top_k_words}_words.csv"))
