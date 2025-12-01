#!/usr/bin/env python3
"""
Enhanced Python/Streamlit Script Runner - Modular Version
A comprehensive script runner with dependency management, virtual environments, and rich UI.
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
from pathlib import Path
from typing import Dict, Optional, Set, List, Tuple

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
            from rich.prompt import Prompt, Confirm
            from rich import box
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
            self.console.print(Panel.fit(banner_text, title="🐍 Enhanced Python/Streamlit Script Runner", style="bold blue"))
            self.console.print("=" * 60)
        else:
            print(banner_text)
            print("🐍 Enhanced Python/Streamlit Script Runner")
            print("=" * 50)
    
    def print_panel(self, title: str, content: str, style: str = "blue") -> None:
        """Print content in a styled panel."""
        if self.rich_available:
            from rich.panel import Panel
            self.console.print(Panel(content, title=title, style=style))
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
                "progress": "🔄"
            }
            styles = {
                "info": "blue",
                "success": "green",
                "warning": "yellow",
                "error": "red",
                "progress": "cyan"
            }
            icon = icons.get(status, "•")
            style = styles.get(status, "white")
            self.console.print(f"[{style}]{icon} {message}[/{style}]")
        else:
            print(f"{message}")
    
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
            
            for num, script in scripts.items():
                script_type = "Streamlit" if ScriptAnalyzer.is_streamlit_app(script) else "Python"
                has_deps = ScriptAnalyzer.has_external_dependencies(script)
                needs_sudo = ScriptAnalyzer.requires_sudo_privileges(script)
                deps_status = "📦" if has_deps else "✅"
                sudo_status = "🔒" if needs_sudo else "🔓"
                
                table.add_row(
                    str(num),
                    script.name,
                    script_type,
                    deps_status,
                    sudo_status
                )
            
            self.console.print(table)
        else:
            print("\n📜 Available Python scripts:")
            print("-" * 60)
            for num, script in scripts.items():
                script_type = "Streamlit app" if ScriptAnalyzer.is_streamlit_app(script) else "Python script"
                has_deps = " (needs env)" if ScriptAnalyzer.has_external_dependencies(script) else " (no deps)"
                needs_sudo = " (needs sudo)" if ScriptAnalyzer.requires_sudo_privileges(script) else ""
                print(f"{num:2d}. {script.name:20} ({script_type}{has_deps}{needs_sudo})")
            print("-" * 60)
    
    def get_user_choice(self, scripts: Dict[int, Path]) -> Optional[Path]:
        """Get user's script selection."""
        while True:
            try:
                if self.rich_available:
                    from rich.prompt import Prompt
                    choice = Prompt.ask(
                        "\n[bold cyan]Enter the number of the script to run[/bold cyan]",
                        choices=[str(i) for i in scripts.keys()] + ["q", "quit"],
                        default="q"
                    )
                else:
                    choice = input("\nEnter the number of the script to run (q to quit): ").strip()
                    
                if choice.lower() in ['q', 'quit']:
                    return None
                    
                choice_num = int(choice)
                if choice_num in scripts:
                    return scripts[choice_num]
                    
                self.print_status(f"Invalid choice. Please enter a number between 1 and {len(scripts)}", "error")
            except ValueError:
                self.print_status("Please enter a valid number or 'q' to quit", "error")
    
    def confirm_action(self, question: str) -> bool:
        """Ask for user confirmation."""
        if self.rich_available:
            from rich.prompt import Confirm
            return Confirm.ask(question)
        else:
            return input(f"{question} [y/N]: ").lower().startswith('y')


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
            'streamlit': ['streamlit']
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
        
        if not requirements:
            self.ui.print_status("No external dependencies found", "info")
            return False
        
        with open("requirements.txt", 'w') as f:
            for req in sorted(requirements):
                f.write(f"{req}\n")
        
        if self.ui.rich_available:
            req_list = "\n".join([f"  • {req}" for req in sorted(requirements)])
            self.ui.print_panel("📋 Generated requirements.txt", req_list, "green")
        else:
            print("📋 Generated requirements.txt with detected dependencies")
            
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
# MODULE 4: SCRIPT RUNNER - Executes scripts with proper environment
# =============================================================================

