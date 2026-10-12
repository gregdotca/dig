import subprocess

import pydig
import pytest

from project import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def dig_calls(monkeypatch):
    """
    Replaces the call to the dig binary, so no test touches the network.
    Set .output to the lines dig should print, .answers to the lines for a
    particular (name, record type) such as a server name's A record, or
    .error to an exception to raise. Each call's argument list is appended
    to .args
    """
    class FakeDig:
        output = ["93.184.215.14"]
        answers = {}
        error = None
        args = []

        @classmethod
        def lookups_of(cls, name):
            return [args for args in cls.args if name in args]

    def execute(args):
        FakeDig.args.append(args)
        if FakeDig.error:
            raise FakeDig.error
        name, record_type = [arg for arg in args[1:] if not arg.startswith(("@", "+"))][:2]
        lines = FakeDig.answers.get((name, record_type), FakeDig.output)
        return "\n".join(lines).encode()

    monkeypatch.setattr(pydig.Resolver, "_execute", staticmethod(execute))
    return FakeDig


def test_home_redirects_to_default_lookup(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"] == "/example.com/A"


def test_form_redirects_to_lookup_url(client):
    response = client.post("/", data={"address": "greg.ca", "record_type": "MX", "server": "8.8.8.8"})
    assert response.headers["Location"] == "/greg.ca/MX/8.8.8.8"


def test_form_without_fields_uses_defaults(client):
    response = client.post("/")
    assert response.headers["Location"] == "/example.com/A"


def test_form_redirect_stays_on_site(client):
    response = client.post("/", data={"address": "//evil.com", "record_type": "", "server": ""})
    location = response.headers["Location"]
    assert location.startswith("/")
    assert not location.startswith("//")


def test_lookup_shows_records(client, dig_calls):
    response = client.get("/example.com/A")
    assert response.status_code == 200
    assert b"93.184.215.14" in response.data
    assert dig_calls.args[-1] == ["dig", "example.com", "A", "+short", "+time=2", "+tries=1"]


def test_lookup_with_server_queries_its_ip(client, dig_calls):
    dig_calls.answers[("one.one.one.one", "A")] = ["1.1.1.1"]
    client.get("/example.com/A/one.one.one.one")
    lookup = dig_calls.lookups_of("example.com")[-1]
    assert lookup[1] == "@1.1.1.1"


def test_server_name_is_resolved_with_timeouts(client, dig_calls):
    dig_calls.answers[("one.one.one.one", "A")] = ["1.1.1.1"]
    client.get("/example.com/A/one.one.one.one")
    assert dig_calls.lookups_of("one.one.one.one")[0] == ["dig", "one.one.one.one", "A", "+short", "+time=2", "+tries=1"]


def test_server_name_skips_cname_lines(client, dig_calls):
    dig_calls.answers[("dns.example", "A")] = ["resolver.example.net.", "1.1.1.1"]
    client.get("/example.com/A/dns.example")
    assert dig_calls.lookups_of("example.com")[-1][1] == "@1.1.1.1"


def test_server_name_falls_back_to_aaaa(client, dig_calls):
    dig_calls.answers[("dns6.example", "A")] = []
    dig_calls.answers[("dns6.example", "AAAA")] = ["2606:4700:4700::1111"]
    client.get("/example.com/A/dns6.example")
    assert dig_calls.lookups_of("example.com")[-1][1] == "@2606:4700:4700::1111"


def test_lookup_accepts_public_ipv6_server(client, dig_calls):
    client.get("/example.com/A/2606:4700:4700::1111")
    assert dig_calls.args[-1][1] == "@2606:4700:4700::1111"


@pytest.mark.parametrize("server", ["10.0.0.1", "127.0.0.1", "192.168.1.1", "169.254.169.254", "::1", "fd00::1", "internal.example"])
def test_lookup_rejects_non_public_servers(client, dig_calls, server):
    dig_calls.answers[("internal.example", "A")] = ["1.1.1.1", "10.0.0.53"]
    response = client.get("/example.com/A/" + server)
    assert b"Error: The server to query must be a public address" in response.data
    assert dig_calls.lookups_of("example.com") == []


@pytest.mark.parametrize("answer", [[], None])
def test_lookup_reports_unknown_server(client, dig_calls, answer):
    if answer is None:
        dig_calls.error = subprocess.CalledProcessError(9, "dig")
    else:
        dig_calls.answers[("nowhere.invalid", "A")] = answer
        dig_calls.answers[("nowhere.invalid", "AAAA")] = answer
    response = client.get("/example.com/A/nowhere.invalid")
    assert b"Error: Unable to find the server &#34;nowhere.invalid&#34;" in response.data
    assert dig_calls.lookups_of("example.com") == []


@pytest.mark.parametrize("server", ["-fmanage.py", "+short"])
def test_lookup_rejects_servers_dig_would_read_as_options(client, dig_calls, server):
    response = client.get("/example.com/A/" + server)
    assert b"Error: A server can&#39;t start with - or +" in response.data
    assert dig_calls.args == []


@pytest.mark.parametrize("address", ["-fmanage.py", "+short"])
def test_lookup_rejects_addresses_dig_would_read_as_options(client, dig_calls, address):
    response = client.get("/" + address + "/A")
    assert b"Error: An address can&#39;t start with - or +" in response.data
    assert dig_calls.args == []


def test_lookup_reports_unknown_record_type(client, dig_calls):
    response = client.get("/example.com/XYZ")
    assert b"Error: Unknown record type &#34;XYZ&#34;. Supported types: A, NS," in response.data
    assert dig_calls.args == []


def test_lookup_accepts_lowercase_record_type(client, dig_calls):
    client.get("/example.com/mx")
    assert dig_calls.args[-1][2] == "MX"


def test_lookup_reports_no_reply(client, dig_calls):
    dig_calls.error = subprocess.CalledProcessError(9, "dig")
    response = client.get("/example.com/A/1.1.1.1")
    assert b"Error: No reply from the DNS server" in response.data


def test_lookup_reports_other_dig_failures(client, dig_calls):
    dig_calls.error = subprocess.CalledProcessError(10, "dig")
    response = client.get("/example.com/A")
    assert b"Error: Unable to get dig results" in response.data


def test_lookup_reports_no_records(client, dig_calls):
    dig_calls.output = []
    response = client.get("/example.com/AAAA")
    assert b"No AAAA records found for example.com" in response.data


def test_lookup_escapes_html_in_records(client, dig_calls):
    dig_calls.output = ['"<script>alert(1)</script>"']
    response = client.get("/example.com/TXT")
    assert b"<script>alert(1)</script>" not in response.data
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.data


def test_responses_have_security_headers(client, dig_calls):
    for path in ["/example.com/A", "/assets/favicon.png"]:
        response = client.get(path)
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Referrer-Policy"] == "same-origin"
        assert response.headers["Content-Security-Policy"] == "frame-ancestors 'none'"
        assert response.headers["X-Frame-Options"] == "DENY"
