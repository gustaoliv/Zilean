import os
import json
import tkinter
import tkinter.messagebox
import customtkinter
import time
from Domain.Models.Card import Card
from Domain.Interfaces.IBoardIntegration import IBoardIntegration
from Infraestructure.JiraIntegration import JiraIntegration

CONFIG_FILE = "config.json"

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Jira Time Tracker")
        self.geometry(f"{1100}x{580}")

        # Initialize variables for credentials
        self.jira_server : str|None = None
        self.email : str|None = None
        self.token : str|None = None

        # Timer variables
        self.running:bool = False
        self.paused:bool = False
        self.elapsed_time = 0
        self.start_time = 0
        
        # Initiliaze integration
        self.jira_integration: IBoardIntegration|None = None
        self.cards: list[Card] = []
        self.update_cards()

        # Add initial grid config
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Create frames for settings and main app
        self.create_settings_screen()
        self.create_main_screen()

        # Load credentials from file or show settings screen
        if self.load_credentials():
            if self.validate_jira_credentials(self.jira_server, self.email, self.token):
                self.show_main_screen()  # Credentials are valid, go to main screen
            else:
                self.show_settings_screen()  # Invalid credentials, show settings
        else:
            self.show_settings_screen()  # No saved credentials, show settings

    def create_settings_screen(self):
        """Create the settings screen where the user inputs Jira credentials."""
        self.settings_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.settings_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.settings_label = customtkinter.CTkLabel(self.settings_frame, text="Configurações Jira", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.settings_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        # Jira server entry
        self.jira_server_label = customtkinter.CTkLabel(self.settings_frame, text="Jira Server:")
        self.jira_server_label.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="w")
        self.jira_server_entry = customtkinter.CTkEntry(self.settings_frame, placeholder_text="https://jira.server.com")
        self.jira_server_entry.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")

        # User email entry
        self.email_label = customtkinter.CTkLabel(self.settings_frame, text="User Email:")
        self.email_label.grid(row=3, column=0, padx=20, pady=(10, 5), sticky="w")
        self.email_entry = customtkinter.CTkEntry(self.settings_frame, placeholder_text="email@example.com")
        self.email_entry.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")

        # Access token entry
        self.token_label = customtkinter.CTkLabel(self.settings_frame, text="Access Token:")
        self.token_label.grid(row=5, column=0, padx=20, pady=(10, 5), sticky="w")
        self.token_entry = customtkinter.CTkEntry(self.settings_frame, placeholder_text="Your Jira access token", show="*")
        self.token_entry.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="ew")

        # Save button
        self.save_button = customtkinter.CTkButton(self.settings_frame, text="Salvar", command=self.save_credentials)
        self.save_button.grid(row=7, column=0, padx=20, pady=(20, 10), sticky="ew")

    def create_main_screen(self):
        """Create the main screen with the timer and card selection."""
        self.main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        
        # Set up grid configuration to ensure proper layout
        self.main_frame.grid_columnconfigure(1, weight=1)  # Ensure column 1 expands
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)

        # create sidebar frame
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="Jira Time Tracker", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # configurações button
        self.sidebar_button_1 = customtkinter.CTkButton(self.sidebar_frame, text="Configurações", command=self.show_settings_screen)
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)

        # appearance mode option
        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=2, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"], command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=3, column=0, padx=20, pady=(10, 10))
        self.appearance_mode_optionemenu.set("Dark")

        # Create dropdown select for cards
        self.card_select_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        self.card_select_frame.grid(row=0, column=1, padx=20, pady=(20, 0), sticky="nsew")

        self.card_select_label = customtkinter.CTkLabel(self.card_select_frame, text="Selecione o Card:", font=customtkinter.CTkFont(size=16))
        self.card_select_label.grid(row=0, column=0, padx=20, pady=(0, 5), sticky="w")

        self.card_select_frame.grid_columnconfigure(1, weight=1)

        self.selected_card = tkinter.StringVar()
        self.card_select = customtkinter.CTkOptionMenu(self.card_select_frame, variable=self.selected_card, values=[card.name for card in self.cards])
        self.card_select.grid(row=0, column=1, padx=20, pady=(0, 5), sticky="ew")
        self.card_select.set(self.cards[0].name)

        # Central frame for timer and buttons
        self.timer_control_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        self.timer_control_frame.grid(row=1, column=1, padx=20, pady=10, sticky="n")

        # Timer label
        self.timer_label = customtkinter.CTkLabel(self.timer_control_frame, text="00:00:00", font=customtkinter.CTkFont(size=40, weight="bold"))
        self.timer_label.grid(row=0, column=0, columnspan=3, padx=20, pady=(50, 20), sticky="ew")

        # Control buttons (Start, Pause, Stop)
        self.start_button = customtkinter.CTkButton(self.timer_control_frame, text="Start", command=self.start_timer)
        self.start_button.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        self.pause_button = customtkinter.CTkButton(self.timer_control_frame, text="Pause", command=self.pause_timer)
        self.pause_button.grid(row=1, column=1, padx=10, pady=10, sticky="n")

        self.stop_button = customtkinter.CTkButton(self.timer_control_frame, text="Stop", command=self.stop_timer)
        self.stop_button.grid(row=1, column=2, padx=10, pady=10, sticky="e")

    def show_settings_screen(self):
        """Show the settings screen and hide the main screen."""

        if os.path.isfile(CONFIG_FILE):
            os.remove(CONFIG_FILE)

        self.main_frame.grid_forget()  # Hide the main screen
        self.settings_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")  # Show the settings screen

    def show_main_screen(self):
        """Show the main screen after successful credential validation."""
        self.settings_frame.grid_forget()  # Hide the settings screen
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")  # Show the main screen
        self.update_cards()
        
    def update_cards(self):
        if self.jira_server is not None and self.email is not None and self.token is not None:
            self.jira_integration = JiraIntegration(self.jira_server, self.email, self.token)
            self.cards = self.jira_integration.get_cards()
            self.card_select.configure(values=[card.name for card in self.cards])
        else:
            self.cards = [Card("", "", "", 0, 0)]

    def save_credentials(self):
        """Save credentials to a local file and validate them."""
        jira_server = self.jira_server_entry.get()
        email = self.email_entry.get()
        token = self.token_entry.get()

        if jira_server and email and token:
            # Save the credentials in a JSON file
            credentials = {
                "jira_server": jira_server,
                "email": email,
                "token": token
            }
            with open(CONFIG_FILE, "w") as config_file:
                json.dump(credentials, config_file)

            # Validate credentials (dummy validation here)
            if self.validate_jira_credentials(jira_server, email, token):
                tkinter.messagebox.showinfo("Success", "Credenciais válidas!")
                self.show_main_screen()
            else:
                tkinter.messagebox.showerror("Error", "Credenciais inválidas. Tente novamente.")
        else:
            tkinter.messagebox.showerror("Error", "Todos os campos são obrigatórios.")

    def load_credentials(self):
        """Load credentials from a local file if it exists."""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as config_file:
                credentials = json.load(config_file)
                self.jira_server = credentials.get("jira_server")
                self.email = credentials.get("email")
                self.token = credentials.get("token")
            return True
        return False

    def validate_jira_credentials(self, server, email, token):
        """Dummy function to simulate Jira credential validation."""
        # Replace this with real Jira API authentication logic
        return True  # Always returns true for this example

    def start_timer(self):
        if self.paused:  # If paused, resume the timer and change the button text to "Continue"
            self.paused = False
            self.running = True
            self.start_button.configure(text="Start")
            self.start_time = time.time() - self.elapsed_time
            self.update_timer()
        else:
            if not self.running:  # If not running, start the timer
                self.running = True
                self.start_time = time.time() - self.elapsed_time
                self.update_timer()

    def pause_timer(self):
        if self.running:
            self.running = False
            self.paused = True
            self.start_button.configure(text="Continue")  # Change the start button text to "Continue"
            self.elapsed_time = time.time() - self.start_time

    def stop_timer(self):
        self.running = False
        self.paused = False
        self.elapsed_time = 0
        self.timer_label.configure(text="00:00:00")
        self.start_button.configure(text="Start")  # Reset the start button text

    def update_timer(self):
        if self.running:
            self.elapsed_time = time.time() - self.start_time
            minutes, seconds = divmod(int(self.elapsed_time), 60)
            hours, minutes = divmod(minutes, 60)
            self.timer_label.configure(text=f"{hours:02}:{minutes:02}:{seconds:02}")
            self.after(1000, self.update_timer)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

if __name__ == "__main__":
    app = App()
    app.mainloop()
