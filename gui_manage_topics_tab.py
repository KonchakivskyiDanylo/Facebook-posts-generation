# D:\Facebook_Posts_generation\gui_manage_topics_tab.py

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import json
import threading
import sys
import re

# Assuming gui_common_dialogs is in the same directory
from gui_common_dialogs import MultilineTextDialog

# Assuming these are in the same directory and you have a database_manager.py
import database_manager

# Import generativeai for Gemini API (you'll need to install it: pip install google-generativeai)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    print("WARNING: google-generativeai not found. Gemini features will be disabled.")
    GEMINI_AVAILABLE = False


# --- Debugging setup ---
DEBUG_GUI_MODE = True

def debug_gui_print(message):
    if DEBUG_GUI_MODE:
        print(f"[DEBUG - GUI - ManageTopics]: {message}")

class ManageTopicsTab(ttk.Frame):
    # Modified __init__ to accept save_config_callback
    def __init__(self, parent, facebook_pages_ref, set_status_callback, save_config_callback):
        super().__init__(parent)
        debug_gui_print("ManageTopicsTab.__init__ started.")

        self.facebook_pages = facebook_pages_ref
        self.set_status = set_status_callback
        self.save_config_callback = save_config_callback

        self.topic_page_selection_var = tk.StringVar()
        self.current_selected_page_index_topic_tab = -1

        self._is_programmatic_update = False

        self._create_widgets()
        debug_gui_print("ManageTopicsTab widgets created.")
        debug_gui_print("ManageTopicsTab.__init__ finished.")

        # Configure Gemini API if available
        if GEMINI_AVAILABLE and os.getenv("GEMINI_API_KEY"):
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            debug_gui_print("Gemini API configured using environment variable.")
        elif GEMINI_AVAILABLE:
            debug_gui_print("WARNING: GEMINI_API_KEY environment variable not set. Gemini features may not work.")
        else:
            debug_gui_print("INFO: google-generativeai not installed. Gemini features are disabled.")


    def _create_widgets(self):
        debug_gui_print("_create_widgets (ManageTopicsTab) called.")

        page_select_frame = ttk.LabelFrame(self, text="Select Page for Topic Management")
        page_select_frame.pack(pady=10, padx=10, fill="x")

        ttk.Label(page_select_frame, text="Select Page:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.topic_page_selection_combobox = ttk.Combobox(page_select_frame, textvariable=self.topic_page_selection_var, values=[], state="readonly")
        self.topic_page_selection_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.topic_page_selection_combobox.bind("<<ComboboxSelected>>", self._on_topic_page_selected)
        page_select_frame.columnconfigure(1, weight=1)

        topic_list_frame = ttk.LabelFrame(self, text="Topics for Selected Page")
        topic_list_frame.pack(pady=10, padx=10, fill="both", expand=True)
        topic_list_frame.columnconfigure(0, weight=1)
        topic_list_frame.rowconfigure(0, weight=1)

        self.topics_listbox = tk.Listbox(topic_list_frame, height=12, selectmode=tk.EXTENDED)
        self.topics_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.topics_listbox.bind("<<ListboxSelect>>", self._on_topic_select)

        topics_scrollbar = ttk.Scrollbar(topic_list_frame, orient="vertical", command=self.topics_listbox.yview)
        topics_scrollbar.grid(row=0, column=1, sticky="ns")
        self.topics_listbox.config(yscrollcommand=topics_scrollbar.set)

        topic_buttons_frame = ttk.Frame(topic_list_frame)
        topic_buttons_frame.grid(row=1, column=0, columnspan=2, pady=5)
        self.add_topic_button = ttk.Button(topic_buttons_frame, text="Add New Topic", command=self._add_topic_gui)
        self.add_topics_from_list_button = ttk.Button(topic_buttons_frame, text="Paste List of Topics", command=self._add_topics_from_list_gui)
        self.add_topics_from_list_button.pack(side="left", padx=5)
        self.add_topic_button.pack(side="left", padx=5)
        self.rename_topic_button = ttk.Button(topic_buttons_frame, text="Rename Selected Topic", command=self._rename_topic_gui)
        self.rename_topic_button.pack(side="left", padx=5)
        self.remove_topic_button = ttk.Button(topic_buttons_frame, text="Remove Selected Topic", command=self._remove_topic_gui)
        self.remove_topic_button.pack(side="left", padx=5)
        ttk.Button(topic_buttons_frame, text="Select All", command=self._select_all_topics).pack(side="left", padx=5)
        ttk.Button(topic_buttons_frame, text="Deselect All", command=self._deselect_all_topics).pack(side="left", padx=5)


        prompts_frame = ttk.LabelFrame(self, text="Edit Prompts for Selected Topic(s)")
        prompts_frame.pack(pady=10, padx=10, fill="x")
        prompts_frame.columnconfigure(1, weight=1)

        ttk.Label(prompts_frame, text="English Image Prompt:").grid(row=0, column=0, sticky="nw", padx=5, pady=2)
        self.english_image_prompt_text = tk.Text(prompts_frame, wrap="word", height=4, width=50)
        self.english_image_prompt_text.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.english_image_prompt_scrollbar = ttk.Scrollbar(prompts_frame, orient="vertical", command=self.english_image_prompt_text.yview)
        self.english_image_prompt_scrollbar.grid(row=0, column=2, sticky="ns")
        self.english_image_prompt_text.config(yscrollcommand=self.english_image_prompt_scrollbar.set)

        ttk.Label(prompts_frame, text="Arabic Post Prompt:").grid(row=1, column=0, sticky="nw", padx=5, pady=2)
        self.arabic_post_prompt_text = tk.Text(prompts_frame, wrap="word", height=4, width=50)
        self.arabic_post_prompt_text.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.arabic_post_prompt_scrollbar = ttk.Scrollbar(prompts_frame, orient="vertical", command=self.arabic_post_prompt_text.yview)
        self.arabic_post_prompt_scrollbar.grid(row=1, column=2, sticky="ns")
        self.arabic_post_prompt_text.config(yscrollcommand=self.arabic_post_prompt_scrollbar.set)

        ttk.Label(prompts_frame, text="Arabic Image Prompt:").grid(row=2, column=0, sticky="nw", padx=5, pady=2)
        self.arabic_image_prompt_text = tk.Text(prompts_frame, wrap="word", height=4, width=50)
        self.arabic_image_prompt_text.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        self.arabic_image_prompt_scrollbar = ttk.Scrollbar(prompts_frame, orient="vertical", command=self.arabic_image_prompt_text.yview)
        self.arabic_image_prompt_scrollbar.grid(row=2, column=2, sticky="ns")
        self.arabic_image_prompt_text.config(yscrollcommand=self.arabic_image_prompt_scrollbar.set)

        self.generate_prompts_button = ttk.Button(prompts_frame, text="Generate Prompts with Gemini", command=self._generate_prompts_with_gemini)
        self.generate_prompts_button.grid(row=3, column=0, pady=5, sticky="w")
        if not GEMINI_AVAILABLE or not os.getenv("GEMINI_API_KEY"):
            self.generate_prompts_button.config(state=tk.DISABLED)
            self.set_status("Gemini API not configured or key missing. Generate Prompts button disabled.", "red")

        self.update_single_topic_button = ttk.Button(prompts_frame, text="Update Selected Topic Prompts", command=self._update_topic_prompts)
        self.update_single_topic_button.grid(row=3, column=1, pady=5, sticky="e")

        self._clear_manage_topics_ui()
        debug_gui_print("_create_widgets (ManageTopicsTab) finished.")

    def _on_topic_page_selected(self, event=None):
        debug_gui_print(f"--- _on_topic_page_selected (ManageTopicsTab) called. Selected: {self.topic_page_selection_var.get()}")

        selected_page_name = self.topic_page_selection_var.get()
        found_index = -1
        for i, page in enumerate(self.facebook_pages):
            if page["page_name"] == selected_page_name:
                found_index = i
                break

        if found_index != -1:
            if found_index != self.current_selected_page_index_topic_tab:
                debug_gui_print(f"  Page changed from index {self.current_selected_page_index_topic_tab} to {found_index}. Updating topics.")
                self.current_selected_page_index_topic_tab = found_index
                self._update_topics_listbox_for_selected_page(found_index)
            elif self._is_programmatic_update:
                debug_gui_print(f"  Same page '{selected_page_name}' re-selected programmatically. Forcing update.")
                self._update_topics_listbox_for_selected_page(found_index)
            else:
                debug_gui_print(f"  Page {selected_page_name} already selected and not a programmatic re-load. Skipping redundant load.")
        else:
            debug_gui_print("  Selected page not found or no selection. Clearing topics UI.")
            self.current_selected_page_index_topic_tab = -1
            self._clear_manage_topics_ui()
        debug_gui_print("--- _on_topic_page_selected (ManageTopicsTab) finished.")

    def _update_topics_listbox_for_selected_page(self, page_index):
        debug_gui_print(f"_update_topics_listbox_for_selected_page (ManageTopicsTab) called for index: {page_index}.")

        self.topics_listbox.delete(0, tk.END)

        if page_index != -1 and page_index < len(self.facebook_pages):
            page_data = self.facebook_pages[page_index]
            topics = page_data.get('topics', [])
            for topic in topics:
                self.topics_listbox.insert(tk.END, topic['name'])

            self.topics_listbox.config(state=tk.NORMAL)
            self.add_topic_button.config(state=tk.NORMAL)
            self.add_topics_from_list_button.config(state=tk.NORMAL)

            self.rename_topic_button.config(state=tk.DISABLED)
            self.remove_topic_button.config(state=tk.DISABLED)
            self.generate_prompts_button.config(state=tk.NORMAL if (GEMINI_AVAILABLE and os.getenv("GEMINI_API_KEY")) else tk.DISABLED)
            self.update_single_topic_button.config(state=tk.DISABLED)
            
            debug_gui_print(f"  Topics listbox populated with {len(topics)} topics. Buttons updated.")

            self._is_programmatic_update = True
            try:
                if topics:
                    self.topics_listbox.selection_set(0)
                    self.topics_listbox.activate(0)
                    self._load_topic_prompts_into_ui(topics[0])
                    self._on_topic_select()
                else:
                    self._load_topic_prompts_into_ui(None)
                    self._on_topic_select()
            finally:
                self._is_programmatic_update = False

        else:
            self.topics_listbox.config(state=tk.DISABLED)
            self.add_topic_button.config(state=tk.DISABLED)
            self.add_topics_from_list_button.config(state=tk.DISABLED)
            self.rename_topic_button.config(state=tk.DISABLED)
            self.remove_topic_button.config(state=tk.DISABLED)
            self.generate_prompts_button.config(state=tk.DISABLED)
            self.update_single_topic_button.config(state=tk.DISABLED)
            debug_gui_print("  Topics listbox disabled (no page selected or invalid index).")
            self._load_topic_prompts_into_ui(None)
            self._on_topic_select()

        debug_gui_print("_update_topics_listbox_for_selected_page (ManageTopicsTab) finished.")

    def _on_topic_select(self, event=None):
        debug_gui_print(f"--- _on_topic_select (ManageTopicsTab) called. Event: {event}")
        
        selected_indices = self.topics_listbox.curselection()

        skip_prompt_load = self._is_programmatic_update and event is None

        if not selected_indices:
            debug_gui_print("  No topic(s) selected.")
            if not skip_prompt_load:
                self._load_topic_prompts_into_ui(None)
            self.rename_topic_button.config(state=tk.DISABLED)
            self.remove_topic_button.config(state=tk.DISABLED)
            self.generate_prompts_button.config(state=tk.DISABLED if (not GEMINI_AVAILABLE or not os.getenv("GEMINI_API_KEY")) else tk.DISABLED)
            self.update_single_topic_button.config(state=tk.DISABLED)
        elif len(selected_indices) == 1:
            debug_gui_print("  Single topic selected.")
            current_topic_index = selected_indices[0]
            if self.current_selected_page_index_topic_tab == -1:
                 debug_gui_print("  No page selected, cannot load topic prompts.")
                 if not skip_prompt_load:
                    self._load_topic_prompts_into_ui(None)
                 self.rename_topic_button.config(state=tk.DISABLED)
                 self.remove_topic_button.config(state=tk.DISABLED)
                 self.generate_prompts_button.config(state=tk.DISABLED)
                 self.update_single_topic_button.config(state=tk.DISABLED)
                 return

            page_data = self.facebook_pages[self.current_selected_page_index_topic_tab]
            topics = page_data.get('topics', [])
            if current_topic_index < len(topics):
                selected_topic_obj = topics[current_topic_index]
                if not skip_prompt_load:
                    self._load_topic_prompts_into_ui(selected_topic_obj)
            else:
                debug_gui_print(f"  ERROR: Single selected index {current_topic_index} out of bounds.")
                if not skip_prompt_load:
                    self._load_topic_prompts_into_ui(None)

            self.rename_topic_button.config(state=tk.NORMAL)
            self.remove_topic_button.config(state=tk.NORMAL)
            self.generate_prompts_button.config(state=tk.NORMAL if (GEMINI_AVAILABLE and os.getenv("GEMINI_API_KEY")) else tk.DISABLED)
            self.update_single_topic_button.config(state=tk.NORMAL)
        else: # Multiple topics selected
            debug_gui_print(f"  Multiple topics selected ({len(selected_indices)}).")
            if not skip_prompt_load:
                self._load_topic_prompts_into_ui(None, message="-- Multiple topics selected --")
            self.rename_topic_button.config(state=tk.DISABLED)
            self.remove_topic_button.config(state=tk.NORMAL)
            self.generate_prompts_button.config(state=tk.NORMAL if (GEMINI_AVAILABLE and os.getenv("GEMINI_API_KEY")) else tk.DISABLED)
            self.update_single_topic_button.config(state=tk.DISABLED)

        debug_gui_print("--- _on_topic_select (ManageTopicsTab) finished.")

    def _select_all_topics(self):
        debug_gui_print("_select_all_topics called.")
        if self.topics_listbox.winfo_exists():
            self._is_programmatic_update = True
            try:
                self.topics_listbox.selection_set(0, tk.END)
                self._on_topic_select()
            finally:
                self._is_programmatic_update = False
        debug_gui_print("All topics selected.")

    def _deselect_all_topics(self):
        debug_gui_print("_deselect_all_topics called.")
        if self.topics_listbox.winfo_exists():
            self._is_programmatic_update = True
            try:
                self.topics_listbox.selection_clear(0, tk.END)
                self._on_topic_select()
            finally:
                self._is_programmatic_update = False
        debug_gui_print("All topics deselected.")


    def _load_topic_prompts_into_ui(self, topic_obj, message=None):
        debug_gui_print(f"_load_topic_prompts_into_ui (ManageTopicsTab) called with topic_obj: {'None' if topic_obj is None else topic_obj.get('name')}, message: {message}.")

        widgets = [self.english_image_prompt_text, self.arabic_post_prompt_text, self.arabic_image_prompt_text]

        for widget in widgets:
            widget.config(state=tk.NORMAL)
            widget.delete("1.0", tk.END)
            self.master.update_idletasks()

        if topic_obj is None:
            for widget in widgets:
                widget.config(state=tk.DISABLED)
                widget.config(bg="lightgray", fg="darkgray")
                if message:
                    widget.insert(tk.END, message)
            debug_gui_print("  All topic prompt fields set to DISABLED.")
        else:
            self.english_image_prompt_text.insert(tk.END, topic_obj.get("english_image_prompt", ""))
            self.arabic_post_prompt_text.insert(tk.END, topic_obj.get("arabic_post_prompt", ""))
            self.arabic_image_prompt_text.insert(tk.END, topic_obj.get("arabic_image_prompt", ""))

            for widget in widgets:
                widget.config(state=tk.NORMAL)
                widget.config(bg="white", fg="black")

            self.master.update_idletasks()
            debug_gui_print("  All topic prompt fields populated and set to NORMAL.")

            if self.english_image_prompt_text.winfo_exists():
                self.english_image_prompt_text.focus_set()

        debug_gui_print("_load_topic_prompts_into_ui (ManageTopicsTab) finished.")

    def _clear_manage_topics_ui(self):
        debug_gui_print("_clear_manage_topics_ui (ManageTopicsTab) called.")

        self.topics_listbox.selection_clear(0, tk.END)
        self.topics_listbox.delete(0, tk.END)
        self.topics_listbox.config(state=tk.DISABLED)

        self.add_topic_button.config(state=tk.DISABLED)
        self.add_topics_from_list_button.config(state=tk.DISABLED)
        self.rename_topic_button.config(state=tk.DISABLED)
        self.remove_topic_button.config(state=tk.DISABLED)
        self.generate_prompts_button.config(state=tk.DISABLED)
        self.update_single_topic_button.config(state=tk.DISABLED)
        debug_gui_print(f"Manage Topic buttons disabled.")

        self._load_topic_prompts_into_ui(None)
        debug_gui_print("Manage Topics UI cleared and disabled.")

    def _update_topic_prompts(self):
        debug_gui_print("_update_topic_prompts (ManageTopicsTab) called.")
        current_page_index = self.current_selected_page_index_topic_tab
        selected_indices = self.topics_listbox.curselection()

        if current_page_index == -1 or current_page_index >= len(self.facebook_pages):
            messagebox.showwarning("Warning", "No page selected for topic prompt update.")
            debug_gui_print("No page selected for topic prompt update.")
            return

        if len(selected_indices) != 1:
            messagebox.showwarning("Warning", "Please select exactly ONE topic to update its prompts.")
            debug_gui_print("Incorrect number of topics selected for single update.")
            return

        current_topic_index = selected_indices[0]

        page_data = self.facebook_pages[current_page_index]
        topics = page_data.get("topics", [])

        if current_topic_index >= len(topics):
            messagebox.showerror("Error", "Selected topic index is out of bounds. Please re-select the page and topic.")
            debug_gui_print(f"ERROR: Selected topic index {current_topic_index} out of bounds for page topics ({len(topics)}).")
            self._load_topic_prompts_into_ui(None)
            return

        topic_obj_to_update = topics[current_topic_index]

        new_en_img_prompt = self.english_image_prompt_text.get("1.0", tk.END).strip()
        new_ar_post_prompt = self.arabic_post_prompt_text.get("1.0", tk.END).strip()
        new_ar_img_prompt = self.arabic_image_prompt_text.get("1.0", tk.END).strip()

        topic_obj_to_update["english_image_prompt"] = new_en_img_prompt
        topic_obj_to_update["arabic_post_prompt"] = new_ar_post_prompt
        topic_obj_to_update["arabic_image_prompt"] = new_ar_img_prompt

        debug_gui_print(f"Prompts updated for topic '{topic_obj_to_update['name']}' in GUI memory.")
        
        self.save_config_callback()
        self.set_status(f"Prompts for '{topic_obj_to_update['name']}' updated and SAVED.", "green")

        self._load_topic_prompts_into_ui(topic_obj_to_update)
        messagebox.showinfo("Success", f"Prompts for topic '{topic_obj_to_update['name']}' updated and saved to file.")
        debug_gui_print("_update_topic_prompts (ManageTopicsTab) finished.")

    def _add_topic_gui(self):
        debug_gui_print("_add_topic_gui (ManageTopicsTab) called.")
        current_page_index = self.current_selected_page_index_topic_tab
        if current_page_index == -1 or current_page_index >= len(self.facebook_pages):
            messagebox.showwarning("Warning", "Please select a page in the 'Select Page for Topic Management' dropdown first.")
            debug_gui_print("No page selected for adding topic.")
            return

        page_data = self.facebook_pages[current_page_index]
        existing_topic_names = {t["name"] for t in page_data.get("topics", [])}
        debug_gui_print(f"Current topics for page '{page_data['page_name']}': {existing_topic_names}")

        new_topic_name = simpledialog.askstring("Add New Topic", "Enter new topic name for this page:")

        if new_topic_name:
            new_topic_name = new_topic_name.strip()
            if not new_topic_name:
                messagebox.showwarning("Input Error", "Topic name cannot be empty.")
                debug_gui_print("Empty topic name entered.")
                return

            if new_topic_name in existing_topic_names:
                messagebox.showwarning("Warning", f"Topic '{new_topic_name}' is already associated with this page.")
                debug_gui_print(f"Attempted to add existing topic '{new_topic_name}' to page.")
                return

            page_data.setdefault("topics", []).append({
                "name": new_topic_name,
                "english_post_prompt": f"Write an engaging Facebook post about '{new_topic_name}' in English. Include relevant hashtags. Focus on automotive parts or maintenance.",
                "english_image_prompt": "",
                "arabic_post_prompt": "",
                "arabic_image_prompt": ""
            })
            debug_gui_print(f"Topic '{new_topic_name}' added to page '{page_data['page_name']}'. New topics list: {[t['name'] for t in page_data['topics']]}")

            self._update_topics_listbox_for_selected_page(current_page_index)
            new_topic_idx = len(page_data["topics"]) - 1
            if new_topic_idx >= 0:
                self._is_programmatic_update = True
                try:
                    self.topics_listbox.selection_clear(0, tk.END)
                    self.topics_listbox.selection_set(new_topic_idx)
                    self.topics_listbox.activate(new_topic_idx)
                    self._on_topic_select()
                finally:
                    self._is_programmatic_update = False

            self.save_config_callback()
            messagebox.showinfo("Success", f"Topic '{new_topic_name}' added to page '{page_data['page_name']}' and saved. Please fill in its prompts below, then click 'Update Topic Prompts'.")
            self.set_status(f"Topic '{new_topic_name}' added to page and saved. Fill prompts and update.", "blue")
        else:
            debug_gui_print("Add topic to page cancelled or empty input.")
            self.set_status("Add topic to page cancelled or empty.", "gray")

    def _add_topics_from_list_gui(self):
        debug_gui_print("_add_topics_from_list_gui (ManageTopicsTab) called.")
        current_page_index = self.current_selected_page_index_topic_tab
        if current_page_index == -1 or current_page_index >= len(self.facebook_pages):
            messagebox.showwarning("Warning", "Please select a page in the 'Select Page for Topic Management' dropdown first.")
            debug_gui_print("No page selected for adding topic list.")
            return

        page_data = self.facebook_pages[current_page_index]
        existing_topic_names = {t["name"].lower() for t in page_data.get("topics", [])}

        dialog = MultilineTextDialog(
            self.master,
            title="Paste List of Topics",
            prompt="Paste your list of topics below, one topic per line:",
            initialvalue=""
        )
        list_input = dialog.result

        if list_input:
            new_topics_raw = list_input.strip().split('\n')
            added_count = 0
            skipped_count = 0
            skipped_topics = []

            for topic_line in new_topics_raw:
                new_topic_name = topic_line.strip()
                if not new_topic_name:
                    continue

                if new_topic_name.lower() in existing_topic_names:
                    skipped_count += 1
                    skipped_topics.append(new_topic_name)
                else:
                    page_data.setdefault("topics", []).append({
                        "name": new_topic_name,
                        "english_post_prompt": f"Write an engaging Facebook post about '{new_topic_name}' in English. Include relevant hashtags. Focus on automotive parts or maintenance.",
                        "english_image_prompt": "",
                        "arabic_post_prompt": "",
                        "arabic_image_prompt": ""
                    })
                    existing_topic_names.add(new_topic_name.lower())
                    added_count += 1

            if added_count > 0:
                self._update_topics_listbox_for_selected_page(current_page_index)
                self.save_config_callback()
                messagebox.showinfo("Topics Added", f"Successfully added {added_count} new topics to page '{page_data['page_name']}' and saved.\n\nRemember to fill in prompts for new topics and click 'Update Selected Topic Prompts'.")
                self.set_status(f"{added_count} topics added and saved. Fill prompts and update.", "blue")

            if skipped_count > 0:
                messagebox.showwarning("Topics Skipped", f"{skipped_count} topics were skipped because they already exist for this page:\n" + "\n".join(skipped_topics))
                debug_gui_print(f"Skipped topics: {skipped_topics}")

            if added_count == 0 and skipped_count == 0:
                messagebox.showinfo("No Topics Added", "No valid topics were entered or all were empty lines.")
        else:
            debug_gui_print("Paste list of topics cancelled or empty input.")
            self.set_status("Paste list of topics cancelled or empty.", "gray")

    def _rename_topic_gui(self):
        debug_gui_print("_rename_topic_gui (ManageTopicsTab) called.")
        current_page_index = self.current_selected_page_index_topic_tab
        selected_indices = self.topics_listbox.curselection()

        if current_page_index == -1 or current_page_index >= len(self.facebook_pages):
            messagebox.showwarning("Warning", "Please select a page first.")
            debug_gui_print("No page selected for renaming topic.")
            return
        if len(selected_indices) != 1:
            messagebox.showwarning("Warning", "Please select exactly ONE topic to rename.")
            debug_gui_print("Incorrect number of topics selected for rename.")
            return

        current_topic_index = selected_indices[0]

        page_data = self.facebook_pages[current_page_index]
        topics = page_data.get("topics", [])

        if current_topic_index >= len(topics):
            messagebox.showerror("Error", "Selected topic index is out of bounds. Please re-select the page and topic.")
            debug_gui_print(f"ERROR: Selected topic index {current_topic_index} out of bounds for page topics ({len(topics)}).")
            self._load_topic_prompts_into_ui(None)
            return

        old_topic_name = topics[current_topic_index]["name"]
        new_topic_name = simpledialog.askstring("Rename Topic", f"Rename '{old_topic_name}' to:", initialvalue=old_topic_name)

        if new_topic_name and new_topic_name.strip() != old_topic_name:
            new_topic_name = new_topic_name.strip()
            if not new_topic_name:
                messagebox.showwarning("Input Error", "Topic name cannot be empty.")
                debug_gui_print("Empty new topic name entered.")
                return

            existing_topic_names = {t["name"] for t in topics if t["name"] != old_topic_name}
            if new_topic_name in existing_topic_names:
                messagebox.showwarning("Warning", f"Topic '{new_topic_name}' already exists for this page.")
                debug_gui_print(f"Attempted to rename topic to existing name '{new_topic_name}'.")
                return

            topics[current_topic_index]["name"] = new_topic_name
            debug_gui_print(f"Topic '{old_topic_name}' renamed to '{new_topic_name}'.")

            self._update_topics_listbox_for_selected_page(current_page_index)
            self._is_programmatic_update = True
            try:
                self.topics_listbox.selection_clear(0, tk.END)
                self.topics_listbox.selection_set(current_topic_index)
                self.topics_listbox.activate(current_topic_index)
                self._on_topic_select()
            finally:
                self._is_programmatic_update = False

            self.save_config_callback()
            messagebox.showinfo("Success", f"Topic renamed to '{new_topic_name}' and saved.")
            self.set_status(f"Topic renamed to '{new_topic_name}' and saved.", "blue")
        else:
            debug_gui_print("Rename topic cancelled or new name is the same.")
            self.set_status("Rename topic cancelled.", "gray")

    def _remove_topic_gui(self):
        debug_gui_print("_remove_topic_gui (ManageTopicsTab) called.")
        current_page_index = self.current_selected_page_index_topic_tab
        selected_indices = self.topics_listbox.curselection()

        if current_page_index == -1 or current_page_index >= len(self.facebook_pages):
            messagebox.showwarning("Warning", "Please select a page first.")
            debug_gui_print("No page selected for removing topic.")
            return
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select one or more topics to remove.")
            debug_gui_print("No topics selected for removal.")
            return

        confirm_message = f"Are you sure you want to remove the selected topic(s)? This cannot be undone."
        if messagebox.askyesno("Confirm Remove Topic(s)", confirm_message):
            page_data = self.facebook_pages[current_page_index]
            topics = page_data.get("topics", [])
            
            removed_count = 0
            for index in sorted(selected_indices, reverse=True):
                if index < len(topics):
                    removed_topic_name = topics.pop(index)["name"]
                    debug_gui_print(f"Removed topic '{removed_topic_name}' from page '{page_data['page_name']}'.")
                    removed_count += 1
            
            self.save_config_callback()
            self.set_status(f"Removed {removed_count} topic(s) and SAVED.", "green")

            self._update_topics_listbox_for_selected_page(current_page_index)
            self._on_topic_select()
            
            messagebox.showinfo("Success", f"Successfully removed {removed_count} topic(s) and saved.")
        else:
            debug_gui_print("Topic removal cancelled by user.")
            self.set_status("Topic removal cancelled.", "gray")

    def _generate_prompts_with_gemini(self):
        debug_gui_print("_generate_prompts_with_gemini (ManageTopicsTab) called.")

        if not GEMINI_AVAILABLE:
            messagebox.showerror("Gemini Error", "The 'google-generativeai' library is not installed. Please install it using 'pip install google-generativeai'.")
            self.set_status("Gemini library not found.", "red")
            return
        if not os.getenv("GEMINI_API_KEY"):
            messagebox.showerror("Gemini Error", "GEMINI_API_KEY environment variable is not set. Please set it to use Gemini API.")
            self.set_status("Gemini API key missing.", "red")
            return

        selected_indices = self.topics_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select one or more topics to generate prompts for.")
            return

        current_page_index = self.current_selected_page_index_topic_tab
        if current_page_index == -1 or current_page_index >= len(self.facebook_pages):
            messagebox.showwarning("Warning", "No page selected. Please select a page first.")
            return

        page_data = self.facebook_pages[current_page_index]
        topics_for_page = page_data.get("topics", [])
        
        selected_topics_to_process = []
        for index in selected_indices:
            if index < len(topics_for_page):
                selected_topics_to_process.append(topics_for_page[index])

        if not selected_topics_to_process:
            messagebox.showwarning("No Valid Topics", "Selected topics are invalid or out of range. Please re-select.")
            return

        self.set_status("Generating prompts with Gemini...", "blue")
        self.generate_prompts_button.config(state=tk.DISABLED)
        self.master.update_idletasks()

        generation_thread = threading.Thread(target=self._run_gemini_generation_thread, args=(selected_topics_to_process, current_page_index))
        generation_thread.start()
        debug_gui_print("Gemini generation thread started.")

    def _run_gemini_generation_thread(self, topics_to_process, page_index):
        debug_gui_print(f"Starting Gemini generation thread for {len(topics_to_process)} topics.")
        generated_count = 0
        total_topics = len(topics_to_process)
        errors_occurred = False

        try:
            model_name = "gemini-1.5-flash"
            temperature = 0.7

            model = genai.GenerativeModel(model_name=model_name, generation_config={"temperature": temperature})

            for i, topic_obj in enumerate(topics_to_process):
                topic_name = topic_obj["name"]
                self.master.after(0, self.set_status, f"Generating prompts for '{topic_name}' ({i+1}/{total_topics})...", "blue")
                
                try:
                    full_prompt = (
                        f"Generate three distinct pieces of content based on the topic: '{topic_name}'. "
                        f"The content should be related to automotive parts, maintenance, or fleet solutions. "
                        f"Provide them in the following structured JSON format. Ensure all strings are properly escaped. "
                        f"Return ONLY the JSON. Do not include any other text or markdown outside the JSON.\n\n"
                        f"{{\n"
                        f'  "english_image_prompt": "A detailed, descriptive image generation prompt in English for an automotive themed image related to {topic_name}. Be very specific about style, colors, and elements, e.g., '
                        f'\'realistic, close-up, high-resolution, engine bay, metallic components, blue wrench, soft studio lighting\'. Consider adding details like aspect ratio (e.g., \'aspect ratio 16:9\') or camera angles (e.g., \'cinematic shot\').",'
                        f'  "arabic_post_prompt": "اكتب منشور فيسبوك جذابًا باللغة العربية حول \'{topic_name}\'. يجب أن يتضمن المنشور وسومًا (hashtags) ذات صلة ويركز على قطع غيار السيارات أو صيانتها أو حلول الأساطيل. يجب أن يكون نصًا عربيًا فصيحًا ومباشرًا, ولا تزيد عن 200 كلمة.",'
                        f'  "arabic_image_prompt": "صورة وصفية تفصيلية باللغة العربية لإنشاء صورة ذات طابع سيارات تتعلق بـ \'{topic_name}\'. كن محددًا جدًا بشأن الأسلوب والألوان والعناصر، على سبيل المثال، '
                        f'\'واقعية، لقطة مقربة، عالية الدقة، محرك السيارة، مكونات معدنية، مفتاح ربط أزرق، إضاءة استوديع ناعمة\'. يمكن إضافة تفاصيل مثل نسبة العرض إلى العرض إلى الارتفاع (مثال: \'نسبة عرض إلى ارتفاع 16:9\') أو زوايا الكاميرا (مثال: \'لقطة سينمائية\')."'
                        f"}}"
                    )
                    debug_gui_print(f"Sending prompt to Gemini for '{topic_name}':\n{full_prompt}")

                    response = model.generate_content(full_prompt)
                    
                    generated_content = ""
                    if hasattr(response, 'text') and response.text:
                        generated_content = response.text
                    elif hasattr(response, 'candidates') and response.candidates:
                        for candidate in response.candidates:
                            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text'):
                                        generated_content += part.text

                    generated_content = generated_content.strip()
                    debug_gui_print(f"Raw Gemini response for '{topic_name}':\n{generated_content}")

                    if generated_content.startswith("```json"):
                        generated_content = generated_content[len("```json"):].strip()
                    if generated_content.endswith("```"):
                        generated_content = generated_content[:-len("```")].strip()
                    
                    parsed_prompts = json.loads(generated_content)
                    if isinstance(parsed_prompts, list) and len(parsed_prompts) > 0:
                        parsed_prompts_data = parsed_prompts[0]
                        debug_gui_print(f"Parsed Gemini response is a list. Using first item: {parsed_prompts_data}")
                    elif isinstance(parsed_prompts, dict):
                        parsed_prompts_data = parsed_prompts
                    else:
                        raise ValueError("Unexpected JSON format from Gemini: Not a list or a dictionary.")


                    topic_obj["english_image_prompt"] = parsed_prompts_data.get("english_image_prompt", "")
                    topic_obj["arabic_post_prompt"] = parsed_prompts_data.get("arabic_post_prompt", "")
                    topic_obj["arabic_image_prompt"] = parsed_prompts_data.get("arabic_image_prompt", "")
                    
                    generated_count += 1
                    debug_gui_print(f"Successfully generated prompts for '{topic_name}'.")

                except (json.JSONDecodeError, ValueError) as e:
                    debug_gui_print(f"ERROR parsing Gemini response for '{topic_name}': {e}. Response was: {generated_content}")
                    self.master.after(0, self.set_status, f"Error parsing Gemini response for '{topic_name}'. Check console.", "red")
                    errors_occurred = True
                except Exception as e:
                    debug_gui_print(f"ERROR during Gemini API call for '{topic_name}': {e}")
                    self.master.after(0, self.set_status, f"Gemini API error for '{topic_name}'. Check console.", "red")
                    errors_occurred = True

            self.master.after(0, self.save_config_callback)
            self.master.after(0, self._post_generation_ui_update, topics_to_process, page_index, errors_occurred, generated_count)

        except Exception as e:
            debug_gui_print(f"CRITICAL ERROR in _run_gemini_generation_thread: {e}")
            self.master.after(0, self.set_status, f"Critical error during Gemini generation: {e}", "red")
            errors_occurred = True
        finally:
            self.master.after(0, lambda: self.generate_prompts_button.config(state=tk.NORMAL if (GEMINI_AVAILABLE and os.getenv("GEMINI_API_KEY")) else tk.DISABLED))
            if not errors_occurred and generated_count == total_topics:
                self.master.after(0, self.set_status, "Gemini prompt generation complete and SAVED.", "green")
                self.master.after(0, lambda: messagebox.showinfo("Generation Complete", f"Successfully generated and SAVED prompts for {generated_count} topic(s)."))
            elif errors_occurred:
                 self.master.after(0, self.set_status, "Gemini prompt generation completed with errors, but changes were SAVED.", "orange")
                 self.master.after(0, lambda: messagebox.showwarning("Generation Finished with Errors", f"Generated and SAVED prompts for {generated_count} out of {total_topics} topic(s). Check console for errors."))


    def _post_generation_ui_update(self, processed_topics, page_index, errors_occurred, generated_count):
        debug_gui_print("_post_generation_ui_update called.")

        current_topics_in_listbox = [self.topics_listbox.get(i) for i in range(self.topics_listbox.size())]
        indices_to_reselect = []
        for p_topic in processed_topics:
            try:
                idx_in_listbox = current_topics_in_listbox.index(p_topic['name'])
                indices_to_reselect.append(idx_in_listbox)
            except ValueError:
                debug_gui_print(f"Warning: Topic '{p_topic['name']}' not found in current listbox. Skipping re-selection.")

        self.topics_listbox.selection_clear(0, tk.END)
        for idx in indices_to_reselect:
            self.topics_listbox.selection_set(idx)
        
        self._is_programmatic_update = True
        try:
            if len(processed_topics) == 1 and generated_count == 1:
                self._load_topic_prompts_into_ui(processed_topics[0])
            self._on_topic_select()
        finally:
            self._is_programmatic_update = False

        if len(processed_topics) > 1 and generated_count > 0:
            self._load_topic_prompts_into_ui(None, message=f"Prompts generated for {generated_count} selected topics. Please re-select a single topic from the list above to view/edit its prompts.")
        elif generated_count == 0 and errors_occurred:
            self.master.after(0, lambda: self._load_topic_prompts_into_ui(None, message="No prompts generated due to errors. Check console for details."))


    def update_page_selection_list(self, page_names, current_selected_page_name):
        debug_gui_print("ManageTopicsTab.update_page_selection_list called.")
        self._is_programmatic_update = True
        try:
            self.topic_page_selection_combobox['values'] = page_names
            if current_selected_page_name in page_names:
                self.topic_page_selection_var.set(current_selected_page_name)
            elif page_names:
                self.topic_page_selection_var.set(page_names[0])
            else:
                self.topic_page_selection_var.set("")
            
            self._on_topic_page_selected()

            self.topic_page_selection_combobox.config(state="readonly" if page_names else "disabled")
        finally:
            self._is_programmatic_update = False
        debug_gui_print("ManageTopicsTab.update_page_selection_list finished.")