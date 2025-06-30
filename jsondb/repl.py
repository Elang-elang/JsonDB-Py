import sys
import os
import json
from typing import Any, Dict, List, Union, Optional
import signal
import atexit

# Import components
from jsondb.core import JsonDB

# Import for advanced terminal features
try:
    from prompt_toolkit import prompt
    from prompt_toolkit.completion import WordCompleter, Completer, Completion
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.shortcuts import confirm
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.styles import Style
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False
    print("⚠️  For advanced features (tab completion, history), install: pip install prompt-toolkit")


class JsonDBCompleter(Completer):
    """
    Custom completer for JsonDB REPL that provides tab completion
    based on current mode and available context
    """
    
    def __init__(self, repl_instance):
        self.repl = repl_instance
    
    def get_completions(self, document, complete_event):
        """
        Generator that yields completion suggestions based on
        current input and REPL mode
        """
        # Get text before cursor position
        text_before_cursor = document.text_before_cursor
        current_word = document.get_word_before_cursor()
        
        # Completion for commands (starting with .)
        if text_before_cursor.startswith('.'):
            mode_commands = self.repl.commands.get(self.repl.mode, {})
            for command in mode_commands.keys():
                if command.startswith(text_before_cursor):
                    # Provide completion with trailing space for commands that need arguments
                    if command in ['.open', '.create', '.use', '.info', '.list']:
                        yield Completion(command + ' ', start_position=-len(text_before_cursor))
                    else:
                        yield Completion(command, start_position=-len(text_before_cursor))
        
        # Completion for JSON filenames when using .open
        elif text_before_cursor.startswith('.open '):
            file_part = text_before_cursor[6:]  # Get part after '.open '
            json_files = self._get_json_files()
            for file_path in json_files:
                if file_path.startswith(file_part):
                    yield Completion(file_path, start_position=-len(file_part))
        
        # Completion for .list with options
        elif text_before_cursor.startswith('.list '):
            options = ['--tables', '--files', '--all']
            option_part = text_before_cursor[6:]  # Get part after '.list '
            for option in options:
                if option.startswith(option_part):
                    yield Completion(option, start_position=-len(option_part))
        
        # Completion for table names
        elif text_before_cursor.startswith(('.use ', '.info ')):
            if self.repl.db:
                command_part = text_before_cursor.split(' ', 1)
                if len(command_part) > 1:
                    table_part = command_part[1]
                    tables = self.repl.db.list_tables()
                    for table in tables:
                        if table.startswith(table_part):
                            yield Completion(table, start_position=-len(table_part))
    
    def _get_json_files(self) -> List[str]:
        """Find all JSON files in current directory and subdirectories"""
        json_files = []
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    # Normalize path for cleaner display
                    if file_path.startswith('./'):
                        file_path = file_path[2:]
                    json_files.append(file_path)
        return json_files

