# D:\Facebook_Posts_generation\gui_post_review_edit_tab.py

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from PIL import Image, ImageTk
import os
import io
import json
from datetime import datetime
import threading
import shutil

# Assume these are available or mocked for testing outside main GUI
try:
    import database_manager
    import text_generator
    import image_generator
    import ml_predictor
    import pandas as pd
except ImportError:
    class MockDBManager:
        def get_all_unposted_posts_for_review(self, *args): return []
        def update_post_content_and_image(self, *args, **kwargs): return True
        def update_post_approval_status(self, *args): return True
        def delete_post_by_id(self, *args): return True, None
    database_manager = MockDBManager()

    class MockTextGenerator:
        def generate_text(self, prompt, target_language, provider, model, temperature):
            return f"Mock EN: {prompt}", f"Mock AR: {prompt}", f"Prompt EN: {prompt}", f"Prompt AR: {prompt}"
    text_generator = MockTextGenerator()

    class MockImageGenerator:
        def generate_image(self, *args, **kwargs): return None
    image_generator = MockImageGenerator()

    class MockMLPredictor:
        def predict_engagement(self, *args): return 0.5
        def train_model(self): return True, "Mock model trained."
    ml_predictor = MockMLPredictor()


# --- Debugging setup ---
DEBUG_GUI_MODE = True

def debug_gui_print(message):
    if DEBUG_GUI_MODE:
        print(f"[DEBUG - GUI - PostReview]: {message}")

