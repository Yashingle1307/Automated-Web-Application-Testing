import os
import sys
import click
import json
from colorama import Fore, Style, init
from config import config
from client import PlaywrightAutomationOrchestrator

# Initialize colorama for Windows support
init(autoreset=True)

def print_banner():
    print("=====================================================")
    
def print_status(message: str, status: str = "info"):
    """Print status messages with colors"""
    colors = {
        "info": Fore.BLUE,
        "success": Fore.GREEN,
        "error": Fore.RED,
        "warning": Fore.YELLOW
    }
    color = colors.get(status, Fore.WHITE)
    print(f"{color}[{status.upper()}]{Style.RESET_ALL} {message}")

def print_action_result(action_result: dict):
    """Print action execution result"""
    action = action_result["action"]
    description = action_result["description"]
    success = action_result["success"]
    
    status_color = Fore.GREEN if success else Fore.RED
    status_text = "✓" if success else "✗"
    
    print(f"  {status_color}{status_text}{Style.RESET_ALL} {description}")
    
    # Special handling for screenshot action
    if action == "take_screenshot" and success:
        result = action_result.get("result", {}).get("result", {})
        screenshot_path = result.get("message", "").replace("Screenshot saved to ", "")
        if screenshot_path:
            print(f"    {Fore.CYAN}📸 Screenshot: {screenshot_path}{Style.RESET_ALL}")
    
    if not success and "error" in action_result["result"]:
        print(f"    {Fore.RED}Error: {action_result['result']['error']}{Style.RESET_ALL}")

@click.group()
def cli():
    """Playwright Automation CLI with MCP and OpenRouter integration"""
    pass

@cli.command()
@click.option('--api-key', '-k', help='OpenRouter API key (optional, uses config.py)')
@click.option('--model', '-m', help='OpenRouter model (default: openai/gpt-3.5-turbo)')
@click.option('--mcp-server', '-s', help='MCP server URL (optional, uses config.py)')
@click.option('--prompt', '-p', help='Automation prompt to execute')
@click.option('--interactive', '-i', is_flag=True, help='Start interactive mode')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--no-screenshot', is_flag=True, help='Disable automatic final screenshot')

def run(api_key, model, mcp_server, prompt, interactive, verbose, no_screenshot):
    """Execute Playwright automation based on natural language prompts"""
    
    print_banner()
    
    # Validate configuration
    if not config.validate():
        print_status("Configuration validation failed. Please check your config.py file.", "error")
        sys.exit(1)
    
    # Get API key from config or command line
    openrouter_api_key = api_key or config.get_openrouter_api_key()
    
    # Get model from config or command line
    openrouter_model = model or config.get_openrouter_model()
    
    # Get MCP server URL from config or command line
    mcp_server_url = mcp_server or config.get_mcp_server_url()
    
    # Show configuration info
    if verbose:
        print_status(f"Using OpenRouter model: {openrouter_model}", "info")
        print_status(f"MCP Server: {mcp_server_url}", "info")
        print_status(f"Auto-screenshot: {'Disabled' if no_screenshot else 'Enabled'}", "info")
        if config.is_using_openrouter():
            print_status("Using OpenRouter API", "info")
        else:
            print_status("Using legacy OpenAI API key with OpenRouter", "warning")
    
    # Create orchestrator
    orchestrator = PlaywrightAutomationOrchestrator(openrouter_api_key, mcp_server_url, openrouter_model)
    
    try:
        if interactive:
            interactive_mode(orchestrator, verbose, not no_screenshot)
        elif prompt:
            execute_single_prompt(orchestrator, prompt, verbose, not no_screenshot)
        else:
            print_status("Please provide a prompt with --prompt or use --interactive mode", "error")
            sys.exit(1)
    finally:
        orchestrator.close()

