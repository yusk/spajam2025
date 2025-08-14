# Makefile for Poetry + Django project

PYTHON = poetry run python
MANAGE = $(PYTHON) manage.py

# ==== 基本コマンド ====

# 仮想環境に入る
shell:
	poetry shell

# Django 開発サーバー起動
run:
	$(MANAGE) runserver

# マイグレーション作成
migrate-make:
	$(MANAGE) makemigrations

# マイグレーション実行
migrate:
	$(MANAGE) migrate

makemigrateandmmigrate:
	$(MANAGE) makemigrations
	$(MANAGE) migrate

# スーパーユーザー作成
superuser:
	$(MANAGE) createsuperuser

# テスト実行
test:
	$(MANAGE) test

# Django シェル
shell-plus:
	$(MANAGE) shell_plus

testuser-create:
	$(MANAGE) maketestuser

schema-gen:
	$(MANAGE) generateschema --file schema/schema.yml

# ==== 環境構築 ====

# 初回セットアップ（依存インストール）
install:
	poetry install

# 新しいパッケージ追加（例: make add pkg=django-debug-toolbar）
add:
	poetry add $(pkg)

# パッケージ削除（例: make remove pkg=django-debug-toolbar）
remove:
	poetry remove $(pkg)

# ==== 静的ファイル ====

collectstatic:
	$(MANAGE) collectstatic --noinput
