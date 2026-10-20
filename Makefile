.PHONY: test validate docx

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

validate: test
	python3 scripts/validate_release.py
	python3 infer.py --help >/dev/null
	python3 train.py --help >/dev/null
	python3 evaluate.py --help >/dev/null
	python3 evaluate_counts.py --help >/dev/null
	python3 export_model.py --help >/dev/null
	python3 benchmark.py --help >/dev/null

docx:
	npm run thesis:docx