class JsonDBREPL:
    """
    REPL (Read-Eval-Print Loop) interface for JsonDB with advanced features
    like tab completion, history navigation, and auto-save
    """
    
    def __init__(self, auto_open_file=None):
        self.db = None
        self.current_db_path = None
        self.mode = "main"
        self.current_table = None
        self.current_key = None  # For dict navigation
        
        # Setup for advanced terminal features
        self.history = InMemoryHistory() if HAS_PROMPT_TOOLKIT else []
        self.completer = JsonDBCompleter(self) if HAS_PROMPT_TOOLKIT else None
        self.auto_save_enabled = True
        
        # Setup signal handlers for auto-save
        self._setup_signal_handlers()
        
        # Style for more attractive prompts
        self.style = Style.from_dict({
            'prompt': '#00ff88 bold',
            'mode': '#ff6b35 bold',
            'path': '#4ecdc4',
            'key': '#ffe66d bold',
        }) if HAS_PROMPT_TOOLKIT else None
        
        # Dictionary to store command handlers by mode
        self.commands = {
            "main": {
                ".help": self.show_help,
                ".build": self.build_mode,
                ".open": self.open_database,
                ".list": self.list_command,
                ".info": self.show_db_info,
                ".exit": self.exit_program,
                ".quit": self.exit_program,
                ".clear": self.clear_screen
            },
            "build": {
                ".back": self.back_to_main,
                ".create": self.create_table,
                ".tables": self.list_tables,
                ".use": self.use_table,
                ".info": self.show_table_info,
                ".help": self.show_build_help,
                ".save": self.manual_save,
                ".list": self.list_command
            },
            "table": {
                ".back": self.back_to_build,
                ".insert": self.insert_data,
                ".update": self.update_data,
                ".delete": self.delete_data,
                ".show": self.show_table_data,
                ".clear": self.clear_table,
                ".help": self.show_table_help,
                ".save": self.manual_save,
                ".list": self.list_command
            }
        }
        
        # Auto-open file if provided
        if auto_open_file:
            self.auto_open_database(auto_open_file)
    
    def auto_open_database(self, file_path):
        """Automatically open database file on startup"""
        if os.path.exists(file_path):
            try:
                self.db = JsonDB(file_path)
                self.current_db_path = file_path
                self.mode = "build"
                print(f"🚀 Auto-opened database: {file_path}")
                tables = self.db.list_tables()
                if tables:
                    print(f"📋 Available tables: {', '.join(tables)}")
            except Exception as e:
                print(f"❌ Failed to auto-open database: {e}")
        else:
            print(f"⚠️  File '{file_path}' not found, starting in normal mode")
    
    def _setup_signal_handlers(self):
        """
        Setup signal handlers for auto-save when program is terminated
        with Ctrl+C, Ctrl+D, or Ctrl+Z
        """
        def auto_save_handler(signum, frame):
            print(f"\n💾 Auto-save triggered by signal {signum}")
            self._perform_auto_save()
            print("👋 JsonDB REPL terminated safely")
            sys.exit(0)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, auto_save_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, auto_save_handler)  # Termination signal
        
        # Register atexit handler as backup
        atexit.register(self._perform_auto_save)
        
        # For Unix systems, handle SIGTSTP (Ctrl+Z)
        if hasattr(signal, 'SIGTSTP'):
            signal.signal(signal.SIGTSTP, auto_save_handler)
    
    def _perform_auto_save(self):
        """Perform auto-save if there's an open database"""
        if self.db and self.current_db_path and self.auto_save_enabled:
            try:
                # JsonDB auto-saves on every operation, but we can add logging
                print(f"💾 Auto-saving database: {self.current_db_path}")
                # Additional: can create backup file
                backup_path = f"{self.current_db_path}.backup"
                import shutil
                if os.path.exists(self.current_db_path):
                    shutil.copy2(self.current_db_path, backup_path)
                    print(f"📋 Backup created: {backup_path}")
            except Exception as e:
                print(f"⚠️  Auto-save warning: {e}")
    
    def get_prompt_text(self) -> str:
        """
        Returns formatted prompt text with attractive style
        for use with prompt_toolkit
        """
        if self.mode == "main":
            return HTML('<prompt>🌟 JsonDB </prompt><mode>>>></mode> ')
        elif self.mode == "build":
            db_name = os.path.basename(self.current_db_path) if self.current_db_path else "unknown"
            return HTML(f'<mode>📦 [</mode><path>{db_name}</path><mode>] >>></mode> ')
        elif self.mode == "table":
            if self.current_key:
                return HTML(f'<mode>📋 [</mode><path>{self.current_table}</path><mode>.</mode><key>{self.current_key}</key><mode>] >>></mode> ')
            return HTML(f'<mode>📋 [</mode><path>{self.current_table}</path><mode>] >>></mode> ')
        return HTML('<prompt>🌟 JsonDB </prompt><mode>>>></mode> ')
    
    def get_simple_prompt(self) -> str:
        """Fallback prompt for when prompt_toolkit is not available"""
        if self.mode == "main":
            return "🌟 JsonDB >>> "
        elif self.mode == "build":
            db_name = os.path.basename(self.current_db_path) if self.current_db_path else "unknown"
            return f"📦 [{db_name}] >>> "
        elif self.mode == "table":
            if self.current_key:
                return f"📋 [{self.current_table}.{self.current_key}] >>> "
            return f"📋 [{self.current_table}] >>> "
        return "🌟 JsonDB >>> "
    
    def get_user_input(self) -> str:
        """
        Gets user input with advanced features if available
        (tab completion, history navigation, cursor editing)
        """
        if HAS_PROMPT_TOOLKIT:
            try:
                return prompt(
                    self.get_prompt_text(),
                    completer=self.completer,
                    history=self.history,
                    complete_while_typing=True,  # Live completion while typing
                    style=self.style,
                    enable_history_search=True,  # Ctrl+R for history search
                    mouse_support=True,          # Mouse support for cursor positioning
                    wrap_lines=True,            # Word wrapping for long input
                    multiline=False,            # Single line input (can be changed for JSON multiline)
                )
            except (KeyboardInterrupt, EOFError):
                # Re-raise exception to be handled at higher level
                raise
            except Exception as e:
                print(f"⚠️  Fallback to simple input due to: {e}")
                return input(self.get_simple_prompt())
        else:
            # Fallback to simple input if prompt_toolkit is not available
            return input(self.get_simple_prompt())
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
        self.print_banner()
    
    def manual_save(self):
        """Perform manual database save"""
        if self.db and self.current_db_path:
            try:
                self._perform_auto_save()
                print("✅ Database saved successfully!")
            except Exception as e:
                print(f"❌ Failed to save database: {e}")
        else:
            print("❌ No open database to save!")
    
    def print_banner(self):
        """Display welcome banner with enhanced colors and design"""
        # Enhanced ANSI Color codes
        NEON_GREEN = '\033[38;5;46m'
        NEON_BLUE = '\033[38;5;51m'
        NEON_PINK = '\033[38;5;205m'
        NEON_YELLOW = '\033[38;5;226m'
        NEON_PURPLE = '\033[38;5;165m'
        NEON_ORANGE = '\033[38;5;202m'
        BRIGHT_WHITE = '\033[97m'
        BRIGHT_CYAN = '\033[96m'
        GRADIENT_1 = '\033[38;5;39m'
        GRADIENT_2 = '\033[38;5;45m'
        GRADIENT_3 = '\033[38;5;51m'
        BOLD = '\033[1m'
        RESET = '\033[0m'
        DIM = '\033[2m'
        
        os.system('cls' if os.name == 'nt' else 'clear')
        print()
        
        # Animated-style ASCII art with gradient colors
        print(f"{GRADIENT_1}{BOLD}  ╔═══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{GRADIENT_2}{BOLD}  ║    {NEON_GREEN}    ██╗███████╗ ██████╗ ███╗   ██╗██████╗ ██████╗      {GRADIENT_2}║{RESET}")
        print(f"{GRADIENT_2}{BOLD}  ║    {NEON_BLUE}    ██║██╔════╝██╔═══██╗████╗  ██║██╔══██╗██╔══██╗     {GRADIENT_2}║{RESET}")
        print(f"{GRADIENT_2}{BOLD}  ║    {NEON_PINK}    ██║███████╗██║   ██║██╔██╗ ██║██║  ██║██████╔╝     {GRADIENT_2}║{RESET}")
        print(f"{GRADIENT_2}{BOLD}  ║    {NEON_YELLOW}██  ██║╚════██║██║   ██║██║╚██╗██║██║  ██║██╔══██╗     {GRADIENT_2}║{RESET}")
        print(f"{GRADIENT_2}{BOLD}  ║    {NEON_PURPLE}╚█████║███████║╚██████╔╝██║ ╚████║██████╔╝██████╔╝     {GRADIENT_2}║{RESET}")
        print(f"{GRADIENT_2}{BOLD}  ║    {NEON_ORANGE} ╚════╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═════╝ ╚═════╝      {GRADIENT_2}║{RESET}")
        print(f"{GRADIENT_3}{BOLD}  ╚═══════════════════════════════════════════════════════════╝{RESET}")
        print()
        
        # Main title with enhanced styling
        print(f"{BRIGHT_WHITE}{BOLD}    🚀 {NEON_GREEN}JsonDB Interactive REPL{BRIGHT_WHITE} - Advanced JSON Database Manager{RESET}")
        print(f"{BRIGHT_CYAN}    ⚡ Manage your JSON databases with style and efficiency{RESET}")
        print()
        
        # Enhanced project info with beautiful tree structure
        print(f"{NEON_BLUE}{BOLD}    ╭─────────────────────────────────────────────────────────╮{RESET}")
        print(f"{NEON_BLUE}{BOLD}    │{RESET} {NEON_PINK}📋 Project Information{RESET}                                  {NEON_BLUE}{BOLD}│{RESET}")
        print(f"{NEON_BLUE}{BOLD}    │{RESET}                                                         {NEON_BLUE}{BOLD}│{RESET}")
        print(f"{NEON_BLUE}{BOLD}    │{RESET} {NEON_YELLOW}👨‍💻 Creator:{RESET}                                           {NEON_BLUE}{BOLD}│{RESET}")
        print(f"{NEON_BLUE}{BOLD}    │{RESET}     {NEON_GREEN}▸ Elang-elang{RESET} {DIM}(Main Developer){RESET}                      {NEON_BLUE}{BOLD}│{RESET}")
        print(f"{NEON_BLUE}{BOLD}    │{RESET}                                                         {NEON_BLUE}{BOLD}│{RESET}")
        print(f"{NEON_BLUE}{BOLD}    │{RESET} {NEON_PURPLE}🌐 Repository:{RESET}                                          {NEON_BLUE}{BOLD}│{RESET}")
        print(f"{NEON_BLUE}{BOLD}    │{RESET}     {NEON_ORANGE}▸ github.com/Elang-elang/JsonDB{RESET}                     {NEON_BLUE}{BOLD}│{RESET}")
        print(f"{NEON_BLUE}{BOLD}    │{RESET}     {BRIGHT_WHITE}⭐ Don't forget to star us!{RESET}                         {NEON_BLUE}{BOLD}│{RESET}")
        print(f"{NEON_BLUE}{BOLD}    │{RESET}                                                         {NEON_BLUE}{BOLD}│{RESET}")
        print(f"{NEON_BLUE}{BOLD}    │{RESET} {NEON_GREEN}🎯 Version:{RESET} {NEON_PINK}Enhanced REPL v2.0{RESET}                          {NEON_BLUE}{BOLD}│{RESET}")
        print(f"{NEON_BLUE}{BOLD}    ╰─────────────────────────────────────────────────────────╯{RESET}")
        print()
        
        # Feature status with enhanced visuals
        if HAS_PROMPT_TOOLKIT:
            print(f"{NEON_GREEN}{BOLD}    ✨ ADVANCED FEATURES ACTIVATED:{RESET}")
            print(f"       {NEON_YELLOW}⚡{RESET} Smart tab completion for commands & files")
            print(f"       {NEON_YELLOW}⚡{RESET} History navigation with Up/Down arrows")
            print(f"       {NEON_YELLOW}⚡{RESET} Advanced cursor editing (Left/Right)")
            print(f"       {NEON_YELLOW}⚡{RESET} Powerful history search (Ctrl+R)")
            print(f"       {NEON_YELLOW}⚡{RESET} Auto-save protection (Ctrl+C/D/Z)")
            print(f"       {NEON_YELLOW}⚡{RESET} Enhanced file path completion")
        else:
            print(f"{NEON_ORANGE}    ⚠️  {BOLD}BASIC MODE ACTIVE{RESET}")
            print(f"       💡 Install {NEON_YELLOW}'prompt-toolkit'{RESET} for advanced features:")
            print(f"       📦 {DIM}pip install prompt-toolkit{RESET}")
        
        print()
        print(f"{NEON_PURPLE}{BOLD}    🎮 Quick Start: {NEON_YELLOW}Type '.help' for complete command list{RESET}")
        print(f"{BRIGHT_CYAN}    {'═' * 65}{RESET}")
        print()
    
    def show_help(self):
        """Enhanced help for main mode with beautiful formatting"""
        # Color definitions
        TITLE = '\033[38;5;51m\033[1m'
        SECTION = '\033[38;5;226m\033[1m'
        COMMAND = '\033[38;5;46m'
        DESC = '\033[38;5;255m'
        EXAMPLE = '\033[38;5;39m'
        ACCENT = '\033[38;5;205m'
        RESET = '\033[0m'
        
        print(f"\n{TITLE}╔═══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{TITLE}║                    📚 HELP - MAIN MODE                    ║{RESET}")
        print(f"{TITLE}╚═══════════════════════════════════════════════════════════╝{RESET}")
        
        print(f"\n{SECTION}🗄️  DATABASE OPERATIONS:{RESET}")
        print(f"   {COMMAND}.build{RESET}                    {DESC}→ Create or edit a new database{RESET}")
        print(f"   {COMMAND}.open <path> [key]{RESET}        {DESC}→ Open database file (with optional dict key){RESET}")
        print(f"   {COMMAND}.list [--tables|--files|--all]{RESET} {DESC}→ List databases/tables/all{RESET}")
        print(f"   {COMMAND}.info{RESET}                    {DESC}→ Show current database information{RESET}")
        
        print(f"\n{SECTION}🎮 SYSTEM COMMANDS:{RESET}")
        print(f"   {COMMAND}.help{RESET}                    {DESC}→ Show this help menu{RESET}")
        print(f"   {COMMAND}.clear{RESET}                   {DESC}→ Clear screen and show banner{RESET}")
        print(f"   {COMMAND}.exit{RESET} / {COMMAND}.quit{RESET}           {DESC}→ Exit program safely{RESET}")
        
        if HAS_PROMPT_TOOLKIT:
            print(f"\n{SECTION}⌨️  KEYBOARD SHORTCUTS:{RESET}")
            print(f"   {ACCENT}Tab{RESET}                      {DESC}→ Smart auto-completion{RESET}")
            print(f"   {ACCENT}↑↓{RESET}                        {DESC}→ Navigate command history{RESET}")
            print(f"   {ACCENT}←→{RESET}                        {DESC}→ Move cursor in line{RESET}")
            print(f"   {ACCENT}Ctrl+R{RESET}                   {DESC}→ Search command history{RESET}")
            print(f"   {ACCENT}Ctrl+C/D/Z{RESET}               {DESC}→ Safe exit with auto-save{RESET}")
        
        print(f"\n{SECTION}💡 USAGE EXAMPLES:{RESET}")
        print(f"   {EXAMPLE}🌟 JsonDB >>> .build{RESET}")
        print(f"   {EXAMPLE}🌟 JsonDB >>> .open data/users.json{RESET}")
        print(f"   {EXAMPLE}🌟 JsonDB >>> .open config.json settings{RESET}")
        print(f"   {EXAMPLE}🌟 JsonDB >>> .list --all{RESET}")
        
        print(f"\n{TITLE}{'═' * 63}{RESET}")
    
    def show_build_help(self):
        """Enhanced help for build mode"""
        TITLE = '\033[38;5;51m\033[1m'
        SECTION = '\033[38;5;226m\033[1m'
        COMMAND = '\033[38;5;46m'
        DESC = '\033[38;5;255m'
        EXAMPLE = '\033[38;5;39m'
        RESET = '\033[0m'
        
        print(f"\n{TITLE}╔═══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{TITLE}║                   📚 HELP - BUILD MODE                    ║{RESET}")
        print(f"{TITLE}╚═══════════════════════════════════════════════════════════╝{RESET}")
        
        print(f"\n{SECTION}🗂️  TABLE OPERATIONS:{RESET}")
        print(f"   {COMMAND}.create <name>{RESET}           {DESC}→ Create new table{RESET}")
        print(f"   {COMMAND}.tables{RESET}                  {DESC}→ List all tables in database{RESET}")
        print(f"   {COMMAND}.use <name>{RESET}              {DESC}→ Select table for editing{RESET}")
        print(f"   {COMMAND}.info <name>{RESET}             {DESC}→ Show detailed table information{RESET}")
        print(f"   {COMMAND}.list [options]{RESET}          {DESC}→ List with various options{RESET}")
        
        print(f"\n{SECTION}💾 DATABASE MANAGEMENT:{RESET}")
        print(f"   {COMMAND}.save{RESET}                    {DESC}→ Manual database save{RESET}")
        print(f"   {COMMAND}.back{RESET}                    {DESC}→ Return to main mode{RESET}")
        print(f"   {COMMAND}.help{RESET}                    {DESC}→ Show this help{RESET}")
        
        print(f"\n{SECTION}💡 USAGE EXAMPLES:{RESET}")
        db_name = os.path.basename(self.current_db_path) if self.current_db_path else "mydb.json"
        print(f"   {EXAMPLE}📦 [{db_name}] >>> .create users{RESET}")
        print(f"   {EXAMPLE}📦 [{db_name}] >>> .use users{RESET}")
        print(f"   {EXAMPLE}📦 [{db_name}] >>> .list --tables{RESET}")
        
        print(f"\n{TITLE}{'═' * 63}{RESET}")
    
    def show_table_help(self):
        """Enhanced help for table mode"""
        TITLE = '\033[38;5;51m\033[1m'
        SECTION = '\033[38;5;226m\033[1m'
        COMMAND = '\033[38;5;46m'
        DESC = '\033[38;5;255m'
        EXAMPLE = '\033[38;5;39m'
        RESET = '\033[0m'
        
        print(f"\n{TITLE}╔═══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{TITLE}║                   📚 HELP - TABLE MODE                    ║{RESET}")
        print(f"{TITLE}╚═══════════════════════════════════════════════════════════╝{RESET}")
        
        print(f"\n{SECTION}📝 DATA OPERATIONS:{RESET}")
        print(f"   {COMMAND}.insert{RESET}                  {DESC}→ Add new data (interactive mode){RESET}")
        print(f"   {COMMAND}.update{RESET}                  {DESC}→ Update existing data{RESET}")
        print(f"   {COMMAND}.delete{RESET}                  {DESC}→ Delete data with conditions{RESET}")
        print(f"   {COMMAND}.show{RESET}                    {DESC}→ Display all table data{RESET}")
        print(f"   {COMMAND}.clear{RESET}                   {DESC}→ Clear all table data{RESET}")
        
        print(f"\n{SECTION}🔄 NAVIGATION:{RESET}")
        print(f"   {COMMAND}.save{RESET}                    {DESC}→ Manual save database{RESET}")
        print(f"   {COMMAND}.back{RESET}                    {DESC}→ Return to build mode{RESET}")
        print(f"   {COMMAND}.help{RESET}                    {DESC}→ Show this help{RESET}")
        
        print(f"\n{SECTION}💡 USAGE EXAMPLES:{RESET}")
        table_name = self.current_table or "users"
        print(f"   {EXAMPLE}📋 [{table_name}] >>> .insert{RESET}")
        print(f"   {EXAMPLE}📋 [{table_name}] >>> .show{RESET}")
        print(f"   {EXAMPLE}📋 [{table_name}] >>> .clear{RESET}")
        
        print(f"\n{TITLE}{'═' * 63}{RESET}")
    
    def list_command(self, args=None):
        """Enhanced list command with options"""
        if args:
            option = args.strip()
        else:
            option = "--files"  # Default option
        
        TITLE = '\033[38;5;51m\033[1m'
        ITEM = '\033[38;5;46m'
        COUNT = '\033[38;5;226m'
        DESC = '\033[38;5;255m'
        RESET = '\033[0m'
        
        print(f"\n{TITLE}╔═══════════════════════════════════════════════════════════╗{RESET}")
        
        if option == "--files" or option == "--all":
            print(f"{TITLE}║                   📁 JSON DATABASE FILES                  ║{RESET}")
            
            json_files = []
            for root, dirs, files in os.walk('.'):
                for file in files:
                    if file.endswith('.json'):
                        json_files.append(os.path.join(root, file))
            
            if json_files:
                for i, file in enumerate(json_files, 1):
                    size = os.path.getsize(file) if os.path.exists(file) else 0
                    # Hitung padding yang diperlukan untuk alignment
                    content_length = len(f"{i:2d}. {file} ({size} bytes)")
                    padding = max(0, 57 - content_length)
                    print(f"{TITLE}║  {COUNT}{i:2d}.{RESET} {ITEM}{file}{RESET} {DESC}({size} bytes){' ' * padding}{TITLE}║{RESET}")
                
                # Total files count
                total_text = f"Total: {len(json_files)} files"
                total_padding = max(0, 56 - len(total_text))
                print(f"{TITLE}║   {COUNT}{total_text}{' ' * total_padding}{TITLE}║{RESET}")
            else:
                print(f"{TITLE}║                   {DESC}📭 No JSON files found                   {TITLE}║{RESET}")
        
        if option == "--tables" or option == "--all":
            if self.db:
                if option == "--all":
                    print(f"{TITLE}║                                                           ║{RESET}")  # Add spacing
                print(f"{TITLE}║                   📋 DATABASE TABLES                      ║{RESET}")
                
                tables = self.db.list_tables()
                if tables:
                    for i, table in enumerate(tables, 1):
                        info = self.db.get_table_info(table)
                        # Format table info
                        table_info = f"{i:2d}. {table} ({info['type']}, {info['length']} items)"
                        padding = max(0, 57 - len(table_info))
                        print(f"{TITLE}║  {COUNT}{i:2d}.{RESET} {ITEM}{table}{RESET} {DESC}({info['type']}, {info['length']} items){' ' * padding}{TITLE}║{RESET}")
                    
                    # Total tables count
                    total_text = f"Total: {len(tables)} tables"
                    total_padding = max(0, 56 - len(total_text))
                    print(f"{TITLE}║   {COUNT}{total_text}{' ' * total_padding}{TITLE}║{RESET}")
                else:
                    print(f"{TITLE}║                   {DESC}📭 No tables found                     {TITLE}║{RESET}")
            elif option == "--tables":
                print(f"{TITLE}║                   ❌ No database is open!                 {TITLE}║{RESET}")
        
        
        if option not in ["--files", "--tables", "--all"]:
            print(f"{TITLE}║                   📋 LIST COMMAND OPTIONS                 ║{RESET}")
            print(f"{TITLE}║   {ITEM}--files{RESET}   {DESC}List all JSON database files                  {TITLE}║{RESET}")
            print(f"{TITLE}║   {ITEM}--tables{RESET}  {DESC}List all tables in current database           {TITLE}║{RESET}")
            print(f"{TITLE}║   {ITEM}--all{RESET}     {DESC}List both files and tables                    {TITLE}║{RESET}")
        print(f"{TITLE}╚═══════════════════════════════════════════════════════════╝{RESET}")

    def build_mode(self):
        """Enter build mode - create or edit database"""
        if not self.current_db_path:
            TITLE = '\033[38;5;201m\033[1m'
            LABEL = '\033[38;5;141m'
            INPUT = '\033[38;5;183m'
            RESET = '\033[0m'
            
            print(f"\n{TITLE}╔═══════════════════════════════════════════════════════════╗{RESET}")
            print(f"{TITLE}║               🏗️  BUILD MODE - Create New Database          ║{RESET}")
            print(f"{TITLE}╚═══════════════════════════════════════════════════════════╝{RESET}")
            
            db_path = input(f"{INPUT}📁 Enter database path (example: data/mydb.json): {RESET}").strip()
            
            if not db_path:
                print(f"{TITLE}❌ Path cannot be empty!{RESET}")
                return
            
            # Add .json extension if not present
            if not db_path.endswith('.json'):
                db_path += '.json'
            
            try:
                self.db = JsonDB(db_path)
                self.current_db_path = db_path
                self.mode = "build"
                print(f"{LABEL}✅ Database '{db_path}' created/opened successfully!{RESET}")
                print(f"{INPUT}💡 Use '.create <table_name>' to create a new table{RESET}")
            except Exception as e:
                print(f"{TITLE}❌ Failed to create database: {e}{RESET}")
        else:
            TITLE = '\033[38;5;201m\033[1m'
            LABEL = '\033[38;5;141m'
            RESET = '\033[0m'
            self.mode = "build"
            print(f"{LABEL}🏗️  Entered build mode for database: {TITLE}{self.current_db_path}{RESET}")
    
    def open_database(self, args=None):
        """Enhanced open command with optional key navigation"""
        TITLE = '\033[38;5;33m\033[1m'
        LABEL = '\033[38;5;75m'
        INPUT = '\033[38;5;117m'
        SUCCESS = '\033[38;5;82m'
        ERROR = '\033[38;5;196m'
        WARNING = '\033[38;5;214m'
        RESET = '\033[0m'
        
        if args:
            parts = args.split(maxsplit=1)
            db_path = parts[0]
            key = parts[1] if len(parts) > 1 else None
        else:
            print(f"\n{TITLE}╔═══════════════════════════════════════════════════════════╗{RESET}")
            print(f"{TITLE}║                    📂 OPEN DATABASE                          ║{RESET}")
            print(f"{TITLE}╚═══════════════════════════════════════════════════════════╝{RESET}")
            
            if HAS_PROMPT_TOOLKIT:
                print(f"{LABEL}💡 Use Tab for JSON file auto-completion!{RESET}")
                json_files = self.completer._get_json_files()
                
                db_path = prompt(
                    f"{INPUT}📁 Enter database path: {RESET}",
                    completer=WordCompleter(json_files),
                    complete_while_typing=True
                ).strip()
                
                if db_path and self.db and isinstance(self.db.get_data('__root__'), dict):
                    # If opening a dict-based JSON, prompt for key
                    keys = list(self.db.get_data('__root__').keys())
                    if keys:
                        key = prompt(
                            f"{INPUT}🔑 Enter dictionary key (optional): {RESET}",
                            completer=WordCompleter(keys),
                            complete_while_typing=True
                        ).strip() or None
                    else:
                        key = None
                else:
                    key = None
            else:
                db_path = input(f"{INPUT}📁 Enter database path: {RESET}").strip()
                if db_path and self.db and isinstance(self.db.get_data('__root__'), dict):
                    keys = list(self.db.get_data('__root__').keys())
                    if keys:
                        print(f"{LABEL}🔑 Available keys: {', '.join(keys)}{RESET}")
                        key = input(f"{INPUT}🔑 Enter dictionary key (optional): {RESET}").strip() or None
                    else:
                        key = None
                else:
                    key = None
        
        if not db_path:
            print(f"{ERROR}❌ Path cannot be empty!{RESET}")
            return
        
        if not os.path.exists(db_path):
            print(f"{ERROR}❌ File '{db_path}' not found!{RESET}")
            return
        
        try:
            self.db = JsonDB(db_path)
            self.current_db_path = db_path
            self.mode = "build"
            
            if key:
                data = self.db.get_data('__root__')
                if isinstance(data, dict) and key in data:
                    self.current_key = key
                    print(f"{SUCCESS}✅ Database '{db_path}' opened with key '{key}'!{RESET}")
                else:
                    print(f"{WARNING}⚠️  Key '{key}' not found, opened database normally{RESET}")
                    self.current_key = None
            else:
                self.current_key = None
                print(f"{SUCCESS}✅ Database '{db_path}' opened successfully!{RESET}")
            
            tables = self.db.list_tables()
            if tables:
                print(f"{LABEL}📋 Available tables: {', '.join(tables)}{RESET}")
        except Exception as e:
            print(f"{ERROR}❌ Failed to open database: {e}{RESET}")
    
    def show_db_info(self):
        """Show enhanced information about current database"""
        if not self.db:
            ERROR = '\033[38;5;196m'
            RESET = '\033[0m'
            print(f"{ERROR}❌ No database is open!{RESET}")
            return
        
        TITLE = '\033[38;5;99m\033[1m'
        LABEL = '\033[38;5;147m'
        VALUE = '\033[38;5;189m'
        ITEM = '\033[38;5;183m'
        RESET = '\033[0m'
        
        print(f"\n{TITLE}╔═══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{TITLE}║                   📊 DATABASE INFORMATION                 ║{RESET}")
        print(f"{TITLE}╠═══════════════════════════════════════════════════════════╣{RESET}")
        
        # Database path
        path_text = f"📁 Path: {self.current_db_path}"
        path_padding = max(0, 58 - len(path_text))
        print(f"{TITLE}║ {LABEL}{path_text}{' ' * path_padding}{TITLE}║{RESET}")
        
        # Get file size
        try:
            size = os.path.getsize(self.current_db_path)
            size_text = f"📏 Size: {size} bytes"
            size_padding = max(0, 58 - len(size_text))
            print(f"{TITLE}║ {LABEL}{size_text}{' ' * size_padding}{TITLE}║{RESET}")
        except:
            pass
        
        tables = self.db.list_tables()
        count_text = f"📋 Table count: {len(tables)}"
        count_padding = max(0, 58 - len(count_text))
        print(f"{TITLE}║ {LABEL}{count_text}{' ' * count_padding}{TITLE}║{RESET}")
        
        if tables:
            print(f"{TITLE}║                                                           ║{RESET}")
            print(f"{TITLE}║                   🗂️  TABLE DETAILS                      ║{RESET}")
            for table in tables:
                info = self.db.get_table_info(table)
                table_detail = f"• {table} ({info['type']}, {info['length']} items)"
                detail_padding = max(0, 58 - len(table_detail))
                print(f"{TITLE}║ {ITEM}{table_detail}{' ' * detail_padding}{TITLE}║{RESET}")
        
        print(f"{TITLE}╚═══════════════════════════════════════════════════════════╝{RESET}")
    
    def create_table(self, args=None):
        """Create a new table"""
        TITLE = '\033[38;5;118m\033[1m'
        LABEL = '\033[38;5;154m'
        INPUT = '\033[38;5;190m'
        SUCCESS = '\033[38;5;82m'
        ERROR = '\033[38;5;196m'
        WARNING = '\033[38;5;214m'
        RESET = '\033[0m'
        
        if not self.db:
            print(f"{ERROR}❌ No database is open!{RESET}")
            return
        
        if args:
            table_name = args
        else:
            print(f"\n{TITLE}╔═══════════════════════════════════════════════════════════╗{RESET}")
            print(f"{TITLE}║                  🆕 CREATE NEW TABLE                      ║{RESET}")
            print(f"{TITLE}╚═══════════════════════════════════════════════════════════╝{RESET}")
            table_name = input(f"{INPUT}📝 Table name: {RESET}").strip()
        
        if not table_name:
            print(f"{ERROR}❌ Table name cannot be empty!{RESET}")
            return
        
        if self.db.create_table(table_name):
            print(f"{SUCCESS}✅ Table '{table_name}' created successfully!{RESET}")
        else:
            print(f"{WARNING}⚠️  Table '{table_name}' already exists!{RESET}")
    
    def list_tables(self):
        """List all tables with enhanced formatting"""
        if not self.db:
            ERROR = '\033[38;5;196m'
            RESET = '\033[0m'
            print(f"{ERROR}❌ No database is open!{RESET}")
            return
        
        TITLE = '\033[38;5;123m\033[1m'
        ITEM = '\033[38;5;159m'
        COUNT = '\033[38;5;195m'
        DESC = '\033[38;5;231m'
        RESET = '\033[0m'
        
        tables = self.db.list_tables()
        
        print(f"\n{TITLE}╔═══════════════════════════════════════════════════════════╗{RESET}")
        header_text = f"📋 TABLE LIST ({len(tables)} tables)"
        header_padding = max(0, 41 - len(header_text))
        print(f"{TITLE}║                 {header_text}{' ' * header_padding}║{RESET}")
        print(f"{TITLE}╠═══════════════════════════════════════════════════════════╣{RESET}")
        
        if tables:
            for i, table in enumerate(tables, 1):
                info = self.db.get_table_info(table)
                table_line = f"{i:2d}. {table}"
                table_padding = max(0, 35 - len(table_line))
                
                type_info = f"Type: {info['type']}, Items: {info['length']}"
                info_padding = max(0, 58 - len(f"{table_line}{' ' * table_padding}{type_info}"))
                
                print(f"{TITLE}║ {COUNT}{table_line}{' ' * table_padding}{DESC}{type_info}{' ' * info_padding}{TITLE}║{RESET}")
        else:
            empty_text = "📭 No tables created yet"
            empty_padding = max(0, 58 - len(empty_text))
            print(f"{TITLE}║                 {DESC}{empty_text}{' ' * empty_padding}{TITLE}║{RESET}")
        
        print(f"{TITLE}╚═══════════════════════════════════════════════════════════╝{RESET}")
    
    def use_table(self, args=None):
        """Select table to edit"""
        TITLE = '\033[38;5;165m\033[1m'
        LABEL = '\033[38;5;171m'
        INPUT = '\033[38;5;177m'
        SUCCESS = '\033[38;5;82m'
        ERROR = '\033[38;5;196m'
        RESET = '\033[0m'
        
        if not self.db:
            print(f"{ERROR}❌ No database is open!{RESET}")
            return
        
        if args:
            table_name = args
        else:
            print(f"\n{TITLE}╔═══════════════════════════════════════════════════════════╗{RESET}")
            print(f"{TITLE}║                    🎯 SELECT TABLE                        ║{RESET}")
            print(f"{TITLE}╚═══════════════════════════════════════════════════════════╝{RESET}")
            self.list_tables()
            table_name = input(f"\n{INPUT}📝 Table name to select: {RESET}").strip()
        
        if not table_name:
            print(f"{ERROR}❌ Table name cannot be empty!{RESET}")
            return
        
        if not self.db.table_exists(table_name):
            print(f"{ERROR}❌ Table '{table_name}' not found!{RESET}")
            return
        
        self.current_table = table_name
        self.mode = "table"
        print(f"{SUCCESS}✅ Successfully selected table '{table_name}'!{RESET}")
        print(f"{LABEL}💡 Use '.insert' to add data{RESET}")
    
    def show_table_info(self, args=None):
        """Show detailed table information with enhanced formatting"""
        TITLE = '\033[38;5;93m\033[1m'
        LABEL = '\033[38;5;135m'
        VALUE = '\033[38;5;177m'
        INPUT = '\033[38;5;219m'
        ERROR = '\033[38;5;196m'
        RESET = '\033[0m'
        
        if not self.db:
            print(f"{ERROR}❌ No database is open!{RESET}")
            return
        
        if args:
            table_name = args
        else:
            table_name = input(f"{INPUT}📝 Table name: {RESET}").strip()
        
        if not table_name:
            print(f"{ERROR}❌ Table name cannot be empty!{RESET}")
            return
        
        info = self.db.get_table_info(table_name)
        if info['exists']:
            print(f"\n{TITLE}╔═══════════════════════════════════════════════════════════╗{RESET}")
            header_text = f"📊 TABLE INFORMATION: {table_name}"
            header_padding = max(0, 45 - len(header_text))
            print(f"{TITLE}║             {header_text}{' ' * header_padding}║{RESET}")
            print(f"{TITLE}╠═══════════════════════════════════════════════════════════╣{RESET}")
            
            # Table name
            name_text = f"📝 Name: {info['name']}"
            name_padding = max(0, 57 - len(name_text))
            print(f"{TITLE}║ {LABEL}{name_text}{' ' * name_padding}{TITLE}║{RESET}")
            
            # Table type
            type_text = f"🏷️  Type: {info['type']}"
            type_padding = max(0, 59 - len(type_text))
            print(f"{TITLE}║ {LABEL}{type_text}{' ' * type_padding}{TITLE}║{RESET}")
            
            # Item count
            count_text = f"📊 Item count: {info['length']}"
            count_padding = max(0, 57 - len(count_text))
            print(f"{TITLE}║ {LABEL}{count_text}{' ' * count_padding}{TITLE}║{RESET}")
            
            # Data preview
            data_preview = str(info['data'])[:35]
            if len(str(info['data'])) > 35:
                data_preview += "..."
            preview_text = f"📋 Data preview: {data_preview}"
            preview_padding = max(0, 57 - len(preview_text))
            print(f"{TITLE}║ {LABEL}{preview_text}{' ' * preview_padding}{TITLE}║{RESET}")
            
            print(f"{TITLE}╚═══════════════════════════════════════════════════════════╝{RESET}")
        else:
            print(f"{ERROR}❌ Table '{table_name}' not found!{RESET}")
    
    def insert_data(self):
        """Add data to current table with enhanced interface"""
        TITLE = '\033[38;5;208m\033[1m'
        OPTION = '\033[38;5;214m'
        INPUT = '\033[38;5;220m'
        SUCCESS = '\033[38;5;82m'
        ERROR = '\033[38;5;196m'
        RESET = '\033[0m'
        
        if not self.current_table:
            print(f"{ERROR}❌ No table selected!{RESET}")
            return
        
        print(f"\n{TITLE}╔═══════════════════════════════════════════════════════════╗{RESET}")
        header_text = f"      ➕ ADD DATA TO TABLE: {self.current_table}"
        header_padding = max(0, 47 - len(header_text))
        print(f"{TITLE}║           {header_text}{' ' * header_padding}║{RESET}")
        print(f"{TITLE}╠═══════════════════════════════════════════════════════════╣{RESET}")
        print(f"{TITLE}║                 💡 Select data format:                    ║{RESET}")
        print(f"{TITLE}║   {OPTION}1.{RESET} JSON Object (dict)                                   {TITLE}║{RESET}")
        print(f"{TITLE}║   {OPTION}2.{RESET} Text/String                                          {TITLE}║{RESET}")
        print(f"{TITLE}║   {OPTION}3.{RESET} Number                                               {TITLE}║{RESET}")
        print(f"{TITLE}║   {OPTION}4.{RESET} List/Array                                           {TITLE}║{RESET}")
        print(f"{TITLE}╚═══════════════════════════════════════════════════════════╝{RESET}")
        
        choice = input(f"\n{INPUT}📝 Choice (1-4): {RESET}").strip()
        
        try:
            if choice == "1":
                print(f"{OPTION}📝 Enter JSON data (example: {{\"name\": \"John\", \"age\": 25}}){RESET}")
                data_str = input(f"{INPUT}Data: {RESET}")
                data = json.loads(data_str)
            elif choice == "2":
                data = input(f"{INPUT}📝 Enter text: {RESET}")
            elif choice == "3":
                data_str = input(f"{INPUT}📝 Enter number: {RESET}")
                data = float(data_str) if '.' in data_str else int(data_str)
            elif choice == "4":
                print(f"{OPTION}📝 Enter JSON array (example: [1, 2, 3] or [\"a\", \"b\", \"c\"]){RESET}")
                data_str = input(f"{INPUT}Data: {RESET}")
                data = json.loads(data_str)
            else:
                print(f"{ERROR}❌ Invalid choice!{RESET}")
                return
            
            if self.db.insert_data(self.current_table, data):
                print(f"{SUCCESS}✅ Data added successfully!{RESET}")
                
                # Show preview of newly added data
                table_data = self.db.get_data(self.current_table)
                if isinstance(table_data, list) and table_data:
                    print(f"{OPTION}📋 Latest data: {table_data[-1]}{RESET}")
            else:
                print(f"{ERROR}❌ Failed to add data!{RESET}")
                
        except json.JSONDecodeError:
            print(f"{ERROR}❌ Invalid JSON format!{RESET}")
        except ValueError:
            print(f"{ERROR}❌ Invalid number format!{RESET}")
        except Exception as e:
            print(f"{ERROR}❌ Error: {e}{RESET}")
    
    def show_table_data(self):
        """Show all data in table with enhanced formatting"""
        TITLE = '\033[38;5;45m\033[1m'
        ITEM = '\033[38;5;87m'
        COUNT = '\033[38;5;123m'
        TYPE = '\033[38;5;159m'
        ERROR = '\033[38;5;196m'
        RESET = '\033[0m'
        
        if not self.current_table:
            print(f"{ERROR}❌ No table selected!{RESET}")
            return
        
        data = self.db.get_data(self.current_table)
        
        print(f"\n{TITLE}╔═══════════════════════════════════════════════════════════╗{RESET}")
        header_text = f"📋 TABLE DATA: {self.current_table}"
        header_padding = max(0, 42 - len(header_text))
        print(f"{TITLE}║                {header_text}{' ' * header_padding}║{RESET}")
        print(f"{TITLE}╠═══════════════════════════════════════════════════════════╣{RESET}")
        
        if isinstance(data, list):
            if data:
                for i, item in enumerate(data, 1):
                    item_str = str(item)[:50]
                    if len(str(item)) > 50:
                        item_str += "..."
                    item_text = f"{i:2d}. {item_str}"
                    item_padding = max(0, 58 - len(item_text))
                    print(f"{TITLE}║ {COUNT}{item_text}{' ' * item_padding}{TITLE}║{RESET}")
            else:
                empty_text = "📭 Table is empty"
                empty_padding = max(0, 39 - len(empty_text))
                print(f"{TITLE}║                   {ITEM}{empty_text}{' ' * empty_padding}{TITLE}║{RESET}")
        else:
            data_str = str(data)[:40]
            if len(str(data)) > 40:
                data_str += "..."
            data_text = f"📊 Data: {data_str}"
            data_padding = max(0, 58 - len(data_text))
            print(f"{TITLE}║ {ITEM}{data_text}{' ' * data_padding}{TITLE}║{RESET}")
            
            type_text = f"🏷️  Type: {type(data).__name__}"
            type_padding = max(0, 58 - len(type_text))
            print(f"{TITLE}║ {TYPE}{type_text}{' ' * type_padding}{TITLE}║{RESET}")
        
        print(f"{TITLE}╚═══════════════════════════════════════════════════════════╝{RESET}")
    
    def clear_table(self):
        """Clear all data in table with confirmation"""
        TITLE = '\033[38;5;196m\033[1m'
        WARNING = '\033[38;5;202m'
        INPUT = '\033[38;5;208m'
        SUCCESS = '\033[38;5;82m'
        ERROR = '\033[38;5;196m'
        RESET = '\033[0m'
        
        if not self.current_table:
            print(f"{ERROR}❌ No table selected!{RESET}")
            return
        
        print(f"\n{TITLE}╔═══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{TITLE}║                   ⚠️  WARNING ZONE                         ║{RESET}")
        print(f"{TITLE}╠═══════════════════════════════════════════════════════════╣{RESET}")
        warning_text = f"This will delete ALL data in table '{self.current_table}'!"
        warning_padding = max(0, 58 - len(warning_text))
        print(f"{TITLE}║ {WARNING}{warning_text}{' ' * warning_padding}{TITLE}║{RESET}")
        print(f"{TITLE}╚═══════════════════════════════════════════════════════════╝{RESET}")
        
        confirm = input(f"{INPUT}🤔 Are you sure? (yes/no): {RESET}").strip().lower()
        
        if confirm in ['yes', 'y']:
            if self.db.delete_data(self.current_table, delete_all=True):
                print(f"{SUCCESS}✅ All data deleted successfully!{RESET}")
            else:
                print(f"{ERROR}❌ Failed to delete data!{RESET}")
        else:
            print(f"{WARNING}❌ Operation cancelled!{RESET}")
    
    def update_data(self):
        """Update data based on condition (simple implementation)"""
        if not self.current_table:
            print("❌ No table selected!")
            return
        
        WARNING = '\033[38;5;208m\033[1m'
        DESC = '\033[38;5;245m'
        RESET = '\033[0m'
        
        print(f"\n{WARNING}╔═══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{WARNING}║                🔄 UPDATE DATA - TABLE: {self.current_table:<15}    ║{RESET}")
        print(f"{WARNING}╚═══════════════════════════════════════════════════════════╝{RESET}")
        print(f"{DESC}⚠️  Data update feature is under development{RESET}")
        print(f"{DESC}💡 Currently you can:{RESET}")
        print(f"{DESC}  • Use '.clear' to delete all data{RESET}")
        print(f"{DESC}  • Use '.insert' to add new data{RESET}")
    
    def delete_data(self):
        """Delete data based on condition (simple implementation)"""
        if not self.current_table:
            print("❌ No table selected!")
            return
        
        WARNING = '\033[38;5;203m\033[1m'
        DESC = '\033[38;5;243m'
        RESET = '\033[0m'
        
        print(f"\n{WARNING}╔═══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{WARNING}║                🗑️  DELETE DATA - TABLE: {self.current_table:<13}      ║{RESET}")
        print(f"{WARNING}╚═══════════════════════════════════════════════════════════╝{RESET}")
        print(f"{DESC}⚠️  Selective delete feature is under development{RESET}")
        print(f"{DESC}💡 Currently you can:{RESET}")
        print(f"{DESC}  • Use '.clear' to delete all data{RESET}")
    
    def back_to_main(self):
        """Return to main mode"""
        self.mode = "main"
        self.current_table = None
        self.current_key = None
        print("🔙 Returned to main mode")
    
    def back_to_build(self):
        """Return to build mode"""
        self.mode = "build"
        self.current_table = None
        self.current_key = None
        print("🔙 Returned to build mode")
    
    def parse_command(self, user_input: str):
        """Parse and execute user command"""
        # Save to simple history if prompt_toolkit is not available
        if not HAS_PROMPT_TOOLKIT:
            if not hasattr(self, 'simple_history'):
                self.simple_history = []
            self.simple_history.append(user_input)
            # Limit history to last 100 items
            if len(self.simple_history) > 100:
                self.simple_history = self.simple_history[-100:]
        
        parts = user_input.strip().split(maxsplit=1)
        command = parts[0]
        args = parts[1] if len(parts) > 1 else None
        
        # Get command handler based on current mode
        mode_commands = self.commands.get(self.mode, {})
        
        if command in mode_commands:
            # Execute command with or without arguments
            if args and command in ['.open', '.create', '.use', '.info', '.list']:
                mode_commands[command](args)
            else:
                mode_commands[command]()
        else:
            print(f"❌ Command '{command}' not recognized in '{self.mode}' mode")
            print("💡 Type '.help' to see available commands")
            if HAS_PROMPT_TOOLKIT:
                print("💡 Use Tab for command auto-completion")
    
    def exit_program(self):
        """Exit program with auto-save"""
        print("\n💾 Performing auto-save before exiting...")
        self._perform_auto_save()
        print("👋 Thank you for using JsonDB REPL!")
        print("💾 Your data has been safely saved")
        sys.exit(0)
    
    def run(self):
        """Run main REPL with advanced features"""
        self.print_banner()
        
        while True:
            try:
                user_input = self.get_user_input().strip()
                
                # Skip empty input
                if not user_input:
                    continue
                
                # Parse and execute command
                self.parse_command(user_input)
                
            except KeyboardInterrupt:
                print("\n\n💾 Auto-save triggered by Ctrl+C")
                self._perform_auto_save()
                print("👋 Program stopped by user")
                break
            except EOFError:
                print("\n\n💾 Auto-save triggered by EOF")
                self._perform_auto_save()
                print("👋 Program finished")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                print("💡 Type '.help' for help")

def main():
    """Main function to run REPL"""
    if not HAS_PROMPT_TOOLKIT:
        print("⚠️  For best experience, install prompt-toolkit:")
        print("   pip install prompt-toolkit")
        print("   Then restart this program\n")
    
    # Check for file argument
    auto_open_file = None
    if len(sys.argv) > 1:
        auto_open_file = sys.argv[1]
        if not auto_open_file.endswith('.json'):
            auto_open_file += '.json'
    
    repl = JsonDBREPL(auto_open_file=auto_open_file)
    repl.run()

if __name__ == "__main__":
    main()
