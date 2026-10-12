#!/usr/bin/env python3
import pydig
from flask import Flask, redirect, render_template, request, url_for
from time import sleep

app = Flask(__name__, static_folder="assets")

APP_TITLE = "dig"
DEFAULT_ADDRESS = "example.com"
DEFAULT_RECORD_TYPE = "A"


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "GET":
        return redirect("/" + DEFAULT_ADDRESS + "/" + DEFAULT_RECORD_TYPE)
    else:
        sleep(0.25)

        url_args = {
            "address": str(request.form["address"]) or DEFAULT_ADDRESS,
            "record_type": str(request.form["record_type"]) or DEFAULT_RECORD_TYPE,
        }

        if str(request.form["server"]) != "":
            url_args["server_to_query"] = str(request.form["server"])

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
    # one starting with "-" or "+" as an option (e.g. "-f<file>")
    if address.startswith(("-", "+")):
        return "Error: Invalid address"

    try:
        if server_to_query != "":
            resolver = pydig.Resolver(nameservers=[server_to_query])
            dig_result = resolver.query(address, record_type)
        else:
            dig_result = pydig.query(address, record_type)

    except Exception:

        dig_result = "Error: Unable to get dig results"

    return dig_result


if __name__ == "__main__":
    app.run()
