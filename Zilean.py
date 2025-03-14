import os
import json
import tkinter
import tkinter.messagebox
import customtkinter
import time
from Domain.Models.Card import Card
from Domain.Interfaces.IBoardIntegration import IBoardIntegration
from Infraestructure.JiraIntegration import JiraIntegration
import fontawesome as fa

CONFIG_FILE = "config.json"

# ICONS
START_ICON = f"{fa.icons['play']} Start"
PAUSE_BUTTON = text=f"{fa.icons['pause']} Pause"
STOP_BUTTON = f"{fa.icons['stop']} Stop"
CONTINUE_BUTTON = f"{fa.icons['play']} Continue"
TOGGLE_SHOW = fa.icons['chevron-right']
TOGGLE_HIDE = fa.icons['chevron-left']
INFO_ICON = fa.icons['info-circle']
REFRESH_ICON = fa.icons['history']

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):

    def __init__(self):
        super().__init__()
        
        self.title("Jira Time Tracker")
        self.geometry(f"{800}x{400}")

        # Initialize variables for credentials
        self.jira_server: str | None = None
        self.email: str | None = None
        self.token: str | None = None

        # Timer variables
        self.running: bool = False
        self.paused: bool = False
        self.elapsed_time: float = 0
        self.start_time: float = 0

        # Initialize integration
        self.jira_integration: IBoardIntegration | None = None
        self.cards: list[Card] = []
        self.selected_card_obj: Card | None = None  # Store the selected card object here
        self.load_cards()

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

        self.settings_label = customtkinter.CTkLabel(self.settings_frame, text="Jira Configuration", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.settings_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        self.turotial_icon = customtkinter.CTkButton(
            self.settings_frame, 
            text=INFO_ICON, 
            width=30,  # Slightly wider to avoid being too thin
            height=30,  # Set a fixed height
            font=customtkinter.CTkFont(size=14),  # Adjust font size
            command=self.show_setup_tutorial
        )

        self.turotial_icon.grid(row=0, column=1, padx=(0, 5), pady=(0, 5))  # Move to bottom row

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
        self.save_button = customtkinter.CTkButton(self.settings_frame, text="Save", command=self.save_credentials)
        self.save_button.grid(row=7, column=0, padx=20, pady=(20, 10), sticky="ew")

    def show_setup_tutorial(self):
        tkinter.messagebox.showinfo(
            "Setup Tutorial", 
            """
                1. Access the url: https://id.atlassian.com/manage-profile/security/api-tokens
                2. Create a token
            """
        )

    def create_main_screen(self):
        """Create the main screen with the timer and card selection."""
        self.main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        
        # Set up grid configuration to ensure proper layout
        self.main_frame.grid_columnconfigure(1, weight=1)  # Ensure column 1 expands
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)

        # Create sidebar frame
        self.sidebar_frame: customtkinter.CTkFrame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=10, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        self.logo_label: customtkinter.CTkLabel = customtkinter.CTkLabel(self.sidebar_frame, text="Jira Time Tracker", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # configurações button
        self.sidebar_button_1: customtkinter.CTkButton = customtkinter.CTkButton(self.sidebar_frame, text="Configurations", command=self.show_settings_screen)
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)

        # appearance mode option
        self.appearance_mode_label: customtkinter.CTkLabel = customtkinter.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=2, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu: customtkinter.CTkOptionMenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"], command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=3, column=0, padx=20, pady=(10, 10))
        self.appearance_mode_optionemenu.set("Dark")

        # Create dropdown select for cards
        self.card_select_frame: customtkinter.CTkFrame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        self.card_select_frame.grid(row=0, column=1, padx=20, pady=(20, 0), sticky="nsew")

        self.card_select_label: customtkinter.CTkLabel = customtkinter.CTkLabel(self.card_select_frame, text="Select the Card:", font=customtkinter.CTkFont(size=16))
        self.card_select_label.grid(row=0, column=0, padx=20, pady=(0, 5), sticky="w")

        self.card_select_frame.grid_columnconfigure(1, weight=1)

        self.selected_card: tkinter.StringVar = tkinter.StringVar()
        self.selected_card.trace_add("write", self.on_card_selected)  # Track changes to selected card
        self.card_select: customtkinter.CTkOptionMenu = customtkinter.CTkOptionMenu(self.card_select_frame, 
                                                                                    variable=self.selected_card, 
                                                                                    values=[card.name for card in self.cards], 
                                                                                    )
        self.card_select.grid(row=0, column=1, padx=20, pady=(0, 5), sticky="ew")
        self.card_select.set(self.cards[0].name)

        self.refresh_cards_button: customtkinter.CTkButton = customtkinter.CTkButton(self.card_select_frame, text=REFRESH_ICON, command=self.load_cards)
        self.refresh_cards_button.grid(row=0, column=2, padx=0, sticky="w")

        # Central frame for timer and buttons
        self.timer_control_frame: customtkinter.CTkFrame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        self.timer_control_frame.grid(row=1, column=1, padx=20, pady=10, sticky="n")

        # Timer label
        self.timer_label: customtkinter.CTkLabel = customtkinter.CTkLabel(self.timer_control_frame, text="00:00:00", font=customtkinter.CTkFont(size=80, weight="bold"))
        self.timer_label.grid(row=0, column=0, columnspan=3, padx=20, pady=(50, 5), sticky="ew")

        self.estimated_duration_label: customtkinter.CTkLabel = customtkinter.CTkLabel(self.timer_control_frame, text="Estimated Time: 00:00:00", font=customtkinter.CTkFont(size=15), text_color="#3B8ED0")
        self.estimated_duration_label.grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 5), sticky="ew")

        # Control buttons (Start, Pause, Stop)
        self.start_button: customtkinter.CTkButton = customtkinter.CTkButton(self.timer_control_frame, text=START_ICON, command=self.start_timer)
        self.start_button.grid(row=2, column=0, padx=10, pady=10, sticky="w")

        self.pause_button: customtkinter.CTkButton = customtkinter.CTkButton(self.timer_control_frame, text=PAUSE_BUTTON, command=self.pause_timer)
        self.pause_button.grid(row=2, column=1, padx=10, pady=10, sticky="n")

        self.stop_button: customtkinter.CTkButton = customtkinter.CTkButton(self.timer_control_frame, text=STOP_BUTTON, command=self.stop_timer)
        self.stop_button.grid(row=2, column=2, padx=10, pady=10, sticky="e")

        # Add a button to toggle the sidebar visibility
        self.toggle_sidebar_button = customtkinter.CTkButton(
            self, 
            text=TOGGLE_HIDE, 
            width=30,  # Slightly wider to avoid being too thin
            height=30,  # Set a fixed height
            font=customtkinter.CTkFont(size=14),  # Adjust font size
            command=self.toggle_sidebar
        )
        self.toggle_sidebar_button.grid(row=3, column=0, sticky="sw", padx=(5, 0), pady=(0, 5))  # Move to bottom row

        # Allow the row to expand, pushing the button to the bottom
        self.grid_rowconfigure(3, weight=1)  # Adjust the row index if needed
        # Prevent the grid from resizing the button
        self.grid_rowconfigure(0, weight=0)  # Prevent row 0 from expanding
        self.grid_columnconfigure(0, weight=0)  # Prevent column 0 from expanding

    def toggle_sidebar(self):
        """Toggle the visibility of the sidebar."""
        if self.sidebar_frame.winfo_ismapped():
            self.sidebar_frame.grid_forget()
            self.toggle_sidebar_button.configure(text=TOGGLE_SHOW,)
        else:
            self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
            self.toggle_sidebar_button.configure(text=TOGGLE_HIDE)

    def on_card_selected(self, *args):
        """Callback function when a card is selected."""
        selected_name = self.selected_card.get()  # Get selected card name

        # Se o timer estiver rodando, pare-o antes de mudar de card
        if self.elapsed_time > 0:
            self.stop_timer()

        self.selected_card_obj = next((card for card in self.cards if card.name == selected_name), None)

        if hasattr(self, 'estimated_duration_label') and self.selected_card_obj:
            self.estimated_duration_label.configure(text=f"Estimated Time: {self.milesseconds_to_time(self.selected_card_obj.estimated_duration)}")

        if self.selected_card_obj:
            if hasattr(self, 'start_button') and self.start_button is not None:
                if self.selected_card_obj.time_spent > 0:
                    self.elapsed_time = self.selected_card_obj.time_spent
                    self.timer_label.configure(text=self.milesseconds_to_time(self.elapsed_time))
                    self.start_button.configure(text=CONTINUE_BUTTON)
                else:
                    self.elapsed_time = 0
                    if hasattr(self, 'timer_label') and self.timer_label is not None:
                        self.timer_label.configure(text="00:00:00")
                    self.start_button.configure(text=START_ICON)

                self.start_button.configure(state="normal")

        self.set_change_card_selector()

    def milesseconds_to_time(self, milliseconds: int) -> str:
        minutes, seconds = divmod(milliseconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def show_settings_screen(self):
        """Show the settings screen and hide the main screen."""
        if os.path.isfile(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        self.main_frame.grid_forget()  # Hide the main screen
        self.settings_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")  # Show the settings screen

    def show_main_screen(self):
        """Show the main screen after successful credential validation."""
        self.load_cards()
        self.settings_frame.grid_forget()  # Hide the settings screen
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")  # Show the main screen

    def load_cards(self, *args):
        if self.jira_server is not None and self.email is not None and self.token is not None:
            self.card_select.configure(state="disabled")
            self.jira_integration = JiraIntegration(self.jira_server, self.email, self.token)
            self.cards = self.jira_integration.get_cards()
            self.card_select.configure(values=[card.name for card in self.cards])
            self.card_select.configure(state="normal")
            
            if self.selected_card_obj and self.selected_card_obj.id:
                if self.selected_card_obj.id in [card.id for card in self.cards]:
                    self.selected_card.set(self.selected_card_obj.name)
                    self.selected_card_obj = next((card for card in self.cards if card.id == self.selected_card_obj.id), None)
                    self.on_card_selected()
                else:
                    self.selected_card.set(self.cards[0].name)
                    self.selected_card_obj = self.cards[0]
                    self.on_card_selected()
        else:
            self.cards = [Card("", "", "", 0, 0, "", [])]
            
    def save_credentials(self):
        """Save credentials to a local file and validate them."""
        self.jira_server = self.jira_server_entry.get()
        self.email = self.email_entry.get()
        self.token = self.token_entry.get()

        if self.jira_server and self.email and self.token:
            credentials = {"jira_server": self.jira_server, "email": self.email, "token": self.token}
            with open(CONFIG_FILE, "w") as config_file:
                json.dump(credentials, config_file)

            if self.validate_jira_credentials(self.jira_server, self.email, self.token):
                tkinter.messagebox.showinfo("Success", "Your credentials were successfully validated!")
                self.show_main_screen()
            else:
                tkinter.messagebox.showerror("Error", "Invalid credentials. Try again.")
        else:
            tkinter.messagebox.showerror("Error", "Every configuration fields are required.")

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
        return True  # Always returns true for this example

    def start_timer(self):
        if self.selected_card_obj is None or not self.selected_card_obj.id:
            tkinter.messagebox.showerror("Error", "Select a card before press start.")
            return

        if self.paused:
            self.stop_button.configure(state="normal")
            self.paused = False
            self.running = True
            self.start_button.configure(text=START_ICON)
            self.start_button.configure(state="disabled")
            self.start_time = time.time() - self.elapsed_time
            self.update_timer()
        else:
            if not self.running:
                self.running = True
                self.elapsed_time = 0
                self.start_time = time.time() - self.selected_card_obj.time_spent
                self.update_timer()
                self.start_button.configure(state="disabled")
                self.stop_button.configure(state="normal")

    def pause_timer(self):
        if self.running:
            self.running = False
            self.paused  = True
            self.start_button.configure(text=CONTINUE_BUTTON)
            self.start_button.configure(state="normal")
            self.elapsed_time = time.time() - self.start_time

    def stop_timer(self):
        if self.running or self.paused:
            self.stop_button.configure(state="disabled")

            self.running = False
            self.paused  = False
            print(f"Finished working on card: {self.selected_card_obj.name if self.selected_card_obj else 'None'}")

            if self.selected_card_obj is not None:
                self.elapsed_time -= self.selected_card_obj.time_spent

            print(f"Register elapsed time: {self.elapsed_time}")

            if self.elapsed_time < 60:
                if self.selected_card_obj is not None:
                    self.elapsed_time += self.selected_card_obj.time_spent
                self.paused  = True
                self.start_button.configure(state="normal") 
                self.start_button.configure(text=CONTINUE_BUTTON)
                tkinter.messagebox.showwarning("Warning", "It's only possible to register times greater than 60 seconds")
                return

            if self.selected_card_obj is not None:
                self.selected_card_obj.time_spent += int(self.elapsed_time)
                print(f"Total time spent on card: {self.selected_card_obj.time_spent}")
            
            # Save the time spent to the selected card
            if self.jira_integration is not None and self.selected_card_obj is not None:
                temp = self.selected_card_obj.time_spent
                self.selected_card_obj.time_spent = int(self.elapsed_time) 
                self.jira_integration.add_timespent_to_card(self.selected_card_obj)
                self.selected_card_obj.time_spent = temp
                tkinter.messagebox.showinfo("Info", f"Registered time: {int(self.elapsed_time)} seconds")

            # Reset timer and clear selection
            self.elapsed_time = 0
            self.start_button.configure(text=START_ICON)

    def update_timer(self):
        if self.running:
            self.elapsed_time = time.time() - self.start_time
            minutes, seconds = divmod(int(self.elapsed_time), 60)
            hours, minutes = divmod(minutes, 60)
            self.timer_label.configure(text=f"{hours:02}:{minutes:02}:{seconds:02}")
            self.after(1000, self.update_timer)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def set_change_card_selector(self):
        if  self.selected_card_obj is not None and self.selected_card_obj.possible_next_stages is not None and len(self.selected_card_obj.possible_next_stages) > 0:
            self.card_stage_selector_label: customtkinter.CTkLabel = customtkinter.CTkLabel(self.sidebar_frame, text="Card Stage manegement:", anchor="w")
            self.card_stage_selector_label.grid(row=4, column=0, padx=20, pady=(20, 10))
            
            self.selected_card_obj_current_stage: tkinter.StringVar = tkinter.StringVar()
            self.selected_card_obj_current_stage.trace_add("write", self.change_card_stage)
            
            self.card_stage_selector: customtkinter.CTkOptionMenu = customtkinter.CTkOptionMenu(self.sidebar_frame, 
                                                                                                variable=self.selected_card_obj_current_stage, 
                                                                                                values=[stage for stage in self.selected_card_obj.possible_next_stages], 
                                                                                            )
            self.card_stage_selector.grid(row=5, column=0, padx=20, pady=(0, 5), sticky="ew")
            self.card_stage_selector.set(self.selected_card_obj.current_stage)

    def change_card_stage(self, *args):
        if self.selected_card_obj is None:
            return
        
        if self.jira_integration is None:
            return

        current_stage = self.selected_card_obj.current_stage
        new_stage     = self.selected_card_obj_current_stage.get()

        if current_stage == new_stage:
            return

        print(f"Changing stage from {current_stage} to {new_stage}")
        try:
            if self.jira_integration.change_card_stage(self.selected_card_obj, new_stage):
                self.refresh_card(self.selected_card_obj)
                tkinter.messagebox.showinfo("Success", f"Successfully changed stage from {current_stage} to {new_stage}.")
            else:
                tkinter.messagebox.showerror("Error", f"Failed to change stage from {current_stage} to {new_stage}.")
        except:
            tkinter.messagebox.showerror("Error", f"Failed to change stage from {current_stage} to {new_stage}.")
 
    def refresh_card(self, card:Card):
        if self.jira_integration == None:
            return card
        
        refreshed_card: Card = self.jira_integration.refresh_card(card)
        self.selected_card_obj = refreshed_card
        
        self.card_stage_selector.configure(values=[stage for stage in refreshed_card.possible_next_stages])
        self.card_stage_selector.set(refreshed_card.current_stage)


if __name__ == "__main__":
    app = App()
    app.mainloop()