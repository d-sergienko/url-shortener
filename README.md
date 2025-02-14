# URL Shortener with FastAPI

[![CI](https://github.com/d-sergienko/url-shortener/actions/workflows/ci.yaml/badge.svg?branch=master)](https://github.com/d-sergienko/url-shortener/actions/workflows/ci.yaml)

[https://github.com/tiangolo/fastapi](https://github.com/tiangolo/fastapi)

```sh
$ docker version
Client: Docker Engine - Community
 Version:           27.5.1
 API version:       1.47
 Go version:        go1.22.11
 Git commit:        9f9e405
 Built:             Wed Jan 22 13:41:31 2025
 OS/Arch:           linux/amd64
 Context:           default

Server: Docker Engine - Community
 Engine:
  Version:          27.5.1
  API version:      1.47 (minimum version 1.24)
  Go version:       go1.22.11
  Git commit:       4c9b3b0
  Built:            Wed Jan 22 13:41:31 2025
  OS/Arch:          linux/amd64
  Experimental:     false
 containerd:
  Version:          1.7.25
  GitCommit:        bcc810d6b9066471b0b6fa75f557a15a1cbf31bb
 runc:
  Version:          1.2.4
  GitCommit:        v1.2.4-0-g6c52b3f
 docker-init:
  Version:          0.19.0
  GitCommit:        de40ad0

$ docker compose version
Docker Compose version v2.32.4
```

```sh
$ git clone https://github.com/d-sergienko/url-shortener.git
$ cd url-shortener
$ docker compose up -d --build
$ docker compose exec api alembic upgrade head # Run for the first time to initialize database schemas
$ docker compose logs -f
$ docker compose exec db psql --username=dev --dbname=dev # Check database schemas
$ docker compose exec api pytest # Run test
```

Using [curl](https://curl.haxx.se) and [jq](https://stedolan.github.io/jq/):
```sh
$ curl -X POST -d '{"url": "https://google.com"}' -H "Content-Type: application/json" http://localhost:8000/api/shorten | jq .
{
  "short_link": "Nw4IY0Y"
}
```

Using [httpie](https://httpie.org):
```sh
$ http POST localhost:8000/api/shorten url=https://freecodecamp.org

HTTP/1.1 200 OK
content-length: 24
content-type: application/json
date: Wed, 15 Jul 2020 13:56:37 GMT
server: uvicorn

{
    "short_link": "pk9nq5_"
}
```

Point your browser to http://localhost:8000/Nw4IY0Y or http://localhost:8000/pk9nq5_ (the links will be varied because they depend on timestamp).

API docs available at http://localhost:8000/docs
