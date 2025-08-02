# D:\Facebook_Posts_generation\ml_predictor.py

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
import joblib # For saving/loading models
import os
import sys
from datetime import datetime # Import datetime for date parsing
import database_manager # To fetch historical data

# --- Debugging setup ---
DEBUG_ML_MODE = True

def debug_ml_print(message):
    if DEBUG_ML_MODE:
        print(f"[DEBUG - ML]: {message}")

MODEL_FILENAME = 'post_engagement_model.pkl'
PREPROCESSOR_FILENAME = 'preprocessor.pkl' # To save the ColumnTransformer, though often integrated into the Pipeline

# --- Helper function for common phrase extraction (RE-ADDED) ---
def get_common_phrases(text_list, top_n=5, ngram_range=(1, 3), stop_words='english'):
    """
    Extracts common phrases (n-grams) from a list of text documents using TF-IDF.
    """
    if not text_list:
        return []
    # Ensure all text items are strings before vectorizing
    text_list = [str(text) for text in text_list if pd.notna(text)] # Handle NaNs explicitly
    if not text_list: # If all were NaN, return empty
        return []

    vectorizer = TfidfVectorizer(ngram_range=ngram_range, stop_words=stop_words, max_features=100)
    try:
        tfidf_matrix = vectorizer.fit_transform(text_list)
        feature_names = vectorizer.get_feature_names_out()
        sums = tfidf_matrix.sum(axis=0)
        ranked_features = []
        for col, term in enumerate(feature_names):
            ranked_features.append((term, sums[0,col]))
        ranked_features = sorted(ranked_features, key=lambda x: x[1], reverse=True)
        return ranked_features[:top_n]
    except ValueError as e:
        debug_ml_print(f"WARNING: ValueError in get_common_phrases: {e}. Returning empty list.")
        return []
    except Exception as e:
        debug_ml_print(f"ERROR: Unexpected error in get_common_phrases: {e}. Returning empty list.")
        return []


