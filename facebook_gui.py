# D:\Facebook_Posts_generation\facebook_gui.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import json
import threading
import sys
from datetime import datetime, timedelta

# Import the new modularized tab classes
from gui_api_settings_tab import APISettingsTab
from gui_page_details_tab import PageDetailsTab
from gui_manage_topics_tab import ManageTopicsTab
from gui_posting_tracking_tab import PostingTrackingTab
from gui_post_review_edit_tab import PostReviewEditTab
from gui_ml_dashboard_tab import MLDashboardTab
from gui_user_feedback_tab import UserFeedbackTab

# ADD THESE LINES TO DEBUG THE IMPORTED MODULE CONTENT:
print("\n--- DEBUG: gui_api_settings_tab.py CONTENT CHECK ---")
try:
    import gui_api_settings_tab # Import here to get its __file__ attribute reliably
    with open(gui_api_settings_tab.__file__, 'r', encoding='utf-8') as f:
        loaded_content = f.read()
        print(f"Content of loaded gui_api_settings_tab.py from {gui_api_settings_tab.__file__}:")
        # Print the first 500 characters for a quick check
        print(loaded_content[:500])
        if "_apply_optimal_posting_time_now" in loaded_content:
            print("CONFIRMATION: '_apply_optimal_posting_time_now' string IS present in the loaded file content.")
        else:
            print("WARNING: '_apply_optimal_posting_time_now' string is NOT present in the loaded file content.")
        print(f"File modification time (timestamp): {os.path.getmtime(gui_api_settings_tab.__file__)}")
        print(f"Current working directory (os.getcwd()): {os.getcwd()}")
        print(f"Script directory (os.path.dirname(os.path.abspath(__file__))): {os.path.dirname(os.path.abspath(__file__))}")
    del gui_api_settings_tab # Delete it to allow the later import in create_widgets to be clean
except Exception as e:
    print(f"ERROR reading loaded gui_api_settings_tab.py content: {e}")
print("--- END DEBUG CHECK ---")


# Assuming database_manager.py is in the same directory
import database_manager

# --- Debugging setup ---
DEBUG_GUI_MODE = True

def debug_gui_print(message):
    if DEBUG_GUI_MODE:
        print(f"[DEBUG - GUI - Main]: {message}")

