import os
import sys
import subprocess
import time
import threading
from pathlib import Path
from config import config

def print_banner():
    """Print the startup banner"""
    print("\n" + "="*80)
    print("Playwright Automation with MCP & OpenAI - Quick Start")
    print("="*80)

def check_dependencies():
    """Check if required dependencies are available"""
    missing_deps = []
    
    # Check for requests library
    try:
        import requests
    except ImportError:
        missing_deps.append("requests")
    
    # Check for colorama
    try:
        import colorama
    except ImportError:
        missing_deps.append("colorama")
    
    # Check for click
    try:
        import click
    except ImportError:
        missing_deps.append("click")
    
    if missing_deps:
        print(f"Missing Python dependencies: {', '.join(missing_deps)}")
        print("Please install them with: pip install " + " ".join(missing_deps))
        return False
    
    return True

def check_server_health():
    """Check if MCP server is running and healthy"""
    try:
        import requests
        response = requests.get('http://localhost:3000/health', timeout=2)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

def start_mcp_server():
    """Start the MCP server in a separate thread"""
    def run_server():
        try:
            # Check if Node.js is available
            subprocess.run(['node', '--version'], check=True, capture_output=True)
            subprocess.run([sys.executable, "main.py", "start-server"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"MCP server failed to start: {e}")
        except FileNotFoundError:
            print("Node.js not found. Please install Node.js to run the MCP server")
        except KeyboardInterrupt:
            print("\nMCP server stopped")
        except Exception as e:
            print(f"Unexpected error starting server: {e}")
    
    print("\nStarting MCP server...")
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    print("⏱️  Waiting for server to start...")
    for i in range(10):  # Wait up to 10 seconds
        time.sleep(1)
        if check_server_health():
            print("✅ MCP server is running at http://localhost:3000")
            return True
        print(f"   Checking server... ({i+1}/10)")
    
    print("⚠️  MCP server might not be ready yet. You can continue anyway...")
    return True

def run_interactive_mode():
    """Run the interactive automation mode"""
    print("\n🎯 Starting interactive mode...")
    print("You can now enter natural language prompts to automate browser actions!")
    print("Type 'help' for available commands, 'quit' to exit.\n")
    
    try:
        subprocess.run([sys.executable, "main.py", "run", "--interactive"])
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except FileNotFoundError:
        print("❌ main.py not found. Please make sure you're in the correct directory.")
    except Exception as e:
        print(f"❌ Error running interactive mode: {e}")

def run_setup():
    """Run the setup command"""
    print("\n🔧 Running setup...")
    try:
        subprocess.run([sys.executable, "main.py", "setup"], check=True)
        return True
    except subprocess.CalledProcessError:
        print("❌ Setup failed")
        return False
    except FileNotFoundError:
        print("❌ main.py not found. Please make sure you're in the correct directory.")
        return False
    except Exception as e:
        print(f"❌ Setup error: {e}")
        return False

def test_configuration():
    """Test the configuration"""
    print("\n🧪 Testing configuration...")
    try:
        subprocess.run([sys.executable, "main.py", "test"], check=True)
        return True
    except subprocess.CalledProcessError:
        print("❌ Configuration test failed")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def main():
    """Main startup function"""
    print_banner()
    
    # Check dependencies first
    if not check_dependencies():
        print("\n💡 Tip: You can install all dependencies by running option 2 (Setup)")
        print()
    
    # Check configuration
    if not config.validate():
        print("\n⚠️  Configuration issues detected. Consider running setup first.")
    
    print("\n🎯 What would you like to do?")
    print("1. Start the system (MCP server + interactive mode)")
    print("2. Run setup (install dependencies)")
    print("3. Test configuration")
    print("4. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice in ['1', '2', '3', '4']:
                break
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            return
        except Exception as e:
            print(f"❌ Input error: {e}")
            return
    
    if choice == '1':
        if not start_mcp_server():
            print("❌ Failed to start MCP server. Please check the logs above.")
            return
        run_interactive_mode()
    elif choice == '2':
        if run_setup():
            print("\n✅ Setup completed! You can now run option 1 to start the system.")
        else:
            print("❌ Setup failed. Please check the error messages above.")
    elif choice == '3':
        if test_configuration():
            print("\n✅ Configuration test passed!")
        else:
            print("❌ Configuration test failed. Consider running setup.")
    elif choice == '4':
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice. Please run the script again.")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check the logs and try again.")
        sys.exit(1)