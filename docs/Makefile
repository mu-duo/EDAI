# Minimal makefile for Sphinx documentation
# Builds both English (en) and Chinese (zh) HTML versions.

SPHINXOPTS    ?= -c source
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

# Default target: build both languages
html: en zh
	@echo ""
	@echo "Both builds finished. HTML pages in $(BUILDDIR)/en and $(BUILDDIR)/zh."

en:
	EDAI_LANG=en $(SPHINXBUILD) -b html "$(SOURCEDIR)/en" "$(BUILDDIR)/en" $(SPHINXOPTS) $(O)
	@echo "English build finished. HTML pages in $(BUILDDIR)/en."

zh:
	EDAI_LANG=zh $(SPHINXBUILD) -b html "$(SOURCEDIR)/zh" "$(BUILDDIR)/zh" $(SPHINXOPTS) $(O)
	@echo "Chinese build finished. HTML pages in $(BUILDDIR)/zh."

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo ""
	@echo "Targets:"
	@echo "  html/`make`  Build both English and Chinese HTML (default)."
	@echo "  en           Build English HTML only."
	@echo "  zh           Build Chinese HTML only."

# Route remaining Sphinx targets to both languages
.PHONY: help Makefile en zh

%: Makefile
	EDAI_LANG=en $(SPHINXBUILD) -M $@ "$(SOURCEDIR)/en" "$(BUILDDIR)/en" $(SPHINXOPTS) $(O)
	EDAI_LANG=zh $(SPHINXBUILD) -M $@ "$(SOURCEDIR)/zh" "$(BUILDDIR)/zh" $(SPHINXOPTS) $(O)
