# D:\Facebook_Posts_generation\facebook_posts_generator.py

import argparse
import json
import os
from datetime import datetime, timedelta
import random
import time
import sys

# Import your database manager
import database_manager

# Import your new modularized generator libraries
import text_generator
import image_generator

# Set up logging or print directly for subprocess output
def log_output(message):
    print(message) # This will be captured by subprocess.PIPE in the GUI

def calculate_schedule_times(start_date_str, start_time_str, num_posts, posts_per_day, interval_hours):
    """
    Calculates the scheduled times for posts.
    """
    start_datetime = datetime.strptime(f"{start_date_str} {start_time_str}", "%Y-%m-%d %H:%M")

    schedule = []
    current_datetime = start_datetime

    if posts_per_day <= 0:
        posts_per_day = 1
        log_output("WARNING: posts_per_day was non-positive, defaulting to 1.")

    if interval_hours <= 0:
        interval_hours = 24.0
        log_output("WARNING: interval_hours was non-positive, defaulting to 24.0.")

    if posts_per_day == 1:
        for _ in range(num_posts):
            schedule.append(current_datetime)
            current_datetime += timedelta(hours=interval_hours)
    else:
        interval_between_daily_posts = timedelta(hours=(24.0 / posts_per_day))
        for i in range(num_posts):
            post_datetime = start_datetime + (i * interval_between_daily_posts)
            schedule.append(post_datetime)
            log_output(f"DEBUG: Scheduled post {i+1} for: {post_datetime}")
    return schedule


