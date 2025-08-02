# gui_api_settings_tab.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import json
import threading
import sys
from datetime import datetime, timedelta
import random
import subprocess # Added: Required for subprocess.Popen

# Assume these are available or mocked for testing outside main GUI
try:
    import database_manager
    import ml_predictor
    import text_generator
    import image_generator
    import pandas as pd
except ImportError:
    # Mocks for standalone testing/IDE without full project structure
    class MockDBManager:
        def get_all_posts_for_ml(self): return pd.DataFrame()
        def save_generated_post(self, *args, **kwargs): return 1
        def update_post_predicted_engagement(self, *args): pass
        def get_feedback_by_page_id(self, page_id): return []
    database_manager = MockDBManager()

    class MockMLPredictor:
        def predict_engagement(self, *args): return 0.5
        def get_topic_performance_insights(self): return [], [], "No topics."
        def get_text_prompt_performance_insights(self): return [], [], "No prompts."
        def get_image_prompt_performance_insights(self): return [], [], "No image prompts."
        def get_optimal_posting_times_insights(self): return [("10:00", 0.8), ("11:00", 0.7)], [("Wednesday", 0.75), ("Tuesday", 0.7)], "Mock optimal times."
        def get_generator_parameter_insights(self): return [("Gemini", 0.9)], [("gemini-1.5-flash", 0.85)], [(0.7, 0.9)], "Mock gen params."
        def get_language_preference_insights(self): return [("English", 0.7), ("Arabic", 0.6)], "Mock language."

    ml_predictor = MockMLPredictor()

    class MockTextGenerator:
        # Adjusted mock to match the new signature of text_generator.generate_text
        def generate_text(self, prompt_en, prompt_ar, target_language, provider, model, temperature, contact_info_en="", contact_info_ar=""):
            mock_en = f"Mock EN content from {provider}/{model} for '{prompt_en[:20]}...'" if prompt_en else ""
            mock_ar = f"محتوى عربي تجريبي من {provider}/{model} لـ '{prompt_ar[:20]}...'" if prompt_ar else ""
            return mock_en, mock_ar, f"Used EN Prompt: {prompt_en}", f"Used AR Prompt: {prompt_ar}"
    text_generator = MockTextGenerator()

    class MockImageGenerator:
        # Adjusted mock to match the new signature of image_generator.generate_image
        def generate_image(self, prompt, output_dir, provider, model): return "mock_image.png"
    image_generator = MockImageGenerator()


# --- Debugging setup ---
DEBUG_GUI_MODE = True

def debug_gui_print(message):
    if DEBUG_GUI_MODE:
        print(f"[DEBUG - GUI - APISettings]: {message}")

