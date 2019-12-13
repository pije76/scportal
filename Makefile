# Software releases
# =================

# Branch and commit ID
DISTVERSION := $(shell git rev-parse --abbrev-ref HEAD)-$(shell git rev-parse HEAD)

# Most recent tag --- or abbreviated commit as fallback
RELEASEVERSION := $(shell git describe --always)

# Use `make dist` to package the current develop/branch
.PHONY: dist
dist: gridplatform-$(DISTVERSION).tar.gz

# Use `make release` on master branch after tagging for official releases
.PHONY: release
release: gridplatform-$(RELEASEVERSION).tar.gz

# Package a "clean" git clone without the .git directory
gridplatform-%.tar.gz:
	TMPDIR=`mktemp -d`; \
	git clone . $$TMPDIR/gridplatform; \
	rm $$TMPDIR/gridplatform/.git -fr; \
	sed "s/^__version__\s*=[^=]*$\/__version__ = '$*'/" -i \
	  $$TMPDIR/gridplatform/gridplatform/__init__.py; \
	tar czf $@ --directory $$TMPDIR gridplatform; \
	rm -fr $$TMPDIR


# Common
# ======

# Django (< 1.7) recognizes apps on the presence of a "models" module
APPS := $(patsubst %/models.py,%,$(wildcard gridplatform/*/models.py)) $(patsubst %/models/__init__.py,%,$(wildcard gridplatform/*/models/__init__.py)) \
    $(patsubst %/models.py,%,$(wildcard energymanager/*/models.py)) $(patsubst %/models/__init__.py,%,$(wildcard energymanager/*/models/__init__.py)) \
    $(patsubst %/models.py,%,$(wildcard legacy/*/models.py)) $(patsubst %/models/__init__.py,%,$(wildcard legacy/*/models/__init__.py))

.DEFAULT_GOAL := test


# I18n and l10n
# =============
#
#     Use-case: in-house Danish Translation
#     -------------------------------------
#
#         1) Just run the `./translate.sh` script.
#
#     Use-case: External Translation for locale $LC
#     ----------------------------------------------
#
#         0) Run `make makemessages LOCALES="$LC"`
#         1) Run `make $LC_translation.zip`
#         2) Send `$LC_translation.zip` to translators.
#         3) Receive translated `$LC_translation.zip` from translators.
#         4) Extract the translated `$LC_translation.zip` into same directory
#            as this `Makefile`
#         5) Run `make compilemessages LOCALES=$LC`
#
# Note: to speed up things, run make with `-j6` or similar.
#
# See also `info gettext Introduction Overview`

# Locales to be processed.  May be overriden from command line to process more
# or fewer locales than default.
LOCALES := da es

# PO_FILES are considdered up to date if the po files exist.
PO_FILES = $(foreach lc, $(LOCALES), $(foreach app, $(APPS), ./$(app)/locale/$(lc)/LC_MESSAGES/django.po ./$(app)/locale/$(lc)/LC_MESSAGES/djangojs.po))

POT_FILES = $(PO_FILES:.po=.pot)
.PHONY: $(POT_FILES)

# extract messages from gettext invocations and merge them into po files.
.PHONY: makemessages
makemessages: $(POT_FILES)

$(filter %django.pot, $(POT_FILES)):
	@echo makemessages $$(dirname $$(dirname $@))/django.po
	-@APP=$$(dirname $$(dirname $$(dirname $$(dirname $@))));\
	LC=$$(basename $$(dirname $$(dirname $@)));\
	mkdir -p $$APP/locale;\
	cd $$APP;\
	django-admin.py makemessages -l $$LC -e html -e tex  2> /dev/null > /dev/null

$(filter %/djangojs.pot, $(POT_FILES)):
	@echo makemessages $$(dirname $$(dirname $@))/djangojs.po
	-@APP=$$(dirname $$(dirname $$(dirname $$(dirname $@))));\
	LC=$$(basename $$(dirname $$(dirname $@)));\
	mkdir -p $$APP/locale;\
	cd $$APP;\
	django-admin.py makemessages -d djangojs -l $$LC 2> /dev/null > /dev/null

$(PO_FILES:.po=.mo) : %.mo : %.po
	@APP=$$(dirname $$(dirname $$(dirname $$(dirname $*))));\
	echo compilemessages $$APP;\
	cd $$APP;\
	django-admin.py compilemessages

.PHONY: compilemessages
compilemessages: $(patsubst %.po,%.mo,$(filter $(shell find . -name "*.po"), $(PO_FILES)))

# Create zip file of PO-files for a given locale, preserving directory
# structure.  Usage::
#
#     make es_translation.zip
$(addsuffix _translation.zip, $(LOCALES)) : %_translation.zip :
	@echo zip $@
	@find . -path "*/locale/$*/*" -name "*.po" | xargs zip $@