def main():
    parser = argparse.ArgumentParser(description="Generate Facebook Posts with AI and save to database.")
    parser.add_argument("--action", type=str, required=True, help="Action to perform: 'generate', 'generate_image_only', or 'train_ml'.")
    parser.add_argument("--num_posts", type=int, default=84, help="Number of posts to generate. (Used with 'generate' action)")
    parser.add_argument("--output_dir", type=str, default="Generated_Posts_Output", help="Directory to save generated images.")
    parser.add_argument("--text_gen_provider", type=str, default="Gemini", help="Text generation AI provider (Gemini, OpenAI, or DeepSeek).")
    parser.add_argument("--gemini_text_model", type=str, default="gemini-1.5-flash", help="Gemini model to use for text generation.")
    parser.add_argument("--openai_text_model", type=str, default="gpt-3.5-turbo", help="OpenAI text model to use for text generation.")
    parser.add_argument("--openai_image_model", type=str, default="dall-e-3", help="OpenAI image model to use for image generation.")
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperature for text generation (0.0 to 1.0).")
    parser.add_argument("--start_date", type=str, default=datetime.now().strftime("%Y-%m-%d"), help="Start date for post scheduling (YYYY-MM-DD). (Used with 'generate' action)")
    parser.add_argument("--start_time", type=str, default="10:00", help="Start time for the first post (HH:MM). (Used with 'generate' action)")
    parser.add_argument("--posts_per_day", type=int, default=1, help="Number of posts to generate per day. (Used with 'generate' action)")
    parser.add_argument("--interval_hours", type=float, default=24.0, help="Interval in hours between posts if posts_per_day is 1. (Used with 'generate' action)")
    parser.add_argument("--post_language", type=str, default="Both", help="Language for posts: 'English', 'Arabic', or 'Both'. (Used with 'generate' action)")
    parser.add_argument("--page_data_path", type=str, required=False, help="Path to a temporary JSON file containing the selected Facebook page data. (Used with 'generate' action)")

    # NEW ARGUMENTS FOR SINGLE IMAGE GENERATION / REVIEW
    parser.add_argument("--image_prompt", type=str, required=False, help="Specific image prompt to use for single image generation. (Used with 'generate_image_only' action)")
    parser.add_argument("--post_id", type=int, required=False, help="ID of the post in the database to update the image for. (Used with 'generate_image_only' action)")
    parser.add_argument("--topic_name", type=str, required=False, help="The topic name associated with the post. (Optional, for logging/context)")
    parser.add_argument("--image_gen_provider", type=str, default="OpenAI (DALL-E)", help="Image generation AI provider (OpenAI (DALL-E) or Google (Imagen)).")


    args = parser.parse_args()

    if args.action == "generate":
        log_output("Starting bulk post generation process...")

        log_output(f"DEBUG_GENERATOR: Output directory specified: {args.output_dir}")

        # DEBUG: Verify API keys immediately before generation starts
        log_output(f"DEBUG_GENERATOR: Checking API Keys within facebook_posts_generator.py:")
        log_output(f"DEBUG_GENERATOR:   GEMINI_API_KEY: {'Set' if os.getenv('GEMINI_API_KEY') else 'NOT SET'}")
        log_output(f"DEBUG_GENERATOR:   OPENAI_API_KEY: {'Set' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
        # END DEBUG


        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)
            log_output(f"Created output directory: {args.output_dir}")

        if not args.page_data_path or not os.path.exists(args.page_data_path):
            log_output("ERROR: Page data path is required for generation and file not found.")
            sys.exit(1)

        try:
            # CRITICAL FIX: Load the single page data from the temporary JSON file
            # The page_data_path is expected to contain a single page dictionary,
            # not the full gui_config.json structure with a "facebook_pages" list.
            with open(args.page_data_path, 'r', encoding='utf-8') as f:
                selected_page_data = json.load(f) # Load directly into selected_page_data
            log_output(f"Loaded page data from {args.page_data_path} for page: {selected_page_data['page_name']}")
        except Exception as e:
            log_output(f"ERROR: Could not load page data from {args.page_data_path}: {e}")
            sys.exit(1)

        # Use selected_page_data directly now
        page_name = selected_page_data['page_name']
        page_id = selected_page_data.get('facebook_page_id')
        access_token = selected_page_data.get('facebook_access_token')
        page_contact_info_en = selected_page_data.get("english_contact_info", "")
        page_contact_info_ar = selected_page_data.get("arabic_contact_info", "")

        topics = selected_page_data.get("topics", [])
        if not topics:
            log_output("ERROR: No topics found for the selected page. Cannot generate posts.")
            sys.exit(1)
        
        # Get default prompts if any from page_data (not topic-specific)
        default_prompts = selected_page_data.get("prompts", {}) # Use selected_page_data

        log_output(f"Generating {args.num_posts} posts for page '{page_name}'.")
        log_output(f"Posts per day: {args.posts_per_day}, Start date: {args.start_date}, Start time: {args.start_time}")
        log_output(f"Text Gen Provider: {args.text_gen_provider}, Text Model: {args.gemini_text_model if args.text_gen_provider == 'Gemini' else args.openai_text_model}")
        log_output(f"Image Model: {args.openai_image_model}")

        scheduled_times = calculate_schedule_times(
            args.start_date, args.start_time, args.num_posts, args.posts_per_day, args.interval_hours
        )

        for i in range(args.num_posts):
            if not topics: # Safety check if topics list somehow becomes empty
                log_output("ERROR: Topics list is empty. Cannot generate more posts.")
                break

            selected_topic_obj = topics[i % len(topics)] # Cycle through topics
            topic_name = selected_topic_obj['name']

            scheduled_datetime = scheduled_times[i] if i < len(scheduled_times) else (datetime.now() + timedelta(days=i))
            post_date = scheduled_datetime.strftime("%Y-%m-%d")
            post_hour = scheduled_datetime.hour

            log_output(f"Generating post {i+1}/{args.num_posts} for topic: '{topic_name}' scheduled for {post_date} {post_hour:02d}:00")

            # Determine final text prompts
            final_text_prompt_en = selected_topic_obj.get("english_post_prompt", "")
            final_text_prompt_ar = selected_topic_obj.get("arabic_post_prompt", "")

            if not final_text_prompt_en:
                final_text_prompt_en = default_prompts.get("default_prompt_en", f"Write an engaging Facebook post about '{topic_name}' in English. Include relevant hashtags. Focus on automotive parts or maintenance.")
            if not final_text_prompt_ar:
                final_text_prompt_ar = default_prompts.get("default_prompt_ar", f"اكتب منشور فيسبوك جذابًا باللغة العربية حول '{topic_name}'. يجب أن يتضمن المنشور وسومًا (hashtags) ذات صلة ويركز على قطع غيار السيارات أو صيانتها أو حلول الأساطيل.")

            # DEBUG: Print specific prompts before text generation
            log_output(f"DEBUG_GENERATOR: Final EN Text Prompt: {final_text_prompt_en[:100]}...")
            log_output(f"DEBUG_GENERATOR: Final AR Text Prompt: {final_text_prompt_ar[:100]}...")
            # END DEBUG

            # Call the modular text_generator
            content_en, content_ar, actual_text_prompt_sent_en, actual_text_prompt_sent_ar = text_generator.generate_text(
                prompt_en=final_text_prompt_en,
                prompt_ar=final_text_prompt_ar,
                target_language=args.post_language,
                provider=args.text_gen_provider,
                model=args.gemini_text_model if args.text_gen_provider == "Gemini" else args.openai_text_model,
                temperature=args.temperature,
                contact_info_en=page_contact_info_en,
                contact_info_ar=page_contact_info_ar
            )

            # Determine final image prompts
            final_image_prompt_en = selected_topic_obj.get("english_image_prompt", "")
            final_image_prompt_ar = selected_topic_obj.get("arabic_image_prompt", "")

            if not final_image_prompt_en:
                final_image_prompt_en = default_prompts.get("default_image_prompt_en", f"A relevant image for a post about {topic_name}.")
            if not final_image_prompt_ar:
                final_image_prompt_ar = default_prompts.get("default_image_prompt_ar", f"صورة ذات صلة بمنشور حول {topic_name}.")

            # Choose image prompt based on language
            image_prompt_to_use = ""
            if args.post_language == "English" or args.post_language == "Both":
                image_prompt_to_use = final_image_prompt_en
            if args.post_language == "Arabic" and not image_prompt_to_use:
                image_prompt_to_use = final_image_prompt_ar
            if not image_prompt_to_use:
                image_prompt_to_use = "A generic automotive part or vehicle related image."

            # DEBUG: Print specific image prompts before image generation
            log_output(f"DEBUG_GENERATOR: Final Image Prompt for generation: {image_prompt_to_use[:100]}...")
            # END DEBUG

            # Call the modular image_generator
            generated_image_filename = image_generator.generate_image(
                prompt=image_prompt_to_use,
                output_dir=args.output_dir, # Pass the base output dir; image_generator handles subdirectory
                provider=args.image_gen_provider,
                model=args.openai_image_model # Assuming openai_image_model covers all image models for CLI
            )

            post_id = database_manager.save_generated_post(
                page_name=page_name,
                post_date=post_date,
                post_hour=post_hour,
                content_en=content_en,
                content_ar=content_ar,
                image_prompt_en=final_image_prompt_en,
                image_prompt_ar=final_image_prompt_ar,
                generated_image_filename=generated_image_filename,
                topic=topic_name,
                language=args.post_language,
                text_gen_provider=args.text_gen_provider,
                text_gen_model=args.gemini_text_model if args.text_gen_provider == "Gemini" else args.openai_text_model,
                gemini_temperature=args.temperature,
                facebook_page_id=page_id,
                facebook_access_token=access_token,
                is_approved=False,
                text_gen_prompt_en=actual_text_prompt_sent_en,
                text_gen_prompt_ar=actual_text_prompt_sent_ar
            )
            if post_id:
                log_output(f"Post saved to DB with ID: {post_id}")
            else:
                log_output(f"ERROR: Failed to save post for topic '{topic_name}' to database.")

            time.sleep(0.5)

        log_output("Bulk post generation process finished.")

    elif args.action == "generate_image_only":
        log_output("Starting single image generation process...")
        log_output(f"DEBUG_GENERATOR: Output directory specified: {args.output_dir}")

        if not args.image_prompt:
            log_output("ERROR: Image prompt is required for single image generation.")
            sys.exit(1)
        if args.post_id is None:
            log_output("ERROR: Post ID is required to update the database after single image generation.")
            sys.exit(1)

        generated_filename = image_generator.generate_image(
            args.image_prompt,
            output_dir=args.output_dir,
            provider=args.image_gen_provider,
            model=args.openai_image_model
        )

        if generated_filename:
            conn = database_manager.connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT content_en, content_ar, image_prompt_en, image_prompt_ar FROM posts WHERE id = ?", (args.post_id,))
            current_post_data = cursor.fetchone()
            conn.close()

            if current_post_data:
                current_content_en, current_content_ar, current_image_prompt_en, current_image_prompt_ar = current_post_data

                updated_image_prompt_en = args.image_prompt
                updated_image_prompt_ar = args.image_prompt 

                if database_manager.update_post_content_and_image(
                    args.post_id,
                    current_content_en,
                    current_content_ar,
                    generated_filename,
                    image_prompt_en=updated_image_prompt_en,
                    image_prompt_ar=updated_image_prompt_ar
                ):
                    log_output(f"SUCCESS: Database updated for post ID {args.post_id} with new image: {generated_filename}")
                else:
                    log_output(f"ERROR: Failed to update database for post ID {args.post_id}.")
                    sys.exit(1)
            else:
                log_output(f"ERROR: Post with ID {args.post_id} not found in database for image update.")
                sys.exit(1)
        else:
            log_output("ERROR: Image generation failed. Database not updated.")
            sys.exit(1)
        log_output("Single image generation process finished.")


    elif args.action == "train_ml":
        log_output("ML model training action requested. This functionality is not fully implemented in this script.")
        log_output("ML training: Placeholder execution.")
        sys.exit(0)

    else:
        log_output(f"ERROR: Unknown action: {args.action}")
        sys.exit(1)

if __name__ == "__main__":
    main()