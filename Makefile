setup:
	poetry install
	poetry shell

start:
	poetry run streamlit run loan_calculator/app.py