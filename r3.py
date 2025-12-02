#!/usr/bin/env python3
"""
Enhanced Python/Streamlit Script Runner - Modular Version with Git Integration
A comprehensive script runner with dependency management, virtual environments, Git integration, and deployment.
"""

import os
import re
import ast
import sys
import venv
import subprocess
import shutil
import hashlib
import socket
import time
import stat
import errno
import fcntl
import json
import getpass
from pathlib import Path
from typing import Dict, Optional, Set, List, Tuple, Any
from datetime import datetime

# =============================================================================
# MODULE 1: UI MANAGER - Handles all user interface components
# =============================================================================

class UIManager:
    """Manages all user interface components including menus, progress bars, and status messages."""
    
    def __init__(self):
        self.rich_available = self._setup_rich()
        self.console = self._get_console()
    
    def _setup_rich(self) -> bool:
        """Initialize rich library for beautiful UI."""
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
            from rich.table import Table
            from rich.prompt import Prompt, Confirm, IntPrompt
            from rich import box
            from rich.layout import Layout
            from rich.columns import Columns
            return True
        except ImportError:
            return False
    
    def _get_console(self):
        """Get console instance if rich is available."""
        if self.rich_available:
            from rich.console import Console
            return Console()
        return None
    
    def print_banner(self) -> None:
        """Print the application banner."""
        banner_text = """
  ____        _   _                 ____            _       _             
 |  _ \ _   _| |_| |__   ___  _ __/ ___|  ___ _ __(_)_ __ | |_ ___ _ __ 
 | |_) | | | | __| '_ \ / _ \| '_ \___ \ / __| '__| | '_ \| __/ _ \ '__|
 |  __/| |_| | |_| | | | (_) | | | |__) | (__| |  | | |_) | ||  __/ |   
 |_|    \__, |\__|_| |_|\___/|_| |_____/ \___|_|  |_| .__/ \__\___|_|   
        |___/                                       |_|                  
"""
        if self.rich_available:
            from rich.panel import Panel
            from rich.columns import Columns
            from rich.text import Text
            
            title = Text("🐍 Enhanced Python/Streamlit Script Runner", style="bold blue")
            subtitle = Text("with Git Integration & Deployment", style="bold cyan")
            self.console.print(Columns([title, subtitle], align="center", equal=True))
            self.console.print(Panel.fit(banner_text, style="bold blue"))
            self.console.print("=" * 80)
        else:
            print(banner_text)
            print("🐍 Enhanced Python/Streamlit Script Runner with Git Integration & Deployment")
            print("=" * 70)
    
    def print_panel(self, title: str, content: str, style: str = "blue") -> None:
        """Print content in a styled panel."""
        if self.rich_available:
            from rich.panel import Panel
            from rich.text import Text
            from rich.markdown import Markdown
            
            # Format content based on type
            if "\n" in content and len(content) > 100:
                content_display = Text(content)
            elif content.startswith("#") or content.startswith("- "):
                content_display = Markdown(content)
            else:
                content_display = Text(content)
            
            self.console.print(Panel(content_display, title=title, style=style))
        else:
            print(f"\n{title}")
            print("-" * len(title))
            print(content)
            print()
    
    def print_status(self, message: str, status: str = "info") -> None:
        """Print a status message with appropriate styling."""
        if self.rich_available:
            icons = {
                "info": "ℹ️",
                "success": "✅",
                "warning": "⚠️",
                "error": "❌",
                "progress": "🔄",
                "git": "📦",
                "deploy": "🚀"
            }
            styles = {
                "info": "blue",
                "success": "green",
                "warning": "yellow",
                "error": "red",
                "progress": "cyan",
                "git": "magenta",
                "deploy": "yellow"
            }
            icon = icons.get(status, "•")
            style = styles.get(status, "white")
            self.console.print(f"[{style}]{icon} {message}[/{style}]")
        else:
            status_icons = {
                "info": "[INFO]",
                "success": "[OK]",
                "warning": "[WARN]",
                "error": "[ERROR]",
                "progress": "[...]",
                "git": "[GIT]",
                "deploy": "[DEPLOY]"
            }
            icon = status_icons.get(status, "[*]")
            print(f"{icon} {message}")
    
    def create_progress_bar(self):
        """Create a rich progress bar."""
        if self.rich_available:
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
            return Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                transient=True
            )
        return None
    
    def display_main_menu(self) -> str:
        """Display the main menu."""
        if self.rich_available:
            from rich.panel import Panel
            from rich.columns import Columns
            
            menu_items = [
                "[bold cyan]1.[/bold cyan] 📜 Run Script",
                "[bold cyan]2.[/bold cyan] 🔧 Manage Git Repository",
                "[bold cyan]3.[/bold cyan] 🚀 Deploy to Cloud",
                "[bold cyan]4.[/bold cyan] ⚙️  Configure Settings",
                "[bold cyan]5.[/bold cyan] ❓ Help / Documentation",
                "[bold cyan]q.[/bold cyan] 🚪 Quit"
            ]
            
            menu_panel = Panel(
                "\n".join(menu_items),
                title="📋 Main Menu",
                border_style="cyan",
                padding=(1, 2)
            )
            
            self.console.print(menu_panel)
            
            from rich.prompt import Prompt
            choice = Prompt.ask(
                "[bold yellow]Select an option[/bold yellow]",
                choices=["1", "2", "3", "4", "5", "q", "quit"],
                default="1"
            )
            return choice
        else:
            print("\n📋 Main Menu:")
            print("=" * 30)
            print("1. 📜 Run Script")
            print("2. 🔧 Manage Git Repository")
            print("3. 🚀 Deploy to Cloud")
            print("4. ⚙️  Configure Settings")
            print("5. ❓ Help / Documentation")
            print("q. 🚪 Quit")
            print("=" * 30)
            return input("Select an option: ").strip()
    
    def display_git_menu(self) -> str:
        """Display the Git management menu."""
        if self.rich_available:
            from rich.panel import Panel
            
            menu_items = [
                "[bold cyan]1.[/bold cyan] 🔧 Setup Git Repository",
                "[bold cyan]2.[/bold cyan] 📊 Check Git Status",
                "[bold cyan]3.[/bold cyan] 📝 Commit & Push Changes",
                "[bold cyan]4.[/bold cyan] 🔄 Pull Latest Changes",
                "[bold cyan]5.[/bold cyan] 🚀 Create Deployment Configs",
                "[bold cyan]6.[/bold cyan] ⚙️  Configure Git Settings",
                "[bold cyan]b.[/bold cyan] ↩️  Back to Main Menu"
            ]
            
            menu_panel = Panel(
                "\n".join(menu_items),
                title="📦 Git Management",
                border_style="magenta",
                padding=(1, 2)
            )
            
            self.console.print(menu_panel)
            
            from rich.prompt import Prompt
            choice = Prompt.ask(
                "[bold yellow]Select an option[/bold yellow]",
                choices=["1", "2", "3", "4", "5", "6", "b", "back"],
                default="1"
            )
            return choice
        else:
            print("\n📦 Git Management:")
            print("=" * 30)
            print("1. 🔧 Setup Git Repository")
            print("2. 📊 Check Git Status")
            print("3. 📝 Commit & Push Changes")
            print("4. 🔄 Pull Latest Changes")
            print("5. 🚀 Create Deployment Configs")
            print("6. ⚙️  Configure Git Settings")
            print("b. ↩️  Back to Main Menu")
            print("=" * 30)
            return input("Select an option: ").strip()
    
    def display_script_menu(self, scripts: Dict[int, Path]) -> None:
        """Display a menu of available scripts."""
        if self.rich_available:
            from rich.table import Table
            from rich import box
            
            table = Table(title="📜 Available Python Scripts", box=box.ROUNDED)
            table.add_column("#", justify="right", style="cyan", no_wrap=True)
            table.add_column("Script", style="magenta")
            table.add_column("Type", justify="center", style="green")
            table.add_column("Dependencies", justify="center", style="yellow")
            table.add_column("Privileges", justify="center", style="red")
            table.add_column("Git Status", justify="center", style="blue")
            
            for num, script in scripts.items():
                script_type = "Streamlit" if ScriptAnalyzer.is_streamlit_app(script) else "Python"
                has_deps = ScriptAnalyzer.has_external_dependencies(script)
                needs_sudo = ScriptAnalyzer.requires_sudo_privileges(script)
                
                deps_status = "📦" if has_deps else "✅"
                sudo_status = "🔒" if needs_sudo else "🔓"
                git_status = "✅"  # Default, actual status would come from GitManager
                
                table.add_row(
                    str(num),
                    script.name,
                    script_type,
                    deps_status,
                    sudo_status,
                    git_status
                )
            
            self.console.print(table)
        else:
            print("\n📜 Available Python scripts:")
            print("-" * 80)
            for num, script in scripts.items():
                script_type = "Streamlit app" if ScriptAnalyzer.is_streamlit_app(script) else "Python script"
                has_deps = " (needs env)" if ScriptAnalyzer.has_external_dependencies(script) else " (no deps)"
                needs_sudo = " (needs sudo)" if ScriptAnalyzer.requires_sudo_privileges(script) else ""
                print(f"{num:2d}. {script.name:25} ({script_type}{has_deps}{needs_sudo})")
            print("-" * 80)
    
    def get_user_choice(self, scripts: Dict[int, Path]) -> Optional[Path]:
        """Get user's script selection."""
        while True:
            try:
                if self.rich_available:
                    from rich.prompt import Prompt
                    choice = Prompt.ask(
                        "\n[bold cyan]Enter the number of the script to run[/bold cyan]",
                        choices=[str(i) for i in scripts.keys()] + ["b", "back", "q", "quit"],
                        default="b"
                    )
                else:
                    choice = input("\nEnter the number of the script to run (b to go back, q to quit): ").strip()
                    
                if choice.lower() in ['b', 'back']:
                    return None
                elif choice.lower() in ['q', 'quit']:
                    self.print_status("Exiting...", "info")
                    sys.exit(0)
                    
                choice_num = int(choice)
                if choice_num in scripts:
                    return scripts[choice_num]
                    
                self.print_status(f"Invalid choice. Please enter a number between 1 and {len(scripts)}", "error")
            except ValueError:
                self.print_status("Please enter a valid number, 'b' to go back, or 'q' to quit", "error")
    
    def confirm_action(self, question: str) -> bool:
        """Ask for user confirmation."""
        if self.rich_available:
            from rich.prompt import Confirm
            return Confirm.ask(f"[yellow]{question}[/yellow]")
        else:
            return input(f"{question} [y/N]: ").lower().startswith('y')
    
    def get_input(self, prompt: str, default: str = "", password: bool = False) -> str:
        """Get user input with a prompt."""
        if self.rich_available:
            from rich.prompt import Prompt
            if password:
                return Prompt.ask(f"[cyan]{prompt}[/cyan]", password=True, default=default)
            else:
                return Prompt.ask(f"[cyan]{prompt}[/cyan]", default=default)
        else:
            if password:
                return getpass.getpass(f"{prompt}: ")
            else:
                response = input(f"{prompt} [{default}]: ").strip()
                return response if response else default


