.PHONY: install test validate security cameras docx paper

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

install:
	$(PYTHON) -m pip install -e ".[runtime,public-model,api]"

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

validate: test
	$(PYTHON) scripts/validate_release.py
	bash -n startup.sh
	bash tests/test_startup.sh
	./startup.sh --help >/dev/null
	$(PYTHON) infer.py --help >/dev/null
	$(PYTHON) discover_sources.py --help >/dev/null
	$(PYTHON) prepare_test_data.py --help >/dev/null
	$(PYTHON) prepare_demo_video.py --help >/dev/null
	$(PYTHON) prepare_training_data.py --help >/dev/null
	$(PYTHON) download_model.py --help >/dev/null
	$(PYTHON) query_counts.py --help >/dev/null
	$(PYTHON) train.py --help >/dev/null
	$(PYTHON) evaluate.py --help >/dev/null
	$(PYTHON) evaluate_public.py --help >/dev/null
	$(PYTHON) evaluate_counts.py --help >/dev/null
	$(PYTHON) export_model.py --help >/dev/null
	$(PYTHON) benchmark.py --help >/dev/null
	$(PYTHON) serve.py --help >/dev/null

security:
	$(PYTHON) -m ruff check src tests scripts *.py
	$(PYTHON) -m bandit -q -r src scripts -ll
	$(PYTHON) -m pip_audit

cameras:
	$(PYTHON) discover_sources.py --list-cameras

docx:
	npm run thesis:docx

paper:
	bash scripts/build_preprint.sh
