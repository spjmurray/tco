.PHONY: all
all: install

.PHONY: requirements
requirements:
	pip3 install -r requirements.txt

.PHONY: install
install:
	pip3 install --upgrade .

.PHONY: clean
clean:
	rm -rf /usr/local/lib/python*/dist-packages/tco*
