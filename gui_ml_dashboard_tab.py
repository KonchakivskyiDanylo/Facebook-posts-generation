# gui_ml_dashboard_tab.py

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
import pandas as pd # Ensure pandas is imported for ml_predictor
from datetime import datetime # Import datetime for date parsing

# Assume these are available or mocked for testing outside main GUI
try:
    import database_manager
    import ml_predictor
except ImportError:
    # Mocks for standalone testing/IDE without full project structure
    class MockDBManager:
        def get_all_posts_for_ml(self): return pd.DataFrame()
    database_manager = MockDBManager()

    class MockMLPredictor:
        def get_topic_performance_insights(self): return [], [], "No topics."
        def get_text_prompt_performance_insights(self): return [], [], "No text prompts."
        def get_image_prompt_performance_insights(self): return [], [], "No image prompts."
        def get_optimal_posting_times_insights(self): return [("10:00", 0.8), ("11:00", 0.7)], [("Wednesday", 0.75), ("Tuesday", 0.7)], "Mock optimal times."
        def get_generator_parameter_insights(self): return [("Gemini", 0.9)], [("gemini-1.5-flash", 0.85)], [(0.7, 0.9)], "Mock gen params."
        def get_language_preference_insights(self): return [("English", 0.7), ("Arabic", 0.6)], "Mock language."
    ml_predictor = MockMLPredictor()


# --- Debugging setup ---
DEBUG_GUI_MODE = True

def debug_gui_print(message):
    if DEBUG_GUI_MODE:
        print(f"[DEBUG - GUI - MLDashboard]: {message}")

