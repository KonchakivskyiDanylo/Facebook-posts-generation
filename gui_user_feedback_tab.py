# gui_user_feedback_tab.py

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
from datetime import datetime

# Assume database_manager is available or mocked
try:
    import database_manager
except ImportError:
    class MockDBManager:
        def get_all_unposted_posts_for_review(self, *args): return []
        def get_feedback_by_page_id(self, page_id): return []
        def add_feedback(self, page_id, feedback_text): return 1
        def update_feedback(self, feedback_id, new_feedback_text): return True
        def delete_feedback(self, feedback_id): return True
    database_manager = MockDBManager()

# --- Debugging setup ---
DEBUG_GUI_MODE = True

def debug_gui_print(message):
    if DEBUG_GUI_MODE:
        print(f"[DEBUG - GUI - UserFeedback]: {message}")

class UserFeedbackTab(ttk.Frame):
    def __init__(self, parent, set_status_callback, facebook_pages_ref):
        super().__init__(parent)
        self.set_status = set_status_callback
        self.facebook_pages = facebook_pages_ref

        self.current_selected_page_id = None # Stores the page_id of the currently selected page
        self.current_selected_feedback_id = None # Stores the ID of the selected feedback entry

        # Tkinter Variables
        self.selected_page_name_var = tk.StringVar()
        self.feedback_text_var = tk.StringVar() # For the single-line entry or initial setting
        
        self._create_widgets()
        debug_gui_print("UserFeedbackTab widgets created.")

    def _create_widgets(self):
        debug_gui_print("_create_widgets (UserFeedbackTab) called.")

        # Top Frame: Page Selection
        page_selection_frame = ttk.LabelFrame(self, text="Select Page for Feedback")
        page_selection_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(page_selection_frame, text="Facebook Page:").pack(side="left", padx=5)
        self.page_combobox = ttk.Combobox(page_selection_frame, textvariable=self.selected_page_name_var, values=[], state="readonly", width=40)
        self.page_combobox.pack(side="left", padx=5, pady=2, fill="x", expand=True)
        self.page_combobox.bind("<<ComboboxSelected>>", self._on_page_selected)
        
        # Center Frame: Feedback List
        feedback_list_frame = ttk.LabelFrame(self, text="Feedback Entries for Selected Page")
        feedback_list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.feedback_tree = ttk.Treeview(feedback_list_frame, columns=("id", "feedback_text", "created_at"), show="headings", height=10)
        self.feedback_tree.heading("id", text="ID")
        self.feedback_tree.heading("feedback_text", text="Feedback Text")
        self.feedback_tree.heading("created_at", text="Created/Updated On")

        self.feedback_tree.column("id", width=50, anchor="center")
        self.feedback_tree.column("feedback_text", width=400, stretch=tk.YES)
        self.feedback_tree.column("created_at", width=150, anchor="center")

        self.feedback_tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.feedback_tree.bind("<<TreeviewSelect>>", self._on_feedback_selected)

        # Bottom Frame: Feedback Details and Actions
        feedback_details_frame = ttk.LabelFrame(self, text="Feedback Details & Actions")
        feedback_details_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(feedback_details_frame, text="Feedback Text:").grid(row=0, column=0, padx=5, pady=2, sticky="nw")
        self.feedback_text_area = scrolledtext.ScrolledText(feedback_details_frame, wrap="word", height=5)
        self.feedback_text_area.grid(row=0, column=1, padx=5, pady=2, sticky="ew", columnspan=2)
        feedback_details_frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(feedback_details_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.add_button = ttk.Button(button_frame, text="Add New Feedback", command=self._add_feedback)
        self.add_button.pack(side="left", padx=5)
        self.edit_button = ttk.Button(button_frame, text="Update Selected Feedback", command=self._update_feedback)
        self.edit_button.pack(side="left", padx=5)
        self.delete_button = ttk.Button(button_frame, text="Delete Selected Feedback", command=self._delete_feedback)
        self.delete_button.pack(side="left", padx=5)

        self._set_ui_state("initial")
        debug_gui_print("_create_widgets (UserFeedbackTab) finished.")

    def _set_ui_state(self, state):
        debug_gui_print(f"UI state set to {state}.")
        if state == "initial":
            self.page_combobox.config(state="readonly" if self.facebook_pages else "disabled")
            self.feedback_text_area.config(state="normal") # Temporarily enable to clear
            self.feedback_text_area.delete(1.0, tk.END)
            self.feedback_text_area.config(state="disabled") # Disable after clearing

            self.add_button.config(state="disabled")
            self.edit_button.config(state="disabled")
            self.delete_button.config(state="disabled")

            self.feedback_tree.delete(*self.feedback_tree.get_children())
            self.feedback_tree.config(selectmode="none")

            self.current_selected_page_id = None
            self.current_selected_feedback_id = None
            self.set_status("Select a page to manage feedback.", "blue")
        elif state == "page_selected":
            self.page_combobox.config(state="readonly")
            self.feedback_text_area.config(state="normal") # Enable feedback text area for input
            self.feedback_text_area.delete(1.0, tk.END) # Clear any old text
            self.add_button.config(state="normal")
            self.edit_button.config(state="disabled")
            self.delete_button.config(state="disabled")
            self.feedback_tree.config(selectmode="browse")
            self.set_status(f"Page '{self.selected_page_name_var.get()}' selected. Add or select feedback.", "blue")
            self._populate_feedback_listbox() # This populates the treeview but won't disable the text area now
        elif state == "feedback_selected":
            self.page_combobox.config(state="readonly")
            self.feedback_text_area.config(state="normal") # Ensure it's normal when feedback is selected
            self.add_button.config(state="normal")
            self.edit_button.config(state="normal")
            self.delete_button.config(state="normal")
            self.feedback_tree.config(selectmode="browse")
            self.set_status(f"Feedback ID {self.current_selected_feedback_id} selected.", "blue")
            

    def update_page_selection_list(self, page_names):
        self.page_combobox['values'] = page_names
        if page_names:
            if self.selected_page_name_var.get() in page_names:
                self._on_page_selected()
            else:
                self.selected_page_name_var.set(page_names[0])
                self._on_page_selected()
        else:
            self.selected_page_name_var.set("")
            self._set_ui_state("initial")


    def _on_page_selected(self, event=None):
        debug_gui_print(f"--- _on_page_selected (UserFeedbackTab) called. Selected: {self.selected_page_name_var.get()}")
        selected_page_name = self.selected_page_name_var.get()
        if not selected_page_name:
            self._set_ui_state("initial")
            return
        
        selected_page_obj = next((p for p in self.facebook_pages if p["page_name"] == selected_page_name), None)
        if selected_page_obj:
            # Corrected: Access facebook_page_id directly from the page object
            self.current_selected_page_id = selected_page_obj.get("facebook_page_id")
            if not self.current_selected_page_id: # Handle case if ID is missing from config
                 debug_gui_print(f"WARNING: Selected page '{selected_page_name}' has no 'facebook_page_id'. Feedback will be linked to None.")
                 self.set_status(f"Warning: Page '{selected_page_name}' has no Facebook Page ID configured.", "orange")

            self._set_ui_state("page_selected")
        else:
            self.current_selected_page_id = None
            self._set_ui_state("initial")
            self.set_status(f"Error: Page '{selected_page_name}' not found in config.", "red")


    def _populate_feedback_listbox(self):
        debug_gui_print(f"_populate_feedback_listbox called for page ID: {self.current_selected_page_id}")
        self.feedback_tree.delete(*self.feedback_tree.get_children())
        if self.current_selected_page_id:
            feedbacks = database_manager.get_feedback_by_page_id(self.current_selected_page_id)
            for fb in feedbacks:
                display_time = datetime.strptime(fb['last_updated_at'], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
                self.feedback_tree.insert("", "end", iid=fb['id'], values=(fb['id'], fb['feedback_text'], display_time))
        debug_gui_print("Feedback listbox populated.")
        self.current_selected_feedback_id = None
        self.feedback_tree.selection_remove(self.feedback_tree.selection())
        self.feedback_text_area.delete(1.0, tk.END) # Clear text area without changing state


    def _on_feedback_selected(self, event=None):
        selected_items = self.feedback_tree.selection()
        if selected_items:
            self.current_selected_feedback_id = int(selected_items[0])
            # Fetch the specific feedback item from the database again, or store them in a local list for faster access
            selected_feedback_data = next((fb for fb in database_manager.get_feedback_by_page_id(self.current_selected_page_id) if fb['id'] == self.current_selected_feedback_id), None)
            if selected_feedback_data:
                self.feedback_text_area.config(state="normal")
                self.feedback_text_area.delete(1.0, tk.END)
                self.feedback_text_area.insert(tk.END, selected_feedback_data['feedback_text'])
                self._set_ui_state("feedback_selected")
            else:
                self.current_selected_feedback_id = None
                self._set_ui_state("page_selected")
        else:
            self.current_selected_feedback_id = None
            self._set_ui_state("page_selected")
            self.feedback_text_area.delete(1.0, tk.END) # Clear text area if nothing is selected


    def _add_feedback(self):
        if not self.current_selected_page_id:
            messagebox.showwarning("No Page Selected", "Please select a page before adding feedback.", parent=self.master)
            return
        
        feedback_text = self.feedback_text_area.get(1.0, tk.END).strip()
        if not feedback_text:
            messagebox.showwarning("No Feedback Text", "Please enter feedback text.", parent=self.master)
            return
        
        success = database_manager.add_feedback(self.current_selected_page_id, feedback_text)
        if success:
            self.set_status("Feedback added successfully.", "green")
            self._populate_feedback_listbox()
            self.feedback_text_area.delete(1.0, tk.END) # Clear text area after adding
            self._set_ui_state("page_selected") # Return to page_selected state
        else:
            self.set_status("Failed to add feedback.", "red")
            messagebox.showerror("Add Feedback Failed", "Failed to add feedback to database.", parent=self.master)

    def _update_feedback(self):
        if not self.current_selected_feedback_id:
            messagebox.showwarning("No Feedback Selected", "Please select feedback to update.", parent=self.master)
            return
        
        new_feedback_text = self.feedback_text_area.get(1.0, tk.END).strip()
        if not new_feedback_text:
            messagebox.showwarning("No Feedback Text", "Feedback text cannot be empty.", parent=self.master)
            return
        
        confirm = messagebox.askyesno("Confirm Update", "Are you sure you want to update this feedback?", parent=self.master)
        if confirm:
            success = database_manager.update_feedback(self.current_selected_feedback_id, new_feedback_text)
            if success:
                self.set_status("Feedback updated successfully.", "green")
                self._populate_feedback_listbox()
                self.feedback_text_area.delete(1.0, tk.END) # Clear text area after updating
                self._set_ui_state("page_selected") # Return to page_selected state
            else:
                self.set_status("Failed to update feedback.", "red")
                messagebox.showerror("Update Feedback Failed", "Failed to update feedback in database.", parent=self.master)

    def _delete_feedback(self):
        if not self.current_selected_feedback_id:
            messagebox.showwarning("No Feedback Selected", "Please select feedback to delete.", parent=self.master)
            return
        
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this feedback entry?", icon='warning', parent=self.master)
        if confirm:
            success = database_manager.delete_feedback(self.current_selected_feedback_id)
            if success:
                self.set_status("Feedback deleted successfully.", "green")
                self._populate_feedback_listbox()
                self.feedback_text_area.delete(1.0, tk.END) # Clear text area after deletion
                self._set_ui_state("page_selected") # Return to page_selected state
            else:
                self.set_status("Failed to delete feedback.", "red")
                messagebox.showerror("Delete Feedback Failed", "Failed to delete feedback from database.", parent=self.master)

    def on_tab_focus(self):
        debug_gui_print("UserFeedbackTab focused.")
        self._set_ui_state("initial")
        # Ensure that the page list is fully updated first, then attempt to select the first page.
        # This callback is usually called by the main GUI, so `self.facebook_pages` should be up-to-date.
        page_names = [page["page_name"] for page in self.facebook_pages]
        self.update_page_selection_list(page_names)

        # After updating the list, if there are pages, try to trigger the selection for the first one
        if page_names:
            # Set the variable, then explicitly call the handler
            # This ensures the UI for the first page loads correctly on tab focus
            current_selected = self.selected_page_name_var.get()
            if current_selected not in page_names: # If previously selected page is gone or none, select first
                self.selected_page_name_var.set(page_names[0])
            # Always call _on_page_selected to ensure UI state is correct
            self._on_page_selected()