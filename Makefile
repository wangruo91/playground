.PHONY: git

git:
	git add --all
	git commit -m "wangruo dev $$(date '+%Y-%m-%d %H:%M:%S')"
	git push
