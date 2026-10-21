.PHONY: install test validate cameras docx

install:
	python3 -m pip install -e ".[runtime,public-model,api]"

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

validate: test
	python3 scripts/validate_release.py
	bash -n startup.sh
	bash tests/test_startup.sh
	./startup.sh --help >/dev/null
	python3 infer.py --help >/dev/null
	python3 discover_sources.py --help >/dev/null
	python3 prepare_test_data.py --help >/dev/null
	python3 prepare_training_data.py --help >/dev/null
	python3 download_model.py --help >/dev/null
	python3 query_counts.py --help >/dev/null
	python3 train.py --help >/dev/null
	python3 evaluate.py --help >/dev/null
	python3 evaluate_counts.py --help >/dev/null
	python3 export_model.py --help >/dev/null
	python3 benchmark.py --help >/dev/null
	python3 serve.py --help >/dev/null

cameras:
	python3 discover_sources.py --list-cameras

docx:
	npm run thesis:docx
