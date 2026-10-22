NEKARRA - Women's Boutique Website with PRIVATE Admin Dashboard

This is a Python/Flask web application (NOT a static HTML-only website).
Your private administration page is /admin; customer-facing website is /.
Customers cannot add/edit/delete products. All write actions require admin login.

WINDOWS - FIRST-TIME SETUP
1. Extract this ZIP to a folder on your PC.
2. Install Python 3.11+ from python.org. Select "Add Python to PATH".
3. Open Command Prompt (cmd) inside the extracted folder.
4. Run: py -m pip install -r requirements.txt
5. Set your private admin password: py app.py setup-admin
   Choose a STRONG password of at least 12 characters. Password characters are hidden while typing.
6. Run the website server: py app.py
7. In Chrome open http://127.0.0.1:5000/ for the public shop.
8. In Chrome open http://127.0.0.1:5000/admin to log in as the owner.

ADMIN WORKFLOW
- Sign in with your admin password.
- Click Add New Product, enter code, name, category, price in INR, sizes, fabric, description.
- Add your photo and tick Publish to make the product visible to customers.
- Save; products are kept in a SQLite database under data/catalog.sqlite3.
- Enter and save your own business WhatsApp number including country code.
- Edit, delete, or unpublish a product later via All Products.
- Your existing NK007 product is preloaded as a PRIVATE DRAFT with no photo; publish when ready.

IMPORTANT SECURITY / HOSTING
- Do not share your password or the data folder with customers.
- Customers can visit /admin but cannot see the dashboard or change products without signing in.
- For a LIVE public website, deploy this Flask app on a Python web host with persistent storage,
  HTTPS, secure session cookies (set NEKARRA_HTTPS=1), and database / upload backups.
- The included development server is only for local testing, NOT public deployment.
- Normal static hosting such as drag-and-drop Netlify static upload WILL NOT support this admin backend.
- Keep the data/ directory persistent across deployments and excluded from public web file access.
- Your uploaded photos stay on the server and are visible on the customer catalog when published.
- The editorial/collection banner photographs are layout placeholders, replace before launch.
- Do not use image content you lack rights to publish.


NEW: AI VIRTUAL FITTING ROOM
- Each published product has a "Try It On with AI" button.
- Customers choose their own photo, explicitly consent to third-party processing, and view the result.
- Customer photo is held in browser temporarily and sent server-side to FASHN AI; no visitor image is saved to local database/uploads folder.
- A real product image MUST be uploaded via /admin first; the draft sample placeholder cannot be used for try-on.
- Requires an external paid FASHN Developer API key (https://docs.fashn.ai/api-reference/tryon-v1-6).
- BEFORE starting app.py, in Windows PowerShell run:  $env:FASHN_API_KEY="YOUR_REAL_API_KEY"
- Then run: py app.py
- To use in cmd.exe instead: set FASHN_API_KEY=YOUR_REAL_API_KEY
- Without a key, the try-on button displays an understandable disabled-service message; no real AI preview can be generated.
- AI service fees apply per generation. Local trial limit: 5 requests per IP per hour; on a public deployment add durable per-user quota, bot protection, rate limits, and privacy/legal notices.
- Provider input and output retention rules apply; photos are transmitted to FASHN for processing. No exact body-size measurements or guaranteed fit are supplied.
- Try-on is optional. WhatsApp orders and your existing private product admin continue functioning normally.
- The AI try-on requires the Python server. Do not open index.html directly for this feature.
