# Typing "make" into the terminal will run the program or Mac and Linux
run:
	python3 main.py

# Typing "make clean" into the terminal removes Python cache files (__pycache__) for Mac and Linux
clean:
	rm -rf __pycache__
	rm -rf */__pycache__

# For Windows, typing "py main.py" into the terminal will run the program. 