def execute_single_prompt(orchestrator: PlaywrightAutomationOrchestrator, prompt: str, verbose: bool, save_screenshot: bool = True):
    """Execute a single prompt"""
    print_status(f"Executing prompt: {prompt}", "info")
    print()
    
    try:
        result = orchestrator.execute_user_prompt(prompt, save_final_screenshot=save_screenshot)
        
        if "error" in result:
            print_status(f"Failed to execute prompt: {result['error']}", "error")
            if verbose and "details" in result:
                print(f"Details: {json.dumps(result['details'], indent=2)}")
            return
        
        # Print interpretation
        interpretation = result.get("interpretation", {})
        if interpretation:
            print_status("AI Interpretation:", "info")
            print(f"  {interpretation.get('explanation', 'No explanation provided')}")
            print()
        
        # Print execution results
        print_status("Execution Results:", "info")
        execution_results = result.get("execution_results", [])
        
        for action_result in execution_results:
            print_action_result(action_result)
        
        print()
        
        # Print overall status
        overall_success = result.get("overall_success", False)
        screenshot_saved = result.get("screenshot_saved", False)
        
        if overall_success:
            print_status("All actions completed successfully! ✨", "success")
            if save_screenshot and screenshot_saved:
                print_status("Final screenshot captured! 📸", "success")
            elif save_screenshot and not screenshot_saved:
                print_status("Automation completed but screenshot failed.", "warning")
        else:
            print_status("Some actions failed. Check the details above.", "warning")
        
        if verbose:
            print()
            print_status("Full Result (JSON):", "info")
            print(json.dumps(result, indent=2))
            
    except Exception as e:
        print_status(f"Unexpected error: {e}", "error")
        if verbose:
            import traceback
            traceback.print_exc()

def interactive_mode(orchestrator: PlaywrightAutomationOrchestrator, verbose: bool, save_screenshot: bool = True):
    """Run in interactive mode"""
    print_status("Starting interactive mode. Type 'quit' or 'exit' to stop.", "info")
    print_status("Type 'help' for available commands.", "info")
    if save_screenshot:
        print_status("Auto-screenshot is ENABLED - final results will be captured.", "info")
    else:
        print_status("Auto-screenshot is DISABLED.", "warning")
    print()
    
    while True:
        try:
            # Get user input
            user_input = input(f"{Fore.CYAN}🎭 Enter your automation prompt: {Style.RESET_ALL}").strip()
            
            if not user_input:
                continue
                
            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print_status("Goodbye! 👋", "info")
                break
            elif user_input.lower() == 'help':
                print_help()
                continue
            elif user_input.lower() == 'clear':
                os.system('cls' if os.name == 'nt' else 'clear')
                print_banner()
                continue
            elif user_input.lower() == 'screenshot':
                print_status("Taking manual screenshot...", "info")
                try:
                    # Use the orchestrator to take a screenshot instead of importing PlaywrightMCPClient
                    result = orchestrator.execute_user_prompt("Take a screenshot")
                    if result.get("overall_success", False):
                        print_status("Screenshot saved! 📸", "success")
                    else:
                        error_msg = result.get("error", "Unknown error occurred")
                        print_status(f"Screenshot failed: {error_msg}", "error")
                except Exception as e:
                    print_status(f"Screenshot error: {e}", "error")
                continue
            
            print()
            execute_single_prompt(orchestrator, user_input, verbose, save_screenshot)
            print()
            
        except KeyboardInterrupt:
            print()
            print_status("Interrupted by user. Goodbye! 👋", "info")
            break
        except Exception as e:
            print_status(f"Unexpected error: {e}", "error")
            if verbose:
                import traceback
                traceback.print_exc()