class ScriptRunner:
    """Handles script execution with proper environment setup and error handling."""
    
    def __init__(self, ui_manager: UIManager, dependency_manager: DependencyManager):
        self.ui = ui_manager
        self.deps = dependency_manager
    
    def run_script(self, script_path: Path, needs_sudo: bool = False) -> None:
        """Main method to run a script with proper environment setup."""
        if ScriptAnalyzer.has_external_dependencies(script_path):
            self.ui.print_status("Script has external dependencies", "info")
            
            if self.deps.generate_requirements(script_path):
                pass
            
            project_fingerprint = self.deps.get_project_fingerprint()
            venv_path = self.deps.setup_venv("venv", project_fingerprint)
            
            if venv_path:
                self.deps.install_dependencies(venv_path)
                self._run_script_with_env(venv_path, script_path, needs_sudo)
            else:
                self.ui.print_status("Failed to setup virtual environment, running directly", "warning")
                self._run_script_directly(script_path, needs_sudo)
        else:
            self.ui.print_status("Script uses only standard library - running directly", "success")
            self._run_script_directly(script_path, needs_sudo)
    
    def _run_script_directly(self, script_path: Path, needs_sudo: bool = False) -> None:
        """Run script directly without virtual environment."""
        if needs_sudo:
            self.ui.print_panel("🚀 Running Script", f"{script_path.name} with sudo privileges", "yellow")
            self._handle_sudo_script(script_path)
        else:
            self.ui.print_panel("🚀 Running Script", f"{script_path.name} directly (no dependencies needed)", "green")
            self._run_regular_script_directly(script_path)
    
    def _run_regular_script_directly(self, script_path: Path) -> None:
        """Run regular script directly."""
        if ScriptAnalyzer.is_interactive_script(script_path):
            self.ui.print_status("Detected interactive script, running without output capture.", "info")
            try:
                subprocess.run([sys.executable, str(script_path)], check=True)
            except subprocess.CalledProcessError as e:
                self.ui.print_status(f"Error in {script_path.name}: {e}", "error")
        else:
            try:
                result = subprocess.run(
                    [sys.executable, str(script_path)],
                    check=True,
                    capture_output=True,
                    text=True
                )
                self._display_script_output(result)
            except subprocess.CalledProcessError as e:
                self.ui.print_status(f"Error in {script_path.name}: {e}", "error")
    
    def _run_script_with_env(self, venv_path: Path, script_path: Path, needs_sudo: bool = False) -> None:
        """Run script using virtual environment."""
        if needs_sudo:
            self.ui.print_panel("🚀 Running Script", f"{script_path.name} with sudo privileges", "yellow")
            self._handle_sudo_script_with_env(venv_path, script_path)
        elif ScriptAnalyzer.is_streamlit_app(script_path):
            self._run_streamlit_app(venv_path, script_path)
        else:
            self._run_regular_script_with_env(venv_path, script_path)
    
    def _run_regular_script_with_env(self, venv_path: Path, script_path: Path) -> None:
        """Run a regular Python script with virtual environment."""
        python_path = self.deps._get_venv_executable(venv_path, "python")
        self.ui.print_panel("🚀 Running Script", f"{script_path.name} with Python interpreter", "green")

        if ScriptAnalyzer.is_interactive_script(script_path):
            self.ui.print_status("Detected interactive script, running without output capture.", "info")
            try:
                subprocess.run([python_path, str(script_path)], check=True)
            except subprocess.CalledProcessError as e:
                self._handle_script_error(e, script_path, venv_path)
        else:
            try:
                result = subprocess.run(
                    [python_path, str(script_path)],
                    check=True,
                    capture_output=True,
                    text=True
                )
                self._display_script_output(result)
            except subprocess.CalledProcessError as e:
                self._handle_script_error(e, script_path, venv_path)
    
    def _run_streamlit_app(self, venv_path: Path, script_path: Path) -> None:
        """Run a Streamlit application."""
        streamlit_path = self.deps._get_venv_executable(venv_path, "streamlit")
        self.ui.print_panel("🚀 Running Streamlit App", 
                           f"{script_path.name}\n\nStreamlit will open in your default browser at http://localhost:8501\n\nPress Ctrl+C to stop the server", 
                           "green")
        
        try:
            subprocess.run(
                [streamlit_path, "run", str(script_path)],
                check=True
            )
        except subprocess.CalledProcessError as e:
            self._handle_script_error(e, script_path, venv_path)
        except KeyboardInterrupt:
            self.ui.print_status("Streamlit server stopped by user", "warning")
    
    def _handle_sudo_script(self, script_path: Path) -> None:
        """Handle scripts that require sudo privileges."""
        if ScriptAnalyzer.is_port_in_use(80):
            self.ui.print_panel("❌ Port Conflict", "Port 80 is already in use by another process!", "red")
            self.ui.print_status("Please stop the service using port 80 and try again.", "info")
            self.ui.print_status("You can check what's using port 80 with: sudo lsof -i :80", "info")
            return
        
        self.ui.print_panel("🔒 Privilege Elevation", "This script requires administrator privileges to bind to port 80", "yellow")
        self.ui.print_status("Attempting to run with sudo...", "progress")
        
        try:
            result = subprocess.run(
                ['sudo', sys.executable, str(script_path)],
                check=True,
                text=True
            )
            if result.stdout:
                self._display_output_panel(result.stdout, "📝 Output", "blue")
        except subprocess.CalledProcessError as e:
            self.ui.print_status(f"Error running with sudo: {e}", "error")
            if "password" in str(e).lower():
                self.ui.print_panel("💡 Manual Sudo Required", "Sudo requires your password. Please run manually:", "yellow")
                print(f"   sudo {sys.executable} {script_path}")
        except KeyboardInterrupt:
            self.ui.print_status("Script stopped by user", "warning")
    
    def _handle_sudo_script_with_env(self, venv_path: Path, script_path: Path) -> None:
        """Handle sudo scripts with virtual environment."""
        if ScriptAnalyzer.is_port_in_use(80):
            self.ui.print_panel("❌ Port Conflict", "Port 80 is already in use by another process!", "red")
            self.ui.print_status("Please stop the service using port 80 and try again.", "info")
            self.ui.print_status("You can check what's using port 80 with: sudo lsof -i :80", "info")
            return
        
        python_path = self.deps._get_venv_executable(venv_path, "python")
        self.ui.print_panel("🔒 Privilege Elevation", "This script requires administrator privileges to bind to port 80", "yellow")
        self.ui.print_status("Attempting to run with sudo...", "progress")
        
        try:
            result = subprocess.run(
                ['sudo', python_path, str(script_path)],
                check=True,
                text=True
            )
            if result.stdout:
                self._display_output_panel(result.stdout, "📝 Output", "blue")
        except subprocess.CalledProcessError as e:
            self.ui.print_status(f"Error running with sudo: {e}", "error")
            if "password" in str(e).lower():
                self.ui.print_panel("💡 Manual Sudo Required", "Sudo requires your password. Please run manually:", "yellow")
                print(f"   sudo {python_path} {script_path}")
        except KeyboardInterrupt:
            self.ui.print_status("Script stopped by user", "warning")
    
    def _display_script_output(self, result: subprocess.CompletedProcess) -> None:
        """Display script output in appropriate format."""
        if result.stdout:
            self._display_output_panel(result.stdout, "📝 Output", "blue")
        if result.stderr:
            self._display_output_panel(result.stderr, "⚠️ Runtime warnings/errors", "yellow")
    
    def _display_output_panel(self, content: str, title: str, style: str) -> None:
        """Display output in a panel."""
        if self.ui.rich_available:
            from rich.panel import Panel
            self.ui.console.print(Panel(content, title=title, style=style))
        else:
            print(f"{title}:\n{content}")
    
    def _handle_script_error(self, error: subprocess.CalledProcessError, script_path: Path, venv_path: Path) -> None:
        """Handle script execution errors and suggest solutions."""
        error_msg = error.stderr if error.stderr else str(error)
        
        if self.ui.rich_available:
            from rich.panel import Panel
            self.ui.console.print(Panel(error_msg, title=f"❌ Error in {script_path.name}", style="red"))
        else:
            print(f"❌ Error in {script_path.name}:\n{error_msg}")
        
        # Detect missing dependencies and attempt to fix
        missing = re.search(r"No module named '([^']+)'", error_msg)
        if missing:
            missing_module = missing.group(1)
            self.ui.print_status(f"Missing dependency detected: {missing_module}", "warning")
            
            if self.ui.confirm_action("Attempt to fix automatically?"):
                self._fix_missing_dependencies(venv_path, error_msg)
                self.ui.print_status("Retrying script...", "progress")
                self._run_script_with_env(venv_path, script_path, ScriptAnalyzer.requires_sudo_privileges(script_path))
            else:
                pip_path = self.deps._get_venv_executable(venv_path, "pip")
                self.ui.print_status(f"Manual fix: Run '{pip_path} install {missing_module}'", "info")
        
        sys.exit(1)
    
    def _fix_missing_dependencies(self, venv_path: Path, error_output: str) -> None:
        """Attempt to fix missing dependencies based on error messages."""
        pip_path = self.deps._get_venv_executable(venv_path, "pip")
        missing_modules = re.findall(r"No module named '([^']+)'", error_output)
        
        for module in missing_modules:
            fix_map = {
                'talib': 'TA-Lib',
                'dotenv': 'python-dotenv',
                'cv2': 'opencv-python',
                'yaml': 'pyyaml',
                'PIL': 'pillow',
                'sklearn': 'scikit-learn',
                'binance': 'python-binance',
                'psycopg2': 'psycopg2-binary',
            }
            
            package = fix_map.get(module, module)
            self.ui.print_status(f"Attempting to fix missing module '{module}' by installing '{package}'", "warning")
            
            try:
                subprocess.run([pip_path, "install", package], check=True, capture_output=True)
                self.ui.print_status(f"✅ Fixed {module} by installing {package}", "success")
            except subprocess.CalledProcessError:
                self.ui.print_status(f"❌ Failed to install {package} for module {module}", "error")


# =============================================================================
# MAIN APPLICATION - Orchestrates all modules
# =============================================================================

def main() -> None:
    """Main entry point for the script runner."""
    # Initialize modules
    ui = UIManager()
    deps = DependencyManager(ui)
    runner = ScriptRunner(ui, deps)
    
    # Display banner
    ui.print_banner()
    
    # Set working directory to script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Find and display available scripts
    scripts = ScriptAnalyzer.find_python_scripts()
    if not scripts:
        ui.print_status("No Python scripts found in current directory", "error")
        sys.exit(1)
    
    ui.display_script_menu(scripts)
    selected_script = ui.get_user_choice(scripts)
    
    if not selected_script:
        ui.print_status("Exiting...", "info")
        sys.exit(0)
    
    ui.print_panel("🔧 Selected Script", selected_script.name, "blue")
    
    # Check if script requires sudo privileges
    needs_sudo = ScriptAnalyzer.requires_sudo_privileges(selected_script)
    
    # Run the selected script
    runner.run_script(selected_script, needs_sudo)


if __name__ == "__main__":
    main()
