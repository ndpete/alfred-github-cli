TARGET_DIR := dist
WORKFLOW_FILE := $(TARGET_DIR)/alfred-github-cli.alfredworkflow

.PHONY: all clean workflow test lint

all: workflow

clean:
	@rm -rf $(TARGET_DIR)

$(TARGET_DIR):
	@mkdir -p $(TARGET_DIR)

workflow: | $(TARGET_DIR)
	@rm -f $(WORKFLOW_FILE)
	zip -r $(WORKFLOW_FILE) \
		info.plist \
		icon.png \
		icons/ \
		src/ \
		README.md \
		LICENSE \
		-x "*__pycache__*" "*.DS_Store*"

test:
	uv run --extra dev pytest

lint:
	uv run --extra dev ruff check .
