# D:\Facebook_Posts_generation\gui_page_details_tab.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog # Import simpledialog
import os
import json
import threading
import re

# Assuming gui_common_dialogs is in the same directory
try:
    from gui_common_dialogs import MultilineTextDialog
except ImportError:
    messagebox.showwarning("Import Error", "Could not import MultilineTextDialog. Ensure gui_common_dialogs.py is in the same directory.")
    class MultilineTextDialog:
        def __init__(self, *args, **kwargs):
            messagebox.showerror("Error", "MultilineTextDialog is not available. Please check gui_common_dialogs.py")
            raise NotImplementedError("MultilineTextDialog is required but not found.")

# Assuming database_manager is in the same directory
import database_manager

# --- Debugging setup ---
DEBUG_GUI_MODE = True

def debug_gui_print(message):
    if DEBUG_GUI_MODE:
        print(f"[DEBUG - GUI - PageDetails]: {message}")

class PageDetailsTab(ttk.Frame):
    def __init__(self, parent, facebook_pages_ref, set_status_callback,
                 save_config_callback, update_all_page_lists_and_selections_callback):
        super().__init__(parent)
        debug_gui_print("PageDetailsTab.__init__ started.")

        self.facebook_pages = facebook_pages_ref
        self.set_status = set_status_callback
        self.save_config_callback = save_config_callback
        self.update_all_page_lists_and_selections_callback = update_all_page_lists_and_selections_callback

        # Internal state variables for the tab
        self.page_name_var = tk.StringVar()
        self.facebook_page_id_var = tk.StringVar()
        self.facebook_access_token_var = tk.StringVar()
        self.english_contact_info_var = tk.StringVar()
        self.arabic_contact_info_var = tk.StringVar()

        self.current_selected_page_index_detail_tab = -1 # Index of the currently selected page in the listbox

        self._create_widgets()
        debug_gui_print("PageDetailsTab widgets created.")
        debug_gui_print("PageDetailsTab.__init__ finished.")

    def _create_widgets(self):
        debug_gui_print("_create_widgets (PageDetailsTab) called.")

        # Page selection frame
        page_select_frame = ttk.LabelFrame(self, text="Select/Manage Facebook Pages")
        page_select_frame.pack(pady=10, padx=10, fill="x")

        ttk.Label(page_select_frame, text="Select Page:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.page_selection_combobox = ttk.Combobox(page_select_frame, textvariable=self.page_name_var, values=[], state="readonly")
        self.page_selection_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.page_selection_combobox.bind("<<ComboboxSelected>>", self._on_page_selected)
        page_select_frame.columnconfigure(1, weight=1)

        page_buttons_frame = ttk.Frame(page_select_frame)
        page_buttons_frame.grid(row=1, column=0, columnspan=2, pady=5)
        ttk.Button(page_buttons_frame, text="Add New Page", command=self._add_page).pack(side="left", padx=5)
        self.save_page_button = ttk.Button(page_buttons_frame, text="Update Selected Page", command=self._update_page_details)
        self.save_page_button.pack(side="left", padx=5)
        self.delete_page_button = ttk.Button(page_buttons_frame, text="Delete Selected Page", command=self._delete_page)
        self.delete_page_button.pack(side="left", padx=5)


        # Page details entry frame
        details_frame = ttk.LabelFrame(self, text="Edit Page Details")
        details_frame.pack(pady=10, padx=10, fill="x")
        details_frame.columnconfigure(1, weight=1) # Make the entry fields expand

        ttk.Label(details_frame, text="Page Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.page_name_entry = ttk.Entry(details_frame, textvariable=self.page_name_var, width=50)
        self.page_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.page_name_entry.config(state="disabled")

        ttk.Label(details_frame, text="Facebook Page ID:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.fb_page_id_entry = ttk.Entry(details_frame, textvariable=self.facebook_page_id_var, width=50)
        self.fb_page_id_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.fb_page_id_entry.config(state="disabled")

        ttk.Label(details_frame, text="Facebook Access Token:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.fb_access_token_entry = ttk.Entry(details_frame, textvariable=self.facebook_access_token_var, show="*" if os.getenv("HIDE_TOKENS") == "true" else "")
        self.fb_access_token_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        self.fb_access_token_entry.config(state="disabled")


        # Contact Info
        ttk.Label(details_frame, text="English Contact Info:").grid(row=3, column=0, sticky="nw", padx=5, pady=2)
        self.english_contact_info_text = tk.Text(details_frame, wrap="word", height=5, width=50)
        self.english_contact_info_text.grid(row=3, column=1, sticky="ew", padx=5, pady=2)
        self.english_contact_info_scrollbar = ttk.Scrollbar(details_frame, orient="vertical", command=self.english_contact_info_text.yview)
        self.english_contact_info_scrollbar.grid(row=3, column=2, sticky="ns")
        self.english_contact_info_text.config(yscrollcommand=self.english_contact_info_scrollbar.set)
        self.english_contact_info_text.config(state="disabled")

        ttk.Label(details_frame, text="Arabic Contact Info:").grid(row=4, column=0, sticky="nw", padx=5, pady=2)
        self.arabic_contact_info_text = tk.Text(details_frame, wrap="word", height=5, width=50)
        self.arabic_contact_info_text.grid(row=4, column=1, sticky="ew", padx=5, pady=2)
        self.arabic_contact_info_scrollbar = ttk.Scrollbar(details_frame, orient="vertical", command=self.arabic_contact_info_text.yview)
        self.arabic_contact_info_scrollbar.grid(row=4, column=2, sticky="ns")
        self.arabic_contact_info_text.config(yscrollcommand=self.arabic_contact_info_scrollbar.set)
        self.arabic_contact_info_text.config(state="disabled")

        # Save Button
        save_button = ttk.Button(details_frame, text="Save Page Details", command=self._update_page_details) # Corrected command here
        save_button.grid(row=5, column=0, columnspan=2, pady=10)

        details_frame.columnconfigure(1, weight=1)

        self._clear_page_details_ui()
        debug_gui_print("_create_widgets (PageDetailsTab) finished.")

    def _on_page_selected(self, event=None):
        debug_gui_print(f"--- _on_page_selected (PageDetailsTab) called. Selected: {self.page_name_var.get()}")
        selected_page_name = self.page_name_var.get()
        found_index = -1
        for i, page in enumerate(self.facebook_pages):
            if page["page_name"] == selected_page_name:
                found_index = i
                break

        if found_index != -1:
            self.current_selected_page_index_detail_tab = found_index
            self._load_page_details_into_ui(self.facebook_pages[found_index])
            self._enable_page_details_editing()
            self.set_status(f"Page '{selected_page_name}' loaded for editing.", "black")
        else:
            debug_gui_print("Selected page not found in data. Clearing UI.")
            self.current_selected_page_index_detail_tab = -1
            self._clear_page_details_ui()
            self.set_status("No page selected or page not found.", "red")
        debug_gui_print("--- _on_page_selected (PageDetailsTab) finished.")

    def _load_page_details_into_ui(self, page_data):
        debug_gui_print(f"_load_page_details_into_ui (PageDetailsTab) called for: {page_data.get('page_name', 'N/A')}")
        self.page_name_var.set(page_data.get("page_name", ""))
        self.facebook_page_id_var.set(page_data.get("facebook_page_id", ""))
        self.facebook_access_token_var.set(page_data.get("facebook_access_token", ""))

        self.english_contact_info_text.config(state=tk.NORMAL)
        self.english_contact_info_text.delete("1.0", tk.END)
        self.english_contact_info_text.insert(tk.END, page_data.get("english_contact_info", ""))
        self.english_contact_info_text.config(state=tk.DISABLED)

        self.arabic_contact_info_text.config(state=tk.NORMAL)
        self.arabic_contact_info_text.delete("1.0", tk.END)
        self.arabic_contact_info_text.insert(tk.END, page_data.get("arabic_contact_info", ""))
        self.arabic_contact_info_text.config(state=tk.DISABLED)
        
        debug_gui_print("Page details loaded into UI fields.")

    def _clear_page_details_ui(self):
        debug_gui_print("_clear_page_details_ui (PageDetailsTab) called.")
        self.page_name_var.set("")
        self.facebook_page_id_var.set("")
        self.facebook_access_token_var.set("")

        self.english_contact_info_text.config(state=tk.NORMAL)
        self.english_contact_info_text.delete("1.0", tk.END)
        self.english_contact_info_text.insert(tk.END, "")
        self.english_contact_info_text.config(state="disabled")

        self.arabic_contact_info_text.config(state=tk.NORMAL)
        self.arabic_contact_info_text.delete("1.0", tk.END)
        self.arabic_contact_info_text.insert(tk.END, "")
        self.arabic_contact_info_text.config(state="disabled")

        self.page_name_entry.config(state="disabled")
        self.fb_page_id_entry.config(state="disabled")
        self.fb_access_token_entry.config(state="disabled")
        self.save_page_button.config(state="disabled")
        self.delete_page_button.config(state="disabled")
        debug_gui_print("Page details UI cleared and disabled.")

    def _enable_page_details_editing(self):
        debug_gui_print("_enable_page_details_editing (PageDetailsTab) called.")
        self.page_name_entry.config(state="normal")
        self.fb_page_id_entry.config(state="normal")
        self.fb_access_token_entry.config(state="normal")
        self.english_contact_info_text.config(state="normal")
        self.arabic_contact_info_text.config(state="normal")
        self.save_page_button.config(state="normal")
        self.delete_page_button.config(state="normal")
        debug_gui_print("Page details editing enabled.")

    def _disable_page_details_editing(self):
        debug_gui_print("_disable_page_details_editing (PageDetailsTab) called.")
        self.page_name_entry.config(state="disabled")
        self.fb_page_id_entry.config(state="disabled")
        self.fb_access_token_entry.config(state="disabled")
        self.english_contact_info_text.config(state="disabled")
        self.arabic_contact_info_text.config(state="disabled")
        debug_gui_print("Page details editing disabled.")

    def _add_page(self):
        debug_gui_print("_add_page (PageDetailsTab) called.")
        from tkinter import simpledialog # Import simpledialog locally where used, if not already global
        new_page_name = simpledialog.askstring("Add New Page", "Enter the name for the new Facebook page:")
        if new_page_name:
            new_page_name = new_page_name.strip()
            if not new_page_name:
                messagebox.showwarning("Input Error", "Page name cannot be empty.")
                debug_gui_print("Add page cancelled: empty name.")
                return

            existing_page_names = {p["page_name"].lower() for p in self.facebook_pages}
            if new_page_name.lower() in existing_page_names:
                messagebox.showwarning("Warning", f"A page with the name '{new_page_name}' already exists.")
                debug_gui_print(f"Attempted to add existing page '{new_page_name}' to page.")
                return

            new_page_data = {
                "page_name": new_page_name,
                "facebook_page_id": "YOUR_FACEBOOK_PAGE_ID",
                "facebook_access_token": "YOUR_LONG_LIVED_PAGE_ACCESS_TOKEN",
                "english_contact_info": "Website: \nTax ID: \nAddress: \nPostal Code : \nLocation: ",
                "arabic_contact_info": "الموقع الاكترونى: \nتسجيل ضريبى: \nالعنوان: \nاللوكيشن: ",
                "topics": [] # Initialize with an empty topics list
            }
            self.facebook_pages.append(new_page_data)
            self.current_selected_page_index_detail_tab = len(self.facebook_pages) - 1
            debug_gui_print(f"New page '{new_page_name}' added to internal list.")

            self.update_all_page_lists_and_selections_callback()
            self.page_name_var.set(new_page_name)
            self._load_page_details_into_ui(new_page_data)
            self._enable_page_details_editing()

            self.save_config_callback()
            self.set_status(f"Page '{new_page_name}' added and saved. Please fill in details.", "blue")
            messagebox.showinfo("New Page Added", f"Page '{new_page_name}' has been added. Please fill in its Facebook ID, Access Token, and Contact Info, then click 'Update Selected Page'.")
        else:
            debug_gui_print("Add page cancelled by user.")
            self.set_status("Add page cancelled.", "gray")

    def _update_page_details(self):
        debug_gui_print("_update_page_details (PageDetailsTab) called.")
        if self.current_selected_page_index_detail_tab == -1 or \
           self.current_selected_page_index_detail_tab >= len(self.facebook_pages):
            messagebox.showwarning("Warning", "No page selected to update.")
            debug_gui_print("Update page cancelled: no page selected.")
            return

        current_page_data = self.facebook_pages[self.current_selected_page_index_detail_tab]
        old_page_name = current_page_data["page_name"]

        new_page_name = self.page_name_var.get().strip()
        new_fb_id = self.facebook_page_id_var.get().strip()
        new_fb_token = self.facebook_access_token_var.get().strip()
        new_en_contact = self.english_contact_info_text.get("1.0", tk.END).strip()
        new_ar_contact = self.arabic_contact_info_text.get("1.0", tk.END).strip()

        if not new_page_name:
            messagebox.showwarning("Input Error", "Page name cannot be empty.")
            debug_gui_print("Update page cancelled: empty name.")
            return

        for i, page in enumerate(self.facebook_pages):
            if i != self.current_selected_page_index_detail_tab and page["page_name"].lower() == new_page_name.lower():
                messagebox.showwarning("Warning", f"A page with the name '{new_page_name}' already exists. Please choose a different name.")
                debug_gui_print(f"Update page cancelled: name '{new_page_name}' already in use.")
                return

        # Update the data in memory
        current_page_data["page_name"] = new_page_name
        current_page_data["facebook_page_id"] = new_fb_id
        current_page_data["facebook_access_token"] = new_fb_token
        current_page_data["english_contact_info"] = new_en_contact
        current_page_data["arabic_contact_info"] = new_ar_contact
        debug_gui_print(f"Page details for '{old_page_name}' updated in memory.")

        self.save_config_callback()

        if old_page_name != new_page_name:
            debug_gui_print(f"Page name changed from '{old_page_name}' to '{new_page_name}'. Updating all page selection lists.")
            self.update_all_page_lists_and_selections_callback()
            self.page_name_var.set(new_page_name)
        else:
            self.update_all_page_lists_and_selections_callback()

        self.set_status(f"Page '{new_page_name}' details updated and SAVED.", "green")
        messagebox.showinfo("Success", f"Page '{new_page_name}' details updated and saved.")
        debug_gui_print("_update_page_details (PageDetailsTab) finished.")


    def _delete_page(self):
        debug_gui_print("_delete_page (PageDetailsTab) called.")
        if self.current_selected_page_index_detail_tab == -1 or \
           self.current_selected_page_index_detail_tab >= len(self.facebook_pages):
            messagebox.showwarning("Warning", "No page selected to delete.")
            debug_gui_print("Delete page cancelled: no page selected.")
            return

        page_to_delete_name = self.facebook_pages[self.current_selected_page_index_detail_tab]["page_name"]
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the page '{page_to_delete_name}' and all its associated topics? This cannot be undone.")

        if confirm:
            del self.facebook_pages[self.current_selected_page_index_detail_tab]
            self.current_selected_page_index_detail_tab = -1
            debug_gui_print(f"Page '{page_to_delete_name}' deleted from internal list.")

            self.save_config_callback()
            self._clear_page_details_ui()
            self.update_all_page_lists_and_selections_callback()

            self.set_status(f"Page '{page_to_delete_name}' deleted and SAVED.", "green")
            messagebox.showinfo("Success", f"Page '{page_to_delete_name}' deleted and saved.")
        else:
            debug_gui_print("Delete page cancelled by user.")
            self.set_status("Delete page cancelled.", "gray")


    def update_page_selection_list(self, page_names, current_selected_page_name):
        """
        Public method to update the combobox with available page names and
        try to re-select the currently active page.
        This is called by the main GUI when pages are added/removed/renamed.
        """
        debug_gui_print("PageDetailsTab.update_page_selection_list called.")
        self.page_selection_combobox['values'] = page_names
        if current_selected_page_name in page_names:
            self.page_name_var.set(current_selected_page_name)
            for i, page in enumerate(self.facebook_pages):
                if page["page_name"] == current_selected_page_name:
                    self.current_selected_page_index_detail_tab = i
                    self._load_page_details_into_ui(page)
                    self._enable_page_details_editing()
                    break
        elif page_names:
            self.page_name_var.set(page_names[0])
            self.current_selected_page_index_detail_tab = 0
            self._load_page_details_into_ui(self.facebook_pages[0])
            self._enable_page_details_editing()
        else:
            self.page_name_var.set("")
            self.current_selected_page_index_detail_tab = -1
            self._clear_page_details_ui()
        debug_gui_print("PageDetailsTab.update_page_selection_list finished.")