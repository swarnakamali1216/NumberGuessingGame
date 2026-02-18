import os
from waitress import serve
from web.server_postgresql import app
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Guess It Game on Windows (Waitress)...")
    print(f"🔗 Local access: http://localhost:{port}")
    
    # Run the app with waitress (the Windows-friendly production server)
    serve(app, host='0.0.0.0', port=port, threads=4)
