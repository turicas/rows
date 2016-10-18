# Makefile for Sphinx documentation
# You can set these variables from the command line.
SPHINXBUILD   = sphinx-build
BUILDDIR      = _build

# Internal variables.
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees .

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  html       to make standalone HTML files"
	@echo "  clean      remove current BUILDDIR"
	@echo "  publish    publish to the gh-pages branch"

clean:
	rm -rf $(BUILDDIR)/*

html:
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."


publish:
	cd $(BUILDDIR)/html; git add . ; git commit -m "rebuilt docs"; git push origin gh-pages

.PHONY: help clean html publish