class MLDashboardTab(ttk.Frame):
    def __init__(self, parent, set_status_callback, update_output_text_callback):
        super().__init__(parent)
        self.set_status = set_status_callback
        self.update_output_text = update_output_text_callback # This callback isn't used directly here for logging to GUI, but rather to the internal log.

        self.analysis_running = False # Flag to prevent multiple analyses

        self._create_widgets()

    def _create_widgets(self):
        debug_gui_print("MLDashboardTab _create_widgets called.")

        # Create a scrollable frame for all insights
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


        # --- ML INSIGHTS SECTION CONTAINER (Main button to run all) ---
        main_controls_frame = ttk.LabelFrame(self.scrollable_frame, text="Overall ML Insights Control")
        main_controls_frame.pack(fill="x", padx=10, pady=10)

        self.run_all_insights_button = ttk.Button(main_controls_frame, text="Run All Insights Analyses", command=self._run_all_insights_async)
        self.run_all_insights_button.pack(pady=10)

        # Separate frame for the output text, as it's shared across all analyses
        output_text_frame = ttk.LabelFrame(self.scrollable_frame, text="ML Analysis Output Log")
        output_text_frame.pack(padx=10, pady=5, fill="x")
        self.output_text = tk.Text(output_text_frame, wrap="word", height=8, state="disabled") # Removed bg
        self.output_text.pack(fill="x", expand=True, padx=5, pady=5)
        self.output_text_scroll = ttk.Scrollbar(output_text_frame, command=self.output_text.yview)
        self.output_text_scroll.pack(side="right", fill="y")
        self.output_text.config(yscrollcommand=self.output_text_scroll.set)


        # --- ML TOPIC INSIGHTS SECTION ---
        topic_insights_frame = ttk.LabelFrame(self.scrollable_frame, text="Topic Performance")
        topic_insights_frame.pack(fill="x", padx=10, pady=10)

        # self.analyze_topics_button = ttk.Button(topic_insights_frame, text="Analyze Topic Performance", command=self._analyze_topic_performance_async)
        # self.analyze_topics_button.pack(pady=(5, 10)) # Removed individual button, now controlled by "Run All"

        # High-performing topics
        high_topics_frame = ttk.Frame(topic_insights_frame)
        high_topics_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(high_topics_frame, text="High-Performing Topics:").pack(anchor="w")
        self.high_topics_text = tk.Text(high_topics_frame, height=4, wrap="word", state="disabled") # Removed bg
        self.high_topics_text.pack(fill="x", expand=True)

        # Low-performing topics
        low_topics_frame = ttk.Frame(topic_insights_frame)
        low_topics_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(low_topics_frame, text="Low-Performing Topics:").pack(anchor="w")
        self.low_topics_text = tk.Text(low_topics_frame, height=4, wrap="word", state="disabled") # Removed bg
        self.low_topics_text.pack(fill="x", expand=True)


        # --- ML TEXT PROMPT INSIGHTS SECTION ---
        text_prompt_insights_frame = ttk.LabelFrame(self.scrollable_frame, text="Text Prompt Performance")
        text_prompt_insights_frame.pack(fill="x", padx=10, pady=10)

        # self.analyze_prompts_button = ttk.Button(text_prompt_insights_frame, text="Analyze Text Prompt Performance", command=self._analyze_text_prompt_performance_async)
        # self.analyze_prompts_button.pack(pady=(5, 10)) # Removed individual button

        # High-performing prompt phrases
        high_prompts_frame = ttk.Frame(text_prompt_insights_frame)
        high_prompts_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(high_prompts_frame, text="High-Performing Prompt Phrases:").pack(anchor="w")
        self.high_prompts_text = tk.Text(high_prompts_frame, height=4, wrap="word", state="disabled") # Removed bg
        self.high_prompts_text.pack(fill="x", expand=True)

        # Low-performing prompt phrases
        low_prompts_frame = ttk.Frame(text_prompt_insights_frame)
        low_prompts_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(low_prompts_frame, text="Low-Performing Prompt Phrases:").pack(anchor="w")
        self.low_prompts_text = tk.Text(low_prompts_frame, height=4, wrap="word", state="disabled") # Removed bg
        self.low_prompts_text.pack(fill="x", expand=True)


        # --- ML IMAGE PROMPT INSIGHTS SECTION ---
        image_prompt_insights_frame = ttk.LabelFrame(self.scrollable_frame, text="Image Prompt Performance")
        image_prompt_insights_frame.pack(fill="x", padx=10, pady=10)

        # self.analyze_image_prompts_button = ttk.Button(image_prompt_insights_frame, text="Analyze Image Prompt Performance", command=self._analyze_image_prompt_performance_async)
        # self.analyze_image_prompts_button.pack(pady=(5, 10)) # Removed individual button

        # High-performing image prompt phrases
        high_image_prompts_frame = ttk.Frame(image_prompt_insights_frame)
        high_image_prompts_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(high_image_prompts_frame, text="High-Performing Image Prompt Phrases:").pack(anchor="w")
        self.high_image_prompts_text = tk.Text(high_image_prompts_frame, height=4, wrap="word", state="disabled") # Removed bg
        self.high_image_prompts_text.pack(fill="x", expand=True)

        # Low-performing image prompt phrases
        low_image_prompts_frame = ttk.Frame(image_prompt_insights_frame)
        low_image_prompts_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(low_image_prompts_frame, text="Low-Performing Image Prompt Phrases:").pack(anchor="w")
        self.low_image_prompts_text = tk.Text(low_image_prompts_frame, height=4, wrap="word", state="disabled") # Removed bg
        self.low_image_prompts_text.pack(fill="x", expand=True)


        # --- ML GENERATOR PARAMETER INSIGHTS SECTION ---
        gen_param_insights_frame = ttk.LabelFrame(self.scrollable_frame, text="Generator Parameter Performance")
        gen_param_insights_frame.pack(fill="x", padx=10, pady=10)

        # self.analyze_gen_params_button = ttk.Button(gen_param_insights_frame, text="Analyze Generator Parameters", command=self._analyze_generator_parameters_async)
        # self.analyze_gen_params_button.pack(pady=(5, 10)) # Removed individual button

        # Best Providers
        best_providers_frame = ttk.Frame(gen_param_insights_frame)
        best_providers_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(best_providers_frame, text="Top Performing Providers (Avg Engagement):").pack(anchor="w")
        self.best_providers_text = tk.Text(best_providers_frame, height=3, wrap="word", state="disabled") # Removed bg
        self.best_providers_text.pack(fill="x", expand=True)

        # Best Models
        best_models_frame = ttk.Frame(gen_param_insights_frame)
        best_models_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(best_models_frame, text="Top Performing Models (Avg Engagement):").pack(anchor="w")
        self.best_models_text = tk.Text(best_models_frame, height=3, wrap="word", state="disabled") # Removed bg
        self.best_models_text.pack(fill="x", expand=True)

        # Best Temperatures
        best_temps_frame = ttk.Frame(gen_param_insights_frame)
        best_temps_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(best_temps_frame, text="Top Performing Temperatures (Avg Engagement):").pack(anchor="w")
        self.best_temperatures_text = tk.Text(best_temps_frame, height=3, wrap="word", state="disabled") # Removed bg
        self.best_temperatures_text.pack(fill="x", expand=True)


        # --- OPTIMAL POSTING TIMES INSIGHTS SECTION ---
        optimal_times_frame = ttk.LabelFrame(self.scrollable_frame, text="Optimal Posting Times")
        optimal_times_frame.pack(fill="x", padx=10, pady=10)

        # self.analyze_times_button = ttk.Button(optimal_times_frame, text="Analyze Optimal Posting Times", command=self._analyze_optimal_posting_times_async)
        # self.analyze_times_button.pack(pady=(5, 10)) # Removed individual button

        # Optimal Hours
        optimal_hours_frame = ttk.Frame(optimal_times_frame)
        optimal_hours_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(optimal_hours_frame, text="Top Performing Hours (Avg Engagement):").pack(anchor="w")
        self.optimal_hours_text = tk.Text(optimal_hours_frame, height=4, wrap="word", state="disabled") # Removed bg
        self.optimal_hours_text.pack(fill="x", expand=True)

        # Optimal Days
        optimal_days_frame = ttk.Frame(optimal_times_frame)
        optimal_days_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(optimal_days_frame, text="Top Performing Days (Avg Engagement):").pack(anchor="w")
        self.optimal_days_text = tk.Text(optimal_days_frame, height=4, wrap="word", state="disabled") # Removed bg
        self.optimal_days_text.pack(fill="x", expand=True)


        # --- LANGUAGE PREFERENCE INSIGHTS SECTION ---
        lang_pref_frame = ttk.LabelFrame(self.scrollable_frame, text="Language Preference")
        lang_pref_frame.pack(fill="x", padx=10, pady=10)

        # self.analyze_languages_button = ttk.Button(lang_pref_frame, text="Analyze Language Performance", command=self._analyze_language_preference_async)
        # self.analyze_languages_button.pack(pady=(5, 10)) # Removed individual button

        self.best_languages_text = tk.Text(lang_pref_frame, height=3, wrap="word", state="disabled") # Removed bg
        self.best_languages_text.pack(fill="x", expand=True)

        debug_gui_print("MLDashboardTab _create_widgets finished.")

    def update_output_text_content(self, text):
        # This is a local update for the dashboard's log, not the main GUI's
        self.output_text.config(state="normal")
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END) # Scroll to the end
        self.output_text.config(state="disabled")

    def _clear_all_insight_texts(self):
        # Clear all text areas before new analysis
        for text_widget_name in [attr for attr in dir(self) if attr.endswith('_text') and isinstance(getattr(self, attr), tk.Text)]:
            text_widget = getattr(self, text_widget_name)
            text_widget.config(state="normal")
            text_widget.delete(1.0, tk.END)
            text_widget.config(state="disabled")
        self.update_output_text_content("") # Clear log too

    def _disable_all_insight_buttons(self):
        self.run_all_insights_button.config(state=tk.DISABLED)

    def _enable_all_insight_buttons(self):
        self.run_all_insights_button.config(state=tk.NORMAL)


    # --- Unified Async Function to Run All Insights ---
    def _run_all_insights_async(self):
        if self.analysis_running:
            self.set_status("Analysis already in progress.", "orange")
            return

        self._clear_all_insight_texts()
        self.set_status("Starting all ML insights analyses...", "blue")
        self._disable_all_insight_buttons()
        self.analysis_running = True

        threading.Thread(target=self._run_all_insights_thread).start()
        debug_gui_print("Run all insights thread started.")

    def _run_all_insights_thread(self):
        debug_gui_print("Run all insights thread started (internal function).")
        overall_status_message = "All ML insights analyses complete."
        overall_status_color = "green"
        try:
            # 1. Topic Performance
            self.master.after(0, self.update_output_text_content, "\n--- Analyzing Topic Performance ---\n")
            high_topics, low_topics, msg = ml_predictor.get_topic_performance_insights()
            self.master.after(0, self._display_topic_insights, high_topics, low_topics)
            self.master.after(0, self.update_output_text_content, f"Topic Analysis Result: {msg}\n")
            if "No historical data" in msg or "Insufficient data" in msg:
                overall_status_color = "orange"

            # 2. Text Prompt Performance
            self.master.after(0, self.update_output_text_content, "\n--- Analyzing Text Prompt Performance ---\n")
            high_prompts, low_prompts, msg = ml_predictor.get_text_prompt_performance_insights()
            self.master.after(0, self._display_text_prompt_insights, high_prompts, low_prompts)
            self.master.after(0, self.update_output_text_content, f"Text Prompt Analysis Result: {msg}\n")
            if "No historical data" in msg or "Insufficient data" in msg:
                overall_status_color = "orange"

            # 3. Image Prompt Performance
            self.master.after(0, self.update_output_text_content, "\n--- Analyzing Image Prompt Performance ---\n")
            high_image_prompts, low_image_prompts, msg = ml_predictor.get_image_prompt_performance_insights()
            self.master.after(0, self._display_image_prompt_insights, high_image_prompts, low_image_prompts)
            self.master.after(0, self.update_output_text_content, f"Image Prompt Analysis Result: {msg}\n")
            if "No historical data" in msg or "Insufficient data" in msg:
                overall_status_color = "orange"

            # 4. Generator Parameter Performance
            self.master.after(0, self.update_output_text_content, "\n--- Analyzing Generator Parameters ---\n")
            best_providers, best_models, best_temperatures, msg = ml_predictor.get_generator_parameter_insights()
            self.master.after(0, self._display_generator_parameter_insights, best_providers, best_models, best_temperatures)
            self.master.after(0, self.update_output_text_content, f"Generator Parameter Analysis Result: {msg}\n")
            if "No historical data" in msg or "Insufficient data" in msg:
                overall_status_color = "orange"

            # 5. Optimal Posting Times
            self.master.after(0, self.update_output_text_content, "\n--- Analyzing Optimal Posting Times ---\n")
            optimal_hours, optimal_days, msg = ml_predictor.get_optimal_posting_times_insights()
            self.master.after(0, self._display_optimal_posting_times_insights, optimal_hours, optimal_days)
            self.master.after(0, self.update_output_text_content, f"Optimal Posting Times Analysis Result: {msg}\n")
            if "No historical data" in msg or "Insufficient data" in msg:
                overall_status_color = "orange"

            # 6. Language Preference
            self.master.after(0, self.update_output_text_content, "\n--- Analyzing Language Preference ---\n")
            best_languages, msg = ml_predictor.get_language_preference_insights()
            self.master.after(0, self._display_language_preference_insights, best_languages)
            self.master.after(0, self.update_output_text_content, f"Language Preference Analysis Result: {msg}\n")
            if "No historical data" in msg or "Insufficient data" in msg:
                overall_status_color = "orange"

        except Exception as e:
            overall_status_message = f"An unexpected error occurred during analysis: {e}"
            overall_status_color = "red"
            self.master.after(0, self.update_output_text_content, f"\nCRITICAL ERROR: {e}\n")
            debug_gui_print(f"CRITICAL ERROR in _run_all_insights_thread: {e}")
        finally:
            self.master.after(0, self.set_status, overall_status_message, overall_status_color)
            self.master.after(0, self._enable_all_insight_buttons)
            self.analysis_running = False
        debug_gui_print("Run all insights thread finished.")


    # --- Individual Display Helper Functions (moved from other tabs) ---

    def _display_topic_insights(self, high_topics, low_topics):
        self.high_topics_text.config(state="normal")
        self.high_topics_text.delete(1.0, tk.END)
        if high_topics:
            for topic, score in high_topics:
                self.high_topics_text.insert(tk.END, f"- {topic}: Avg Engagement {score:.2f}\n")
        else:
            self.high_topics_text.insert(tk.END, "No high-performing topics identified yet.\n")
        self.high_topics_text.config(state="disabled")

        self.low_topics_text.config(state="normal")
        self.low_topics_text.delete(1.0, tk.END)
        if low_topics:
            for topic, score in low_topics:
                self.low_topics_text.insert(tk.END, f"- {topic}: Avg Engagement {score:.2f}\n")
        else:
            self.low_topics_text.insert(tk.END, "No low-performing topics identified yet.\n")
        self.low_topics_text.config(state="disabled")
        debug_gui_print("Topic insights displayed.")

    def _display_text_prompt_insights(self, high_phrases, low_phrases):
        self.high_prompts_text.config(state="normal")
        self.high_prompts_text.delete(1.0, tk.END)
        if high_phrases:
            for phrase, score in high_phrases:
                self.high_prompts_text.insert(tk.END, f"- {phrase}: Score {score:.4f}\n")
        else:
            self.high_prompts_text.insert(tk.END, "No high-performing prompt phrases identified yet.\n")
        self.high_prompts_text.config(state="disabled")

        self.low_prompts_text.config(state="normal")
        self.low_prompts_text.delete(1.0, tk.END)
        if low_phrases:
            for phrase, score in low_phrases:
                self.low_prompts_text.insert(tk.END, f"- {phrase}: Score {score:.4f}\n")
        else:
            self.low_prompts_text.insert(tk.END, "No low-performing prompt phrases identified yet.\n")
        self.low_prompts_text.config(state="disabled")
        debug_gui_print("Text prompt insights displayed.")

    def _display_image_prompt_insights(self, high_phrases, low_phrases):
        self.high_image_prompts_text.config(state="normal")
        self.high_image_prompts_text.delete(1.0, tk.END)
        if high_phrases:
            for phrase, score in high_phrases:
                self.high_image_prompts_text.insert(tk.END, f"- {phrase}: Score {score:.4f}\n")
        else:
            self.high_image_prompts_text.insert(tk.END, "No high-performing image prompt phrases identified yet.\n")
        self.high_image_prompts_text.config(state="disabled")

        self.low_image_prompts_text.config(state="normal")
        self.low_image_prompts_text.delete(1.0, tk.END)
        if low_phrases:
            for phrase, score in low_phrases:
                self.low_image_prompts_text.insert(tk.END, f"- {phrase}: Score {score:.4f}\n")
        else:
            self.low_image_prompts_text.insert(tk.END, "No low-performing image prompt phrases identified yet.\n")
        self.low_image_prompts_text.config(state="disabled")
        debug_gui_print("Image prompt insights displayed.")

    def _display_generator_parameter_insights(self, best_providers, best_models, best_temperatures):
        # Display Best Providers
        self.best_providers_text.config(state="normal")
        self.best_providers_text.delete(1.0, tk.END)
        if best_providers:
            for provider, score in best_providers:
                self.best_providers_text.insert(tk.END, f"- {provider}: Avg Engagement {score:.2f}\n")
        else:
            self.best_providers_text.insert(tk.END, "No provider insights identified yet.\n")
        self.best_providers_text.config(state="disabled")

        # Display Best Models
        self.best_models_text.config(state="normal")
        self.best_models_text.delete(1.0, tk.END)
        if best_models:
            for model, score in best_models:
                self.best_models_text.insert(tk.END, f"- {model}: Avg Engagement {score:.2f}\n")
        else:
            self.best_models_text.insert(tk.END, "No model insights identified yet.\n")
        self.best_models_text.config(state="disabled")

        # Display Best Temperatures
        self.best_temperatures_text.config(state="normal")
        self.best_temperatures_text.delete(1.0, tk.END)
        if best_temperatures:
            for temp, score in best_temperatures:
                self.best_temperatures_text.insert(tk.END, f"- Temp {temp:.1f}: Avg Engagement {score:.2f}\n")
        else:
            self.best_temperatures_text.insert(tk.END, "No temperature insights identified yet.\n")
        self.best_temperatures_text.config(state="disabled")
        debug_gui_print("Generator parameter insights displayed.")

    def _display_optimal_posting_times_insights(self, optimal_hours, optimal_days):
        self.optimal_hours_text.config(state="normal")
        self.optimal_hours_text.delete(1.0, tk.END)
        if optimal_hours:
            for hour_str, score in optimal_hours[:5]:
                self.optimal_hours_text.insert(tk.END, f"- {hour_str}: Avg Engagement {score:.2f}\n")
        else:
            self.optimal_hours_text.insert(tk.END, "No optimal hours identified yet.\n")
        self.optimal_hours_text.config(state="disabled")

        self.optimal_days_text.config(state="normal")
        self.optimal_days_text.delete(1.0, tk.END)
        if optimal_days:
            for day_name, score in optimal_days[:5]:
                self.optimal_days_text.insert(tk.END, f"- {day_name}: Avg Engagement {score:.2f}\n")
        else:
            self.optimal_days_text.insert(tk.END, "No optimal days identified yet.\n")
        self.optimal_days_text.config(state="disabled")
        debug_gui_print("Optimal posting times insights displayed.")

    def _display_language_preference_insights(self, best_languages):
        self.best_languages_text.config(state="normal")
        self.best_languages_text.delete(1.0, tk.END)
        if best_languages:
            for lang, score in best_languages:
                self.best_languages_text.insert(tk.END, f"- {lang}: Avg Engagement {score:.2f}\n")
        else:
            self.best_languages_text.insert(tk.END, "No language preference insights identified yet.\n")
        self.best_languages_text.config(state="disabled")
        debug_gui_print("Language preference insights displayed.")

    def on_tab_focus(self):
        # Optionally, you can trigger _run_all_insights_async here if you want
        # insights to load automatically when the tab is focused.
        # self.master.after(100, self._run_all_insights_async)
        debug_gui_print("MLDashboardTab focused. Ready for analysis.")