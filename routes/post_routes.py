# routes/post_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
import os
import json
import threading
import sys
import subprocess
from datetime import datetime, timedelta
import shutil # For copying images
import re # Added for post_review_page regex check


# Import necessary modules
import database_manager
import text_generator
import image_generator
import ml_predictor
from .config_loader import FACEBOOK_PAGES, ConfigLoader # For accessing pages config and saving

post_routes = Blueprint('post_routes', __name__)

# A simple log to capture output from background processes (similar to GUI's output_text)
generation_output_log = []

def _log_to_output(message):
    print(f"[Web Log - Generator]: {message}") # Also print to console for Flask debug
    generation_output_log.append(message)
    # Keep the log from growing indefinitely
    if len(generation_output_log) > 200:
        del generation_output_log[0]

# --- Route for the "Generate Posts" page ---
@post_routes.route('/generate-posts', methods=['GET', 'POST'])
def generate_posts_page():
    page_names = [page["page_name"] for page in FACEBOOK_PAGES]
    
    # Get initial values from app config
    initial_config = {
        'OUTPUT_DIR': current_app.config.get('OUTPUT_DIR', 'Generated_Posts_Output'),
        'DEFAULT_TEXT_GEN_PROVIDER': current_app.config.get('DEFAULT_TEXT_GEN_PROVIDER', "Gemini"),
        'DEFAULT_GEMINI_MODEL': current_app.config.get('DEFAULT_GEMINI_MODEL', "gemini-1.5-flash"),
        'DEFAULT_OPENAI_TEXT_MODEL': current_app.config.get('DEFAULT_OPENAI_TEXT_MODEL', "gpt-3.5-turbo"),
        'DEFAULT_OPENAI_IMAGE_MODEL': current_app.config.get('DEFAULT_OPENAI_IMAGE_MODEL', "dall-e-3"),
        'DEFAULT_IMAGE_GEN_PROVIDER': current_app.config.get('DEFAULT_IMAGE_GEN_PROVIDER', "OpenAI (DALL-E)"),
        'DEFAULT_NUM_POSTS': int(current_app.config.get('DEFAULT_NUM_POSTS', 84)),
        'DEFAULT_GEMINI_TEMPERATURE': float(current_app.config.get('DEFAULT_GEMINI_TEMPERATURE', 0.7)),
        'DEFAULT_START_DATE': current_app.config.get('DEFAULT_START_DATE', datetime.now().strftime("%Y-%m-%d"))
    }

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'generate_posts':
            selected_page_name = request.form.get('gen_page_selection')
            num_posts = int(request.form.get('num_posts', 0))
            output_dir = request.form.get('output_dir')
            text_gen_provider = request.form.get('text_gen_provider')
            gemini_model = request.form.get('gemini_model') 
            openai_text_model = request.form.get('openai_text_model')
            openai_image_model = request.form.get('openai_image_model')
            temperature = float(request.form.get('temperature', 0.7))
            start_date_str = request.form.get('start_date')
            use_optimal_posting_time = 'use_optimal_posting_time' in request.form
            use_optimal_gen_params = 'use_optimal_gen_params' in request.form
            use_optimal_language = 'use_optimal_language' in request.form

            print(f"[DEBUG - POST Data]: request.form content: {request.form}")

            if not selected_page_name or num_posts <= 0:
                flash("Please select a page and enter a positive number of posts.", "danger")
                return redirect(url_for('post_routes.generate_posts_page'))

            selected_page_data = next((p for p in FACEBOOK_PAGES if p["page_name"] == selected_page_name), None)
            if not selected_page_data:
                flash(f"Selected page '{selected_page_name}' not found in configuration.", "danger")
                return redirect(url_for('post_routes.generate_posts_page'))

            image_gen_provider = request.form.get('image_gen_provider')

            # Update app config with current UI values before starting generation
            current_app.config['OUTPUT_DIR'] = output_dir
            current_app.config['DEFAULT_TEXT_GEN_PROVIDER'] = text_gen_provider
            current_app.config['DEFAULT_GEMINI_MODEL'] = gemini_model
            current_app.config['DEFAULT_OPENAI_TEXT_MODEL'] = openai_text_model
            current_app.config['DEFAULT_OPENAI_IMAGE_MODEL'] = openai_image_model
            current_app.config['DEFAULT_IMAGE_GEN_PROVIDER'] = image_gen_provider
            current_app.config['DEFAULT_NUM_POSTS'] = num_posts
            current_app.config['DEFAULT_GEMINI_TEMPERATURE'] = temperature
            current_app.config['DEFAULT_START_DATE'] = start_date_str
            ConfigLoader.save_app_config(current_app)

            _log_to_output("Starting bulk post generation process...")
            generation_output_log.clear()

            threading.Thread(target=_run_post_generation_background, args=(
                current_app._get_current_object(),
                num_posts, output_dir, text_gen_provider, gemini_model, openai_text_model,
                openai_image_model, temperature, start_date_str, selected_page_data,
                use_optimal_posting_time, use_optimal_gen_params, use_optimal_language,
                image_gen_provider
            )).start()
            
            flash("Post generation started in the background. Check Activity Log for progress.", "info")
            return redirect(url_for('post_routes.generate_posts_page'))
        else:
            flash(f"Unknown action: {action}", "warning")
            return redirect(url_for('post_routes.generate_posts_page'))


    return render_template('generate_posts.html', 
                           page_names=page_names,
                           initial_config=initial_config,
                           generation_output_log=generation_output_log)


