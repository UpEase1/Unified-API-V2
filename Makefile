# Define the name of the virtual environment directory
VENV_DIR := .venv

# Define the command to activate the virtual environment
ifeq ($(OS),Windows_NT)
    VENV_ACTIVATE = $(VENV_DIR)\Scripts\activate
else
    VENV_ACTIVATE = . $(VENV_DIR)/bin/activate
endif

# Define the command to install requirements
INSTALL_REQS := pip install -r requirements.txt

# Define the command to run the server
RUN_SERVER := uvicorn ams_api:app --reload

.PHONY: venv install run

venv:
	# Create the virtual environment directory if it doesn't exist
	test -d $(VENV_DIR) || python3 -m venv $(VENV_DIR)

activate: venv
	# Activate the virtual environment
	$(VENV_ACTIVATE)

install: venv
	# Activate the virtual environment and install requirements
	$(VENV_ACTIVATE) && $(INSTALL_REQS)

run: install
	# Activate the virtual environment and run the server
	$(VENV_ACTIVATE) && $(RUN_SERVER)
