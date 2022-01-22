BUILDDIR := build
MD_IN := content/*.md
HTML := $(BUILDDIR)/paper.html
PDF := $(BUILDDIR)/paper.pdf
METADATA := metadata.yaml
PLOTS_DIR := results
PLOT_CSV_FILES := $(wildcard $(PLOTS_DIR)/*-plot.csv)
PLOT_PDF_FILES := $(patsubst $(PLOTS_DIR)/%-plot.csv,$(PLOTS_DIR)/%.pdf,$(PLOT_CSV_FILES))

all: html pdf

$(BUILDDIR):
	@mkdir $(BUILDDIR) -p

pdf: $(PDF)
.PHONY: $(PDF)
$(PDF): $(BUILDDIR) $(MD_IN) $(PLOT_PDF_FILES)
	@echo "> Building PDF"
	@pandoc $(MD_IN) \
	--fail-if-warnings \
	--defaults "pandoc/defaults.yaml" \
	--defaults "pandoc/defaults-latex.yaml" \
	--metadata-file $(METADATA) \
	--output=$(PDF)

open: open-pdf
open-pdf:
	@open $(PDF)

html: $(HTML)
.PHONY: $(HTML)
$(HTML): $(BUILDDIR) $(MD_IN) $(PLOT_PDF_FILES)
	@echo "> Building HTML"
	@pandoc $(MD_IN) \
	--fail-if-warnings \
	--defaults "pandoc/defaults.yaml" \
	--metadata-file $(METADATA) \
	--to=html5 \
	--output=$(HTML) \
	--self-contained

open-html:
	@open $(HTML)

$(PLOTS_DIR)/%.pdf: $(PLOTS_DIR)/%-plot.py $(PLOTS_DIR)/%-plot.csv
	@echo "> Plotting $(@F)"
	@cd $(<D); ./$(<F)

.PHONY: clean
clean:
	@rm -rf $(BUILDDIR) output-tex

.PHONY: clean-plots
clean-plots:
	@rm $(PLOTS_DIR)/*.pdf

.PHONY: install-requirements
install-requirements:
	brew install pandoc pandoc-citeproc pandoc-crossref

.PHONY: install-python-requirements
install-python-requirements:
	python -m pip install -r requirements.txt

.PHONY: count-words
count-words:
	@pandoc --lua-filter ./filters/count-words.lua $(MD_IN)
