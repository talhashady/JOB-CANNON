.PHONY: install dev test run api lint clean

install:
	pip install -e .

dev:
	pip install -e ".[all]"

test:
	pytest -q

run:
	career-assistant run --profile examples/sample_profile.json --query "python developer" --location "Remote" --sites indeed --results 25

api:
	uvicorn career_assistant.api.app:app --reload

clean:
	rm -rf build dist *.egg-info .pytest_cache **/__pycache__ *.db