def train_model():
    """
    Fetches data from the database, trains an ML model, and saves it.
    """
    debug_ml_print("Starting model training process...")
    df = database_manager.get_all_posts_for_ml()

    if df.empty:
        debug_ml_print("ERROR: No historical data available for ML training. Skipping training.")
        return False, "No historical data to train on. Generate and schedule some posts first."
    
    # Create a combined 'content' column from content_en or content_ar
    # This 'content' will now implicitly contain the user feedback instructions
    # as they are incorporated into text_gen_prompt_en/ar by gui_api_settings_tab.py
    df['content'] = df.apply(lambda row: row['content_en'] if row['language'] == 'English' or (row['language'] == 'Both' and pd.notna(row['content_en'])) else row['content_ar'], axis=1)
    df = df.dropna(subset=['content']) # Drop rows where content is still empty/None after this.

    if df.empty:
        debug_ml_print("ERROR: No valid content after language selection for ML training. Skipping training.")
        return False, "No valid content in fetched posts for ML training."

    if len(df) < 5:
        debug_ml_print(f"WARNING: Insufficient data ({len(df)} rows) for robust ML training. Consider generating more posts.")

    debug_ml_print(f"Fetched {len(df)} rows for ML training.")
    
    # --- Robust Feature Preparation ---
    # Define feature lists
    categorical_features_cols = ['topic', 'language', 'text_gen_provider', 'text_gen_model']
    numerical_features_cols = ['gemini_temperature']

    # 1. Handle NaNs and ensure correct types for all features
    # Fill NaN for 'content' to ensure it's a string
    df['content'] = df['content'].fillna('').astype(str)
    # Fill NaN for text prompt columns with empty string
    df['text_gen_prompt_en'] = df['text_gen_prompt_en'].fillna('').astype(str)
    df['text_gen_prompt_ar'] = df['text_gen_prompt_ar'].fillna('').astype(str)

    # Create a NEW combined text column that TfidfVectorizer will process
    # This ensures TfidfVectorizer always receives a single, concatenated string per document (row)
    df['combined_text_features'] = df['content'] + " " + df['text_gen_prompt_en'] + " " + df['text_gen_prompt_ar']
    df['combined_text_features'] = df['combined_text_features'].astype(str) # Ensure it's string type for TF-IDF

    # Now, the 'text_features' for the ColumnTransformer will be just this one combined column
    text_features_cols_for_transformer = ['combined_text_features']


    for col in categorical_features_cols:
        df[col] = df[col].fillna('missing').astype(str) # Fill NaN categorical with 'missing', ensure string type

    for col in numerical_features_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce') # Ensure numeric, coerce errors to NaN
        df[col] = df[col].fillna(df[col].median() if not df[col].isnull().all() else 0.0) # Fill NaN numerical with median, or 0.0 if all are NaN


    # 2. Re-check for NaNs in target before final split
    df = df.dropna(subset=['engagement_score'])
    if df.empty:
        debug_ml_print("ERROR: No valid engagement scores after filtering for ML training. Skipping training.")
        return False, "No valid engagement scores in fetched posts for ML training."

    # Now create X and y from the cleaned DataFrame, including the new combined text feature
    X = df[text_features_cols_for_transformer + categorical_features_cols + numerical_features_cols]
    y = df['engagement_score'].astype(float) # Ensure target is float

    # Define preprocessing steps for different column types using the explicit feature lists
    text_transformer = TfidfVectorizer(max_features=1000, stop_words='english')
    categorical_transformer = OneHotEncoder(handle_unknown='ignore')
    numerical_transformer = StandardScaler()

    preprocessor = ColumnTransformer(
        transformers=[
            # Pass the name of the single text column directly as a string, NOT as a list of one string.
            # This ensures TfidfVectorizer receives a pandas Series (1D array-like) as expected.
            ('text', text_transformer, text_features_cols_for_transformer[0]),
            ('cat', categorical_transformer, categorical_features_cols),
            ('num', numerical_transformer, numerical_features_cols)
        ],
        remainder='drop'
    )

    # Create the full pipeline
    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))
    ])

    # Split data for validation (optional, but good practice)
    if len(df) > 10:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        debug_ml_print(f"Data split: Train {len(X_train)} rows, Test {len(X_test)} rows.")
    else:
        X_train, y_train = X, y
        debug_ml_print("Data not split due to small size. Training on all data.")
        X_test = pd.DataFrame()
        y_test = pd.Series()


    try:
        model_pipeline.fit(X_train, y_train)
        debug_ml_print("Model training complete.")

        if not X_test.empty and not y_test.empty:
            y_pred = model_pipeline.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            rmse = mse**0.5
            r2 = r2_score(y_test, y_pred)
            debug_ml_print(f"Model Evaluation (on test data): RMSE={rmse:.4f}, R-squared={r2:.4f}")
        else:
            debug_ml_print("Skipping model evaluation due to insufficient data for test set.")


        script_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(script_dir, MODEL_FILENAME)
        joblib.dump(model_pipeline, model_path)
        debug_ml_print(f"Model saved to: {model_path}")

        return True, "Model trained and saved successfully."
    except Exception as e:
        debug_ml_print(f"ERROR during model training or saving: {e}")
        return False, f"Error during model training: {e}"

