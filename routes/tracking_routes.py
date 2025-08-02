# routes/tracking_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
import os
import json
import threading
import subprocess
import sys
from datetime import datetime, timedelta
import re # Ensure re is imported for regex checks

import database_manager
import ml_predictor
import facebook_metrics_gui_helpers # This module has fetch_combined_post_metrics
from .config_loader import FACEBOOK_PAGES # For accessing page details like access tokens

tracking_routes = Blueprint('tracking_routes', __name__)

# A simple log to capture output from background processes
tracking_output_log = []

# DEBUGGING SETUP
DEBUG_SCHEDULER_MODE = True # Needs to be defined before it's used

def debug_scheduler_print(message):
    if DEBUG_SCHEDULER_MODE:
        print(f"[DEBUG - Scheduler]: {message}")

def _log_to_tracking_output(message):
    print(f"[Web Log - Tracking]: {message}") # Also print to console for Flask debug
    tracking_output_log.append(message)
    # Keep the log from growing indefinitely
    if len(tracking_output_log) > 200:
        del tracking_output_log[0]

@tracking_routes.route('/posting_tracking', methods=['GET', 'POST'])
def posting_tracking_page():
    # Initial data fetch for GET request or after a redirect
    unposted_posts_data = database_manager.get_unposted_posts_for_scheduling()
    posted_posts_df = database_manager.get_all_posts_for_ml()
    
    # Format data for template
    unposted_posts = []
    # Get column names to zip with fetched tuples for easier dict creation
    db_cols = database_manager.get_unposted_posts_for_scheduling_columns()
    for post_tuple in unposted_posts_data:
        post_dict = dict(zip(db_cols, post_tuple))
        # Format post_hour for display
        post_dict['post_hour'] = f"{post_dict['post_hour']:02d}:00"
        unposted_posts.append(post_dict)

    posted_posts = []
    if not posted_posts_df.empty:
        for index, row in posted_posts_df.iterrows():
            # Convert row to dict for consistent access in template
            post_data = row.to_dict()
            post_data['post_hour'] = f"{post_data['post_hour']:02d}:00" # Format hour
            post_data['predicted_engagement_score'] = f"{post_data['predicted_engagement_score']:.2f}" if post_data['predicted_engagement_score'] is not None else 'N/A'
            post_data['engagement_score'] = f"{post_data['engagement_score']:.2f}" if post_data['engagement_score'] is not None else 'N/A'
            posted_posts.append(post_data)

    # Get the current Flask app instance to pass to threads
    app_for_thread = current_app._get_current_object()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'post_selected':
            selected_db_ids = request.form.getlist('selected_posts_to_post')
            if not selected_db_ids:
                flash("No posts selected to publish.", "warning")
            else:
                db_ids_to_schedule = [int(id_str) for id_str in selected_db_ids]
                posts_to_process = [database_manager.get_post_details_by_db_id(db_id) for db_id in db_ids_to_schedule]
                posts_to_process = [p for p in posts_to_process if p is not None]

                if not posts_to_process:
                    flash("No valid posts found to publish.", "danger")
                else:
                    _log_to_tracking_output(f"Attempting to publish {len(posts_to_process)} selected post(s)...")
                    tracking_output_log.clear() 
                    threading.Thread(target=_run_scheduler_for_posts_background, args=(app_for_thread, posts_to_process, True)).start()
                    flash("Publishing selected posts started in the background. Check Activity Log for progress.", "info")
            return redirect(url_for('tracking_routes.posting_tracking_page'))

        elif action == 'post_all':
            if not unposted_posts_data:
                flash("No approved unposted posts available to publish.", "info")
            else:
                _log_to_tracking_output(f"Attempting to publish ALL {len(unposted_posts_data)} approved unposted posts...")
                tracking_output_log.clear()
                db_cols_full = database_manager.get_unposted_posts_for_scheduling_columns()
                all_unposted_dicts = [dict(zip(db_cols_full, p_tuple)) for p_tuple in unposted_posts_data]
                
                threading.Thread(target=_run_scheduler_for_posts_background, args=(app_for_thread, all_unposted_dicts, False)).start()
                flash("Publishing all approved posts started in the background. Check Activity Log for progress.", "info")
            return redirect(url_for('tracking_routes.posting_tracking_page'))

        elif action == 'run_ml_predictor':
            _log_to_tracking_output("Starting ML model prediction...")
            tracking_output_log.clear()
            threading.Thread(target=_run_ml_predictor_background, args=(app_for_thread,)).start()
            flash("ML prediction started in the background. Check Activity Log for progress.", "info")
            return redirect(url_for('tracking_routes.posting_tracking_page'))

        elif action == 'fetch_metrics':
            _log_to_tracking_output("Fetching latest metrics from Facebook...")
            tracking_output_log.clear()
            threading.Thread(target=_run_fetch_metrics_background, args=(app_for_thread,)).start()
            flash("Metric fetching started in the background. Check Activity Log for progress.", "info")
            return redirect(url_for('tracking_routes.posting_tracking_page'))

    return render_template('posting_tracking.html',
                           unposted_posts=unposted_posts,
                           posted_posts=posted_posts,
                           tracking_output_log=tracking_output_log)

