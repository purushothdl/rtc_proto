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
