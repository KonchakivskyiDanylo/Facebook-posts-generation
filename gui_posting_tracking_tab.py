# gui_posting_tracking_tab.py

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import datetime
import os
import requests
import json
import time
import subprocess
import re
import sys # ADDED: Import the sys module

import database_manager
import ml_predictor
import facebook_metrics_gui_helpers

DEBUG_GUI_MODE = True

def debug_gui_print(message):
    if DEBUG_GUI_MODE:
        print(f"[DEBUG - GUI - PostingTracking]: {message}")

class PostingTrackingTab(ttk.Frame):
    def __init__(self, parent, facebook_pages_ref, set_status_callback, update_output_text_callback, output_dir_var_ref, populate_all_unposted_post_lists_callback):
        super().__init__(parent)
        self.facebook_pages = facebook_pages_ref
        self.set_status = set_status_callback
        self.update_output_text = update_output_text_callback
        self.output_dir_var = output_dir_var_ref
        self.populate_all_unposted_post_lists_callback = populate_all_unposted_post_lists_callback

        self.unposted_posts = []
        
        self._create_widgets() 
        
        self._populate_unposted_listbox() 
        self._populate_posted_listbox()
        debug_gui_print("PostingTrackingTab widgets created and populated.")

    def _populate_unposted_listbox(self):
        debug_gui_print("_populate_unposted_listbox (PostingTrackingTab) called.")
        self.unposted_tree.delete(*self.unposted_tree.get_children())
        posts = database_manager.get_unposted_posts_for_scheduling() #
        self.unposted_posts = posts
        debug_gui_print(f"Fetched {len(self.unposted_posts)} APPROVED unposted posts for scheduling.")
        for post in self.unposted_posts:
            post_id = post[0]
            page_name = post[1]
            post_date = post[2]
            post_hour = post[3]
            topic = post[9] #

            self.unposted_tree.insert("", "end", iid=post_id, values=(post_id, page_name, post_date, f"{post_hour:02d}:00", topic))
        debug_gui_print("Unposted posts Treeview populated.")

    def _populate_posted_listbox(self):
        debug_gui_print("_populate_posted_listbox (PostingTrackingTab) called.")
        self.posted_tree.delete(*self.posted_tree.get_children())
        posted_df = database_manager.get_all_posts_for_ml() #
        if not posted_df.empty:
            for index, post in posted_df.iterrows():
                display_time = f"{post['post_hour']:02d}:00"
                self.posted_tree.insert("", "end", iid=post['id'], values=(
                    post['page_name'], post['post_date'], display_time, post['topic'],
                    post.get('actual_post_id', 'N/A'), post.get('likes', 0), post.get('comments', 0),
                    post.get('shares', 0), post.get('reach', 0), f"{post.get('engagement_score', 0.0):.2f}"
                ))
        debug_gui_print("Posted posts Treeview populated.")


    def _create_widgets(self):
        debug_gui_print("_create_widgets (PostingTrackingTab) called.")
        # Frame for unposted post list
        unposted_posts_frame = ttk.LabelFrame(self, text="Approved & Unposted Posts")
        unposted_posts_frame.pack(fill="x", padx=10, pady=(10, 0))

        self.unposted_tree = ttk.Treeview(unposted_posts_frame, columns=("id", "page", "date", "time", "topic"), show="headings", height=8)
        for col in ("id", "page", "date", "time", "topic"):
            self.unposted_tree.heading(col, text=col.capitalize())
            self.unposted_tree.column(col, anchor="w", width=100 if col in ("id", "date", "time") else 150)
        
        self.unposted_tree.pack(fill="x", padx=5, pady=5)

        unposted_button_frame = ttk.Frame(unposted_posts_frame)
        unposted_button_frame.pack(pady=5)
        self.post_selected_button = ttk.Button(unposted_button_frame, text="Post Selected", command=self._post_selected)
        self.post_selected_button.pack(side="left", padx=5)
        self.post_all_button = ttk.Button(unposted_button_frame, text="Post All", command=self._post_all)
        self.post_all_button.pack(side="left", padx=5)
        self.run_ml_predictor_button = ttk.Button(unposted_button_frame, text="Run ML Predictor (on Posted)", command=self._run_ml_predictor)
        self.run_ml_predictor_button.pack(side="left", padx=5)

        # Frame for posted post list
        posted_posts_frame = ttk.LabelFrame(self, text="Posted Posts & Metrics")
        posted_posts_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.posted_tree = ttk.Treeview(posted_posts_frame, columns=("page", "date", "time", "topic", "actual_id", "likes", "comments", "shares", "reach", "engagement"), show="headings")
        self.posted_tree.heading("page", text="Page")
        self.posted_tree.heading("date", text="Date")
        self.posted_tree.heading("time", text="Time")
        self.posted_tree.heading("topic", text="Topic")
        self.posted_tree.heading("actual_id", text="FB Post ID")
        self.posted_tree.heading("likes", text="Likes")
        self.posted_tree.heading("comments", text="Comments")
        self.posted_tree.heading("shares", text="Shares")
        self.posted_tree.heading("reach", text="Reach")
        self.posted_tree.heading("engagement", text="Engagement")

        # Adjust column widths for readability
        self.posted_tree.column("page", width=80, stretch=tk.NO)
        self.posted_tree.column("date", width=90, stretch=tk.NO)
        self.posted_tree.column("time", width=60, stretch=tk.NO)
        self.posted_tree.column("topic", width=150, stretch=tk.YES)
        self.posted_tree.column("actual_id", width=120, stretch=tk.NO)
        self.posted_tree.column("likes", width=60, stretch=tk.NO, anchor=tk.E)
        self.posted_tree.column("comments", width=70, stretch=tk.NO, anchor=tk.E)
        self.posted_tree.column("shares", width=60, stretch=tk.NO, anchor=tk.E)
        self.posted_tree.column("reach", width=70, stretch=tk.NO, anchor=tk.E)
        self.posted_tree.column("engagement", width=80, stretch=tk.NO, anchor=tk.E)

        self.posted_tree.pack(fill="both", expand=True, padx=5, pady=5)

        posted_button_frame = ttk.Frame(posted_posts_frame)
        posted_button_frame.pack(pady=5)
        self.fetch_metrics_button = ttk.Button(posted_button_frame, text="Fetch Latest Metrics (from FB)", command=self._fetch_metrics_async)
        self.fetch_metrics_button.pack(side="left", padx=5)
        ttk.Button(posted_button_frame, text="Refresh Display", command=self._populate_posted_listbox).pack(side="left", padx=5) 

        # ADDED: Local output text area for Posting & Tracking tab
        self._create_output_text_area() # Call the helper to create the log text widget
        # END ADDED

        debug_gui_print("_create_widgets (PostingTrackingTab) finished.")

    # ADDED: Local output text area creation helper
    def _create_output_text_area(self):
        output_text_frame = ttk.LabelFrame(self, text="Activity Log")
        output_text_frame.pack(padx=10, pady=5, fill="x", expand=False)
        self.local_output_text = tk.Text(output_text_frame, wrap="word", height=5, state="disabled")
        self.local_output_text.pack(fill="x", expand=True, padx=5, pady=5)
        self.local_output_text_scroll = ttk.Scrollbar(output_text_frame, command=self.local_output_text.yview)
        self.local_output_text_scroll.pack(side="right", fill="y")
        self.local_output_text.config(yscrollcommand=self.local_output_text_scroll.set)
    # END ADDED

    def _post_selected(self):
        debug_gui_print("_post_selected (PostingTrackingTab) called.")
        selected_ids = self.unposted_tree.selection()
        if not selected_ids:
            messagebox.showinfo("No Selection", "Please select a post to publish.", parent=self.master)
            debug_gui_print("No post selected for direct posting.")
            return

        posts_to_process = []
        db_cols = database_manager.get_unposted_posts_for_scheduling_columns() #
        for item_id_str in selected_ids:
            item_id = int(item_id_str)
            found_post_tuple = next((p_tuple for p_tuple in self.unposted_posts if p_tuple[0] == item_id), None)
            if found_post_tuple:
                post_dict = dict(zip(db_cols, found_post_tuple))
                posts_to_process.append(post_dict)
            else:
                debug_gui_print(f"WARNING: Post ID {item_id} not found in current unposted list. Skipping.")

        if not posts_to_process:
            messagebox.showwarning("No Valid Posts", "No valid posts found to publish from selection.", parent=self.master)
            return

        confirm_message = f"Are you sure you want to attempt to publish {len(posts_to_process)} selected post(s) to Facebook?\n\nThis will mark them as 'Posted' in the database regardless of API success (you can re-approve them if needed)."
        if not messagebox.askyesno("Confirm Publish", confirm_message, icon='question', parent=self.master):
            debug_gui_print("User cancelled selected post publishing.")
            self.set_status("Publishing cancelled.", "gray")
            return

        self.set_status(f"Attempting to publish {len(posts_to_process)} selected post(s)...", "blue")
        self._disable_ui_buttons()
        
        threading.Thread(target=self._run_scheduler_for_posts, args=(posts_to_process, True)).start()
        debug_gui_print("Thread started for selected post publishing.")


    def _post_all(self):
        debug_gui_print("_post_all (PostingTrackingTab) called.")
        if not self.unposted_posts:
            messagebox.showinfo("No Posts", "No approved unposted posts available to publish.", parent=self.master)
            debug_gui_print("No posts to publish for 'Post All'.")
            return

        confirm_message = f"Are you sure you want to attempt to publish ALL {len(self.unposted_posts)} approved unposted posts to Facebook?\n\nThis will mark them as 'Posted' in the database regardless of API success (you can re-approve them if needed)."
        if not messagebox.askyesno("Confirm Publish All", confirm_message, icon='question', parent=self.master):
            debug_gui_print("User cancelled 'Post All' publishing.")
            self.set_status("Publishing cancelled.", "gray")
            return
        
        self.set_status(f"Attempting to publish ALL {len(self.unposted_posts)} approved unposted posts...", "blue")
        self._disable_ui_buttons()

        db_cols = database_manager.get_unposted_posts_for_scheduling_columns() #
        posts_to_process = [dict(zip(db_cols, p_tuple)) for p_tuple in self.unposted_posts]

        threading.Thread(target=self._run_scheduler_for_posts, args=(posts_to_process, False)).start()
        debug_gui_print("Thread started for 'Post All' publishing.")


    def _run_scheduler_for_posts(self, posts_data, is_selected_only):
        debug_gui_print(f"_run_scheduler_for_posts thread started. Selected only: {is_selected_only}")
        success_count = 0
        fail_count = 0
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        scheduler_script_path = os.path.join(script_dir, "facebook_scheduler.py")
        
        if not os.path.exists(scheduler_script_path):
            self.master.after(0, self.set_status, f"Error: facebook_scheduler.py not found at {scheduler_script_path}", "red")
            self.master.after(0, self.update_output_text, f"ERROR: Scheduler script not found: {scheduler_script_path}\n")
            self.master.after(0, self._enable_ui_buttons)
            return

        try:
            db_ids_to_schedule = [str(post['id']) for post in posts_data]
            db_ids_str = ",".join(db_ids_to_schedule)
            
            output_dir_for_scheduler = self.output_dir_var.get()
            
            cmd = [
                sys.executable,
                scheduler_script_path,
                db_ids_str,
                output_dir_for_scheduler
            ]
            debug_gui_print(f"Executing scheduler subprocess: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                bufsize=1
            )

            while True:
                line = process.stdout.readline()
                if line == '' and process.poll() is not None:
                    break
                if line:
                    self.master.after(0, self.update_output_text, line)
                    if "Successfully scheduled" in line:
                        success_count += 1
                    elif "Failed to schedule" in line:
                        fail_count += 1

            stderr_output = process.stderr.read()
            if stderr_output:
                self.master.after(0, self.update_output_text, "\n--- SCHEDULER ERROR OUTPUT ---")
                self.master.after(0, self.update_output_text, stderr_output)
                debug_gui_print(f"Scheduler subprocess produced stderr:\n{stderr_output}")


            return_code = process.wait()
            debug_gui_print(f"Scheduler subprocess exited with code: {return_code}")

            if return_code == 0:
                self.master.after(0, self.set_status, f"Publishing complete. Successful: {success_count}, Failed: {fail_count}", "green")
            else:
                self.master.after(0, self.set_status, f"Publishing completed with errors. Successful: {success_count}, Failed: {fail_count}. Check console.", "orange")
                self.master.after(0, self.update_output_text, f"Scheduler subprocess finished with non-zero exit code: {return_code}\n")


        except FileNotFoundError:
            error_msg = f"Scheduler script not found at: {scheduler_script_path}"
            self.master.after(0, self.set_status, error_msg, "red")
            self.master.after(0, self.update_output_text, f"ERROR: {error_msg}\n")
            debug_gui_print(f"ERROR: {error_msg}")
        except Exception as e:
            error_msg = f"An unexpected error occurred running scheduler: {e}"
            self.master.after(0, self.set_status, error_msg, "red")
            self.master.after(0, self.update_output_text, f"ERROR: {error_msg}\n")
            debug_gui_print(f"CRITICAL ERROR: {error_msg}")
        finally:
            self.master.after(0, self._enable_ui_buttons)
            self.master.after(0, self._populate_unposted_listbox)
            self.master.after(0, self._populate_posted_listbox)
            self.master.after(0, self.populate_all_unposted_post_lists_callback)

        debug_gui_print("_run_scheduler_for_posts thread finished.")


    def _disable_ui_buttons(self):
        # Explicitly disable buttons.
        self.post_selected_button.config(state=tk.DISABLED)
        self.post_all_button.config(state=tk.DISABLED)
        self.run_ml_predictor_button.config(state=tk.DISABLED)
        self.fetch_metrics_button.config(state=tk.DISABLED)
        # Treeview's cannot have a 'state' option. Instead, you can unbind selection events.
        # This will prevent new selections, but existing ones will remain visual.
        self.unposted_tree.unbind("<<TreeviewSelect>>")
        self.posted_tree.unbind("<<TreeviewSelect>>")

    def _enable_ui_buttons(self):
        # Explicitly enable buttons
        self.post_selected_button.config(state=tk.NORMAL)
        self.post_all_button.config(state=tk.NORMAL)
        self.run_ml_predictor_button.config(state=tk.NORMAL)
        self.fetch_metrics_button.config(state=tk.NORMAL)
        # Re-bind Treeview selection events
        # You might have specific handlers for these; replace lambda with actual handler if so.
        self.unposted_tree.bind("<<TreeviewSelect>>", lambda e: None) # Default/dummy handler
        self.posted_tree.bind("<<TreeviewSelect>>", lambda e: None) # Default/dummy handler

    def _run_ml_predictor(self):
        debug_gui_print("_run_ml_predictor (PostingTrackingTab) called.")
        self.set_status("Starting ML model prediction...", "blue")
        self._disable_ui_buttons()

        threading.Thread(target=self._run_ml_predictor_thread).start()
        debug_gui_print("ML predictor thread started.")

    def _run_ml_predictor_thread(self):
        debug_gui_print("ML predictor thread started (internal function).")
        try:
            # First, check if the model can be loaded BEFORE attempting to train or predict
            # This helps catch missing model files early.
            current_model = ml_predictor.load_model()
            if current_model is None:
                self.master.after(0, self.set_status, "ML model not found. Attempting to train model first...", "orange")
                self.master.after(0, self.update_output_text, "ML model not found. Attempting to train...\n")
                
                # If model is not found, try to train it
                train_success, train_message = ml_predictor.train_model()
                if not train_success:
                    self.master.after(0, self.set_status, f"ML training failed: {train_message}. Cannot proceed with prediction.", "red")
                    self.master.after(0, self.update_output_text, f"ML training failed: {train_message}. Aborting prediction.\n")
                    debug_gui_print(f"ML training failed: {train_message}. Aborting prediction.")
                    return # Exit if training fails
                
                self.master.after(0, self.update_output_text, f"ML model trained successfully: {train_message}. Proceeding with prediction...\n")
                debug_gui_print(f"ML model trained. Proceeding with prediction.")
                current_model = ml_predictor.load_model() # Load the newly trained model
                if current_model is None: # Should not happen if train_model was successful and saved
                    self.master.after(0, self.set_status, "ML model trained but failed to load for prediction. Check console.", "red")
                    self.master.after(0, self.update_output_text, "ML model trained but failed to load for prediction. Aborting.\n")
                    debug_gui_print("ML model trained but failed to load for prediction. Aborting.")
                    return
            else:
                self.master.after(0, self.update_output_text, "ML model loaded successfully. Starting prediction...\n")


            posts_for_prediction = database_manager.get_all_unposted_posts_for_review(approval_filter="All") #

            if not posts_for_prediction:
                self.master.after(0, self.set_status, "No unposted posts found for ML prediction.", "blue")
                self.master.after(0, self.update_output_text, "No unposted posts to predict engagement for.\n")
                debug_gui_print("No posts for ML prediction.")
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
                debug_gui_print(f"ML: Predicting for Post ID {post_id} - Topic: {post_features['topic']}")

                predicted_score = ml_predictor.predict_engagement(post_features) #

                if predicted_score is not None:
                    database_manager.update_post_predicted_engagement(post_id, predicted_score) #
                    predicted_count += 1
                    self.master.after(0, self.update_output_text, f"Predicted engagement for Post ID {post_id}: {predicted_score:.2f}\n")
                    debug_gui_print(f"ML: Predicted engagement for Post ID {post_id}: {predicted_score:.2f}")
                else:
                    self.master.after(0, self.update_output_text, f"Failed to predict engagement for Post ID {post_id}. See console for error details.\n")
                    debug_gui_print(f"ML: Failed to predict engagement for Post ID {post_id}.")

            self.master.after(0, self.set_status, f"ML prediction complete. {predicted_count} posts updated.", "green")
            self.master.after(0, self.populate_all_unposted_post_lists_callback)
            
        except Exception as e:
            error_msg = f"An unexpected error occurred during ML prediction: {e}"
            self.master.after(0, self.set_status, error_msg, "red")
            self.master.after(0, self.update_output_text, f"ERROR: {error_msg}\n")
            debug_gui_print(f"CRITICAL ERROR in ML predictor thread: {e}")
        finally:
            self.master.after(0, self._enable_ui_buttons)
        debug_gui_print("ML predictor thread finished.")

    def _fetch_metrics_async(self):
        debug_gui_print("_fetch_metrics_async (PostingTrackingTab) called.")
        self.set_status("Fetching latest metrics from Facebook...", "blue")
        self._disable_ui_buttons()

        threading.Thread(target=self._run_fetch_metrics_thread).start()
        debug_gui_print("Fetch metrics thread started.")

    def _run_fetch_metrics_thread(self):
        debug_gui_print("Fetch metrics thread started (internal function).")
        try:
            posts_to_fetch = database_manager.get_posts_to_fetch_insights_for() #
            if not posts_to_fetch:
                self.master.after(0, self.set_status, "No posts found requiring metric updates.", "blue")
                self.master.after(0, self.update_output_text, "No posts requiring metric updates.\n")
                debug_gui_print("No posts to fetch insights for.")
                return

            self.master.after(0, self.update_output_text, f"Fetching insights for {len(posts_to_fetch)} posts...\n")
            
            successful_fetches = 0
            for post_tuple in posts_to_fetch:
                db_id, fb_post_id, content_snippet, fb_page_id, fb_access_token = post_tuple
                
                if fb_page_id == "YOUR_FACEBOOK_PAGE_ID" or fb_access_token == "YOUR_LONG_LIVED_PAGE_ACCESS_TOKEN":
                    self.master.after(0, self.update_output_text, f"SKIPPING metrics for FB Post ID {fb_post_id} (DB ID {db_id}): Placeholder credentials.\n")
                    debug_gui_print(f"Skipping metrics for FB Post ID {fb_post_id} due to placeholder credentials.")
                    database_manager.increment_fetch_attempts(db_id) #
                    continue

                # Ensure 're' is imported at the top of the file. This was the specific NameError from the log.
                if not re.match(r'^\d+_?\d+$', str(fb_post_id)):
                    self.master.after(0, self.update_output_text, f"WARNING: Invalid Facebook Post ID format for DB ID {db_id}: '{fb_post_id}'. Skipping insights fetch.\n")
                    debug_gui_print(f"WARNING: Invalid Facebook Post ID format for DB ID {db_id}: '{fb_post_id}'. Skipping insights fetch.")
                    database_manager.increment_fetch_attempts(db_id) #
                    continue

                self.master.after(0, self.update_output_text, f"Processing DB ID {db_id}, FB Post ID: {fb_post_id}...\n")
                
                try:
                    combined_metrics = facebook_metrics_gui_helpers.fetch_combined_post_metrics(fb_post_id, fb_access_token) #
                    
                    if combined_metrics:
                        if database_manager.update_post_metrics(fb_post_id, combined_metrics): #
                            successful_fetches += 1
                            self.master.after(0, self.update_output_text, 
                                f"Updated metrics for {fb_post_id}. Reach: {combined_metrics['reach']}, Likes: {combined_metrics['likes']}, Comments: {combined_metrics['comments']}, Shares: {combined_metrics['shares']}, Engagement: {combined_metrics['engagement_score']:.2f}\n")
                            debug_gui_print(f"Updated metrics for {fb_post_id}: {combined_metrics}")
                        else:
                            self.master.after(0, self.update_output_text, f"Failed to update DB for {fb_post_id} after fetch.\n")
                            debug_gui_print(f"Failed to update DB for {fb_post_id} after fetch.")
                    else:
                        self.master.after(0, self.update_output_text, f"No metrics returned for {fb_post_id}. Check console for details.\n")
                        debug_gui_print(f"No metrics returned for {fb_post_id}. Helper function likely logged error.")
                        database_manager.increment_fetch_attempts(db_id) #
                except Exception as e:
                    self.master.after(0, self.update_output_text, f"ERROR: Exception fetching metrics for {fb_post_id}: {e}\n")
                    debug_gui_print(f"ERROR: Exception fetching metrics for {fb_post_id}: {e}")
                    database_manager.increment_fetch_attempts(db_id) #
                
                time.sleep(0.5) # Small delay between API calls

            self.master.after(0, self.set_status, f"Metric fetching complete. Successfully updated {successful_fetches} posts.", "green")
            self.master.after(0, self._populate_posted_listbox) # Refresh the displayed list
            
        except Exception as e:
            error_msg = f"An unexpected error occurred during metric fetching: {e}"
            self.master.after(0, self.set_status, error_msg, "red")
            self.master.after(0, self.update_output_text, f"ERROR: {error_msg}\n")
            debug_gui_print(f"CRITICAL ERROR in fetch metrics thread: {e}")
        finally:
            self.master.after(0, self._enable_ui_buttons)
        debug_gui_print("Fetch metrics thread finished.")


    def on_tab_focus(self):
        debug_gui_print("PostingTrackingTab focused. Populating lists.")
        self._populate_unposted_listbox()
        self._populate_posted_listbox()
        # Start auto-scheduler when tab is focused, but only if not already running
        # This requires checking if the scheduler thread is alive, which is complex.
        # For simplicity, we'll keep it as a button-triggered action for now.
        # If you want it truly automated, you'd integrate the scheduler into the main GUI loop
        # or have a persistent background thread managed by the main application.