# At the module level - BEFORE any background thread functions
@post_routes.route('/post_review', methods=['GET', 'POST'])
def post_review_page():
    filter_options = ["All", "Approved", "Not Approved"]
    current_filter = request.args.get('filter', 'All')
    selected_post_id = request.args.get('selected_post_id', type=int)

    posts_to_review = database_manager.get_all_unposted_posts_for_review(current_filter)

    selected_post = None
    if selected_post_id:
        selected_post = next((p for p in posts_to_review if p['id'] == selected_post_id), None)
        # Ensure post_hour is formatted for HTML <input type="number">
        if selected_post and 'post_hour' in selected_post:
            selected_post['post_hour'] = int(selected_post['post_hour'])

    app_for_thread = current_app._get_current_object()  # Get app object for thread

    if request.method == 'POST':
        action = request.form.get('action')
        post_id = request.form.get('post_id', type=int)

        # Ensure we have the latest post data from DB for actions
        if post_id:
            current_post_data = database_manager.get_post_details_by_db_id(post_id)
            if not current_post_data:
                flash(f"Post ID {post_id} not found in database.", "danger")
                return redirect(url_for('post_routes.post_review_page', filter=current_filter))
        else:
            flash("No post ID provided for action.", "danger")
            return redirect(url_for('post_routes.post_review_page', filter=current_filter))

        if action == 'update_post':
            updated_content_en = request.form.get('content_en', '').strip()
            updated_content_ar = request.form.get('content_ar', '').strip()
            updated_image_prompt_en = request.form.get('image_prompt_en', '').strip()
            updated_image_prompt_ar = request.form.get('image_prompt_ar', '').strip()
            updated_page_name = request.form.get('page_name_select')
            updated_post_date = request.form.get('post_date')
            updated_post_hour = int(request.form.get('post_hour', 0))
            is_approved = 'is_approved' in request.form

            try:
                datetime.strptime(updated_post_date, "%Y-%m-%d")
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
                return redirect(
                    url_for('post_routes.post_review_page', filter=current_filter, selected_post_id=post_id))

            if not (0 <= updated_post_hour <= 23):
                flash("Please enter a valid hour between 0 and 23.", "danger")
                return redirect(
                    url_for('post_routes.post_review_page', filter=current_filter, selected_post_id=post_id))

            selected_page_obj = next((p for p in FACEBOOK_PAGES if p["page_name"] == updated_page_name), None)

            if not selected_page_obj:
                flash(f"Selected page '{updated_page_name}' not found in configuration. Cannot update post.", "danger")
                return redirect(
                    url_for('post_routes.post_review_page', filter=current_filter, selected_post_id=post_id))

            updated_facebook_page_id = selected_page_obj.get("facebook_page_id")
            updated_facebook_access_token = selected_page_obj.get("facebook_access_token")

            if not updated_facebook_page_id or not updated_facebook_access_token:
                flash(
                    f"Facebook Page ID or Access Token is missing for page '{updated_page_name}'. Please update page details in 'Page Details' tab.",
                    "warning")

            success = database_manager.update_post_content_and_image(
                post_id,
                content_en=updated_content_en,
                content_ar=updated_content_ar,
                generated_image_filename=current_post_data.get('generated_image_filename'),
                image_prompt_en=updated_image_prompt_en,
                image_prompt_ar=updated_image_prompt_ar,
                post_date=updated_post_date,
                post_hour=updated_post_hour,
                page_name=updated_page_name,
                facebook_page_id=updated_facebook_page_id,
                facebook_access_token=updated_facebook_access_token
            )
            if success:
                database_manager.update_post_approval_status(post_id, is_approved)
                flash(f"Post ID {post_id} updated successfully.", "success")
                return redirect(
                    url_for('post_routes.post_review_page', filter=current_filter, selected_post_id=post_id))
            else:
                flash(f"Failed to update Post ID {post_id}.", "danger")
                return redirect(
                    url_for('post_routes.post_review_page', filter=current_filter, selected_post_id=post_id))

        elif action == 'delete_post':
            success, image_filename_from_db = database_manager.delete_post_by_id(post_id)
            if success:
                if image_filename_from_db:
                    image_save_dir = os.path.join(current_app.config['OUTPUT_DIR'], "generated_images")
                    image_path = os.path.join(image_save_dir, image_filename_from_db)
                    if os.path.exists(image_path):
                        try:
                            os.remove(image_path)
                            print(f"Deleted associated image file: {image_path}")
                        except Exception as e:
                            print(f"Error deleting image file {image_path}: {e}")
                            flash(f"Post deleted, but could not delete image file: {e}", "warning")

                flash(f"Post ID {post_id} deleted successfully.", "success")
                return redirect(url_for('post_routes.post_review_page', filter=current_filter))
            else:
                flash(f"Failed to delete Post ID {post_id}.", "danger")
                return redirect(
                    url_for('post_routes.post_review_page', filter=current_filter, selected_post_id=post_id))

        elif action == 'generate_image':
            image_prompt_en = request.form.get('image_prompt_en', '').strip()
            image_prompt_ar = request.form.get('image_prompt_ar', '').strip()
            image_gen_provider = request.form.get('image_gen_provider')
            image_gen_model = request.form.get('image_gen_model')

            if not (image_prompt_en or image_prompt_ar):
                flash("Please enter an image prompt (English or Arabic) before generating.", "danger")
                return redirect(
                    url_for('post_routes.post_review_page', filter=current_filter, selected_post_id=post_id))

            effective_prompt = ""
            post_language = current_post_data.get('language')
            if post_language == "English" and image_prompt_en:
                effective_prompt = image_prompt_en
            elif post_language == "Arabic" and image_prompt_ar:
                effective_prompt = image_prompt_ar
            elif post_language == "Both":
                effective_prompt = image_prompt_en if image_prompt_en else image_prompt_ar

            if not effective_prompt:
                flash("No effective image prompt (EN or AR) available for generation based on post language.", "danger")
                return redirect(
                    url_for('post_routes.post_review_page', filter=current_filter, selected_post_id=post_id))

            threading.Thread(target=_run_single_image_generation_background, args=(
                app_for_thread,
                post_id, effective_prompt, image_gen_provider, image_gen_model,
                current_app.config['OUTPUT_DIR'], image_prompt_en, image_prompt_ar,
                current_filter
            )).start()

            flash("Image generation started in background. Page will refresh upon completion.", "info")
            return redirect(url_for('post_routes.post_review_page', filter=current_filter, selected_post_id=post_id))

        elif action == 'upload_image':
            image_file = request.files.get('image_file')
            if not image_file:
                return jsonify(status='error', message='No image file provided.'), 400

            destination_dir = os.path.join(current_app.config['OUTPUT_DIR'], "generated_images")
            os.makedirs(destination_dir, exist_ok=True)

            filename = f"uploaded_image_{post_id}_{int(datetime.now().timestamp())}{os.path.splitext(image_file.filename)[1]}"
            filepath = os.path.join(destination_dir, filename)

            try:
                image_file.save(filepath)
                database_manager.update_post_content_and_image(
                    post_id,
                    None, None,
                    generated_image_filename=filename,
                    image_prompt_en=current_post_data.get('image_prompt_en', ''),
                    image_prompt_ar=current_post_data.get('image_prompt_ar', '')
                )
                return jsonify(status='success',
                               message=f"Image '{filename}' uploaded successfully for Post ID {post_id}.")
            except Exception as e:
                print(f"Error uploading image for Post ID {post_id}: {e}")
                return jsonify(status='error', message=f"Failed to upload image: {e}"), 500

        elif action == 'clear_image':
            image_filename_from_db = current_post_data.get('generated_image_filename')
            if image_filename_from_db:
                image_path = os.path.join(current_app.config['OUTPUT_DIR'], "generated_images", image_filename_from_db)
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                        print(f"Deleted associated image file: {image_path}")
                    except Exception as e:
                        print(f"Error deleting image file {image_path}: {e}")
                        flash(f"Post deleted, but could not delete image file: {e}", "warning")

                database_manager.update_post_content_and_image(
                    post_id,
                    None, None,
                    generated_image_filename=None,
                    image_prompt_en=None,
                    image_prompt_ar=None
                )
                flash(f"Image for Post ID {post_id} cleared.", "success")
            else:
                flash("No image to clear for selected post.", "info")

            return redirect(url_for('post_routes.post_review_page', filter=current_filter, selected_post_id=post_id))
        else:
            flash(f"Unknown action: {action}", "danger")
            return redirect(url_for('post_routes.post_review_page', filter=current_filter, selected_post_id=post_id))

    page_names = [page["page_name"] for page in FACEBOOK_PAGES]

    image_gen_settings = {
        'default_image_gen_provider': current_app.config.get('DEFAULT_IMAGE_GEN_PROVIDER'),
        'default_openai_image_model': current_app.config.get('DEFAULT_OPENAI_IMAGE_MODEL')
    }

    return render_template('post_review.html',
                           filter_options=filter_options,
                           current_filter=current_filter,
                           posts=posts_to_review,
                           selected_post=selected_post,
                           page_names=page_names,
                           image_gen_settings=image_gen_settings)

