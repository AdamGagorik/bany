CLEAN_CACHE=find .                                 \
          -not \( -path ./.git           -prune \) \
          -not \( -path ./.idea          -prune \) \
          -not \( -path ./repos          -prune \) \
          -type d -name __pycache__

CLEAN_FILES=find .                                 \
          -not \( -path ./.git           -prune \) \
          -not \( -path ./.idea          -prune \) \
          -not \( -path ./repos          -prune \) \
          \(                                       \
                -type f -name \*.pyc               \
            -or -type f -name .coverage            \
            -or -type d -name __pycache__          \
            -or -type f -name cache.db             \
            -or -type f -name cache.db-shm         \
            -or -type f -name cache.db-wal         \
            -or -type d -name .pytest_cache        \
            -or -type d -name .ipynb_checkpoints   \
          \)                                       \
          -print

.PHONY : help
help:
ifneq (,$(shell which mdcat))
	@mdcat README.md
else
	@cat README.md
endif

.PHONY : clean
clean:
	-@$(CLEAN_CACHE) | xargs -I xxx rm -rvf xxx
	-@$(CLEAN_FILES) | xargs -I xxx rm -rvf xxx

.PHONY : pre-commit
pre-commit:
ifeq (, $(shell which pre-commit))
	brew install pre-commit
	pre-commit run -a
else
	pre-commit run -a
endif

.PHONY : release
release:
	gh release create
	git pull
	poetry dist
	poetry build
	poetry publish
	pipx upgrade bany
