# D:\Facebook_Posts_generation\gui_common_dialogs.py

import tkinter as tk
from tkinter import ttk, simpledialog # Import simpledialog here, as MultilineTextDialog inherits from it

class MultilineTextDialog(simpledialog.Dialog):
    """
    A custom dialog that provides a multi-line text input field with a scrollbar.
    """
    def __init__(self, parent, title=None, prompt=None, initialvalue=""):
        self.prompt_text = prompt
        self.initial_value = initialvalue
        self.result = None # This will hold the text from the widget after apply()
        super().__init__(parent, title)

    def body(self, master):
        if self.prompt_text:
            # Using tk.Label for the prompt text
            tk.Label(master, text=self.prompt_text, wraplength=400, justify=tk.LEFT).pack(pady=5, padx=5, anchor="w")
        
        # Frame to hold the Text widget and its scrollbar
        text_frame = ttk.Frame(master)
        text_frame.pack(expand=True, fill="both", padx=5, pady=5)
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        self.text_widget = tk.Text(text_frame, wrap="word", height=15, width=80) # Increased height and width
        self.text_widget.grid(row=0, column=0, sticky="nsew")
        self.text_widget.insert("1.0", self.initial_value)
        
        # Add a scrollbar
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.text_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text_widget.config(yscrollcommand=scrollbar.set)
        
        return self.text_widget # Set initial focus to the text widget

    def apply(self):
        # This method is called when the dialog is closed with OK
        self.result = self.text_widget.get("1.0", tk.END).strip()

# Example usage (for testing this dialog independently):
if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw() # Hide the root window

    # Test the MultilineTextDialog
    dialog = MultilineTextDialog(root, 
                                 title="Enter Multi-line Text", 
                                 prompt="Please enter multiple lines of text here:",
                                 initialvalue="Line 1\nLine 2\nLine 3")
    
    if dialog.result is not None:
        print("User entered:")
        print(dialog.result)
    else:
        print("Dialog cancelled.")
    
    root.destroy()