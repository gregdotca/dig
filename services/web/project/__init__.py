#!/usr/bin/env python3
import ipaddress
import subprocess

import pydig
from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__, static_folder="assets")

APP_TITLE = "dig"
DEFAULT_ADDRESS = "example.com"
DEFAULT_RECORD_TYPE = "A"

# Wait 2 seconds for each server's answer and don't retry, so a server that
# doesn't respond can't tie up a gunicorn worker for long. Without a server
# to query, dig tries each resolver in resolv.conf, 2 seconds apiece
DIG_TIMEOUT_ARGS = ["+time=2", "+tries=1"]

# dig exits with this status when no server answered
DIG_EXIT_NO_REPLY = 9


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    # The page has nothing to show in a frame, so refuse to be framed
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "GET":
        return redirect("/" + DEFAULT_ADDRESS + "/" + DEFAULT_RECORD_TYPE)
    else:
        url_args = {
            "address": request.form.get("address", "") or DEFAULT_ADDRESS,
            "record_type": request.form.get("record_type", "") or DEFAULT_RECORD_TYPE,
        }

        server = request.form.get("server", "")
        if server != "":
            url_args["server_to_query"] = server

        # url_for() encodes each value, so the redirect always stays on this site
        return redirect(url_for("lookup_get", **url_args))


@app.route("/<address>", defaults={'record_type': '', 'server_to_query': ''}, methods=["GET"])
@app.route("/<address>/<record_type>", defaults={'server_to_query': ''}, methods=["GET"])
@app.route("/<address>/<record_type>/<server_to_query>", methods=["GET"])
def lookup_get(address, record_type, server_to_query):
    return display_homepage(address, record_type, server_to_query, run_dig(address, record_type, server_to_query))


def display_homepage(address, record_type, server_to_query, page_body):
    return render_template(
        "home.html",
        app_title=APP_TITLE,
        address=address,
        record_type=record_type,
        server=server_to_query,
        page_body=page_body,
    )


def run_dig(address, record_type, server_to_query):
    address = address or DEFAULT_ADDRESS
    record_type = record_type or DEFAULT_RECORD_TYPE

    # pydig passes the address to dig as its own argument, so dig would read
    # one starting with "-" or "+" as an option (e.g. "-f<file>"). A server
    # name is looked up with dig too, so the same goes for it
    if address.startswith(("-", "+")):
        return "Error: An address can't start with - or +"
    if server_to_query.startswith(("-", "+")):
        return "Error: A server can't start with - or +"

    try:
        query_type = pydig.QueryType.get(record_type)
    except pydig.InvalidQueryType:
        supported = ", ".join(t.name for t in pydig.QueryType)
        return 'Error: Unknown record type "' + record_type + '". Supported types: ' + supported

    nameservers = None
    if server_to_query != "":
        try:
            nameservers = [resolve_public_server(server_to_query)]
        except ValueError as error:
            return "Error: " + str(error)

    try:
        resolver = pydig.Resolver(nameservers=nameservers, additional_args=DIG_TIMEOUT_ARGS)
        dig_result = resolver.query(address, query_type)

    except subprocess.CalledProcessError as error:

        if error.returncode == DIG_EXIT_NO_REPLY:
            return "Error: No reply from the DNS server"
        return "Error: Unable to get dig results"

    except Exception:

        return "Error: Unable to get dig results"

    if not dig_result:
        return "No " + query_type.name + " records found for " + address

    return dig_result


def resolve_public_server(server):
    """
    Returns the IP address to query for a server name or IP, or raises
    ValueError if it can't be found or isn't a public address

    Only public addresses are allowed, so the lookup can't be used to probe
    the network the container runs on. The resolved IP is what gets passed to
    dig, so the name can't resolve to a different address when dig looks it up.
    Names are resolved with dig and DIG_TIMEOUT_ARGS, so each A or AAAA
    query for a name whose DNS doesn't answer gives up like a lookup does
    """
    try:
        addresses = [ipaddress.ip_address(server)]
    except ValueError:
        addresses = []
        resolver = pydig.Resolver(additional_args=DIG_TIMEOUT_ARGS)
        try:
            for record_type in ("A", "AAAA"):
                # +short also prints the names in a CNAME chain, so keep
                # only the lines that are IPs
                for line in resolver.query(server, record_type):
                    try:
                        addresses.append(ipaddress.ip_address(line))
                    except ValueError:
                        pass
                if addresses:
                    break
        except Exception:
            pass

    if not addresses:
        raise ValueError('Unable to find the server "' + server + '"')

    if not all(address.is_global for address in addresses):
        raise ValueError("The server to query must be a public address")

    return str(addresses[0])


if __name__ == "__main__":
    app.run()
