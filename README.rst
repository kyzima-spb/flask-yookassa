Flask-Yookassa
==============

|PyPI| |LICENCE| |STARS|

|DOWNLOADS| |DOWNLOADS_M| |DOWNLOADS_W|

**Flask-Yookassa** - Integration of Flask and YuKassa.

Installation
------------

Install the latest stable version by running the command::

    pip install Flask-Yookassa

Configuration
-------------

The following configuration options are available to specify:

=========================================    ================================================================
Option                                       Description
=========================================    ================================================================
``YOOKASSA_SHOP_ID``                         **Required**. Store ID issued by ЮKassa.
``YOOKASSA_SHOP_SECRET_KEY``                 **Required**. The secret key of the store, issued by ЮKassa.
``YOOKASSA_NOTIFICATIONS_IP``                A set of IP addresses or masks
                                             from which hook calls are allowed. By default: `set()`.
=========================================    ================================================================

Custom error handler
--------------------

You can register your ЮKassa API error handler.
For example, display a standard Flask page for HTTP errors:

.. code-block:: python

    from flask import Flask, abort
    from flask_yookassa import Yookassa


    app = Flask(__name__)
    app.config.from_prefixed_env()
    yookassa = Yookassa(app)


    @yookassa.errorhandler
    def handle_api_error(resp, code):
        """Registers a custom error handler for the ЮKassa API."""
        abort(code, resp['description'])

Only HTTPException will be caught and handled automatically,
other exception types need to be handled manually.

Notifications handler
---------------------

Any entry point can be decorated with a special ``flask_yookassa.Yookassa.hookhandler`` decorator.

The decorator checks the request for spam. The request must come from allowed IP addresses,
the resource is checked for existence and for the relevance of the status:

.. code-block:: python

    from flask import Flask
    from flask_yookassa import Yookassa


    app = Flask(__name__)
    app.config.from_prefixed_env()
    yookassa = Yookassa(app)


    @app.route('/callback')
    @yookassa.hookhandler
    def handle_hook(notification):
        """The entry point handles the ЮKassa notifications."""
        # Any code to handle the event.
        return ''


.. |PyPI| image:: https://img.shields.io/pypi/v/flask-yookassa.svg
   :target: https://pypi.org/project/flask-yookassa/
   :alt: Latest Version

.. |LICENCE| image:: https://img.shields.io/github/license/kyzima-spb/flask-yookassa.svg
   :target: https://github.com/kyzima-spb/flask-yookassa/blob/master/LICENSE
   :alt: MIT

.. |STARS| image:: https://img.shields.io/github/stars/kyzima-spb/flask-yookassa.svg
   :target: https://github.com/kyzima-spb/flask-yookassa/stargazers
   :alt: GitHub stars

.. |DOWNLOADS| image:: https://pepy.tech/badge/flask-yookassa
   :target: https://pepy.tech/project/flask-yookassa

.. |DOWNLOADS_M| image:: https://pepy.tech/badge/flask-yookassa/month
   :target: https://pepy.tech/project/flask-yookassa)

.. |DOWNLOADS_W| image:: https://pepy.tech/badge/flask-yookassa/week
   :target: https://pepy.tech/project/flask-yookassa)