class APISettingsTab(ttk.Frame):
    def __init__(self, parent, output_dir_var_ref, api_key_status_var_ref,
                 text_gen_provider_var_ref, gemini_model_var_ref,
                 openai_text_model_var_ref, openai_image_model_var_ref,
                 image_provider_var_ref,
                 num_posts_var_ref, gemini_temperature_var_ref,
                 gen_page_selection_var_ref, facebook_pages_ref,
                 start_date_var_ref, set_status_callback, populate_lists_callback):
        super().__init__(parent)
        self.output_dir_var = output_dir_var_ref
        self.api_key_status_var = api_key_status_var_ref
        self.selected_text_gen_provider_var = text_gen_provider_var_ref
        self.selected_gemini_model_var = gemini_model_var_ref
        self.selected_openai_text_model_var = openai_text_model_var_ref
        self.selected_openai_image_model_var = openai_image_model_var_ref
        self.selected_image_gen_provider_var = image_provider_var_ref
        self.num_posts_var = num_posts_var_ref
        self.gemini_temperature_var = gemini_temperature_var_ref
        self.gen_page_selection_var = gen_page_selection_var_ref
        self.facebook_pages = facebook_pages_ref
        self.start_date_var = start_date_var_ref
        self.set_status = set_status_callback
        self.populate_all_unposted_post_lists_callback = populate_lists_callback

        self.generation_running = False
        self.use_optimal_posting_time = tk.BooleanVar(value=False)
        self.use_optimal_gen_params = tk.BooleanVar(value=False)
        self.use_optimal_language = tk.BooleanVar(value=False)

        self._create_widgets()

    def _create_widgets(self):
        debug_gui_print("APISettingsTab _create_widgets called.")

        # API Keys Status Frame
        api_status_frame = ttk.LabelFrame(self, text="API Key Status")
        api_status_frame.pack(padx=10, pady=5, fill="x")

        self.api_key_status_label = ttk.Label(api_status_frame, textvariable=self.api_key_status_var, wraplength=700)
        self.api_key_status_label.pack(padx=10, pady=5, anchor="w")

        # Output Directory Frame
        output_frame = ttk.LabelFrame(self, text="Output Directory")
        output_frame.pack(padx=10, pady=5, fill="x")

        output_entry = ttk.Entry(output_frame, textvariable=self.output_dir_var, width=60)
        output_entry.pack(side="left", padx=5, pady=5, fill="x", expand=True)

        browse_button = ttk.Button(output_frame, text="Browse", command=self._browse_output_directory)
        browse_button.pack(side="right", padx=5, pady=5)

        # Generation Settings Frame
        gen_settings_frame = ttk.LabelFrame(self, text="Post Generation Settings")
        gen_settings_frame.pack(padx=10, pady=5, fill="x")

        # Page Selection
        ttk.Label(gen_settings_frame, text="Select Facebook Page:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.gen_page_combobox = ttk.Combobox(gen_settings_frame, textvariable=self.gen_page_selection_var, state="readonly", width=40)
        self.gen_page_combobox.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        # Number of posts
        ttk.Label(gen_settings_frame, text="Number of Posts to Generate:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(gen_settings_frame, textvariable=self.num_posts_var, width=10).grid(row=1, column=1, padx=5, pady=2, sticky="w")

        # Start Date
        ttk.Label(gen_settings_frame, text="Start Date (YYYY-MM-DD):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(gen_settings_frame, textvariable=self.start_date_var, width=20).grid(row=2, column=1, padx=5, pady=2, sticky="w")
        ttk.Label(gen_settings_frame, text="(Posts will be scheduled from this date hourly)").grid(row=2, column=2, padx=5, pady=2, sticky="w")

        # Optimal Posting Time Checkbutton and Button (Row 3)
        self.use_optimal_posting_time_checkbox = ttk.Checkbutton(gen_settings_frame, text="Use Optimal Posting Times", variable=self.use_optimal_posting_time, command=self._apply_optimal_posting_time_now_checkbox_state) # Bind to a new command
        self.use_optimal_posting_time_checkbox.grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.apply_optimal_time_button = ttk.Button(gen_settings_frame, text="Apply Optimal Time Now", command=self._apply_optimal_posting_time_now)
        self.apply_optimal_time_button.grid(row=3, column=1, padx=5, pady=2, sticky="w")

        # Optimal Generation Parameters Checkbox and Button (Row 4)
        self.use_optimal_gen_params_checkbox = ttk.Checkbutton(gen_settings_frame, text="Use Optimal Gen. Parameters", variable=self.use_optimal_gen_params, command=self._apply_optimal_gen_params_now_checkbox_state) # Bind to a new command
        self.use_optimal_gen_params_checkbox.grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.apply_optimal_gen_params_button = ttk.Button(gen_settings_frame, text="Apply Gen. Params Now", command=self._apply_optimal_gen_params_now)
        self.apply_optimal_gen_params_button.grid(row=4, column=1, padx=5, pady=2, sticky="w")

        # Optimal Language Checkbox (Row 5)
        self.use_optimal_language_checkbox = ttk.Checkbutton(gen_settings_frame, text="Use Optimal Language", variable=self.use_optimal_language, command=self._apply_optimal_language_now_checkbox_state) # Bind to a new command
        self.use_optimal_language_checkbox.grid(row=5, column=0, padx=5, pady=2, sticky="w")


        # Text Generation Provider (now at Row 6)
        ttk.Label(gen_settings_frame, text="Text Generation Provider:").grid(row=6, column=0, padx=5, pady=2, sticky="w")
        provider_options = ["Gemini", "OpenAI", "DeepSeek", "Mistral"]
        self.text_provider_combobox = ttk.Combobox(gen_settings_frame, textvariable=self.selected_text_gen_provider_var, values=provider_options, state="readonly", width=20)
        self.text_provider_combobox.grid(row=6, column=1, padx=5, pady=2, sticky="w")
        self.text_provider_combobox.bind("<<ComboboxSelected>>", self._on_text_provider_selected)

        # Model Selection (dynamic based on provider) (now at Row 7)
        ttk.Label(gen_settings_frame, text="Text Generation Model:").grid(row=7, column=0, padx=5, pady=2, sticky="w")
        self.text_model_combobox = ttk.Combobox(gen_settings_frame, state="readonly", width=40)
        self.text_model_combobox.grid(row=7, column=1, padx=5, pady=2, sticky="ew")

        # Gemini Temperature (now at Row 8)
        self.gemini_temperature_var_label = ttk.Label(gen_settings_frame, text="Gemini Temperature (0.0-1.0):")
        self.gemini_temperature_var_label.grid(row=8, column=0, padx=5, pady=2, sticky="w")
        self.gemini_temperature_scale = ttk.Scale(gen_settings_frame, from_=0.0, to=1.0, orient="horizontal", variable=self.gemini_temperature_var)
        self.gemini_temperature_scale.grid(row=8, column=1, padx=5, pady=2, sticky="ew")
        self.gemini_temperature_value_label = ttk.Label(gen_settings_frame, textvariable=self.gemini_temperature_var)
        self.gemini_temperature_value_label.grid(row=8, column=2, padx=5, pady=2, sticky="w")

        # Image Generation Provider (now at Row 9)
        ttk.Label(gen_settings_frame, text="Image Generation Provider:").grid(row=9, column=0, padx=5, pady=2, sticky="w")
        image_provider_options = ["OpenAI (DALL-E)", "Google (Imagen)"]
        self.image_provider_combobox = ttk.Combobox(gen_settings_frame, textvariable=self.selected_image_gen_provider_var, values=image_provider_options, state="readonly", width=20)
        self.image_provider_combobox.set("OpenAI (DALL-E)")
        self.image_provider_combobox.grid(row=9, column=1, padx=5, pady=2, sticky="w")

        # Model Selection (dynamic for image provider) (now at Row 10)
        ttk.Label(gen_settings_frame, text="Image Generation Model:").grid(row=10, column=0, padx=5, pady=2, sticky="w")
        self.image_model_combobox = ttk.Combobox(gen_settings_frame, textvariable=self.selected_openai_image_model_var, state="readonly", width=40)
        self.image_model_combobox['values'] = ["dall-e-3"]
        self.image_model_combobox.grid(row=10, column=1, padx=5, pady=2, sticky="ew")

        gen_settings_frame.columnconfigure(1, weight=1)

        self._on_text_provider_selected() # Initialize text model combobox

        # Generate Button
        self.generate_button = ttk.Button(self, text="Generate Posts", command=self._generate_posts_async)
        self.generate_button.pack(pady=10)

        # Output Text Area
        output_text_frame = ttk.LabelFrame(self, text="Generation Output")
        output_text_frame.pack(padx=10, pady=5, fill="both", expand=True)
        self.output_text = tk.Text(output_text_frame, wrap="word", height=10, state="disabled")
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.output_text_scroll = ttk.Scrollbar(output_text_frame, command=self.output_text.yview)
        self.output_text_scroll.pack(side="right", fill="y")
        self.output_text.config(yscrollcommand=self.output_text_scroll.set)

        debug_gui_print("APISettingsTab _create_widgets finished.")


    def _browse_output_directory(self):
        directory = filedialog.askdirectory(parent=self.master, initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)
            self.set_status(f"Output directory set to: {directory}", "blue")

    def _on_text_provider_selected(self, event=None):
        provider = self.selected_text_gen_provider_var.get()
        if provider == "Gemini":
            gemini_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
            self.text_model_combobox['values'] = gemini_models
            self.selected_gemini_model_var.set(gemini_models[0])
            self.text_model_combobox.config(textvariable=self.selected_gemini_model_var)
            self.gemini_temperature_var_label.grid(row=8, column=0, padx=5, pady=2, sticky="w")
            self.gemini_temperature_scale.grid(row=8, column=1, padx=5, pady=2, sticky="ew")
            self.gemini_temperature_value_label.grid(row=8, column=2, padx=5, pady=2, sticky="w")
        elif provider == "OpenAI":
            openai_text_models = ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]
            self.text_model_combobox['values'] = openai_text_models
            self.selected_openai_text_model_var.set(openai_text_models[0])
            self.text_model_combobox.config(textvariable=self.selected_openai_text_model_var)
            self.gemini_temperature_var_label.grid_forget()
            self.gemini_temperature_scale.grid_forget()
            self.gemini_temperature_value_label.grid_forget()
        elif provider == "DeepSeek":
            deepseek_models = ["deepseek-coder", "deepseek-r1"]
            self.text_model_combobox['values'] = deepseek_models
            self.selected_openai_text_model_var.set("deepseek-r1")
            self.text_model_combobox.config(textvariable=self.selected_openai_text_model_var)
            self.gemini_temperature_var_label.grid_forget()
            self.gemini_temperature_scale.grid_forget()
            self.gemini_temperature_value_label.grid_forget()
        elif provider == "Mistral":
            mistral_models = ["mistral", "mistral-openorca"]
            self.text_model_combobox['values'] = mistral_models
            self.selected_openai_text_model_var.set(mistral_models[0])
            self.text_model_combobox.config(textvariable=self.selected_openai_text_model_var)
            self.gemini_temperature_var_label.grid_forget()
            self.gemini_temperature_scale.grid_forget()
            self.gemini_temperature_value_label.grid_forget()


        if provider == "Gemini":
            self.text_model_combobox.config(textvariable=self.selected_gemini_model_var)
        else:
            self.text_model_combobox.config(textvariable=self.selected_openai_text_model_var)


    def update_page_selection_list(self, page_names, current_selection):
        self.gen_page_combobox['values'] = page_names
        if current_selection in page_names:
            self.gen_page_combobox.set(current_selection)
        elif page_names:
            self.gen_page_combobox.set(page_names[0])
        else:
            self.gen_page_combobox.set("")
        self.gen_page_combobox.config(state="readonly" if page_names else "disabled")


    def update_output_text_content(self, text):
        self.output_text.config(state="normal")
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.config(state="disabled")

    def _disable_generation_ui(self):
        self.generate_button.config(state=tk.DISABLED)
        self.apply_optimal_time_button.config(state=tk.DISABLED)
        self.use_optimal_posting_time_checkbox.config(state=tk.DISABLED)
        self.use_optimal_gen_params_checkbox.config(state=tk.DISABLED)
        self.apply_optimal_gen_params_button.config(state=tk.DISABLED)
        self.use_optimal_language_checkbox.config(state=tk.DISABLED)
        self.text_provider_combobox.config(state=tk.DISABLED)
        self.text_model_combobox.config(state=tk.DISABLED)
        self.image_provider_combobox.config(state=tk.DISABLED)
        self.image_model_combobox.config(state=tk.DISABLED)
        self.gen_page_combobox.config(state=tk.DISABLED)


    def _enable_generation_ui(self):
        self.generate_button.config(state=tk.NORMAL)
        self.apply_optimal_time_button.config(state=tk.NORMAL)
        self.use_optimal_posting_time_checkbox.config(state=tk.NORMAL)
        self.use_optimal_gen_params_checkbox.config(state=tk.NORMAL)
        self.apply_optimal_gen_params_button.config(state=tk.NORMAL)
        self.use_optimal_language_checkbox.config(state=tk.NORMAL)
        self.text_provider_combobox.config(state="readonly")
        self.text_model_combobox.config(state="readonly")
        self.image_provider_combobox.config(state="readonly")
        self.image_model_combobox.config(state="readonly")
        self.gen_page_combobox.config(state="readonly" if self.facebook_pages else "disabled")


    def _generate_posts_async(self):
        if self.generation_running:
            self.set_status("Generation already in progress.", "orange")
            return

        selected_page_name = self.gen_page_selection_var.get()
        if not selected_page_name:
            messagebox.showwarning("No Page Selected", "Please select a Facebook page before generating posts.", parent=self.master)
            self.set_status("Generation failed: No page selected.", "red")
            return

        num_posts = self.num_posts_var.get()
        if num_posts <= 0:
            messagebox.showwarning("Invalid Number", "Please enter a positive number of posts to generate.", parent=self.master)
            self.set_status("Generation failed: Invalid post count.", "red")
            return

        self.update_output_text_content("")
        self.set_status("Starting post generation...", "blue")
        self._disable_generation_ui()
        self.generation_running = True

        threading.Thread(target=self._run_generation_thread).start()


    def _run_generation_thread(self):
        try:
            selected_page_name = self.gen_page_selection_var.get()
            selected_page = next((p for p in self.facebook_pages if p["page_name"] == selected_page_name), None)

            if not selected_page:
                self.set_status("Error: Selected page not found in configuration.", "red")
                self.update_output_text_content("ERROR: Selected page not found in configuration.\n")
                return

            page_id = selected_page["facebook_page_id"]
            access_token = selected_page["facebook_access_token"]

            # Get general page contact information
            page_contact_info_en = selected_page.get("english_contact_info", "")
            page_contact_info_ar = selected_page.get("arabic_contact_info", "")

            # Fetch user feedback for this page and incorporate into prompts
            user_feedback_entries = database_manager.get_feedback_by_page_id(page_id)
            feedback_instructions_en = ""
            feedback_instructions_ar = ""
            if user_feedback_entries:
                combined_feedback_text = ". ".join([fbe['feedback_text'] for fbe in user_feedback_entries])
                feedback_instructions_en = f"\n\nAdditionally, consider this user feedback: {combined_feedback_text}"
                feedback_instructions_ar = f"\n\nبالإضافة إلى ذلك، ضع في اعتبارك ملاحظات المستخدم هذه: {combined_feedback_text}"


            topics = selected_page.get("topics", [])
            if not topics:
                self.set_status("Error: No topics defined for the selected page. Please manage topics.", "red")
                self.update_output_text_content("ERROR: No topics defined for the selected page. Please manage topics.\n")
                return

            # Get default prompts from selected_page's 'prompts' dict (if they exist)
            default_prompts = selected_page.get("prompts", {})
            default_post_prompt_en = default_prompts.get("default_prompt_en", "")
            default_post_prompt_ar = default_prompts.get("default_prompt_ar", "")
            default_image_prompt_en = default_prompts.get("default_image_prompt_en", "")
            default_image_prompt_ar = default_prompts.get("default_image_prompt_ar", "")


            num_posts = self.num_posts_var.get()
            # Get generation parameters (from UI)
            text_gen_provider = self.selected_text_gen_provider_var.get()
            text_gen_model = self.selected_gemini_model_var.get() if text_gen_provider == "Gemini" else self.selected_openai_text_model_var.get()
            gemini_temperature = self.gemini_temperature_var.get()
            language_choice_for_generation = random.choice(["English", "Arabic", "Both"])


            image_gen_provider = self.selected_image_gen_provider_var.get()
            image_gen_model = self.selected_openai_image_model_var.get()


            # Apply Optimal Generator Parameters if checkbox is checked
            if self.use_optimal_gen_params.get():
                best_providers, best_models, best_temperatures, msg = ml_predictor.get_generator_parameter_insights()
                
                applied_provider = False
                if best_providers:
                    text_gen_provider_optimal = best_providers[0][0]
                    self.master.after(0, lambda: self.selected_text_gen_provider_var.set(text_gen_provider_optimal))
                    self.master.after(0, self._on_text_provider_selected)
                    self.update_output_text_content(f"  Applying optimal provider: {text_gen_provider_optimal}\n")
                    text_gen_provider = text_gen_provider_optimal
                    applied_provider = True
                else:
                    self.update_output_text_content(f"  No optimal provider insights: {msg}\n")

                if applied_provider and best_models:
                    current_provider_models = self.text_model_combobox['values']
                    found_best_model = False
                    for model_name_optimal, _score in best_models:
                        if model_name_optimal in current_provider_models:
                            if text_gen_provider_optimal == "Gemini":
                                self.master.after(0, lambda: self.selected_gemini_model_var.set(model_name_optimal))
                            elif text_gen_provider_optimal in ["OpenAI", "DeepSeek", "Mistral"]:
                                self.master.after(0, lambda: self.selected_openai_text_model_var.set(model_name_optimal))
                            
                            text_gen_model = model_name_optimal
                            found_best_model = True
                            break
                    if not found_best_model:
                        self.update_output_text_content("  No optimal model found that matches selected provider's available models.\n")
                else:
                    self.update_output_text_content(f"  No optimal model insights: {msg}\n")
                
                if best_temperatures:
                    gemini_temperature_optimal = best_temperatures[0][0]
                    self.master.after(0, lambda: self.gemini_temperature_var.set(gemini_temperature_optimal))
                    gemini_temperature = gemini_temperature_optimal
                    self.update_output_text_content(f"  Applied optimal temperature: {gemini_temperature_optimal:.1f}\n")
                else:
                    self.update_output_text_content(f"  No optimal temperature insights: {msg}\n")

            # Apply Optimal Language if checkbox is checked
            if self.use_optimal_language.get():
                best_languages, msg = ml_predictor.get_language_preference_insights()
                if best_languages:
                    language_choice_for_generation = best_languages[0][0]
                    self.update_output_text_content(f"  Applying optimal language: {language_choice_for_generation}\n")
                else:
                    self.update_output_text_content(f"  No optimal language insights: {msg}\n")


            generated_count = 0
            start_date_str = self.start_date_var.get()
            try:
                datetime.strptime(start_date_str, "%Y-%m-%d")
            except ValueError:
                self.set_status(f"Error: Invalid start date format '{start_date_str}'. Please use YYYY-MM-DD.", "red")
                self.update_output_text_content(f"ERROR: Invalid start date format '{start_date_str}'. Aborting generation.\n")
                return

            initial_schedule_datetime = None
            if self.use_optimal_posting_time.get():
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
                    self.master.after(0, self.update_output_text_content, f"  Using optimal starting time: {initial_schedule_datetime.strftime('%Y-%m-%d %H:%M')}\n")
                else:
                    self.master.after(0, self.update_output_text_content, f"  Could not determine optimal posting time: {msg}. Falling back to default start date/time.\n")
                    initial_schedule_datetime = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d").replace(hour=10)
            else:
                initial_schedule_datetime = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d").replace(hour=10)

            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "facebook_posts_generator.py")
            
            temp_config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
            os.makedirs(temp_config_dir, exist_ok=True)
            temp_page_data_path = os.path.join(temp_config_dir, f"temp_page_data_{page_id}.json")
            try:
                with open(temp_page_data_path, 'w', encoding='utf-8') as f:
                    json.dump(selected_page, f, indent=4, ensure_ascii=False)
                debug_gui_print(f"Temporary page data saved to: {temp_page_data_path}")
            except Exception as e:
                self.set_status(f"Error saving temporary page data: {e}", "red")
                self.update_output_text_content(f"ERROR: Could not save temporary page data for generator: {e}\n")
                return


            args = [
                sys.executable, script_path,
                "--action", "generate",
                "--num_posts", str(num_posts),
                "--output_dir", self.output_dir_var.get(),
                "--text_gen_provider", text_gen_provider,
                "--gemini_text_model", self.selected_gemini_model_var.get(),
                "--openai_text_model", self.selected_openai_text_model_var.get(),
                "--openai_image_model", self.selected_openai_image_model_var.get(),
                "--temperature", str(gemini_temperature),
                "--start_date", initial_schedule_datetime.strftime("%Y-%m-%d"),
                "--start_time", initial_schedule_datetime.strftime("%H:%M"),
                "--posts_per_day", "1",
                "--interval_hours", "24.0",
                "--post_language", language_choice_for_generation,
                "--page_data_path", temp_page_data_path,
                "--image_gen_provider", image_gen_provider
            ]
            debug_gui_print(f"Generator subprocess command: {' '.join(args)}")

            process = subprocess.Popen(
                args,
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
                    self.master.after(0, self.update_output_text_content, line)
                    if "Post saved to DB with ID" in line:
                        generated_count += 1

            stderr_output = process.stderr.read()
            if stderr_output:
                self.master.after(0, self.update_output_text_content, "\n--- GENERATOR ERROR OUTPUT ---")
                self.master.after(0, self.update_output_text_content, stderr_output)
                debug_gui_print(f"Generator subprocess produced stderr:\n{stderr_output}")

            return_code = process.wait()
            debug_gui_print(f"Generator subprocess exited with code: {return_code}")

            if return_code == 0 and generated_count == num_posts:
                self.set_status(f"Successfully generated {generated_count} posts.", "green")
            elif return_code == 0 and generated_count < num_posts:
                self.set_status(f"Generated {generated_count} of {num_posts} posts. Some errors may have occurred. Check output.", "orange")
            else:
                self.set_status(f"Post generation failed. Exit code: {return_code}. Check output.", "red")
            
            if os.path.exists(temp_page_data_path):
                os.remove(temp_page_data_path)
                debug_gui_print(f"Removed temporary page data file: {temp_page_data_path}")

        except FileNotFoundError:
            self.set_status(f"Error: Generator script not found at {script_path}", "red")
            self.update_output_text_content(f"ERROR: Generator script not found: {script_path}\n")
        except Exception as e:
            self.set_status(f"An unexpected error occurred: {e}", "red")
            self.update_output_text_content(f"ERROR: An unexpected error occurred during generation: {e}\n")
            debug_gui_print(f"CRITICAL ERROR in _run_generation_thread: {e}")
        finally:
            self.generation_running = False
            self.master.after(0, self._enable_generation_ui)
            self.master.after(0, self.populate_all_unposted_post_lists_callback)
            debug_gui_print("_run_generation_thread finished.")

    def _apply_optimal_posting_time_now_checkbox_state(self):
        if self.use_optimal_posting_time.get():
            self.apply_optimal_time_button.config(state=tk.NORMAL)
        else:
            self.apply_optimal_time_button.config(state=tk.DISABLED)

    def _apply_optimal_gen_params_now_checkbox_state(self):
        if self.use_optimal_gen_params.get():
            self.apply_optimal_gen_params_button.config(state=tk.NORMAL)
        else:
            self.apply_optimal_gen_params_button.config(state=tk.DISABLED)

    def _apply_optimal_language_now_checkbox_state(self):
        pass

    def _apply_optimal_posting_time_now(self):
        debug_gui_print("_apply_optimal_posting_time_now called.")
        self.set_status("Applying optimal posting time...", "blue")
        self._disable_generation_ui()

        try:
            optimal_hours, optimal_days, message = ml_predictor.get_optimal_posting_times_insights()
            
            best_hour_str_local = "N/A"
            best_day_name_local = "N/A"
            
            if optimal_hours and optimal_days:
                best_hour_str_local = optimal_hours[0][0]
                best_hour = int(best_hour_str_local.split(':')[0])
                best_day_name_local = optimal_days[0][0]

                day_names_map = {
                    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
                    "Friday": 4, "Saturday": 5, "Sunday": 6
                }
                
                today = datetime.now()
                today_weekday_num = today.weekday()
                target_weekday_num = day_names_map.get(best_day_name_local, today_weekday_num)

                days_diff = (target_weekday_num - today_weekday_num + 7) % 7
                
                if days_diff == 0 and best_hour <= today.hour:
                    days_diff = 7
                
                target_date = today.date() + timedelta(days=days_diff)
                
                optimal_datetime = datetime(target_date.year, target_date.month, target_date.day, best_hour)

                self.master.after(0, self.start_date_var.set, optimal_datetime.strftime("%Y-%m-%d"))
                self.master.after(0, self.set_status, f"Applied optimal start: {optimal_datetime.strftime('%Y-%m-%d %H:%M')} (Day: {best_day_name_local}, Hour: {best_hour:02d}:00)", "green")
                self.master.after(0, self.update_output_text_content, f"Applied optimal start date/time: {optimal_datetime.strftime('%Y-%m-%d %H:%M')} (Best Day: {best_day_name_local}, Best Hour: {best_hour:02d}:00)\n")
                self.master.after(0, lambda: messagebox.showinfo("Optimal Time Applied",
                                            f"Start Date set to {optimal_datetime.strftime('%Y-%m-%d')}.\n"
                                            f"First post will be scheduled at {optimal_datetime.strftime('%H:00')} on this date.\n"
                                            f"(Based on best day: {best_day_name_local}, best hour: {best_hour_str_local})",
                                            parent=self.master))
            else:
                self.master.after(0, self.set_status, f"Could not apply optimal time: {message}", "orange")
                self.master.after(0, self.update_output_text_content, f"Could not apply optimal time: {message}\n")
                self.master.after(0, lambda: messagebox.showwarning("Optimal Time Not Found",
                                           f"Could not determine optimal posting times due to insufficient data or error: {message}\n"
                                           "Please ensure you have fetched metrics for enough posted content in the 'ML Dashboard' tab.",
                                           parent=self.master))
        except Exception as e:
            self.set_status(f"Error applying optimal time: {e}", "red")
            self.update_output_text_content(f"ERROR applying optimal time: {e}\n")
            debug_gui_print(f"CRITICAL ERROR in _apply_optimal_posting_time_now: {e}")
        finally:
            self._enable_generation_ui()
            debug_gui_print("_apply_optimal_posting_time_now finished.")

    def _apply_optimal_gen_params_now(self):
        debug_gui_print("_apply_optimal_gen_params_now called.")
        self.set_status("Applying optimal generator parameters...", "blue")
        self._disable_generation_ui()

        try:
            best_providers, best_models, best_temperatures, message = ml_predictor.get_generator_parameter_insights()
            
            applied_provider = False
            if best_providers:
                text_gen_provider_optimal = best_providers[0][0]
                self.master.after(0, lambda: self.selected_text_gen_provider_var.set(text_gen_provider_optimal))
                self.master.after(0, self._on_text_provider_selected)
                self.update_output_text_content(f"  Applying optimal provider: {text_gen_provider_optimal}\n")
                applied_provider = True
            else:
                self.update_output_text_content(f"  No optimal provider insights: {message}\n")

            if applied_provider and best_models:
                current_provider_models = self.text_model_combobox['values']
                found_best_model = False
                for model_name_optimal, _score in best_models:
                    if model_name_optimal in current_provider_models:
                        if text_gen_provider_optimal == "Gemini":
                            self.master.after(0, lambda: self.selected_gemini_model_var.set(model_name_optimal))
                        elif text_gen_provider_optimal in ["OpenAI", "DeepSeek", "Mistral"]:
                            self.master.after(0, lambda: self.selected_openai_text_model_var.set(model_name_optimal))
                        found_best_model = True
                        break
                if not found_best_model:
                    self.update_output_text_content("  No optimal model found that matches selected provider's available models.\n")
            else:
                self.update_output_text_content(f"  No optimal model insights: {message}\n")
            
            if best_temperatures:
                gemini_temperature_optimal = best_temperatures[0][0]
                self.master.after(0, lambda: self.gemini_temperature_var.set(gemini_temperature_optimal))
                self.update_output_text_content(f"  Applied optimal temperature: {gemini_temperature_optimal:.1f}\n")
            else:
                self.update_output_text_content(f"  No optimal temperature insights: {message}\n")

            self.set_status(f"Optimal generator parameters applied. {message}", "green")
            messagebox.showinfo("Optimal Gen. Params Applied", f"Optimal generation parameters applied based on insights.\n{message}", parent=self.master)

        except Exception as e:
            self.set_status(f"Error applying optimal generator parameters: {e}", "red")
            self.update_output_text_content(f"ERROR applying optimal generator parameters: {e}\n")
            debug_gui_print(f"CRITICAL ERROR in _apply_optimal_gen_params_now: {e}")
        finally:
            self._enable_generation_ui()
            debug_gui_print("_apply_optimal_gen_params_now finished.")

    def _apply_optimal_language_now(self):
        debug_gui_print("_apply_optimal_language_now called.")
        self.set_status("Applying optimal language...", "blue")
        self._disable_generation_ui()

        try:
            best_languages, message = ml_predictor.get_language_preference_insights()
            if best_languages:
                self.update_output_text_content(f"  Optimal language identified: {best_languages[0][0]} (Avg Engagement: {best_languages[0][1]:.2f})\n")
                self.set_status(f"Optimal language insight: {best_languages[0][0]}", "green")
                messagebox.showinfo("Optimal Language Insight",
                                    f"Based on historical data, the optimal language is: {best_languages[0][0]} (Avg Engagement: {best_languages[0][1]:.2f}).\n"
                                    "This will be used during generation if 'Use Optimal Language' is checked.",
                                    parent=self.master)
            else:
                self.set_status(f"Could not apply optimal language: {message}", "orange")
                self.update_output_text_content(f"  Could not apply optimal language: {message}\n")
                messagebox.showwarning("Optimal Language Not Found",
                                       f"Could not determine optimal language preference due to insufficient data or error: {message}\n"
                                       "Please ensure you have fetched metrics for enough posted content in the 'ML Dashboard' tab.",
                                       parent=self.master)
        except Exception as e:
            self.set_status(f"Error applying optimal language: {e}", "red")
            self.update_output_text_content(f"ERROR applying optimal language: {e}\n")
            debug_gui_print(f"CRITICAL ERROR in _apply_optimal_language_now: {e}")
        finally:
            self._enable_generation_ui()
            debug_gui_print("_apply_optimal_language_now finished.")