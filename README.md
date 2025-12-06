# README

## env

* python 3.10.x
  * poetry
* redis

## setup

### all

```bash
cp .env.sample .env
poetry run poetry install
poetry run python manage.py migrate
```

## run

```bash
poetry run python manage.py runserver
```

## create user

```bash
poetry run python manage.py createsuperuser
```

## check api schema

```bash
# after run server
open localhost:8000/schema/ # need session login
```

## rollback

```bash
python manage.py showmigrations
 python manage.py migrate main 00xx  # rollback to 00xx
```

## httpie

```bash
http post http://localhost:8000/api/register/dummy/
http post http://localhost:8000/api/auth/user/ email=test@test.com password=testuser

http post http://localhost:8000/api/auth/refresh/ token=$TOKEN
http post http://localhost:8000/api/auth/verify/ token=$TOKEN

http http://localhost:8000/api/user/ Authorization:"JWT $TOKEN"
```

## wscat

### install

```bash
npm install -g wscat
```

### run

```bash
wscat -c localhost:8000/ws/capsule/test/ -H "Authorization:JWT $TOKEN"
```

### run prd

```bash
http post https://spajam2024.volare.site/api/auth/user/ email=test@test.com password=testuser | jq .
export TOKEN=
http post https://spajam2024.volare.site/api/capsules/ title="1" description="description"  Authorization:"JWT $TOKEN"
export PK=
wscat -c wss://spajam2024.volare.site/ws/capsule/$PK/ -H "Authorization:JWT $TOKEN"
```

### github

https://github.com/login/oauth/authorize?client_id=Ov23liFu18guxrgPDJsZ&redirect_uri=http://localhost:8000/github/callback&scope=repo,user&state=RANDOM_STRING

https://github.com/login/oauth/authorize?client_id=Ov23liMJblwufji01SnW&redirect_uri=https://spajam2025.volare.site/github/callback&scope=repo,user&state=RANDOM_STRING