def _run_scheduler_for_posts_background(app, posts_data, is_selected_only):
    with app.app_context():
        debug_scheduler_print(f"Scheduler started for DB IDs: {len(posts_data)} posts. Selected only: {is_selected_only}")
        success_count = 0
        fail_count = 0
        
        script_dir = app.root_path # Use app.root_path to find scripts
        scheduler_script_path = os.path.join(script_dir, "facebook_scheduler.py")
        
        if not os.path.exists(scheduler_script_path):
            _log_to_tracking_output(f"ERROR: facebook_scheduler.py not found at {scheduler_script_path}")
            return

        try:
            db_ids_to_schedule = [str(post['id']) for post in posts_data]
            db_ids_str = ",".join(db_ids_to_schedule)
            
            output_dir_for_scheduler = app.config['OUTPUT_DIR']
            
            cmd = [
                sys.executable,
                scheduler_script_path,
                db_ids_str,
                output_dir_for_scheduler
            ]
            debug_scheduler_print(f"Executing scheduler subprocess: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                bufsize=1,
                env=os.environ.copy()
            )

            for line in iter(process.stdout.readline, ''):
                _log_to_tracking_output(line.strip())
            
            stderr_output = process.stderr.read()
            if stderr_output:
                _log_to_tracking_output("\n--- SCHEDULER ERROR OUTPUT ---")
                _log_to_tracking_output(stderr_output.strip())

            return_code = process.wait()
            _log_to_tracking_output(f"Scheduler subprocess exited with code: {return_code}")

            if return_code == 0:
                _log_to_tracking_output(f"Publishing complete. Successful: {success_count}, Failed: {fail_count}")
            else:
                _log_to_tracking_output(f"Publishing completed with errors. Successful: {success_count}, Failed: {fail_count}. Check output.")

        except FileNotFoundError:
            _log_to_tracking_output(f"ERROR: Scheduler script not found at: {scheduler_script_path}")
        except Exception as e:
            _log_to_tracking_output(f"CRITICAL ERROR in _run_scheduler_for_posts_background: {e}")

    def _run_ml_predictor_background(app):
        with app.app_context():
            try:
                current_model = ml_predictor.load_model()
                if current_model is None:
                    _log_to_tracking_output("ML model not found. Attempting to train model first...")
                    train_success, train_message = ml_predictor.train_model()
                    if not train_success:
                        _log_to_tracking_output(f"ML training failed: {train_message}. Cannot proceed with prediction.")
                        return
                    _log_to_tracking_output(f"ML model trained successfully: {train_message}. Proceeding with prediction...")
                    current_model = ml_predictor.load_model()
                    if current_model is None:
                        _log_to_tracking_output("ML model trained but failed to load for prediction. Aborting.")
                        return
                else:
                    _log_to_tracking_output("ML model loaded successfully. Starting prediction...")

                posts_for_prediction = database_manager.get_all_unposted_posts_for_review(approval_filter="All")

                if not posts_for_prediction:
                    _log_to_tracking_output("No unposted posts found for ML prediction.")
                    return

                predicted_count = 0
                for post_dict in posts_for_prediction:
                    post_id = post_dict['id']
                    content_for_ml = ""
                    if post_dict['language'] == "English":
                        content_for_ml = post_dict['content_en']
                    elif post_dict['language'] == "Arabic":
                        content_for_ml = post_dict['content_ar']
                    elif post_dict['language'] == "Both":
                        content_for_ml = post_dict['content_en'] if post_dict['content_en'] else post_dict['content_ar']

                    text_model_used = post_dict.get('text_gen_model')
                    if not text_model_used:
                         text_model_used = post_dict.get('gemini_text_model') if post_dict.get('text_gen_provider') == "Gemini" else post_dict.get('openai_text_model')


                    post_features = {
                        'topic': post_dict['topic'],
                        'language': post_dict['language'],
                        'text_gen_provider': post_dict['text_gen_provider'],
                        'text_gen_model': text_model_used,
                        'gemini_temperature': post_dict.get('gemini_temperature', 0.7),
                        'content': content_for_ml,
                        'text_gen_prompt_en': post_dict.get('text_gen_prompt_en', ''),
                        'text_gen_prompt_ar': post_dict.get('text_gen_prompt_ar', '')
                    }
                    _log_to_tracking_output(f"Predicting for Post ID {post_id} - Topic: {post_features['topic']}")

                    predicted_score = ml_predictor.predict_engagement(post_features)

                    if predicted_score is not None:
                        database_manager.update_post_predicted_engagement(post_id, predicted_score)
                        predicted_count += 1
                        _log_to_tracking_output(f"Predicted engagement for Post ID {post_id}: {predicted_score:.2f}")
                    else:
                        _log_to_tracking_output(f"Failed to predict engagement for Post ID {post_id}.")

                _log_to_tracking_output(f"ML prediction complete. {predicted_count} posts updated with predicted scores.")
            except Exception as e:
                _log_to_tracking_output(f"CRITICAL ERROR during ML prediction: {e}")
            finally:
                pass

    def _run_fetch_metrics_background(app):
        with app.app_context():
            try:
                posts_to_fetch = database_manager.get_posts_to_fetch_insights_for()
                if not posts_to_fetch:
                    _log_to_tracking_output("No posts found requiring metric updates.")
                    return

                _log_to_tracking_output(f"Fetching insights for {len(posts_to_fetch)} posts...")
                
                successful_fetches = 0
                for post_tuple in posts_to_fetch:
                    db_id, fb_post_id, content_snippet, fb_page_id, fb_access_token = post_tuple
                    
                    if fb_page_id == "YOUR_FACEBOOK_PAGE_ID" or fb_access_token == "YOUR_LONG_LIVED_PAGE_ACCESS_TOKEN":
                        _log_to_tracking_output(f"SKIPPING metrics for FB Post ID {fb_post_id} (DB ID {db_id}): Placeholder credentials. Please update page details in 'Page Details' tab.")
                        database_manager.increment_fetch_attempts(db_id)
                        continue

                    if not re.match(r'^\d+_?\d+$', str(fb_post_id)):
                        _log_to_tracking_output(f"WARNING: Invalid Facebook Post ID format for DB ID {db_id}: '{fb_post_id}'. Skipping insights fetch.")
                        database_manager.increment_fetch_attempts(db_id)
                        continue

                    _log_to_tracking_output(f"Processing DB ID {db_id}, FB Post ID: {fb_post_id}...")
                    
                    try:
                        combined_metrics = facebook_metrics_gui_helpers.fetch_combined_post_metrics(fb_post_id, fb_access_token)
                        
                        if combined_metrics:
                            if database_manager.update_post_metrics(fb_post_id, combined_metrics):
                                successful_fetches += 1
                                _log_to_tracking_output(
                                    f"Updated metrics for {fb_post_id}. Reach: {combined_metrics['reach']}, Likes: {combined_metrics['likes']}, Comments: {combined_metrics['comments']}, Shares: {combined_metrics['shares']}, Engagement: {combined_metrics['engagement_score']:.2f}")
                            else:
                                _log_to_tracking_output(f"Failed to update DB for {fb_post_id} after fetch.")
                        else:
                            _log_to_tracking_output(f"No metrics returned for {fb_post_id}. Helper function likely logged error.")
                            database_manager.increment_fetch_attempts(db_id)
                    except Exception as e:
                        _log_to_tracking_output(f"ERROR: Exception fetching metrics for {fb_post_id}: {e}")
                        database_manager.increment_fetch_attempts(db_id)
                    
                    time.sleep(0.5)

                _log_to_tracking_output(f"Metric fetching complete. Successfully updated {successful_fetches} posts.")
            except Exception as e:
                _log_to_tracking_output(f"CRITICAL ERROR in fetch metrics thread: {e}")
            finally:
                pass