def load_model():
    """
    Loads a pre-trained ML model pipeline.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, MODEL_FILENAME)
    
    if not os.path.exists(model_path):
        debug_ml_print(f"WARNING: Model file not found at {model_path}. Please train the model first.")
        return None
    
    try:
        model_pipeline = joblib.load(model_path)
        debug_ml_print(f"Model loaded successfully from: {model_path}")
        return model_pipeline
    except Exception as e:
        debug_ml_print(f"ERROR: Failed to load model from {model_path}: {e}")
        return None

def predict_engagement(post_features: dict):
    """
    Predicts the engagement score for a single new post.
    post_features should be a dictionary with keys matching the training features:
    'topic', 'language', 'text_gen_provider', 'text_gen_model', 'gemini_temperature', 'content',
    'text_gen_prompt_en', 'text_gen_prompt_ar'
    """
    debug_ml_print(f"Predicting engagement for post with content snippet: {post_features.get('content', '')[:30]}...")
    
    model = load_model()
    if model is None:
        debug_ml_print("ERROR: Model not loaded. Cannot make prediction.")
        return None
    
    # Ensure all expected features are present, even if empty, for the DataFrame
    # If the feature doesn't exist in post_features, provide a default empty string or 0.0
    features_for_df = {
        'topic': post_features.get('topic', ''),
        'language': post_features.get('language', ''),
        'text_gen_provider': post_features.get('text_gen_provider', ''),
        'text_gen_model': post_features.get('text_gen_model', ''),
        'gemini_temperature': post_features.get('gemini_temperature', 0.0),
        'content': post_features.get('content', ''),
        'text_gen_prompt_en': post_features.get('text_gen_prompt_en', ''),
        'text_gen_prompt_ar': post_features.get('text_gen_prompt_ar', '')
    }

    try:
        # Create the combined_text_features for the single input_df
        input_df = pd.DataFrame([features_for_df])
        input_df['combined_text_features'] = input_df['content'].fillna('') + " " + \
                                           input_df['text_gen_prompt_en'].fillna('') + " " + \
                                           input_df['text_gen_prompt_ar'].fillna('')
        input_df['combined_text_features'] = input_df['combined_text_features'].astype(str)

        # Select only the features that the model was trained on.
        # The order of columns in this DataFrame must match the order expected by the ColumnTransformer.
        # Order expected: ['combined_text_features', 'topic', 'language', 'text_gen_provider', 'text_gen_model', 'gemini_temperature']
        final_input_df = input_df[['combined_text_features', 'topic', 'language', 'text_gen_provider', 'text_gen_model', 'gemini_temperature']]

        predicted_score = model.predict(final_input_df)[0]
        debug_ml_print(f"Prediction successful. Predicted score: {predicted_score:.4f}")
        return predicted_score
    except Exception as e:
        debug_ml_print(f"ERROR during prediction: {e}")
        return None

# --- Helper function for common phrase extraction ---
def get_common_phrases(text_list, top_n=5, ngram_range=(1, 3), stop_words='english'):
    """
    Extracts common phrases (n-grams) from a list of text documents using TF-IDF.
    """
    if not text_list:
        return []
    # Ensure all text items are strings before vectorizing
    text_list = [str(text) for text in text_list if pd.notna(text)]
    if not text_list:
        return []

    vectorizer = TfidfVectorizer(ngram_range=ngram_range, stop_words=stop_words, max_features=100)
    try:
        tfidf_matrix = vectorizer.fit_transform(text_list)
        feature_names = vectorizer.get_feature_names_out()
        sums = tfidf_matrix.sum(axis=0)
        ranked_features = []
        for col, term in enumerate(feature_names):
            ranked_features.append((term, sums[0,col]))
        ranked_features = sorted(ranked_features, key=lambda x: x[1], reverse=True)
        return ranked_features[:top_n]
    except ValueError as e:
        debug_ml_print(f"WARNING: ValueError in get_common_phrases: {e}. Returning empty list.")
        return []
    except Exception as e:
        debug_ml_print(f"ERROR: Unexpected error in get_common_phrases: {e}. Returning empty list.")
        return []


# --- ML INSIGHTS FUNCTIONS (adjusted based on available columns) ---

def get_topic_performance_insights():
    """
    Analyzes historical posted data to identify high and low-performing topics.
    """
    debug_ml_print("Getting topic performance insights...")
    df = database_manager.get_all_posts_for_ml()

    if df.empty:
        debug_ml_print("No historical posted data available for topic insights.")
        return [], [], "No historical data to analyze for topic performance."

    if 'topic' not in df.columns or 'engagement_score' not in df.columns:
        debug_ml_print("Required columns 'topic' or 'engagement_score' not found in data for topic insights.")
        return [], [], "Missing 'topic' or 'engagement_score' data in historical posts."

    topic_performance = df.groupby('topic')['engagement_score'].mean().reset_index()
    topic_performance = topic_performance.sort_values(by='engagement_score', ascending=False)
    sorted_topics = [(row['topic'], row['engagement_score']) for index, row in topic_performance.iterrows()]

    if not sorted_topics:
        debug_ml_print("No topics found with engagement scores.")
        return [], [], "No topics with recorded engagement scores to analyze."

    num_suggestions = min(3, len(sorted_topics) // 2 or 1)
    high_performing_topics = sorted_topics[:num_suggestions]
    low_performing_topics = sorted_topics[-num_suggestions:][::-1]

    debug_ml_print(f"High performing topics: {high_performing_topics}")
    debug_ml_print(f"Low performing topics: {low_performing_topics}")

    return high_performing_topics, low_performing_topics, "Topic performance insights generated."


def get_text_prompt_performance_insights(min_posts_per_category=2):
    """
    Analyzes historical posted data to identify common elements in high-performing
    and low-performing text generation prompts (raw prompts sent to LLM).
    """
    debug_ml_print("Getting text prompt performance insights...")
    df = database_manager.get_all_posts_for_ml()

    if df.empty:
        debug_ml_print("No historical posted data available for text prompt insights.")
        return [], [], "No historical data to analyze for text prompt performance."

    required_cols = ['text_gen_prompt_en', 'text_gen_prompt_ar', 'engagement_score', 'language']
    if not all(col in df.columns for col in required_cols):
        debug_ml_print(f"Missing one or more required columns for text prompt insights: {required_cols}")
        return [], [], "Missing text prompt or engagement score data in historical posts."

    df_filtered = df.dropna(subset=['engagement_score'])
    df_filtered = df_filtered[
        ((df_filtered['language'] == 'English') & (df_filtered['text_gen_prompt_en'].notna())) |
        ((df_filtered['language'] == 'Arabic') & (df_filtered['text_gen_prompt_ar'].notna())) |
        ((df_filtered['language'] == 'Both') & (df_filtered['text_gen_prompt_en'].notna()))
    ]

    if df_filtered.empty:
        debug_ml_print("No valid posts with both prompts and engagement scores after filtering.")
        return [], [], "No valid text prompts with engagement scores to analyze."

    if len(df_filtered) < 4:
        debug_ml_print(f"Not enough data ({len(df_filtered)} posts) for meaningful high/low engagement prompt analysis.")
        return [], [], "Insufficient data for detailed prompt analysis. Need more posts."

    low_threshold = df_filtered['engagement_score'].quantile(0.25)
    high_threshold = df_filtered['engagement_score'].quantile(0.75)

    high_engagement_prompts_en = df_filtered[(df_filtered['language'].isin(['English', 'Both'])) & (df_filtered['engagement_score'] >= high_threshold)]['text_gen_prompt_en'].dropna().tolist()
    low_engagement_prompts_en = df_filtered[(df_filtered['language'].isin(['English', 'Both'])) & (df_filtered['engagement_score'] <= low_threshold)]['text_gen_prompt_en'].dropna().tolist()

    high_engagement_prompts_ar = df_filtered[(df_filtered['language'].isin(['Arabic', 'Both'])) & (df_filtered['engagement_score'] >= high_threshold)]['text_gen_prompt_ar'].dropna().tolist()
    low_engagement_prompts_ar = df_filtered[(df_filtered['language'].isin(['Arabic', 'Both'])) & (df_filtered['engagement_score'] <= low_threshold)]['text_gen_prompt_ar'].dropna().tolist()

    high_phrases = []
    low_phrases = []
    status_message = "Text prompt insights generated."

    arabic_stop_words = ["من", "في", "على", "إلى", "عن", "مع", "و", "أو", "لا", "ب", "ك", "ل", "هذا", "هذه", "الذي", "التي"]
    if len(high_engagement_prompts_en) >= min_posts_per_category:
        high_phrases_en = get_common_phrases(high_engagement_prompts_en, stop_words='english')
        high_phrases.extend([(f"[EN] {phrase}", score) for phrase, score in high_phrases_en])

    if len(low_engagement_prompts_en) >= min_posts_per_category:
        low_phrases_en = get_common_phrases(low_engagement_prompts_en, stop_words='english')
        low_phrases.extend([(f"[EN] {phrase}", score) for phrase, score in low_phrases_en])

    if len(high_engagement_prompts_ar) >= min_posts_per_category:
        high_phrases_ar = get_common_phrases(high_engagement_prompts_ar, stop_words=arabic_stop_words)
        high_phrases.extend([(f"[AR] {phrase}", score) for phrase, score in high_phrases_ar])

    if len(low_engagement_prompts_ar) >= min_posts_per_category:
        low_phrases_ar = get_common_phrases(low_engagement_prompts_ar, stop_words=arabic_stop_words)
        low_phrases.extend([(f"[AR] {phrase}", score) for phrase, score in low_phrases_ar])

    high_phrases = sorted(high_phrases, key=lambda x: x[1], reverse=True)
    low_phrases = sorted(low_phrases, key=lambda x: x[1], reverse=True)

    if not high_phrases and not low_phrases:
        status_message = "No meaningful prompt insights could be generated (insufficient data or no distinct patterns)."

    debug_ml_print(f"High performing prompt phrases: {high_phrases}")
    debug_ml_print(f"Low performing prompt phrases: {low_phrases}")

    return high_phrases, low_phrases, status_message


def get_image_prompt_performance_insights(min_posts_per_category=2):
    """
    Analyzes historical posted data to identify common elements in high-performing
    and low-performing image generation prompts.
    """
    debug_ml_print("Getting image prompt performance insights...")
    df = database_manager.get_all_posts_for_ml()

    if df.empty:
        debug_ml_print("No historical posted data available for image prompt insights.")
        return [], [], "No historical data to analyze for image prompt performance."

    required_cols = ['image_prompt_en', 'image_prompt_ar', 'engagement_score', 'language']
    if not all(col in df.columns for col in required_cols):
        debug_ml_print(f"Missing one or more required columns for image prompt insights: {required_cols}")
        return [], [], "Missing image prompt or engagement score data in historical posts."

    df_filtered = df.dropna(subset=['engagement_score'])
    df_filtered = df_filtered[
        ((df_filtered['language'] == 'English') & (df_filtered['image_prompt_en'].notna())) |
        ((df_filtered['language'] == 'Arabic') & (df_filtered['image_prompt_ar'].notna())) |
        ((df_filtered['language'] == 'Both') & (df_filtered['image_prompt_en'].notna()))
    ]

    if df_filtered.empty:
        debug_ml_print("No valid posts with both image prompts and engagement scores after filtering.")
        return [], [], "No valid image prompts with engagement scores to analyze."

    if len(df_filtered) < 4:
        debug_ml_print(f"Not enough data ({len(df_filtered)} posts) for meaningful high/low engagement image prompt analysis.")
        return [], [], "Insufficient data for detailed image prompt analysis. Need more posts."

    low_threshold = df_filtered['engagement_score'].quantile(0.25)
    high_threshold = df_filtered['engagement_score'].quantile(0.75)

    high_engagement_prompts_en = df_filtered[(df_filtered['language'].isin(['English', 'Both'])) & (df_filtered['engagement_score'] >= high_threshold)]['image_prompt_en'].dropna().tolist()
    low_engagement_prompts_en = df_filtered[(df_filtered['language'].isin(['English', 'Both'])) & (df_filtered['engagement_score'] <= low_threshold)]['image_prompt_en'].dropna().tolist()

    high_engagement_prompts_ar = df_filtered[(df_filtered['language'].isin(['Arabic', 'Both'])) & (df_filtered['engagement_score'] >= high_threshold)]['image_prompt_ar'].dropna().tolist()
    low_engagement_prompts_ar = df_filtered[(df_filtered['language'].isin(['Arabic', 'Both'])) & (df_filtered['engagement_score'] <= low_threshold)]['image_prompt_ar'].dropna().tolist()

    high_phrases = []
    low_phrases = []
    status_message = "Image prompt insights generated."

    arabic_stop_words = ["من", "في", "على", "إلى", "عن", "مع", "و", "أو", "لا", "ب", "ك", "ل", "هذا", "هذه", "الذي", "التي"]
    if len(high_engagement_prompts_en) >= min_posts_per_category:
        high_phrases_en = get_common_phrases(high_engagement_prompts_en, stop_words='english')
        high_phrases.extend([(f"[EN] {phrase}", score) for phrase, score in high_phrases_en])

    if len(low_engagement_prompts_en) >= min_posts_per_category:
        low_phrases_en = get_common_phrases(low_engagement_prompts_en, stop_words='english')
        low_phrases.extend([(f"[EN] {phrase}", score) for phrase, score in low_phrases_en])

    if len(high_engagement_prompts_ar) >= min_posts_per_category:
        high_phrases_ar = get_common_phrases(high_engagement_prompts_ar, stop_words=arabic_stop_words)
        high_phrases.extend([(f"[AR] {phrase}", score) for phrase, score in high_phrases_ar])

    if len(low_engagement_prompts_ar) >= min_posts_per_category:
        low_phrases_ar = get_common_phrases(low_engagement_prompts_ar, stop_words=arabic_stop_words)
        low_phrases.extend([(f"[AR] {phrase}", score) for phrase, score in low_phrases_ar])

    high_phrases = sorted(high_phrases, key=lambda x: x[1], reverse=True)
    low_phrases = sorted(low_phrases, key=lambda x: x[1], reverse=True)

    if not high_phrases and not low_phrases:
        status_message = "No meaningful image prompt insights could be generated (insufficient data or no distinct patterns)."

    debug_ml_print(f"High performing image prompt phrases: {high_phrases}")
    debug_ml_print(f"Low performing image prompt phrases: {low_phrases}")

    return high_phrases, low_phrases, status_message


def get_optimal_posting_times_insights():
    """
    Analyzes historical posted data to identify optimal posting days and hours
    based on average engagement score.
    """
    debug_ml_print("Getting optimal posting times insights...")
    df = database_manager.get_all_posts_for_ml()

    if df.empty:
        debug_ml_print("No historical posted data available for posting time insights.")
        return [], [], "No historical data to analyze for optimal posting times."

    required_cols = ['post_date', 'post_hour', 'engagement_score']
    if not all(col in df.columns for col in required_cols):
        debug_ml_print(f"Missing one or more required columns for posting time insights: {required_cols}")
        return [], [], "Missing post date/hour or engagement score data in historical posts."

    df_filtered = df.dropna(subset=['post_date', 'post_hour', 'engagement_score'])

    if df_filtered.empty:
        debug_ml_print("No valid posts with posting times and engagement scores after filtering.")
        return [], [], "No valid posting times with engagement scores to analyze."

    df_filtered['post_date_dt'] = pd.to_datetime(df_filtered['post_date'])
    df_filtered['day_of_week'] = df_filtered['post_date_dt'].dt.day_name()

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df_filtered['day_of_week'] = pd.Categorical(df_filtered['day_of_week'], categories=day_order, ordered=True)


    hour_performance = df_filtered.groupby('post_hour')['engagement_score'].mean().reset_index()
    hour_performance = hour_performance.sort_values(by='engagement_score', ascending=False)
    optimal_hours = [(f"{int(row['post_hour']):02d}:00", row['engagement_score']) for index, row in hour_performance.iterrows()]

    day_performance = df_filtered.groupby('day_of_week')['engagement_score'].mean().reset_index()
    day_performance = day_performance.sort_values(by='engagement_score', ascending=False)
    optimal_days = [(row['day_of_week'], row['engagement_score']) for index, row in day_performance.iterrows()]

    status_message = "Optimal posting time insights generated."

    debug_ml_print(f"Optimal Hours: {optimal_hours}")
    debug_ml_print(f"Optimal Days: {optimal_days}")

    return optimal_hours, optimal_days, status_message


# --- NEW INSIGHTS FUNCTIONS: get_generator_parameter_insights and get_language_preference_insights ---

def get_generator_parameter_insights(min_posts_per_category=2):
    """
    Analyzes historical posted data to identify high-performing
    text generation providers, models, and temperatures.
    """
    debug_ml_print("Getting generator parameter insights...")
    df = database_manager.get_all_posts_for_ml()

    if df.empty:
        debug_ml_print("No historical data for generator parameter insights.")
        return [], [], [], "No historical data to analyze for generator parameters."

    required_cols = ['text_gen_provider', 'text_gen_model', 'gemini_temperature', 'engagement_score']
    if not all(col in df.columns for col in required_cols):
        debug_ml_print(f"Missing one or more required columns for generator parameter insights: {required_cols}")
        return [], [], [], "Missing generator parameter data in historical posts."

    df_filtered = df.dropna(subset=['engagement_score'])
    
    status_message = "Generator parameter insights generated."

    # Analyze Providers
    provider_performance = df_filtered.groupby('text_gen_provider')['engagement_score'].mean().reset_index()
    provider_performance = provider_performance.sort_values(by='engagement_score', ascending=False)
    best_providers = [(row['text_gen_provider'], row['engagement_score']) for _, row in provider_performance.iterrows()]
    
    # Analyze Models
    model_performance = df_filtered.groupby('text_gen_model')['engagement_score'].mean().reset_index()
    model_performance = model_performance.sort_values(by='engagement_score', ascending=False)
    best_models = [(row['text_gen_model'], row['engagement_score']) for _, row in model_performance.iterrows()]

    # Analyze Temperatures
    # Convert temperature to a discrete category for grouping if it's continuous
    df_filtered['temp_bin'] = df_filtered['gemini_temperature'].round(1) # Round to 1 decimal for grouping
    temp_performance = df_filtered.groupby('temp_bin')['engagement_score'].mean().reset_index()
    temp_performance = temp_performance.sort_values(by='engagement_score', ascending=False)
    best_temperatures = [(row['temp_bin'], row['engagement_score']) for _, row in temp_performance.iterrows()]

    if not best_providers and not best_models and not best_temperatures:
        status_message = "No meaningful generator parameter insights could be generated."

    debug_ml_print(f"Best Providers: {best_providers}")
    debug_ml_print(f"Best Models: {best_models}")
    debug_ml_print(f"Best Temperatures: {best_temperatures}")

    return best_providers, best_models, best_temperatures, status_message

def get_language_preference_insights(min_posts_per_category=2):
    """
    Analyzes historical posted data to identify high-performing languages.
    """
    debug_ml_print("Getting language preference insights...")
    df = database_manager.get_all_posts_for_ml()

    if df.empty:
        debug_ml_print("No historical data for language preference insights.")
        return [], "No historical data to analyze for language preference."

    required_cols = ['language', 'engagement_score']
    if not all(col in df.columns for col in required_cols):
        debug_ml_print(f"Missing one or more required columns for language preference insights: {required_cols}")
        return [], "Missing language or engagement score data in historical posts."

    df_filtered = df.dropna(subset=['engagement_score', 'language'])
    
    status_message = "Language preference insights generated."

    lang_performance = df_filtered.groupby('language')['engagement_score'].mean().reset_index()
    lang_performance = lang_performance.sort_values(by='engagement_score', ascending=False)
    best_languages = [(row['language'], row['engagement_score']) for _, row in lang_performance.iterrows()]

    if not best_languages:
        status_message = "No meaningful language preference insights could be generated."

    debug_ml_print(f"Best Languages: {best_languages}")

    return best_languages, status_message


if __name__ == '__main__':
    # This block allows you to run ml_predictor directly to train the model
    # Example: python ml_predictor.py train
    if len(sys.argv) > 1 and sys.argv[1] == 'train':
        success, message = train_model()
        print(f"Model training result: {message}")
    elif len(sys.argv) > 1 and sys.argv[1] == 'analyze_topics':
        high, low, msg = get_topic_performance_insights()
        print(f"\n--- Topic Performance Insights ---")
        if high:
            print("High-Performing Topics (Average Engagement Score):")
            for topic, score in high:
                print(f"  - {topic}: {score:.4f}")
        else:
            print("No high-performing topics identified.")

        if low:
            print("\nLow-Performing Topics (Average Engagement Score):")
            for topic, score in low:
                print(f"  - {topic}: {score:.4f}")
        else:
            print("No low-performing topics identified.")
        print(f"Message: {msg}")
    elif len(sys.argv) > 1 and sys.argv[1] == 'analyze_text_prompts':
        high_phrases, low_phrases, msg = get_text_prompt_performance_insights()
        print(f"\n--- Text Prompt Performance ---\nMessage: {msg}")
        if high_phrases:
            print("High-Performing Prompt Phrases (TF-IDF Score):")
            for phrase, score in high_phrases:
                print(f"  - {phrase}: {score:.4f}")
        else:
            print("No high-performing prompt phrases identified.")

        if low_phrases:
            print("\nLow-Performing Prompt Phrases (TF-IDF Score):")
            for phrase, score in low_phrases:
                print(f"  - {phrase}: {score:.4f}")
        else:
            print("No low-performing prompt phrases identified.")
        print(f"Message: {msg}")
    elif len(sys.argv) > 1 and sys.argv[1] == 'analyze_image_prompts':
        high_phrases, low_phrases, msg = get_image_prompt_performance_insights()
        print(f"\n--- Image Prompt Performance ---\nMessage: {msg}")
        if high_phrases:
            print("High-Performing Image Prompt Phrases (TF-IDF Score):")
            for phrase, score in high_phrases:
                print(f"  - {phrase}: {score:.4f}")
        else:
            print("No high-performing image prompt phrases identified.")

        if low_phrases:
            print("\nLow-Performing Image Prompt Phrases (TF-IDF Score):")
            for phrase, score in low_phrases:
                print(f"  - {phrase}: {score:.4f}")
        else:
            print("No low-performing image prompt phrases identified.")
        print(f"Message: {msg}")
    elif len(sys.argv) > 1 and sys.argv[1] == 'analyze_posting_times':
        optimal_hours, optimal_days, msg = get_optimal_posting_times_insights()
        print(f"\n--- Optimal Posting Times Insights ---\nMessage: {msg}")
        if optimal_hours:
            print("Top Performing Hours (Avg Engagement Score):")
            for hour_str, score in optimal_hours:
                print(f"  - {hour_str}: {score:.4f}")
        else:
            print("No optimal hours identified.")

        if optimal_days:
            print("\nTop Performing Days (Avg Engagement Score):\n")
            for day_name, score in optimal_days:
                print(f"  - {day_name}: {score:.4f}")
        else:
            print("No optimal days identified.")
        print(f"Message: {msg}")
    elif len(sys.argv) > 1 and sys.argv[1] == 'analyze_gen_params': # CLI option for new insights
        best_providers, best_models, best_temperatures, msg = get_generator_parameter_insights()
        print(f"\n--- Generator Parameter Insights ---\nMessage: {msg}")
        if best_providers:
            print("Top Performing Providers (Avg Engagement Score):")
            for provider, score in best_providers:
                print(f"  - {provider}: {score:.4f}")
        if best_models:
            print("\nTop Performing Models (Avg Engagement Score):")
            for model_name, score in best_models:
                print(f"  - {model_name}: {score:.4f}")
        if best_temperatures:
            print("\nTop Performing Temperatures (Avg Engagement Score):")
            for temp, score in best_temperatures:
                print(f"  - Temp {temp:.1f}: {score:.4f}")
    elif len(sys.argv) > 1 and sys.argv[1] == 'analyze_languages': # CLI option for new insights
        best_languages, msg = get_language_preference_insights()
        print(f"\n--- Language Preference Insights ---\nMessage: {msg}")
        if best_languages:
            print("Top Performing Languages (Avg Engagement Score):")
            for lang, score in best_languages:
                print(f"  - {lang}: {score:.4f}")
    else:
        print("ML Predictor: Run 'python ml_predictor.py train' to train the model.")
        print("ML Predictor: Run 'python ml_predictor.py analyze_topics' to get topic insights.")
        print("ML Predictor: Run 'python ml_predictor.py analyze_text_prompts' to get text prompt insights.")
        print("ML Predictor: Run 'python ml_predictor.py analyze_image_prompts' to get image prompt insights.")
        print("ML Predictor: Run 'python ml_predictor.py analyze_posting_times' to get optimal posting times insights.")
        print("ML Predictor: Run 'python ml_predictor.py analyze_gen_params' to get generator parameter insights.")
        print("ML Predictor: Run 'python ml_predictor.py analyze_languages' to get language preference insights.")