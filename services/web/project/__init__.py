#!/usr/bin/env python3
import pydig
from flask import Flask, redirect, render_template, request
from time import sleep

app = Flask(__name__, static_folder="assets")

APP_TITLE = "dig"
DEFAULT_ADDRESS = "example.com"
DEFAULT_RECORD_TYPE = "A"


@app.route("/", methods=["GET"])
def home():
    return redirect("/" + DEFAULT_ADDRESS + "/" + DEFAULT_RECORD_TYPE, code=302)


@app.route("/<address>", defaults={'record_type': '', 'server_to_query': ''}, methods=["GET"])
@app.route("/<address>/<record_type>", defaults={'server_to_query': ''}, methods=["GET"])
@app.route("/<address>/<record_type>/<server_to_query>", methods=["GET"])
def lookup_get(address, record_type, server_to_query):
    return display_homepage(address, record_type, server_to_query, run_dig(address, record_type, server_to_query))


@app.route("/", methods=["POST"])
def lookup_post():
    sleep(0.25)

    if str(request.form["address"]) == "":
        full_url = DEFAULT_ADDRESS
    else:
        full_url = str(request.form["address"])

    if str(request.form["record_type"]) == "":
        full_url += "/" + DEFAULT_RECORD_TYPE
    else:
        full_url += "/" + str(request.form["record_type"])

    if str(request.form["server"]) != "":
        full_url += "/" + str(request.form["server"])

    return redirect(full_url, code=302)


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
