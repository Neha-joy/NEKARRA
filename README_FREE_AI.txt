NEKARRA FREE LOCAL AI FITTING ROOM - WINDOWS

IMPORTANT: This package contains the integration, NOT the 2+ GB model weights.
It is for testing on your own computer. No API key is necessary.

1. Back up any previous NEKARRA_admin_website/data folder with your products, uploads, and admin login.
2. Extract this ZIP. The project files are inside NEKARRA_admin_website.
3. Open that folder in VS Code (the folder containing app.py).
4. Check your GPU in PowerShell: .\CHECK_GPU.ps1
   Or Task Manager > Performance > GPU. NVIDIA RTX 30xx or newer preferred.
5. Install Python 3.11 and Git. Then run:
   powershell -ExecutionPolicy Bypass -File .\INSTALL_FREE_AI.ps1
   This fetches the upstream open-source repository, dependencies, and about 2 GB of model weights;
   additional model weights may be downloaded on first run. Installation needs internet.
6. If you do not already have an admin account, run:
   .\.venv\Scripts\python.exe app.py setup-admin
7. Start your local server:
   .\.venv\Scripts\python.exe app.py
8. Open http://127.0.0.1:5000/admin and add a real garment photo, publish a product.
   Open http://127.0.0.1:5000 and try the AI button.

IF THE MODEL IS SLOW OR FAILS: GPU and CUDA setup can be complex; CPU may be impractically slow
and may lack sufficient RAM. Check the VS Code terminal for details. Try-on works only after
model dependencies and weights are installed.

PRIVACY: Customer images are processed on your computer, in memory during inference.
Generated results are temporarily held in RAM for up to 15 minutes. No product database photo storage.
There is no paid API request. Local processing is not the same as a production-ready public service.
Do not publish this development server on the internet: a public deployment needs HTTPS,
queueing, durable rate limiting, access controls, consent/privacy compliance and a capable GPU host.
Model weights are downloaded from upstream and subject to its licensing terms.