# Flake8
# ======
MODIFIED_FILES = $(shell git status --porcelain | awk '/^ ?[AMU].*\.py$$/ {print $$2}' | grep -v '/migrations/')

.PHONY: flake8
flake8:
ifneq ($(MODIFIED_FILES), )
	flake8 $(MODIFIED_FILES) $(FLAKE8FLAGS)
else
	@echo "No modifications, skipping flake8"
endif


# Unit tests
# ==========
TESTS := $(subst /,.,$(APPS))
RERUN_TESTS := $(if $(wildcard test_rerun.txt),$(shell grep -v '^unittest.loader.ModuleImportFailure' test_rerun.txt),$(TESTS))
TESTFLAGS := --noinput --traceback

DJANGO_SETTINGS_MODULE := gridplatform.settings.test

# Run tests for all our apps
.PHONY: test
test: flake8
	DJANGO_SETTINGS_MODULE=$(DJANGO_SETTINGS_MODULE) \
	./manage.py test $(TESTS) $(TESTFLAGS)

# Run tests marked for rerun by the test runner
.PHONY: test-rerun
test-rerun: flake8
	DJANGO_SETTINGS_MODULE=$(DJANGO_SETTINGS_MODULE) \
	./manage.py test $(RERUN_TESTS) $(TESTFLAGS)

COVERAGE_INCLUDE_PATTERN = *gridplatform/*,*energymanager/*,*legacy/*

.PHONY: test-coverage
test-coverage: flake8
	DJANGO_SETTINGS_MODULE=$(DJANGO_SETTINGS_MODULE) \
	coverage run --branch \
	./manage.py test $(TESTS) $(TESTFLAGS) && \
	coverage report --include="$(COVERAGE_INCLUDE_PATTERN)" --omit="*/migrations/*" --show-missing

# Prerequisites of running selenium-test target:
#
# - pip install selenium
# - apt-get install xvfb
# - download and extract the relevant chromedriver to the current directory:
#     wget http://chromedriver.storage.googleapis.com/2.9/chromedriver_linux64.zip
#     unzip chromedriver_linux64.zip
.PHONY: selenium-test
selenium-test: export PATH+=:$(abspath .)
selenium-test: export SELENIUM_SERVER=TRUE
selenium-test: test


# Playground...
# =============
.PHONY: tags
tags: TAGS

.PHONY: TAGS
TAGS:
	find . -name "[a-z_]*.py" | xargs etags

.PHONY: test-failures
test-failures: flake8 failure-list.txt
	test -s failure-list.txt
	DJANGO_SETTINGS_MODULE=$(DJANGO_SETTINGS_MODULE) \
	./manage.py test $(shell cat failure-list.txt) $(TESTFLAGS)


TESTRUNNERS = $(addsuffix .run, $(TESTS))

.PHONY: $(TESTRUNNERS)
$(TESTRUNNERS): %.run : flake8
	DJANGO_SETTINGS_MODULE=$(DJANGO_SETTINGS_MODULE) \
	TEST_DATABASE_NAME=test_$* \
	TEST_LOG_FILE=$*.log \
	TEST_RERUN_FILE=$*.rerun \
	./manage.py test $* $(TESTFLAGS) --verbosity=0

.PHONY: parallel-test
parallel-test: $(TESTRUNNERS)

# Intentionally fail rebuilding this target if there were any import errors.
failure-list.txt: $(wildcard *.rerun) $(wildcard test_rerun.txt)
	test -n "$?"
	cat $? | grep -q '^unittest.loader.ModuleImportFailure'; test $$? -ne 0
	cat $? | sort | uniq > $@

SCSS_FILES = $(shell find legacy/website/static/ -type f -name "*.scss")

legacy/website/static/style.css : $(SCSS_FILES)
	scss legacy/website/static/style.scss:legacy/website/static/style.css

.PHONY: scss
scss: legacy/website/static/style.css


.PHONY: clean
clean:
	find . -name "*.pyc" -delete
	rm -f *.rerun
	rm -f *.log
	rm -f GridPlatform.pdf GridPlatformDomainModel.pdf

.PHONY: html
html:
	PYTHONPATH=$(abspath .) sphinx-build -b html documentation/source documentation/build

.PHONY: pdf
pdf: GridPlatform.pdf GridPlatformDomainModel.pdf

RST_FILES = $(shell find documentation/source . -name "*.rst")
PY_FILES = $(shell find documentation/source . -name "*.py")

GridPlatform.pdf GridPlatformDomainModel.pdf: $(RST_FILES) $(PY_FILES)
	PYTHONPATH=$(abspath .) sphinx-build -b latex documentation/source documentation/build
	make -C documentation/build
	cp documentation/build/GridPlatform.pdf ./
	cp documentation/build/GridPlatformDomainModel.pdf ./
