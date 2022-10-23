BUILDDIR := build
MD_IN := content/*.md
HTML := $(BUILDDIR)/paper.html
PDF := $(BUILDDIR)/paper.pdf
METADATA := pandoc/metadata.yaml

PLOTS_DIR             := results
PLOT_CSV_FILES        := $(wildcard $(PLOTS_DIR)/*.csv $(PLOTS_DIR)/*/*.csv)
PLOT_PY_FILES         := $(wildcard $(PLOTS_DIR)/*-plot.py)
PLOT_COMMON_PY_FILES  := $(filter-out $(PLOT_PY_FILES),$(wildcard $(PLOTS_DIR)/*.py))
PLOT_PDF_FILES        := $(patsubst $(PLOTS_DIR)/%-plot.py,$(PLOTS_DIR)/%.pdf,$(PLOT_PY_FILES))

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

plots: $(PLOT_PDF_FILES)

$(PLOTS_DIR)/%.pdf: $(PLOTS_DIR)/%-plot.py $(PLOT_COMMON_PY_FILES) $(PLOT_CSV_FILES)
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
	brew install pandoc pandoc-crossref

.PHONY: install-python-requirements
install-python-requirements:
	@true

.PHONY: count-words
count-words:
	@pandoc --lua-filter ./pandoc/filters/count-words.lua $(MD_IN)