# =============================================================================
# MODULE 2: SCRIPT ANALYZER - Analyzes scripts for dependencies and properties
# =============================================================================

class ScriptAnalyzer:
    """Analyzes Python scripts to detect dependencies, requirements, and script properties."""
    
    @staticmethod
    def find_python_scripts(directory: str = ".") -> Dict[int, Path]:
        """Find all Python scripts in the directory except the current file."""
        current_script = os.path.basename(__file__)
        scripts = [f for f in Path(directory).glob("*.py") 
                   if f.is_file() and f.name != current_script]
        return {i+1: script for i, script in enumerate(scripts)}
    
    @staticmethod
    def is_streamlit_app(script_path: Path) -> bool:
        """Check if a script is a Streamlit application."""
        try:
            with open(script_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Check for streamlit imports
            import_patterns = [
                r'^\s*import\s+streamlit',
                r'^\s*from\s+streamlit',
                r'^\s*import\s+streamlit\s+as\s+\w+',
            ]
            
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if (re.match(r'^\s*import\s+streamlit', line) or 
                    re.match(r'^\s*from\s+streamlit', line) or
                    re.match(r'^\s*import\s+streamlit\s+as\s+\w+', line)):
                    return True
            
            return False
        except Exception as e:
            print(f"Warning: Could not check if {script_path.name} is a Streamlit app: {e}")
            return False
    
    @staticmethod
    def requires_sudo_privileges(script_path: Path) -> bool:
        """Check if a script requires sudo/administrator privileges."""
        try:
            with open(script_path, 'r', encoding='utf-8') as file:
                content = file.read()
                port_80_patterns = [
                    r'port\s*[=:]\s*80',
                    r'PORT\s*[=:]\s*80',
                    r'port\s*=\s*80',
                    r'PORT\s*=\s*80',
                    r':80',
                    r'bind.*80',
                    r'0\.0\.0\.0:80',
                    r'localhost:80',
                    r'127\.0\.0\.1:80'
                ]
                return any(re.search(pattern, content) for pattern in port_80_patterns)
        except Exception:
            return False
    
    @staticmethod
    def extract_imports(script_path: Path) -> Set[str]:
        """Extract all imports from a Python script."""
        try:
            with open(script_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except Exception as e:
            print(f"Warning: Could not read {script_path.name}: {str(e)}")
            return set()
        
        imports = set()
        
        # AST parsing (most accurate)
        try:
            node = ast.parse(content, filename=str(script_path))
            for n in ast.walk(node):
                if isinstance(n, ast.Import):
                    for alias in n.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(n, ast.ImportFrom):
                    if n.module and n.level == 0:
                        imports.add(n.module.split('.')[0])
        except SyntaxError:
            # Regex fallback for syntax errors
            import_patterns = [
                r'^\s*import\s+(\w+)',
                r'^\s*from\s+(\w+)\s+import',
                r'^\s*import\s+(\w+)\s+as',
            ]
            for pattern in import_patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                imports.update(matches)
        
        return imports
    
    @staticmethod
    def has_external_dependencies(script_path: Path) -> bool:
        """Check if a script has external dependencies."""
        all_imports = ScriptAnalyzer.extract_imports(script_path)
        local_modules = {'db_utils'}
        
        for imp in all_imports:
            if imp not in local_modules and not ScriptAnalyzer.is_stdlib_module(imp):
                return True
        
        if 'streamlit' in all_imports:
            return True
        
        return False
    
    @staticmethod
    def is_stdlib_module(module_name: str) -> bool:
        """Check if a module is part of Python standard library."""
        try:
            return module_name in sys.stdlib_module_names
        except AttributeError:
            # Fallback for Python < 3.10
            import distutils.sysconfig
            stdlib_path = distutils.sysconfig.get_python_lib(standard_lib=True)
            return (Path(stdlib_path) / module_name).exists()
    
    @staticmethod
    def is_interactive_script(script_path: Path) -> bool:
        """Detect if script uses input() function for interactive input."""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return bool(re.search(r'\binput\s*\(', content))
        except Exception as e:
            print(f"Warning: Could not check if script is interactive: {e}")
            return False
    
    @staticmethod
    def is_port_in_use(port: int = 80) -> bool:
        """Check if a port is already in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return False
            except socket.error:
                return True
    
    @staticmethod
    def analyze_for_deployment(script_path: Path) -> Dict[str, Any]:
        """Analyze script for deployment requirements."""
        analysis = {
            'type': 'streamlit' if ScriptAnalyzer.is_streamlit_app(script_path) else 'python',
            'dependencies': list(ScriptAnalyzer.extract_imports(script_path)),
            'has_database': False,
            'has_web_ui': False,
            'has_api': False,
            'needs_env_vars': False
        }
        
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Check for database connections
                db_keywords = ['psycopg2', 'sqlite3', 'mysql', 'postgresql', 'sqlalchemy', 'cursor', 'execute']
                analysis['has_database'] = any(keyword in content.lower() for keyword in db_keywords)
                
                # Check for web UI frameworks
                ui_keywords = ['streamlit', 'flask', 'django', 'fastapi', 'gradio', 'panel']
                analysis['has_web_ui'] = any(keyword in content.lower() for keyword in ui_keywords)
                
                # Check for API frameworks
                api_keywords = ['fastapi', 'flask', 'requests', 'api', 'endpoint']
                analysis['has_api'] = any(keyword in content.lower() for keyword in api_keywords)
                
                # Check for environment variables
                env_keywords = ['os.getenv', 'os.environ', 'dotenv', 'load_dotenv', 'environ.get']
                analysis['needs_env_vars'] = any(keyword in content.lower() for keyword in env_keywords)
                
        except Exception as e:
            print(f"Warning: Could not analyze deployment requirements: {e}")
        
        return analysis


# =============================================================================
# MODULE 3: DEPENDENCY MANAGER - Manages virtual environments and dependencies
# =============================================================================

class DependencyManager:
    """Manages virtual environments, dependency installation, and project fingerprinting."""
    
    def __init__(self, ui_manager: UIManager):
        self.ui = ui_manager
    
    def get_project_fingerprint(self) -> str:
        """Generate a fingerprint for the current project based on script content."""
        scripts = [f for f in Path('.').glob('*.py') if f.is_file()]
        requirements_file = Path('requirements.txt')
        
        content_hash = hashlib.md5()
        
        # Hash all Python scripts
        for script in sorted(scripts):
            try:
                with open(script, 'rb') as f:
                    content_hash.update(f.read())
            except:
                pass
        
        # Hash requirements.txt if it exists
        if requirements_file.exists():
            try:
                with open(requirements_file, 'rb') as f:
                    content_hash.update(f.read())
            except:
                pass
        
        return content_hash.hexdigest()
    
    def generate_requirements(self, script_path: Path) -> bool:
        """Generate requirements.txt based on script imports."""
        all_imports = ScriptAnalyzer.extract_imports(script_path)
        
        self.ui.print_status(f"Detected imports: {all_imports}", "info")
        
        local_modules = {'db_utils'}
        dependency_map = {
            'talib': ['TA-Lib'],
            'binance': ['python-binance'],
            'sklearn': ['scikit-learn'],
            'cv2': ['opencv-python'],
            'yaml': ['pyyaml'],
            'PIL': ['pillow'],
            'bs4': ['beautifulsoup4'],
            'requests': ['requests'],
            'dotenv': ['python-dotenv'],
            'tqdm': ['tqdm'],
            'rich': ['rich'],
            'psycopg2': ['psycopg2-binary'],
            'streamlit': ['streamlit'],
            'fastapi': ['fastapi'],
            'flask': ['flask'],
            'django': ['django'],
            'numpy': ['numpy'],
            'pandas': ['pandas'],
            'matplotlib': ['matplotlib'],
            'seaborn': ['seaborn'],
            'plotly': ['plotly'],
            'pytest': ['pytest'],
            'black': ['black'],
            'flake8': ['flake8'],
            'mypy': ['mypy']
        }
        
        requirements = set()
        for imp in all_imports:
            if imp in local_modules:
                self.ui.print_status(f"Skipping local module: {imp}", "info")
                continue
            if ScriptAnalyzer.is_stdlib_module(imp):
                self.ui.print_status(f"Skipping stdlib module: {imp}", "info")
                continue
                
            self.ui.print_status(f"Processing import: {imp}", "info")
            
            if imp in dependency_map:
                mapped_packages = dependency_map[imp]
                requirements.update(mapped_packages)
                self.ui.print_status(f"Mapped {imp} to {mapped_packages}", "success")
            else:
                requirements.add(imp)
                self.ui.print_status(f"Added direct package: {imp}", "success")
        
        # Force include python-dotenv if we have database-related imports
        if any(imp in all_imports for imp in ['psycopg2', 'dotenv']):
            requirements.add('python-dotenv')
            self.ui.print_status("Added python-dotenv (required for database utils)", "info")
        
        if 'streamlit' in all_imports or ScriptAnalyzer.is_streamlit_app(script_path):
            requirements.add('streamlit')
        
        # Add common development dependencies
        if self.ui.confirm_action("Include development dependencies (pytest, black, flake8)?"):
            requirements.update(['pytest', 'black', 'flake8', 'mypy'])
        
        if not requirements:
            self.ui.print_status("No external dependencies found", "info")
            return False
        
        with open("requirements.txt", 'w') as f:
            for req in sorted(requirements):
                f.write(f"{req}\n")
        
        # Create requirements-dev.txt
        dev_requirements = {'pytest', 'black', 'flake8', 'mypy', 'pre-commit'}
        with open("requirements-dev.txt", 'w') as f:
            for req in sorted(dev_requirements):
                f.write(f"{req}\n")
        
        if self.ui.rich_available:
            req_list = "\n".join([f"  • {req}" for req in sorted(requirements)])
            self.ui.print_panel("📋 Generated requirements.txt", req_list, "green")
            self.ui.print_status("Also created requirements-dev.txt for development", "info")
        else:
            print("📋 Generated requirements.txt with detected dependencies")
            print("Also created requirements-dev.txt for development")
            
        return True
    
    def setup_venv(self, venv_name: str = "venv", current_fingerprint: str = "") -> Optional[Path]:
        """Create or reuse a Python virtual environment."""
        venv_path = Path(venv_name)
        
        if venv_path.exists():
            if self._is_venv_locked(venv_path):
                self.ui.print_status(f"Virtual environment is locked: {venv_name}", "warning")
                if not self._force_unlock_venv(venv_path):
                    return self._create_new_venv(f"{venv_name}_{int(time.time())}", current_fingerprint)
            
            if self._is_venv_owned_by_another_user(venv_path):
                self.ui.print_status(f"Virtual environment owned by another user: {venv_name}", "warning")
                if not self._force_remove_venv(venv_path):
                    return self._create_new_venv(f"{venv_name}_{int(time.time())}", current_fingerprint)
            
            if self._is_venv_valid(venv_path, current_fingerprint):
                self.ui.print_status(f"Reusing existing virtual environment: {venv_name}", "success")
                return venv_path
            else:
                self.ui.print_status(f"Virtual environment needs refresh. Deleting: {venv_name}", "warning")
                if not self._force_remove_venv(venv_path):
                    return self._create_new_venv(f"{venv_name}_{int(time.time())}", current_fingerprint)
        
        return self._create_new_venv(venv_name, current_fingerprint)
    
    def _create_new_venv(self, venv_name: str, current_fingerprint: str) -> Optional[Path]:
        """Create a new virtual environment."""
        venv_path = Path(venv_name)
        
        try:
            progress = self.ui.create_progress_bar()
            if progress:
                with progress:
                    task = progress.add_task("[cyan]Creating venv...", total=100)
                    try:
                        subprocess.run([sys.executable, "-m", "venv", venv_name, "--copies"], 
                                      check=True, capture_output=True)
                        progress.update(task, completed=100)
                    except subprocess.CalledProcessError as e:
                        self.ui.print_status(f"Failed to create virtual environment: {e}", "error")
                        return None
            else:
                try:
                    subprocess.run([sys.executable, "-m", "venv", venv_name, "--copies"], 
                                  check=True, capture_output=True)
                except subprocess.CalledProcessError as e:
                    self.ui.print_status(f"Failed to create virtual environment: {e}", "error")
                    return None
            
            self.ui.print_status(f"Successfully created virtual environment: {venv_name}", "success")
            self._set_venv_fingerprint(venv_path, current_fingerprint)
            return venv_path
        except Exception as e:
            self.ui.print_status(f"Unexpected error creating venv: {e}", "error")
            return None
    
    def install_dependencies(self, venv_path: Path) -> None:
        """Install dependencies from requirements.txt."""
        pip_path = self._get_venv_executable(venv_path, "pip")
        
        if not Path("requirements.txt").exists():
            self.ui.print_status("No requirements.txt found - nothing to install", "info")
            return
        
        self.ui.print_status("Checking dependencies...", "progress")
        
        try:
            # Upgrade pip first
            self.ui.print_status("Upgrading pip...", "progress")
            subprocess.run([pip_path, "install", "--upgrade", "pip"], 
                          check=True, capture_output=True, text=True)
            
            # Install all requirements
            self.ui.print_status("Installing all dependencies...", "progress")
            
            result = subprocess.run(
                [pip_path, "install", "-r", "requirements.txt"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.ui.print_status("✅ Dependencies installed successfully", "success")
                if result.stdout:
                    self.ui.print_status("Installation output:", "info")
                    print(result.stdout)
            else:
                self.ui.print_status("❌ Failed to install some dependencies", "error")
                if result.stderr:
                    self.ui.print_status("Error details:", "error")
                    print(result.stderr)
                
                # Try installing packages one by one
                self.ui.print_status("Attempting individual package installation...", "warning")
                with open("requirements.txt", 'r') as f:
                    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
                for req in requirements:
                    try:
                        self.ui.print_status(f"Installing {req}...", "progress")
                        subprocess.run(
                            [pip_path, "install", req],
                            check=True,
                            capture_output=True,
                            text=True,
                            timeout=120
                        )
                        self.ui.print_status(f"✅ {req} installed successfully", "success")
                    except subprocess.CalledProcessError as e:
                        self.ui.print_status(f"❌ Failed to install {req}", "error")
                        if e.stderr:
                            print(e.stderr)
            
        except subprocess.TimeoutExpired:
            self.ui.print_status("❌ Installation timeout - try again", "error")
        except Exception as e:
            self.ui.print_status(f"❌ Unexpected error during installation: {e}", "error")
    
    def _get_venv_executable(self, venv_path: Path, name: str) -> str:
        """Get path to an executable in the virtual environment."""
        if sys.platform == "win32":
            return str(venv_path/"Scripts"/f"{name}.exe")
        return str(venv_path/"bin"/name)
    
    def _get_venv_fingerprint(self, venv_path: Path) -> Optional[str]:
        """Get the project fingerprint stored in the venv."""
        fingerprint_file = venv_path / ".project_fingerprint"
        if fingerprint_file.exists():
            try:
                return fingerprint_file.read_text().strip()
            except:
                return None
        return None
    
    def _set_venv_fingerprint(self, venv_path: Path, fingerprint: str) -> None:
        """Store the project fingerprint in the venv."""
        fingerprint_file = venv_path / ".project_fingerprint"
        fingerprint_file.write_text(fingerprint)
    
    def _is_venv_valid(self, venv_path: Path, current_fingerprint: str) -> bool:
        """Check if a virtual environment is valid and matches the current project."""
        stored_fingerprint = self._get_venv_fingerprint(venv_path)
        if stored_fingerprint != current_fingerprint:
            self.ui.print_status("Project changed, venv needs refresh", "warning")
            return False
        
        python_exec = self._get_venv_executable(venv_path, "python")
        pip_exec = self._get_venv_executable(venv_path, "pip")
        
        if not os.path.exists(python_exec) or not os.path.exists(pip_exec):
            self.ui.print_status("Virtual environment missing executables", "error")
            return False
        
        try:
            result = subprocess.run([python_exec, "--version"], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _is_venv_locked(self, venv_path: Path) -> bool:
        """Check if the virtual environment is locked by another process."""
        try:
            lock_file = venv_path / ".lock"
            fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
                os.unlink(str(lock_file))
                return False
            except (IOError, OSError):
                os.close(fd)
                return True
        except (IOError, OSError):
            return True
    
    def _force_unlock_venv(self, venv_path: Path) -> bool:
        """Force unlock a virtual environment."""
        try:
            lock_file = venv_path / ".lock"
            if lock_file.exists():
                os.unlink(str(lock_file))
                self.ui.print_status("Removed stale lock file", "success")
            
            for lock_pattern in ["*.lock", "*.pid"]:
                for lock_file in venv_path.glob(lock_pattern):
                    try:
                        os.unlink(str(lock_file))
                        self.ui.print_status(f"Removed lock file: {lock_file.name}", "success")
                    except:
                        pass
            
            return True
        except Exception as e:
            self.ui.print_status(f"Failed to unlock venv: {e}", "error")
            return False
    
    def _is_venv_owned_by_another_user(self, venv_path: Path) -> bool:
        """Check if the virtual environment was created by another user."""
        if not venv_path.exists():
            return False
        
        try:
            current_uid = os.getuid()
            venv_stat = os.stat(str(venv_path))
            return venv_stat.st_uid != current_uid
        except (AttributeError, OSError):
            return False
    
    def _force_remove_venv(self, venv_path: Path) -> bool:
        """Force remove a virtual environment."""
        if not venv_path.exists():
            return True
        
        self.ui.print_status(f"Force removing virtual environment: {venv_path}", "warning")
        
        try:
            shutil.rmtree(venv_path)
            self.ui.print_status("Successfully removed virtual environment", "success")
            return True
        except PermissionError:
            self.ui.print_status("Permission denied, trying to fix permissions...", "warning")
            try:
                for root, dirs, files in os.walk(venv_path):
                    for name in files:
                        file_path = os.path.join(root, name)
                        os.chmod(file_path, stat.S_IWRITE)
                shutil.rmtree(venv_path)
                self.ui.print_status("Successfully removed virtual environment after fixing permissions", "success")
                return True
            except Exception as e:
                self.ui.print_status(f"Failed to remove virtual environment: {e}", "error")
                return False
        except Exception as e:
            self.ui.print_status(f"Failed to remove virtual environment: {e}", "error")
            return False


# =============================================================================
# MODULE 4: GIT MANAGER - Handles Git repository setup and management
# =============================================================================

class GitManager:
    """Manages Git repository setup, credentials, and deployment configuration."""
    
    def __init__(self, ui_manager: UIManager):
        self.ui = ui_manager
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        config_file = Path(".git_runner_config.json")
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'git_username': '',
            'git_email': '',
            'github_token': '',
            'render_token': '',
            'preferred_remote': 'github',
            'auto_commit': True,
            'protected_branches': ['main', 'master']
        }
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        config_file = Path(".git_runner_config.json")
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def setup_git_repository(self) -> None:
        """Setup Git repository with proper configuration."""
        self.ui.print_panel("🔧 Git Repository Setup", "Setting up Git repository and configuration files", "blue")
        
        # Check if already a git repository
        if self.is_git_repository():
            self.ui.print_status("Already a Git repository", "info")
            if not self.ui.confirm_action("Reconfigure Git settings?"):
                return
        
        # Gather Git credentials
        self._gather_git_credentials()
        
        # Initialize or reinitialize Git repository
        self._init_git_repository()
        
        # Create essential Git files
        self._create_git_files()
        
        # Set up Git hooks
        self._setup_git_hooks()
        
        # Create initial commit
        if self.ui.confirm_action("Create initial commit?"):
            self._create_initial_commit()
        
        # Set up remote repository
        if self.ui.confirm_action("Set up remote repository (GitHub/GitLab)?"):
            self._setup_remote_repository()
        
        self.ui.print_status("✅ Git repository setup complete!", "success")
    
    def _gather_git_credentials(self) -> None:
        """Gather Git credentials from user."""
        self.ui.print_panel("🔐 Git Credentials", "Please provide your Git configuration details", "yellow")
        
        # Get Git username
        current_user = getpass.getuser()
        git_username = self.ui.get_input("Git username", current_user)
        self.config['git_username'] = git_username
        
        # Get Git email
        default_email = f"{current_user}@users.noreply.github.com"
        git_email = self.ui.get_input("Git email", default_email)
        self.config['git_email'] = git_email
        
        # Ask about GitHub token
        if self.ui.confirm_action("Do you have a GitHub personal access token?"):
            github_token = self.ui.get_input("GitHub token (leave blank to skip)", "", password=True)
            if github_token:
                self.config['github_token'] = github_token
        
        # Ask about Render token
        if self.ui.confirm_action("Do you want to deploy to Render.com?"):
            render_token = self.ui.get_input("Render API token (leave blank to skip)", "", password=True)
            if render_token:
                self.config['render_token'] = render_token
        
        self._save_config()
    
    def _init_git_repository(self) -> None:
        """Initialize Git repository with proper configuration."""
        try:
            # Initialize git repository
            subprocess.run(["git", "init"], check=True, capture_output=True)
            
            # Configure git user
            subprocess.run(["git", "config", "user.name", self.config['git_username']], check=True)
            subprocess.run(["git", "config", "user.email", self.config['git_email']], check=True)
            
            # Set default branch to main
            subprocess.run(["git", "config", "init.defaultBranch", "main"], check=True)
            
            self.ui.print_status("✅ Git repository initialized", "success")
        except subprocess.CalledProcessError as e:
            self.ui.print_status(f"❌ Failed to initialize Git repository: {e}", "error")
    
    def _create_git_files(self) -> None:
        """Create essential Git and deployment files."""
        self.ui.print_status("Creating essential files...", "progress")
        
        # Create .gitignore
        gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environment
venv/
env/
.env
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Coverage
.coverage
htmlcov/

# Jupyter
.ipynb_checkpoints

# Streamlit
.streamlit/

# Test
.pytest_cache/
.tox/

# Secrets
secrets.toml
.devcontainer/
"""
        
        with open(".gitignore", "w") as f:
            f.write(gitignore_content)
        self.ui.print_status("✅ Created .gitignore", "success")
        
        # Create README.md
        readme_content = f"""# {Path('.').name}

## Project Description
A Python project created with Enhanced Script Runner.

## Features
- Python application
- Virtual environment management
- Git integration
- Deployment ready

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
