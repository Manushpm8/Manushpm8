import requests


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


class FakeSession:
    def __init__(self, graphql=(), rest=None):
        self.graphql = list(graphql)
        self.rest = dict(rest or {})
        self.posts = []
        self.gets = []

    def post(self, url, json, timeout):
        self.posts.append(json["variables"])
        item = self.graphql.pop(0)
        if isinstance(item, Exception):
            raise item
        return item if isinstance(item, FakeResponse) else FakeResponse(item)

    def get(self, url, timeout):
        self.gets.append(url)
        item = self.rest[url]
        if isinstance(item, Exception):
            raise item
        return item
