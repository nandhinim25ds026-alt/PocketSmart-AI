# PocketSmart AI

## How to run this

1. Rename `.env.example` to `.env` and paste in your real Gemini API key.
2. Open a terminal in this folder and run:
   ```
   python -m venv venv
   ```
   Then activate it:
   - Windows: `venv\Scripts\activate`
   - Mac: `source venv/bin/activate`
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Start the server:
   ```
   uvicorn app:app --reload
   ```
5. Open your browser to: http://127.0.0.1:8000