class PostReviewEditTab(ttk.Frame):
    def __init__(self, parent, set_status_callback, output_dir_var_ref, facebook_pages_ref,
                 api_settings_tab_instance_ref, populate_unposted_listbox_callback, script_dir_ref,
                 image_provider_var_ref,
                 openai_image_model_var_ref
                 ):
        super().__init__(parent)
        self.set_status = set_status_callback
        self.output_dir_var = output_dir_var_ref
        self.facebook_pages = facebook_pages_ref
        self.image_provider_var_ref = image_provider_var_ref
        self.openai_image_model_var_ref = openai_image_model_var_ref

        self.api_settings_tab_instance = api_settings_tab_instance_ref
        self.populate_unposted_listbox_callback = populate_unposted_listbox_callback
        self.script_dir = script_dir_ref

        self.posts_to_review = []
        self.selected_post = None
        self.current_filter = tk.StringVar(value="All")

        self.is_approved_var = tk.BooleanVar()
        self._on_approval_change_trace_id = None # Will be set when approve_checkbutton is created
        self._ignore_approval_trace = False

        # Flag to prevent recursive Treeview selection handling
        self._ignore_treeview_select = False # NEW FLAG HERE

        self._create_widgets()
        # Initial population of the list is handled by on_tab_focus

    def _populate_posts_list(self, event=None, reset_ui=True):
        debug_gui_print(f"_populate_posts_list called. reset_ui={reset_ui}")

        # Set the flag to ignore selection events during programmatic updates
        self._ignore_treeview_select = True # SET FLAG

        try:
            self.posts_tree.delete(*self.posts_tree.get_children())
            approval_filter = self.current_filter.get()
            self.posts_to_review = database_manager.get_all_unposted_posts_for_review(approval_filter)
            debug_gui_print(f"Fetched {len(self.posts_to_review)} posts for review (Filter: {approval_filter}).")

            for post in self.posts_to_review:
                self.posts_tree.insert("", "end", iid=post['id'], values=(
                    post['id'], post['page_name'], post['post_date'], f"{post['post_hour']:02d}:00",
                    post['topic'], post['language'], "Yes" if post['is_approved'] else "No",
                    f"{post['predicted_engagement_score']:.2f}" if post['predicted_engagement_score'] is not None else "N/A"
                ))

            if reset_ui:
                self._set_ui_state("initial")
            else:
                if self.selected_post:
                    current_id = self.selected_post['id']
                    if self.posts_tree.exists(current_id):
                        self.posts_tree.selection_set(current_id)
                        self.posts_tree.focus(current_id)
                        debug_gui_print(f"Re-selected post ID {current_id} after refresh.")
                        # Manually trigger _on_post_select for the re-selected item
                        # since the event was ignored.
                        # This ensures the details panel is updated correctly.
                        self._on_post_select_internal(current_id) # Call new internal helper
                    else:
                        debug_gui_print(f"Previously selected post ID {current_id} not found after refresh. Resetting UI.")
                        self._set_ui_state("initial")
                else:
                    debug_gui_print("No post was selected to re-select after refresh.")
                    self._set_ui_state("initial")

        finally:
            # Always reset the flag
            self._ignore_treeview_select = False # RESET FLAG


    def _on_post_select(self, event):
        # This is the public event handler. It checks the flag.
        if self._ignore_treeview_select: # CHECK FLAG
            debug_gui_print("Ignoring Treeview select event due to programmatic update.")
            return

        debug_gui_print("_on_post_select called (via event).")
        selected_items = self.posts_tree.selection()
        debug_gui_print(f"Selected items found: {selected_items}")
        if not selected_items:
            debug_gui_print("No items actually selected in Treeview. Resetting UI.")
            self._set_ui_state("initial")
            return

        post_id = int(selected_items[0])
        self._on_post_select_internal(post_id) # Call the internal helper

    def _on_post_select_internal(self, post_id): # NEW HELPER FUNCTION
        debug_gui_print(f"_on_post_select_internal called for post ID: {post_id}")
        self.selected_post = next((p for p in self.posts_to_review if p['id'] == post_id), None)

        if self.selected_post:
            debug_gui_print(f"Loaded details for post ID: {self.selected_post['id']}")
            debug_gui_print(f"Image Prompt EN in self.selected_post: '{self.selected_post.get('image_prompt_en', 'N/A')}'")
            debug_gui_print(f"Image Prompt AR in self.selected_post: '{self.selected_post.get('image_prompt_ar', 'N/A')}'")
            self._load_post_details_into_ui(self.selected_post)
            self._set_ui_state("post_selected")
        else:
            self._set_ui_state("initial")


    def _load_post_details_into_ui(self, post_data):
        debug_gui_print(f"_load_post_details_into_ui for post ID: {post_data['id']}")
        self.detail_post_id_var.set(post_data['id'])
        self.selected_page_for_post_var.set(post_data['page_name'])
        self.detail_post_date_var.set(post_data['post_date'])
        self.detail_post_hour_var.set(post_data['post_hour'])

        self.content_en_text.config(state="normal")
        self.content_en_text.delete(1.0, tk.END)
        self.content_en_text.insert(tk.END, post_data.get('content_en', ''))

        self.content_ar_text.config(state="normal")
        self.content_ar_text.delete(1.0, tk.END)
        self.content_ar_text.insert(tk.END, post_data.get('content_ar', ''))

        self.image_prompt_en_text.config(state="normal")
        self.image_prompt_en_text.delete(1.0, tk.END)
        self.image_prompt_en_text.insert(tk.END, post_data.get('image_prompt_en', ''))

        self.image_prompt_ar_text.config(state="normal")
        self.image_prompt_ar_text.delete(1.0, tk.END)
        self.image_prompt_ar_text.insert(tk.END, post_data.get('image_prompt_ar', ''))

        # --- Approval trace handling (as before, this part is good) ---
        if self._on_approval_change_trace_id:
            try:
                self.is_approved_var.trace_remove("write", self._on_approval_change_trace_id)
                debug_gui_print(f"Temporarily removed trace for is_approved_var (ID: {self._on_approval_change_trace_id}).")
                self._on_approval_change_trace_id = None
            except tk.TclError as e:
                debug_gui_print(f"WARNING: Could not remove trace {self._on_approval_change_trace_id} (might be already removed or invalid): {e}")
                self._on_approval_change_trace_id = None

        self._ignore_approval_trace = True
        self.is_approved_var.set(post_data['is_approved'] == 1)
        debug_gui_print(f"Post ID {post_data['id']} approval set to {post_data['is_approved']==1} during load.")

        self._ignore_approval_trace = False
        if self._on_approval_change_trace_id is None:
            self._on_approval_change_trace_id = self.is_approved_var.trace_add("write", self._on_approval_change)
            debug_gui_print(f"Trace for is_approved_var re-established with new ID: {self._on_approval_change_trace_id}.")
        # --- End approval trace handling ---

        self.predicted_engagement_score_var.set(f"{post_data['predicted_engagement_score']:.2f}" if post_data['predicted_engagement_score'] is not None else "N/A")

        self._load_image_preview(post_data.get('generated_image_filename'))
        debug_gui_print("Post details loaded into UI.")

    def _create_widgets(self):
        debug_gui_print("_create_widgets called.")
        # Top Frame: Filter and Refresh
        control_frame = ttk.Frame(self)
        control_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(control_frame, text="Filter:").pack(side="left", padx=5)
        filter_options = ["All", "Approved", "Not Approved"]
        self.filter_combobox = ttk.Combobox(control_frame, textvariable=self.current_filter, values=filter_options, state="readonly", width=15)
        self.filter_combobox.pack(side="left", padx=5)
        # Bind this directly to _populate_posts_list as it's a user action
        self.filter_combobox.bind("<<ComboboxSelected>>", self._populate_posts_list)


        self.refresh_button = ttk.Button(control_frame, text="Refresh List", command=self._populate_posts_list)
        self.refresh_button.pack(side="left", padx=10)

        # Left Frame: Posts List
        list_frame = ttk.LabelFrame(self, text="Generated Posts for Review")
        list_frame.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=5)

        self.posts_tree = ttk.Treeview(list_frame, columns=("id", "page", "date", "time", "topic", "language", "approved", "predicted_score"), show="headings", height=15)
        self.posts_tree.heading("id", text="ID")
        self.posts_tree.heading("page", text="Page")
        self.posts_tree.heading("date", text="Date")
        self.posts_tree.heading("time", text="Time")
        self.posts_tree.heading("topic", text="Topic")
        self.posts_tree.heading("language", text="Lang")
        self.posts_tree.heading("approved", text="Approved?")
        self.posts_tree.heading("predicted_score", text="Pred. Score")

        self.posts_tree.column("id", width=40, anchor="center")
        self.posts_tree.column("page", width=100)
        self.posts_tree.column("date", width=80)
        self.posts_tree.column("time", width=60)
        self.posts_tree.column("topic", width=120)
        self.posts_tree.column("language", width=50, anchor="center")
        self.posts_tree.column("approved", width=70, anchor="center")
        self.posts_tree.column("predicted_score", width=80, anchor="center")

        self.posts_tree.pack(fill="both", padx=5, pady=5)
        # Store the bind ID directly when creating the binding
        self.posts_tree._on_select_bind_id = self.posts_tree.bind("<<TreeviewSelect>>", self._on_post_select)

        # Add a scrollbar to the Treeview
        tree_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.posts_tree.yview)
        tree_scrollbar.pack(side="right", fill="y")
        self.posts_tree.config(yscrollcommand=tree_scrollbar.set)

        # Right Frame: Post Details and Actions
        details_frame = ttk.LabelFrame(self, text="Post Details & Actions")
        details_frame.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=5)

        details_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(details_frame, text="Post ID:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.detail_post_id_var = tk.StringVar()
        ttk.Label(details_frame, textvariable=self.detail_post_id_var).grid(row=0, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(details_frame, text="Facebook Page:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.selected_page_for_post_var = tk.StringVar()
        self.post_page_combobox = ttk.Combobox(details_frame, textvariable=self.selected_page_for_post_var, state="readonly")
        self.post_page_combobox.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.post_page_combobox.bind("<<ComboboxSelected>>", self._on_page_selection_change)

        ttk.Label(details_frame, text="Post Date (YYYY-MM-DD):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.detail_post_date_var = tk.StringVar()
        self.detail_post_date_entry = ttk.Entry(details_frame, textvariable=self.detail_post_date_var)
        self.detail_post_date_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(details_frame, text="Post Hour (0-23):").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.detail_post_hour_var = tk.IntVar()
        self.detail_post_hour_spinbox = ttk.Spinbox(details_frame, from_=0, to=23, textvariable=self.detail_post_hour_var, wrap=True)
        self.detail_post_hour_spinbox.grid(row=3, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(details_frame, text="Content (EN):").grid(row=4, column=0, padx=5, pady=2, sticky="nw")
        self.content_en_text = scrolledtext.ScrolledText(details_frame, wrap="word", height=5)
        self.content_en_text.grid(row=4, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        ttk.Label(details_frame, text="Content (AR):").grid(row=5, column=0, padx=5, pady=2, sticky="nw")
        self.content_ar_text = scrolledtext.ScrolledText(details_frame, wrap="word", height=5)
        self.content_ar_text.grid(row=5, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        ttk.Label(details_frame, text="Image Prompt (EN):").grid(row=6, column=0, padx=5, pady=2, sticky="nw")
        self.image_prompt_en_text = scrolledtext.ScrolledText(details_frame, wrap="word", height=3)
        self.image_prompt_en_text.grid(row=6, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        ttk.Label(details_frame, text="Image Prompt (AR):").grid(row=7, column=0, padx=5, pady=2, sticky="nw")
        self.image_prompt_ar_text = scrolledtext.ScrolledText(details_frame, wrap="word", height=3)
        self.image_prompt_ar_text.grid(row=7, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        self.image_preview_label = ttk.Label(details_frame, text="Image Preview", relief="solid", anchor="center")
        self.image_preview_label.grid(row=8, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        self.image_preview_label.grid_propagate(False)
        details_frame.grid_rowconfigure(8, weight=1)

        self.image_action_frame = ttk.Frame(details_frame)
        self.image_action_frame.grid(row=9, column=0, columnspan=3, pady=5, sticky="ew")
        ttk.Button(self.image_action_frame, text="Generate New Image", command=self._generate_new_image_async).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(self.image_action_frame, text="Select Image from File", command=self._select_image_from_file).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(self.image_action_frame, text="Clear Image", command=self._clear_image).pack(side="left", expand=True, fill="x", padx=2)


        ttk.Label(details_frame, text="Approved:").grid(row=10, column=0, padx=5, pady=2, sticky="w")
        self.approve_checkbutton = ttk.Checkbutton(details_frame, variable=self.is_approved_var, text="Approve for Posting")
        self.approve_checkbutton.grid(row=10, column=1, padx=5, pady=2, sticky="w")
        if self._on_approval_change_trace_id is None:
            self._on_approval_change_trace_id = self.is_approved_var.trace_add("write", self._on_approval_change)
            debug_gui_print(f"Initial trace added for is_approved_var in _create_widgets with ID: {self._on_approval_change_trace_id}")

        ttk.Label(details_frame, text="Predicted Score:").grid(row=11, column=0, padx=5, pady=2, sticky="w")
        self.predicted_engagement_score_var = tk.DoubleVar()
        ttk.Label(details_frame, textvariable=self.predicted_engagement_score_var).grid(row=11, column=1, padx=5, pady=2, sticky="w")


        action_button_frame = ttk.Frame(details_frame)
        action_button_frame.grid(row=12, column=0, columnspan=3, pady=10, sticky="ew")
        self.update_post_button = ttk.Button(action_button_frame, text="Update Post", command=self._update_post)
        self.update_post_button.pack(side="left", expand=True, fill="x", padx=5)
        self.delete_post_button = ttk.Button(action_button_frame, text="Delete Post", command=self._delete_post)
        self.delete_post_button.pack(side="left", expand=True, fill="x", padx=5)


        details_frame.columnconfigure(1, weight=1)

        self._set_ui_state("initial")

        self._update_page_selection_list()

    def _select_image_from_file(self):
        if not self.selected_post:
            messagebox.showwarning("No Post Selected", "Please select a post to attach an image to.", parent=self.master)
            return

        file_path = filedialog.askopenfilename(
            parent=self.master,
            title="Select Image File",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")]
        )
        if file_path:
            destination_dir = os.path.join(self.output_dir_var.get(), "generated_images")
            os.makedirs(destination_dir, exist_ok=True)

            filename = os.path.basename(file_path)
            destination_path = os.path.join(destination_dir, filename)

            try:
                shutil.copy(file_path, destination_path)

                database_manager.update_post_content_and_image(
                    self.selected_post['id'],
                    None, None,
                    generated_image_filename=filename,
                    image_prompt_en=self.selected_post.get('image_prompt_en', ''),
                    image_prompt_ar=self.selected_post.get('image_prompt_ar', '')
                )
                self.selected_post['generated_image_filename'] = filename
                self._load_image_preview(filename)
                self.set_status(f"Image '{filename}' selected and saved for Post ID {self.selected_post['id']}.", "green")
                self._populate_posts_list(reset_ui=False)

            except Exception as e:
                debug_gui_print(f"Error selecting/copying image file {file_path}: {e}")
                self.set_status(f"Error selecting/copying image file: {e}", "red")
                messagebox.showerror("Image Selection Error", f"Failed to select and save image: {e}", parent=self.master)
        else:
            self.set_status("Image file selection cancelled.", "blue")

    def _update_page_selection_list(self):
        page_names = [page["page_name"] for page in self.facebook_pages]
        self.post_page_combobox['values'] = page_names

    def _on_page_selection_change(self, event):
        pass

    def _set_ui_state(self, state):
        debug_gui_print(f"UI state set to {state}.")

        ttk_widgets_to_control = [
            self.post_page_combobox, self.approve_checkbutton,
            self.detail_post_date_entry, self.detail_post_hour_spinbox,
            self.update_post_button, self.delete_post_button
        ]

        tk_text_widgets_to_control = [
            self.content_en_text, self.content_ar_text,
            self.image_prompt_en_text, self.image_prompt_ar_text
        ]

        image_action_buttons = []
        for child in self.image_action_frame.winfo_children():
            if isinstance(child, (ttk.Button, tk.Button)):
                image_action_buttons.append(child)


        if state == "initial":
            self.detail_post_id_var.set("")
            self.selected_page_for_post_var.set("")
            self.detail_post_date_var.set("")
            self.detail_post_hour_var.set(0)
            self.predicted_engagement_score_var.set(0.0)
            self.image_preview_label.config(image='', text="Image Preview")
            self.image_preview_label.image = None

            # --- CRITICAL FIX: Ensure no selection when going to initial state ---
            # Do NOT unbind/rebind the treeview here. _populate_posts_list handles that.
            # Just clear the selection. The _ignore_treeview_select flag in _on_post_select
            # will prevent an event storm if _populate_posts_list calls this.
            self.posts_tree.selection_remove(self.posts_tree.selection())
            self.selected_post = None
            # --- END CRITICAL FIX ---


            for widget in ttk_widgets_to_control + image_action_buttons:
                if widget and hasattr(widget, 'config'):
                    widget.config(state="disabled")

            for widget in tk_text_widgets_to_control:
                if widget:
                    widget.config(state=tk.DISABLED)

            for widget in tk_text_widgets_to_control:
                if widget:
                    widget.config(state=tk.NORMAL)
                    widget.delete(1.0, tk.END)
                    widget.config(state=tk.DISABLED)

            try:
                self.posts_tree.state(['!disabled'])
                debug_gui_print("posts_tree visual state set to 'normal' via .state() method.")
            except tk.TclError as e:
                debug_gui_print(f"WARNING: posts_tree.state(['!disabled']) failed visually: {e}. Functionality still managed by bind.")

            self.master.update_idletasks()

        elif state == "post_selected":
            for widget in ttk_widgets_to_control + image_action_buttons:
                if widget and hasattr(widget, 'config'):
                    widget.config(state="normal")

            for widget in tk_text_widgets_to_control:
                if widget:
                    widget.config(state=tk.NORMAL)

            self.post_page_combobox.config(state="readonly" if self.facebook_pages else "disabled")

            try:
                self.posts_tree.state(['!disabled'])
            except tk.TclError as e:
                debug_gui_print(f"WARNING: posts_tree.state(['!disabled']) in post_selected failed visually: {e}.")


        elif state == "generating_image":
            for widget in image_action_buttons:
                if widget and hasattr(widget, 'config'):
                    widget.config(state="disabled")

            for widget in tk_text_widgets_to_control:
                if widget:
                    widget.config(state=tk.DISABLED)

            self.set_status("Generating new image...", "blue")
            self.update_post_button.config(state="disabled")
            self.delete_post_button.config(state="disabled")

            try:
                self.posts_tree.state(['disabled'])
            except tk.TclError as e:
                debug_gui_print(f"WARNING: posts_tree.state(['disabled']) in generating_image failed visually: {e}.")

            # --- CRITICAL FIX: Unbind Treeview during long operations ---
            if hasattr(self.posts_tree, '_on_select_bind_id'):
                self.posts_tree.unbind("<<TreeviewSelect>>", self.posts_tree._on_select_bind_id)
                debug_gui_print("Temporarily unbound Treeview select event during image generation.")
            # --- END CRITICAL FIX ---

    def _load_image_preview(self, filename):
        if not filename or filename.startswith("ERROR_"):
            debug_gui_print("No image path or file not found.")
            self.image_preview_label.config(image='', text="No Image Generated or Failed")
            self.image_preview_label.image = None
            return

        image_save_dir = os.path.join(self.output_dir_var.get(), "generated_images")
        image_path = os.path.join(image_save_dir, filename)
        if os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                max_size = (200, 200)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

                self.tk_img = ImageTk.PhotoImage(img)
                self.image_preview_label.config(image=self.tk_img, text="")
                debug_gui_print(f"Image preview loaded from: {image_path}")
            except Exception as e:
                debug_gui_print(f"Error loading image preview from {image_path}: {e}")
                self.image_preview_label.config(image='', text=f"Error loading image: {os.path.basename(image_path)}")
                self.image_preview_label.image = None
        else:
            debug_gui_print(f"Image file not found: {image_path}")
            self.image_preview_label.config(image='', text=f"Image file not found: {os.path.basename(image_path)}")
            self.image_preview_label.image = None

    def _clear_image(self):
        if self.selected_post:
            filename_to_delete = self.selected_post.get('generated_image_filename')
            if filename_to_delete and not filename_to_delete.startswith("ERROR_"):
                image_save_dir = os.path.join(self.output_dir_var.get(), "generated_images")
                filepath = os.path.join(image_save_dir, filename_to_delete)
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        debug_gui_print(f"Deleted associated image file: {filepath}")
                        self.selected_post['generated_image_filename'] = None
                        self._load_image_preview(None)
                        database_manager.update_post_content_and_image(self.selected_post['id'],
                                                                        None, None, None,
                                                                        image_prompt_en=None,
                                                                        image_prompt_ar=None)
                        self.set_status(f"Image for Post ID {self.selected_post['id']} cleared.", "green")
                        self._populate_posts_list(reset_ui=False)
                    except Exception as e:
                        debug_gui_print(f"Error deleting image file {filepath}: {e}")
                        self.set_status(f"Error deleting image file: {e}", "red")
                else:
                    self.set_status("Image file not found on disk.", "orange")
                    self.selected_post['generated_image_filename'] = None
                    self._load_image_preview(None)
                    database_manager.update_post_content_and_image(self.selected_post['id'],
                                                                    None, None, None,
                                                                    image_prompt_en=None,
                                                                    image_prompt_ar=None)
                    self._populate_posts_list(reset_ui=False)
            else:
                self.set_status("No valid image to clear for selected post.", "blue")
        else:
            self.set_status("No post selected to clear image.", "orange")

    def _generate_new_image_async(self):
        if not self.selected_post:
            messagebox.showwarning("No Post Selected", "Please select a post to generate a new image for.", parent=self.master)
            return

        prompt_from_ui_en = self.image_prompt_en_text.get(1.0, tk.END).strip()
        prompt_from_ui_ar = self.image_prompt_ar_text.get(1.0, tk.END).strip()

        if not (prompt_from_ui_en or prompt_from_ui_ar):
            messagebox.showwarning("No Image Prompt", "Please enter an image prompt (English or Arabic) before generating.", parent=self.master)
            return

        self._set_ui_state("generating_image")

        threading.Thread(target=self._run_ai_image_generation_process,
                         args=(prompt_from_ui_en, prompt_from_ui_ar)).start()
        debug_gui_print("AI image generation thread started.")

    def _run_ai_image_generation_process(self, prompt_en, prompt_ar):
        debug_gui_print(f"_run_ai_image_generation_process called with prompt_en: {prompt_en[:50]}..., prompt_ar: {prompt_ar[:50]}..., post_id: {self.selected_post['id']}")
        try:
            effective_prompt = ""
            if self.selected_post['language'] == "English" and prompt_en:
                effective_prompt = prompt_en
            elif self.selected_post['language'] == "Arabic" and prompt_ar:
                effective_prompt = prompt_ar
            elif self.selected_post['language'] == "Both":
                effective_prompt = prompt_en if prompt_en else prompt_ar

            if not effective_prompt:
                self.master.after(0, self.set_status, "Error: No effective image prompt (EN or AR) available for generation.", "red")
                self.master.after(0, lambda: messagebox.showerror("Image Gen Error", "No image prompt provided for generation.", parent=self.master))
                return


            image_gen_provider = self.image_provider_var_ref.get()
            image_gen_model = self.openai_image_model_var_ref.get()

            generated_filename = image_generator.generate_image(
                effective_prompt,
                output_dir=self.output_dir_var.get(),
                provider=image_gen_provider,
                model=image_gen_model
            )

            if generated_filename:
                database_manager.update_post_content_and_image(self.selected_post['id'],
                                                                None, None,
                                                                generated_image_filename=generated_filename,
                                                                image_prompt_en=prompt_en,
                                                                image_prompt_ar=prompt_ar)
                self.selected_post['generated_image_filename'] = generated_filename
                self.selected_post['image_prompt_en'] = prompt_en
                self.selected_post['image_prompt_ar'] = prompt_ar

                self.master.after(0, self._load_image_preview, generated_filename)
                self.master.after(0, self.set_status, f"New image generated and saved for Post ID {self.selected_post['id']}.", "green")
                self.master.after(0, self._populate_posts_list, None, False)
            else:
                self.master.after(0, self.set_status, "AI image generation failed. See console for details.", "red")
                self.master.after(0, lambda: messagebox.showerror("Image Generation Error",
                                                                  "AI image generation failed. Check console for details.",
                                                                  parent=self.master))
        except Exception as e:
            debug_gui_print(f"CRITICAL ERROR in _run_ai_image_generation_process thread: {e}")
            self.master.after(0, self.set_status, f"Image generation error: {e}", "red")
            self.master.after(0, lambda: messagebox.showerror("Image Generation Error",
                                                              f"AI image generation failed unexpectedly: {e}",
                                                              parent=self.master))
        finally:
            # Re-bind Treeview after image generation finishes
            if hasattr(self.posts_tree, '_on_select_bind_id') and self.posts_tree._on_select_bind_id not in self.posts_tree.bind("<<TreeviewSelect>>"):
                 self.posts_tree._on_select_bind_id = self.posts_tree.bind("<<TreeviewSelect>>", self._on_post_select)
                 debug_gui_print("Re-bound Treeview select event after image generation.")

            self.master.after(0, self._set_ui_state, "post_selected")
            debug_gui_print("_run_ai_image_generation_process finished.")

    def _on_approval_change(self, *args):
        if self._ignore_approval_trace:
            debug_gui_print("Ignoring programmatic trace call for is_approved_var.")
            return

        if self.selected_post:
            new_status = self.is_approved_var.get()
            debug_gui_print(f"Post ID {self.selected_post['id']} approval changed to {new_status} by user interaction.")
            database_manager.update_post_approval_status(self.selected_post['id'], new_status)
            self.selected_post['is_approved'] = 1 if new_status else 0
            self.set_status(f"Post ID {self.selected_post['id']} approval status updated to {'Approved' if new_status else 'Not Approved'}.", "green")
            self._populate_posts_list(reset_ui=False)
            self.populate_unposted_listbox_callback()

    def _update_post(self):
        if not self.selected_post:
            messagebox.showwarning("No Post Selected", "Please select a post to update.", parent=self.master)
            return

        updated_content_en = self.content_en_text.get(1.0, tk.END).strip()
        updated_content_ar = self.content_ar_text.get(1.0, tk.END).strip()
        updated_image_prompt_en = self.image_prompt_en_text.get(1.0, tk.END).strip()
        updated_image_prompt_ar = self.image_prompt_ar_text.get(1.0, tk.END).strip()
        updated_page_name = self.selected_page_for_post_var.get()
        updated_post_date = self.detail_post_date_var.get()
        updated_post_hour = self.detail_post_hour_var.get()

        try:
            datetime.strptime(updated_post_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Invalid Date Format", "Please enter the post date in YYYY-MM-DD format.", parent=self.master)
            return

        if not (0 <= updated_post_hour <= 23):
            messagebox.showwarning("Invalid Hour", "Please enter a valid hour between 0 and 23.", parent=self.master)
            return

        selected_page_obj = next((p for p in self.facebook_pages if p["page_name"] == updated_page_name), None)

        if not selected_page_obj:
            messagebox.showerror("Page Not Found", f"Selected page '{updated_page_name}' not found in configuration. Cannot update post.", parent=self.master)
            return

        updated_facebook_page_id = selected_page_obj.get("facebook_page_id")
        updated_facebook_access_token = selected_page_obj.get("facebook_access_token")

        if not updated_facebook_page_id or not updated_facebook_access_token:
            messagebox.showwarning("Missing Page Credentials", f"Facebook Page ID or Access Token is missing for page '{updated_page_name}'. Please update page details in 'Page Details' tab.", parent=self.master)

        success = database_manager.update_post_content_and_image(
            self.selected_post['id'],
            content_en=updated_content_en,
            content_ar=updated_content_ar,
            generated_image_filename=self.selected_post.get('generated_image_filename'),
            image_prompt_en=updated_image_prompt_en,
            image_prompt_ar=updated_image_prompt_ar,
            post_date=updated_post_date,
            post_hour=updated_post_hour,
            page_name=updated_page_name,
            facebook_page_id=updated_facebook_page_id,
            facebook_access_token=updated_facebook_access_token
        )
        if success:
            self.set_status(f"Post ID {self.selected_post['id']} updated successfully.", "green")
            self.selected_post.update({
                'content_en': updated_content_en,
                'content_ar': updated_content_ar,
                'image_prompt_en': updated_image_prompt_en,
                'image_prompt_ar': updated_image_prompt_ar,
                'page_name': updated_page_name,
                'post_date': updated_post_date,
                'post_hour': updated_post_hour,
                'facebook_page_id': updated_facebook_page_id,
                'facebook_access_token': updated_facebook_access_token
            })
            self._populate_posts_list(reset_ui=False)
            self.populate_unposted_listbox_callback()
        else:
            self.set_status(f"Failed to update Post ID {self.selected_post['id']}.", "red")
            messagebox.showerror("Update Failed", "Failed to update post in database.", parent=self.master)

    def _delete_post(self):
        if not self.selected_post:
            messagebox.showwarning("No Post Selected", "Please select a post to delete.", parent=self.master)
            return

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete Post ID {self.selected_post['id']}? This action cannot be undone and will also delete the generated image file.", icon='warning', parent=self.master)
        if confirm:
            success, image_filename_from_db = database_manager.delete_post_by_id(self.selected_post['id'])
            if success:
                self.set_status(f"Post ID {self.selected_post['id']} deleted successfully.", "green")
                if image_filename_from_db:
                    image_save_dir = os.path.join(self.output_dir_var.get(), "generated_images")
                    image_path = os.path.join(image_save_dir, image_filename_from_db)
                    if os.path.exists(image_path):
                        try:
                            os.remove(image_path)
                            debug_gui_print(f"Deleted associated image file: {image_path}")
                        except Exception as e:
                            debug_gui_print(f"Error deleting image file {image_path}: {e}")
                            self.set_status(f"Post deleted, but could not delete image file: {e}", "orange")

                self._populate_posts_list()
                self.populate_unposted_listbox_callback()
            else:
                self.set_status(f"Failed to delete Post ID {self.selected_post['id']}.", "red")
                messagebox.showerror("Delete Failed", "Failed to delete post from database.", parent=self.master)

    def on_tab_focus(self):
        debug_gui_print("PostReviewEditTab focused. Populating list.")
        self._populate_posts_list()
        self._update_page_selection_list()
        self._set_ui_state("initial")