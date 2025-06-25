# Install project dependencies
install:
	pip install -r requirements.txt

# Activate virtual environment (Windows)
venv:
	if not exist venv python -m venv venv
	@echo Run '.\venv\Scripts\activate' to activate.

# Start the FastAPI server
run:
	uvicorn app.main:app --reload

# Start the FastAPI server with 0.0.0.0 binding
run-public:
	uvicorn app.main:app --reload --host 0.0.0.0

# Start the frontend development server
serve:
	cd front_end && python -m http.server 8001

# Start the frontend development server with 0.0.0.0 binding
serve-public:
	cd front_end && python -m http.server 8001 --bind 0.0.0.0