class FacebookPostGeneratorGUI:
    def __init__(self, master):
        debug_gui_print("FacebookPostGeneratorGUI.__init__ started.")
        self.master = master
        master.title("Facebook Post Generator (GUI)")
        master.geometry("1000x850")

        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.default_output_dir = os.path.join(self.script_dir, "Generated_Posts_Output")
        self.config_dir = os.path.join(self.script_dir, "config")
        debug_gui_print(f"Config directory: {self.config_dir}")

        # --- Shared Tkinter Variables and Data Structures ---
        self.output_dir_var = tk.StringVar(value=self.default_output_dir)
        self.api_key_status_var = tk.StringVar(value="API Keys: Check Status Below")

        self.selected_text_gen_provider_var = tk.StringVar(value="Gemini")

        self.selected_gemini_model_var = tk.StringVar(value="gemini-1.5-flash")
        self.selected_openai_text_model_var = tk.StringVar(value="gpt-3.5-turbo")
        self.selected_openai_image_model_var = tk.StringVar(value="dall-e-3")
        # NEW: Shared variable for Image Provider
        self.selected_image_gen_provider_var = tk.StringVar(value="OpenAI (DALL-E)") # Default value

        self.num_posts_var = tk.IntVar(value=84)
        self.gemini_temperature_var = tk.DoubleVar(value=0.7)
        self.gen_page_selection_var = tk.StringVar()
        self.start_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))

        self.facebook_pages = []

        self.create_widgets()
        debug_gui_print("Widgets created.")

        database_manager.create_tables()
        debug_gui_print("Database tables ensured to exist.")

        self._load_config_from_files()
        debug_gui_print("Configuration loaded from files.")

        self._update_all_page_lists_and_selections()
        debug_gui_print("All page lists updated initially.")

        self._populate_all_unposted_post_lists()
        debug_gui_print("All unposted/review lists populated.")

        self._check_api_key_status()
        debug_gui_print("API key status checked.")
        debug_gui_print("FacebookPostGeneratorGUI.__init__ finished.")

    # Wrapper method to safely call update_output_text_content from APISettingsTab
    def _update_output_text_content_wrapper(self, text):
        # Use master.after to ensure this runs on the main Tkinter thread
        # This now routes to APISettingsTab for generation output
        self.master.after(0, self._do_update_output_text_content_wrapper, text)

    def _do_update_output_text_content_wrapper(self, text):
        if hasattr(self, 'api_settings_tab_instance') and hasattr(self.api_settings_tab_instance, 'update_output_text_content'):
            self.api_settings_tab_instance.update_output_text_content(text)
        else:
            debug_gui_print("WARNING: api_settings_tab_instance or its update_output_text_content not available yet for output update.")
            print(text, end='')


    def create_widgets(self):
        debug_gui_print("create_widgets (Main GUI) called.")
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # The actual import for the class constructor
        from gui_api_settings_tab import APISettingsTab

        self.api_settings_tab_instance = APISettingsTab(
            self.notebook,
            output_dir_var_ref=self.output_dir_var,
            api_key_status_var_ref=self.api_key_status_var,
            text_gen_provider_var_ref=self.selected_text_gen_provider_var,
            gemini_model_var_ref=self.selected_gemini_model_var,
            openai_text_model_var_ref=self.selected_openai_text_model_var,
            openai_image_model_var_ref=self.selected_openai_image_model_var,
            # Pass the new image provider variable
            image_provider_var_ref=self.selected_image_gen_provider_var,
            num_posts_var_ref=self.num_posts_var,
            gemini_temperature_var_ref=self.gemini_temperature_var,
            gen_page_selection_var_ref=self.gen_page_selection_var,
            facebook_pages_ref=self.facebook_pages,
            start_date_var_ref=self.start_date_var,
            set_status_callback=self.set_status,
            populate_lists_callback=self._populate_all_unposted_post_lists
        )
        self.notebook.add(self.api_settings_tab_instance, text="Generate Posts")

        from gui_page_details_tab import PageDetailsTab
        self.page_details_tab_instance = PageDetailsTab(
            self.notebook,
            facebook_pages_ref=self.facebook_pages,
            set_status_callback=self.set_status,
            save_config_callback=self._save_config_to_files,
            update_all_page_lists_and_selections_callback=self._update_all_page_lists_and_selections
        )
        self.notebook.add(self.page_details_tab_instance, text="Page Details")

        from gui_manage_topics_tab import ManageTopicsTab
        self.manage_topics_tab_instance = ManageTopicsTab(
            self.notebook,
            facebook_pages_ref=self.facebook_pages,
            set_status_callback=self.set_status,
            save_config_callback=self._save_config_to_files
        )
        self.notebook.add(self.manage_topics_tab_instance, text="Manage Topics")

        from gui_post_review_edit_tab import PostReviewEditTab
        self.post_review_edit_tab_instance = PostReviewEditTab(
            self.notebook,
            set_status_callback=self.set_status,
            output_dir_var_ref=self.output_dir_var,
            facebook_pages_ref=self.facebook_pages,
            # --- NEW: Pass direct references to shared image gen variables ---
            image_provider_var_ref=self.selected_image_gen_provider_var,
            openai_image_model_var_ref=self.selected_openai_image_model_var,
            # --- END NEW ---
            api_settings_tab_instance_ref=self.api_settings_tab_instance, # Keep this for other general references if needed
            populate_unposted_listbox_callback=self._populate_all_unposted_post_lists,
            script_dir_ref=self.script_dir
        )
        self.notebook.add(self.post_review_edit_tab_instance, text="Post Review & Edit")

        from gui_posting_tracking_tab import PostingTrackingTab
        self.posting_tracking_tab_instance = PostingTrackingTab(
            self.notebook,
            facebook_pages_ref=self.facebook_pages,
            set_status_callback=self.set_status,
            update_output_text_callback=self._update_output_text_content_wrapper,
            output_dir_var_ref=self.output_dir_var,
            populate_all_unposted_post_lists_callback=self._populate_all_unposted_post_lists
        )
        self.notebook.add(self.posting_tracking_tab_instance, text="Posting & Tracking")

        from gui_ml_dashboard_tab import MLDashboardTab
        self.ml_dashboard_tab_instance = MLDashboardTab(
            self.notebook,
            set_status_callback=self.set_status,
            update_output_text_callback=self._update_output_text_content_wrapper
        )
        self.notebook.add(self.ml_dashboard_tab_instance, text="ML Dashboard")

        from gui_user_feedback_tab import UserFeedbackTab
        self.user_feedback_tab_instance = UserFeedbackTab(
            self.notebook,
            set_status_callback=self.set_status,
            facebook_pages_ref=self.facebook_pages
        )
        self.notebook.add(self.user_feedback_tab_instance, text="User Feedback")


        self.status_bar = tk.Label(self.master, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        debug_gui_print("Widgets created.")

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, event):
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        debug_gui_print(f"Tab changed to: {selected_tab}")

        # Call on_tab_focus for the respective tab instances
        if selected_tab == "Manage Topics":
            self.manage_topics_tab_instance.on_tab_focus()
        elif selected_tab == "Post Review & Edit":
            self.post_review_edit_tab_instance.on_tab_focus()
        elif selected_tab == "Posting & Tracking":
            self.posting_tracking_tab_instance.on_tab_focus()
        elif selected_tab == "ML Dashboard":
            self.ml_dashboard_tab_instance.on_tab_focus()
        elif selected_tab == "User Feedback":
            self.user_feedback_tab_instance.on_tab_focus()


    def _check_api_key_status(self):
        debug_gui_print("_check_api_key_status (Main GUI) called.")

        gemini_status = "Not Found"
        if os.getenv('GEMINI_API_KEY'):
            gemini_status = "Found"
        else:
            debug_gui_print("WARNING: GEMINI_API_KEY environment variable not set. Gemini generation will not work.")

        openai_api_key_status = "Not Found"
        if os.getenv('OPENAI_API_KEY'):
            openai_api_key_status = "Found"
        else:
            debug_gui_print("WARNING: OPENAI_API_KEY environment variable not set. OpenAI generation will not work.")

        gcp_project_id = os.getenv('GCP_PROJECT_ID')
        gcp_region = os.getenv('GCP_REGION')
        imagen_status_msg = "Not Set (Required for Imagen)"
        if gcp_project_id and gcp_region:
            imagen_status_msg = f"Set (Project: {gcp_project_id}, Region: {gcp_region})"
        else:
            debug_gui_print("WARNING: GCP_PROJECT_ID or GCP_REGION environment variables not set. Imagen functionality will be limited.")


        self.api_key_status_var.set(
            f"Gemini API Key: {gemini_status} (for Text Gen)\n"
            f"OpenAI API Key: {openai_api_key_status} (for Text & Image Gen)\n"
            f"Google Cloud (Imagen) Config: {imagen_status_msg}\n"
            "Facebook Page Tokens: Set/Verify in 'Manage Facebook Pages' tab."
        )


    def _save_config_to_files(self):
        debug_gui_print("_save_config_to_files (Main GUI) called.")
        os.makedirs(self.config_dir, exist_ok=True)
        debug_gui_print(f"Ensured config directory exists: {self.config_dir}")

        gui_config_path = os.path.join(self.config_dir, "gui_config.json")
        gui_config_data = {
            "output_dir": self.output_dir_var.get(),
            "selected_text_gen_provider": self.selected_text_gen_provider_var.get(),
            "selected_gemini_model": self.selected_gemini_model_var.get(),
            "selected_openai_text_model": self.selected_openai_text_model_var.get(),
            "selected_openai_image_model": self.selected_openai_image_model_var.get(),
            # Save the image provider variable's value
            "selected_image_gen_provider": self.selected_image_gen_provider_var.get(),
            "gemini_temperature": self.gemini_temperature_var.get(),
            "num_posts_default": self.num_posts_var.get(),
            "start_date": self.start_date_var.get(),
            "facebook_pages": self.facebook_pages
        }
        try:
            with open(gui_config_path, 'w', encoding='utf-8') as f:
                json.dump(gui_config_data, f, indent=4, ensure_ascii=False)
            debug_gui_print(f"gui_config.json saved to: {gui_config_path}")
        except Exception as e:
            self.set_status(f"Error saving main GUI config: {e}", "red")
            messagebox.showerror("Save Error", f"Failed to save main GUI configuration: {e}", parent=self.master)
            debug_gui_print(f"ERROR: Failed to save gui_config.json: {e}")
            return

        self.set_status(f"All configurations saved successfully to {self.config_dir}", "green")
        debug_gui_print("_save_config_to_files (Main GUI) finished.")

    def _load_config_from_files(self):
        debug_gui_print("_load_config_from_files (Main GUI) called.")
        os.makedirs(self.config_dir, exist_ok=True)
        debug_gui_print(f"Ensured config directory exists: {self.config_dir}")

        gui_config_path = os.path.join(self.config_dir, "gui_config.json")

        if os.path.exists(gui_config_path):
            try:
                with open(gui_config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self.output_dir_var.set(config_data.get("output_dir", self.default_output_dir))

                    self.selected_text_gen_provider_var.set(config_data.get("selected_text_gen_provider", "Gemini"))
                    self.selected_gemini_model_var.set(config_data.get("selected_gemini_model", "gemini-1.5-flash"))
                    self.selected_openai_text_model_var.set(config_data.get("selected_openai_text_model", "gpt-3.5-turbo"))
                    self.selected_openai_image_model_var.set(config_data.get("selected_openai_image_model", config_data.get("selected_openai_model", "dall-e-3")))
                    # Load the image provider variable's value
                    self.selected_image_gen_provider_var.set(config_data.get("selected_image_gen_provider", "OpenAI (DALL-E)"))

                    self.gemini_temperature_var.set(config_data.get("gemini_temperature", 0.7))
                    self.num_posts_var.set(config_data.get("num_posts_default", 84))
                    self.start_date_var.set(config_data.get("start_date", datetime.now().strftime("%Y-%m-%d")))
                    debug_gui_print("Loaded core GUI settings from gui_config.json.")

                    self.facebook_pages.clear()
                    self.facebook_pages.extend(config_data.get("facebook_pages", []))
                    debug_gui_print(f"Loaded {len(self.facebook_pages)} Facebook pages from gui_config.json, with embedded topics and prompts.")

            except json.JSONDecodeError as e:
                messagebox.showerror("Config Load Error", f"Error reading gui_config.json: {e}. File might be corrupted. Initializing pages to empty list.")
                self.facebook_pages.clear()
                debug_gui_print(f"ERROR: Corrupted gui_config.json: {e}")
            except Exception as e:
                messagebox.showerror("Config Load Error", f"An unexpected error occurred loading gui_config.json: {e}. Initializing pages to empty list.")
                self.facebook_pages.clear()
                debug_gui_print(f"ERROR: Unexpected error loading gui_config.json: {e}")
        else:
            self.facebook_pages.clear()
            messagebox.showinfo("Config Info", "gui_config.json not found. Starting with no configured Facebook pages. Please add pages via the 'Manage Facebook Pages' tab and save.")
            debug_gui_print("gui_config.json not found. Initializing with empty pages.")

        self.set_status("Configuration loaded successfully.", "green")
        self._check_api_key_status()
        debug_gui_print("_load_config_from_files (Main GUI) finished.")

    def set_status(self, message, color="black"):
        """Centralized method to update the main status bar."""
        self.master.after(0, lambda: self.status_bar.config(text=message, fg=color))
        debug_gui_print(f"Status set: {message} ({color})")

    def _update_all_page_lists_and_selections(self):
        debug_gui_print("_update_all_page_lists_and_selections (Main GUI) called.")
        page_names = [page["page_name"] for page in self.facebook_pages]

        current_selected_page_name_detail = ""
        if hasattr(self, 'page_details_tab_instance') and \
           self.page_details_tab_instance.current_selected_page_index_detail_tab != -1 and \
           self.page_details_tab_instance.current_selected_page_index_detail_tab < len(self.facebook_pages):
            current_selected_page_name_detail = self.facebook_pages[self.page_details_tab_instance.current_selected_page_index_detail_tab]["page_name"]

        current_selected_page_name_topic = ""
        if hasattr(self, 'manage_topics_tab_instance'):
            current_selected_page_name_topic = self.manage_topics_tab_instance.topic_page_selection_var.get()

        current_selected_page_name_gen = ""
        if hasattr(self, 'api_settings_tab_instance'):
            current_selected_page_name_gen = self.api_settings_tab_instance.gen_page_selection_var.get()

        # Call update methods on all relevant tab instances
        self.page_details_tab_instance.update_page_selection_list(page_names, current_selected_page_name_detail)
        self.manage_topics_tab_instance.update_page_selection_list(page_names, current_selected_page_name_topic)
        self.api_settings_tab_instance.update_page_selection_list(page_names, current_selected_page_name_gen)
        # Also update the page selection for PostReviewEditTab
        if hasattr(self, 'post_review_edit_tab_instance'):
            self.post_review_edit_tab_instance.post_page_combobox['values'] = page_names
            if self.post_review_edit_tab_instance.selected_post and \
               self.post_review_edit_tab_instance.selected_post.get('page_name') in page_names:
                self.post_review_edit_tab_instance.selected_page_for_post_var.set(self.post_review_edit_tab_instance.selected_post['page_name'])
            elif page_names:
                self.post_review_edit_tab_instance.selected_page_for_post_var.set(page_names[0])
            else:
                self.post_review_edit_tab_instance.selected_page_for_post_var.set("")
            self.post_review_edit_tab_instance.post_page_combobox.config(state="readonly" if page_names else "disabled")
        
        # Update UserFeedbackTab page list
        if hasattr(self, 'user_feedback_tab_instance'):
            self.user_feedback_tab_instance.update_page_selection_list(page_names)


        self._check_api_key_status()

        debug_gui_print("_update_all_page_lists_and_selections (Main GUI) finished.")

    def _populate_all_unposted_post_lists(self):
        debug_gui_print("_populate_all_unposted_post_lists (Main GUI) called.")
        if hasattr(self, 'posting_tracking_tab_instance'):
            self.posting_tracking_tab_instance._populate_unposted_listbox()
        else:
            debug_gui_print("WARNING: posting_tracking_tab_instance not yet initialized. Cannot populate unposted listbox.")

        if hasattr(self, 'post_review_edit_tab_instance'):
            self.post_review_edit_tab_instance._populate_posts_list()
        else:
            debug_gui_print("WARNING: post_review_edit_tab_instance not yet initialized. Cannot populate review list.")


if __name__ == "__main__":
    debug_gui_print("Starting GUI application.")
    root = tk.Tk()
    app = FacebookPostGeneratorGUI(root)
    root.mainloop()
    debug_gui_print("GUI application closed.")