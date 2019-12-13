classes.pdf: classes_No_Name.dot
	dot $< -Tpdf -o $@

classes_No_Name.dot: *.py
	pyreverse -A .
