import json
import requests
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

class PlaywrightMCPClient:
    """Client for communicating with the Playwright MCP server"""
    
    def __init__(self, server_url: str = "http://localhost:3000"):
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 30
    
    def _send_message(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to the MCP server"""
        message = {
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params
        }
        
        try:
            response = self.session.post(
                f"{self.server_url}/messages",
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=45
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON response: {str(e)}"}
    
    def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL"""
        return self._send_message("navigate", {"url": url})
    
    def click(self, selector: str) -> Dict[str, Any]:
        """Click on an element"""
        return self._send_message("click", {"selector": selector})
    
    def type(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into an element"""
        return self._send_message("type", {"selector": selector, "text": text})
    
    def wait_for_element(self, selector: str, timeout: int = 10000) -> Dict[str, Any]:
        """Wait for an element to appear"""
        return self._send_message("waitForElement", {"selector": selector, "timeout": timeout})
    
    def take_screenshot(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot"""
        if not path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"screenshots/screenshot_{timestamp}.png"
        return self._send_message("screenshot", {"path": path})
    
    def debug(self) -> Dict[str, Any]:
        """Get debug information about the current page"""
        return self._send_message("debug", {})
    
    def health_check(self) -> Dict[str, Any]:
        """Check server health"""
        try:
            response = self.session.get(f"{self.server_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Health check failed: {str(e)}"}
    
    def close(self):
        """Close the session"""
        self.session.close()


class OpenRouterPlaywrightAssistant:
    """Assistant that uses OpenRouter API to interpret natural language prompts"""
    
    def __init__(self, api_key: str, model: str = "openai/gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
    
    def interpret_prompt(self, prompt: str) -> Dict[str, Any]:
        """Interpret a natural language prompt and convert it to Playwright actions"""
        
        system_prompt = """You are a Playwright automation assistant. Convert natural language instructions into specific Playwright actions.

Available actions:
1. navigate(url) - Navigate to a URL
2. click(selector) - Click an element (use CSS selectors)
3. type(selector, text) - Type text into an input field
4. waitForElement(selector) - Wait for an element to appear
5. screenshot(path) - Take a screenshot
6. debug() - Get page information

Respond with a JSON object containing:
{
    "explanation": "Brief explanation of what you'll do",
    "actions": [
        {"action": "navigate", "params": {"url": "https://example.com"}},
        {"action": "click", "params": {"selector": "#button-id"}},
        {"action": "type", "params": {"selector": "input[name='search']", "text": "search term"}}
    ]
}

Be specific with selectors. Use common patterns like:
- #id for IDs
- .class for classes
- input[name="name"] for input fields
- button[type="submit"] for submit buttons
- a[href*="text"] for links containing text

Example input: "Go to google.com and search for cats"
Example output:
{
    "explanation": "Navigate to Google and perform a search for 'cats'",
    "actions": [
        {"action": "navigate", "params": {"url": "https://google.com"}},
        {"action": "type", "params": {"selector": "input[name='q']", "text": "cats"}},
        {"action": "click", "params": {"selector": "input[name='btnK']"}}
    ]
}"""

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/playwright-automation",
                    "X-Title": "Playwright Automation"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000
                },
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "choices" not in result or not result["choices"]:
                return {"error": "No response from AI model"}
            
            content = result["choices"][0]["message"]["content"]
            
            try:
                parsed_response = json.loads(content)
                return parsed_response
            except json.JSONDecodeError:
                return {
                    "error": "Invalid JSON from AI model",
                    "raw_response": content
                }
                
        except requests.exceptions.RequestException as e:
            return {"error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}


class PlaywrightAutomationOrchestrator:
    """Main orchestrator that combines AI interpretation with Playwright execution"""
    
    def __init__(self, api_key: str, mcp_server_url: str, model: str = "openai/gpt-3.5-turbo"):
        self.assistant = OpenRouterPlaywrightAssistant(api_key, model)
        self.client = PlaywrightMCPClient(mcp_server_url)
        self.execution_history = []
    
    def execute_user_prompt(self, prompt: str, save_final_screenshot: bool = True) -> Dict[str, Any]:
        """Execute a user prompt end-to-end"""
        
        # Step 1: Interpret the prompt
        interpretation = self.assistant.interpret_prompt(prompt)
        
        if "error" in interpretation:
            return {
                "error": "Failed to interpret prompt",
                "details": interpretation,
                "overall_success": False
            }
        
        # Step 2: Execute the actions
        actions = interpretation.get("actions", [])
        execution_results = []
        
        for action_data in actions:
            action = action_data.get("action")
            params = action_data.get("params", {})
            
            # Execute the action
            if action == "navigate":
                result = self.client.navigate(params.get("url"))
            elif action == "click":
                result = self.client.click(params.get("selector"))
            elif action == "type":
                result = self.client.type(params.get("selector"), params.get("text"))
            elif action == "waitForElement":
                result = self.client.wait_for_element(params.get("selector"), params.get("timeout", 10000))
            elif action == "screenshot":
                result = self.client.take_screenshot(params.get("path"))
            elif action == "debug":
                result = self.client.debug()
            else:
                result = {"error": f"Unknown action: {action}"}
            
            # Record the execution result
            execution_result = {
                "action": action,
                "params": params,
                "result": result,
                "success": result.get("success", False) and "error" not in result,
                "description": f"Execute {action} with params {params}"
            }
            
            execution_results.append(execution_result)
            
            # If action failed, we might want to continue or stop
            if not execution_result["success"]:
                print(f"Warning: Action {action} failed: {result.get('error', 'Unknown error')}")
                # Continue with other actions for now
        
        # Step 3: Take final screenshot if requested
        screenshot_saved = False
        if save_final_screenshot:
            try:
                screenshot_result = self.client.take_screenshot()
                screenshot_saved = screenshot_result.get("success", False) and "error" not in screenshot_result
                if screenshot_saved:
                    execution_results.append({
                        "action": "take_screenshot",
                        "params": {},
                        "result": screenshot_result,
                        "success": True,
                        "description": "Take final screenshot"
                    })
            except Exception as e:
                print(f"Warning: Final screenshot failed: {e}")
        
        # Step 4: Determine overall success
        overall_success = all(result["success"] for result in execution_results)
        
        # Record in history
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "interpretation": interpretation,
            "execution_results": execution_results,
            "overall_success": overall_success,
            "screenshot_saved": screenshot_saved
        }
        
        self.execution_history.append(execution_record)
        
        return execution_record
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get the execution history"""
        return self.execution_history
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of all components"""
        return {
            "mcp_server": self.client.health_check(),
            "ai_model": self.assistant.model,
            "timestamp": datetime.now().isoformat()
        }
    
    def close(self):
        """Close all connections"""
        self.client.close()