def _run_post_generation_background(app, num_posts, output_dir, text_gen_provider, gemini_model, openai_text_model,
                                    openai_image_model, temperature, start_date_str, selected_page_data,
                                    use_optimal_posting_time, use_optimal_gen_params, use_optimal_language,
                                    image_gen_provider):
    
    with app.app_context(): 
        script_path = os.path.join(app.root_path, "facebook_posts_generator.py") 
        
        temp_config_dir = os.path.join(app.root_path, "config") 
        os.makedirs(temp_config_dir, exist_ok=True)
        temp_page_data_path = os.path.join(temp_config_dir, f"temp_page_data_{selected_page_data['facebook_page_id']}.json")
        try:
            with open(temp_page_data_path, 'w', encoding='utf-8') as f:
                json.dump(selected_page_data, f, indent=4, ensure_ascii=False)
            _log_to_output(f"Temporary page data saved to: {temp_page_data_path}")
        except Exception as e:
            _log_to_output(f"ERROR: Could not save temporary page data for generator: {e}")
            return

        initial_schedule_datetime = datetime.strptime(start_date_str, "%Y-%m-%d").replace(hour=10)
        language_choice_for_generation = "Both" 
        current_text_gen_provider = text_gen_provider
        current_text_gen_model_final = gemini_model if text_gen_provider == "Gemini" else openai_text_model
        current_gemini_temperature = temperature

        if use_optimal_posting_time:
            optimal_hours, optimal_days, msg = ml_predictor.get_optimal_posting_times_insights()
            if optimal_hours and optimal_days:
                best_hour_str = optimal_hours[0][0]
                best_hour = int(best_hour_str.split(':')[0])
                best_day_name = optimal_days[0][0]

                day_names_map = {
                    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
                    "Friday": 4, "Saturday": 5, "Sunday": 6
                }
                
                today = datetime.now()
                current_weekday_num = datetime.now().weekday()
                target_weekday_num = day_names_map.get(best_day_name, current_weekday_num)

                days_diff = (target_weekday_num - current_weekday_num + 7) % 7
                
                if days_diff == 0 and best_hour <= today.hour:
                    days_diff = 7
                
                target_date = today.date() + timedelta(days=days_diff)
                
                initial_schedule_datetime = datetime(target_date.year, target_date.month, target_date.day, best_hour)
                _log_to_output(f"  Using optimal starting time: {initial_schedule_datetime.strftime('%Y-%m-%d %H:%M')}\n")
            else:
                _log_to_output(f"  Could not determine optimal posting time: {msg}. Falling back to default start date/time.\n")
        
        if use_optimal_gen_params:
            best_providers, best_models, best_temperatures, msg = ml_predictor.get_generator_parameter_insights()
            if best_providers:
                current_text_gen_provider = best_providers[0][0]
                _log_to_output(f"  Applying optimal provider: {current_text_gen_provider}\n")
            if best_models:
                found_best_model_for_provider = False
                for model_name_opt, _score in best_models:
                    if (current_text_gen_provider == "Gemini" and model_name_opt in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]) or \
                       (current_text_gen_provider == "OpenAI" and model_name_opt in ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]) or \
                       (current_text_gen_provider == "DeepSeek" and model_name_opt in ["deepseek-coder", "deepseek-r1"]) or \
                       (current_text_gen_provider == "Mistral" and model_name_opt in ["mistral", "mistral-openorca"]):
                            current_text_gen_model_final = model_name_opt
                            _log_to_output(f"  Applying optimal model: {current_text_gen_model_final}\n")
                            found_best_model_for_provider = True
                            break
                    if not found_best_model_for_provider:
                        _log_to_output("  No optimal model found that matches selected (or optimal) provider's available models.\n")

            if best_temperatures and current_text_gen_provider == "Gemini":
                current_gemini_temperature = best_temperatures[0][0]
                _log_to_output(f"  Applying optimal temperature: {current_gemini_temperature:.1f}\n")

        if use_optimal_language:
            best_languages, msg = ml_predictor.get_language_preference_insights()
            if best_languages:
                language_choice_for_generation = best_languages[0][0]
                _log_to_output(f"  Applying optimal language: {language_choice_for_generation}\n")


        # Prepare arguments for the subprocess call
        args = [
            sys.executable, script_path,
            "--action", "generate",
            "--num_posts", str(num_posts),
            "--output_dir", output_dir,
            "--text_gen_provider", current_text_gen_provider,
            "--gemini_text_model", current_text_gen_model_final,
            "--openai_text_model", current_text_gen_model_final,
            "--openai_image_model", openai_image_model,
            "--temperature", str(current_gemini_temperature),
            "--start_date", initial_schedule_datetime.strftime("%Y-%m-%d"),
            "--start_time", initial_schedule_datetime.strftime("%H:%M"),
            "--posts_per_day", "1",
            "--interval_hours", "24.0",
            "--post_language", language_choice_for_generation,
            "--page_data_path", temp_page_data_path,
            "--image_gen_provider", image_gen_provider
        ]

        # DEBUG: Print the exact command list being executed
        _log_to_output(f"[DEBUG - Subprocess Command]: {' '.join(args)}")
        # END DEBUG

        try:
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                bufsize=1, # Line-buffered output
                env=os.environ.copy() # Pass a copy of the current environment
            )

            # Read stdout line by line
            for line in iter(process.stdout.readline, ''):
                _log_to_output(line.strip())
            
            # Read any remaining stderr output
            stderr_output = process.stderr.read()
            if stderr_output:
                _log_to_output("\n--- GENERATOR ERROR OUTPUT ---")
                _log_to_output(stderr_output.strip())

            return_code = process.wait()
            _log_to_output(f"Generator subprocess exited with code: {return_code}")

            if return_code == 0:
                _log_to_output(f"Successfully generated {num_posts} posts.")
            else:
                _log_to_output(f"Post generation failed. Exit code: {return_code}. Check Activity Log.")

        except FileNotFoundError:
            _log_to_output(f"ERROR: Generator script not found at {script_path}")
        except Exception as e:
            _log_to_output(f"CRITICAL ERROR in _run_post_generation_background: {e}")
        finally:
            if os.path.exists(temp_page_data_path):
                os.remove(temp_page_data_path)
                _log_to_output(f"Removed temporary page data file: {temp_page_data_path}")


def _run_single_image_generation_background(app, post_id, effective_prompt, image_gen_provider, image_gen_model,
                                            output_dir, image_prompt_en, image_prompt_ar, current_filter):
    with app.app_context():
        _log_to_output(f"Starting single image generation for Post ID {post_id}...")
        try:
            generated_filename = image_generator.generate_image(
                effective_prompt,
                output_dir=output_dir,
                provider=image_gen_provider,
                model=image_gen_model
            )

            if generated_filename:
                database_manager.update_post_content_and_image(
                    post_id,
                    None, None,
                    generated_image_filename=generated_filename,
                    image_prompt_en=image_prompt_en,
                    image_prompt_ar=image_prompt_ar
                )
                _log_to_output(f"New image generated and saved for Post ID {post_id}.")
            else:
                _log_to_output(f"AI image generation failed for Post ID {post_id}. See server console for details.")
        except Exception as e:
            _log_to_output(f"CRITICAL ERROR in single image generation thread for Post ID {post_id}: {e}")
        finally:
            pass