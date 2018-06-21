.PHONY: requirements
requirements:
	pip install -r requirements.txt

.PHONY: install
install:
	pip install --upgrade .

.PHONY: clean
clean:
	rm -rf /usr/local/lib/python*/dist-packages/tco*
