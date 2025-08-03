from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import json
from client import PlaywrightAutomationOrchestrator
from config import config

app = Flask(__name__)
CORS(app)

# Global orchestrator instance
orchestrator = None

def get_orchestrator():
    """Get or create orchestrator instance"""
    global orchestrator
    if orchestrator is None:
        api_key = config.get_openrouter_api_key()
        mcp_server_url = config.get_mcp_server_url()
        model = config.get_openrouter_model()
        
        if not api_key:
            raise ValueError("OpenRouter API key not configured")
        
        orchestrator = PlaywrightAutomationOrchestrator(api_key, mcp_server_url, model)
    
    return orchestrator

@app.route('/')
def index():
    """Serve the main HTML page"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <h1>index.html not found</h1>
        <p>Please make sure index.html is in the same directory as app.py</p>
        <p>Current directory: {}</p>
        """.format(os.getcwd())

@app.route('/api/execute', methods=['POST'])
def execute_automation():
    """Execute automation based on natural language prompt"""
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({
                'success': False,
                'error': 'Prompt is required'
            }), 400
        
        prompt = data['prompt'].strip()
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Prompt cannot be empty'
            }), 400
        
        print(f"🚀 Executing prompt: {prompt}")
        
        # Get orchestrator and execute
        orch = get_orchestrator()
        result = orch.execute_user_prompt(prompt, save_final_screenshot=True)
        
        # Process the result
        if "error" in result:
            return jsonify({
                'success': False,
                'error': result['error'],
                'details': result.get('details', {})
            }), 500
        
        # Extract useful information
        overall_success = result.get('overall_success', False)
        execution_results = result.get('execution_results', [])
        screenshot_saved = result.get('screenshot_saved', False)
        interpretation = result.get('interpretation', {})
        
        # Find screenshot path if available
        screenshot_path = None
        for exec_result in execution_results:
            if exec_result.get('action') == 'take_screenshot' and exec_result.get('success'):
                screenshot_result = exec_result.get('result', {}).get('result', {})
                message = screenshot_result.get('message', '')
                if 'Screenshot saved to' in message:
                    screenshot_path = message.replace('Screenshot saved to ', '').strip()
                    break
        
        # Create summary of actions
        actions_summary = []
        for exec_result in execution_results:
            actions_summary.append({
                'action': exec_result.get('action'),
                'description': exec_result.get('description'),
                'success': exec_result.get('success', False),
                'error': exec_result.get('result', {}).get('error') if not exec_result.get('success') else None
            })
        
        response_data = {
            'success': overall_success,
            'interpretation': interpretation.get('explanation', 'No explanation provided'),
            'actions': actions_summary,
            'screenshot': f'/screenshot/{os.path.basename(screenshot_path)}' if screenshot_path else None,
            'screenshot_saved': screenshot_saved,
            'execution_count': len(execution_results),
            'timestamp': result.get('timestamp')
        }
        
        print(f"✅ Automation completed. Success: {overall_success}")
        return jsonify(response_data)
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return jsonify({
            'success': False,
            'error': f'Configuration error: {str(e)}'
        }), 500
        
    except Exception as e:
        print(f"❌ Automation error: {e}")
        return jsonify({
            'success': False,
            'error': f'Automation failed: {str(e)}'
        }), 500

@app.route('/screenshot/<filename>')
def serve_screenshot(filename):
    """Serve screenshot files"""
    try:
        # Look for screenshot in current directory and screenshots folder
        possible_paths = [
            filename,
            f'screenshots/{filename}',
            f'screenshot_{filename}' if not filename.startswith('screenshot_') else filename
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                from flask import send_file
                return send_file(path, mimetype='image/png')
        
        return jsonify({'error': 'Screenshot not found'}), 404
        
    except Exception as e:
        return jsonify({'error': f'Error serving screenshot: {str(e)}'}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check if orchestrator can be created and MCP server is accessible
        orch = get_orchestrator()
        health_result = orch.health_check()
        
        return jsonify({
            'status': 'healthy',
            'mcp_server': health_result.get('mcp_server', {}),
            'ai_model': health_result.get('ai_model', ''),
            'config': {
                'openrouter_configured': bool(config.get_openrouter_api_key()),
                'mcp_server_url': config.get_mcp_server_url(),
                'model': config.get_openrouter_model()
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/api/config')
def get_config():
    """Get current configuration"""
    return jsonify({
        'mcp_server_url': config.get_mcp_server_url(),
        'openrouter_model': config.get_openrouter_model(),
        'openrouter_configured': bool(config.get_openrouter_api_key())
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Validate configuration on startup
    if not config.validate():
        print("❌ Configuration validation failed. Please check your config.py file.")
        exit(1)
    
    print("🎭 Playwright Automation Frontend Server")
    print("=" * 50)
    print(f"🌐 Frontend: http://localhost:5000")
    print(f"🔗 API: http://localhost:5000/api/execute")
    print(f"❤️  Health: http://localhost:5000/api/health")
    print(f"🤖 Model: {config.get_openrouter_model()}")
    print(f"🎯 MCP Server: {config.get_mcp_server_url()}")
    print("=" * 50)
    print("Make sure your MCP server (server.js) is running on port 3000!")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)