def print_help():
    """Print help information"""
    help_text = f"""
{Fore.CYAN}Available Commands:{Style.RESET_ALL}
  help        - Show this help message
  clear       - Clear the screen
  screenshot  - Take a manual screenshot
  quit/exit/q - Exit the application

{Fore.CYAN}Example Prompts:{Style.RESET_ALL}
  • "Go to google.com and search for cats"
  • "Navigate to amazon.com and click on the sign-in button"
  • "Open github.com, go to the search box, and type 'playwright'"
  • "Take a screenshot of the current page"
  • "Click on the first link in the search results"

{Fore.CYAN}Tips:{Style.RESET_ALL}
  • Be specific about what you want to automate
  • Use natural language - the AI will convert it to actions
  • Make sure the MCP server is running (npm start)
  • Use CSS selectors for precise element targeting
  • Final screenshots are automatically saved with timestamps

{Fore.CYAN}OpenRouter Configuration:{Style.RESET_ALL}
  • Current model: {config.get_openrouter_model()}
  • API Status: {'OpenRouter' if config.is_using_openrouter() else 'Legacy OpenAI key'}
"""
    print(help_text)

@cli.command()
@click.option('--port', '-p', default=3000, help='Port number for the MCP server')
def start_server(port):
    """Start the JavaScript MCP server"""
    print_status("Starting Playwright MCP server...", "info")
    print_status(f"Server will be available at http://localhost:{port}", "info")
    print_status("Press Ctrl+C to stop the server", "warning")
    
    try:
        import subprocess
        process = subprocess.Popen(
            ['npm', 'start'],
            env={**os.environ, 'PORT': str(port)}
        )
        process.wait()
    except KeyboardInterrupt:
        print_status("Server stopped by user", "info")
    except FileNotFoundError:
        print_status("npm not found. Please install Node.js and npm", "error")
    except Exception as e:
        print_status(f"Error starting server: {e}", "error")

@cli.command()
def test():
    """Test OpenRouter client connection"""
    print_status("Testing OpenRouter client connection...", "info")
    
    try:
        from client import OpenRouterPlaywrightAssistant
        
        api_key = config.get_openrouter_api_key()
        model = config.get_openrouter_model()
        
        if not api_key:
            print_status("No API key found in configuration", "error")
            return
        
        print_status(f"Testing with model: {model}", "info")
        
        assistant = OpenRouterPlaywrightAssistant(api_key, model)
        result = assistant.interpret_prompt("Navigate to google.com")
        
        if "error" in result:
            print_status(f"OpenRouter test failed: {result['error']}", "error")
        else:
            print_status("OpenRouter client test passed! ✅", "success")
            print(f"Response: {result.get('explanation', 'No explanation')}")
            
    except ImportError as e:
        print_status(f"Import error: {e}. Please check if client.py contains OpenRouterPlaywrightAssistant class.", "error")
    except Exception as e:
        print_status(f"OpenRouter client test failed: {e}", "error")

@cli.command()
def setup():
    """Setup the environment and install dependencies"""
    print_status("Setting up Playwright Automation environment with OpenRouter...", "info")
    
    try:
        # Install Python dependencies
        print_status("Installing Python dependencies...", "info")
        req_file = "requirements_simple.txt" if os.path.exists("requirements_simple.txt") else "requirements.txt"
        
        if not os.path.exists(req_file):
            print_status(f"Requirements file {req_file} not found", "warning")
        else:
            os.system(f"pip install -r {req_file}")
        
        # Install Node.js dependencies
        print_status("Installing Node.js dependencies...", "info")
        if not os.path.exists("package.json"):
            print_status("package.json not found", "warning")
        else:
            os.system("npm install")
        
        # Install Playwright browsers
        print_status("Installing Playwright browsers...", "info")
        os.system("npx playwright install")
        
        print_status("Setup complete! 🎉", "success")
        print()
        print_status("Next steps:", "info")
        print("1. Set your OpenRouter API key: export OPENROUTER_API_KEY=your_key_here")
        print("2. Optional: Set model: export OPENROUTER_MODEL=openai/gpt-3.5-turbo")
        print("3. Test OpenRouter: python main.py test")
        print("4. Start the MCP server: python main.py start-server")
        print("5. Run automation: python main.py run --interactive")
        
    except Exception as e:
        print_status(f"Setup failed: {e}", "error")

if __name__ == '__main__':
    cli()