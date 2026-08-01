simplifiapi
===========

An unofficial Python API and CLI for `Quicken Simplifi`_.

.. _Quicken Simplifi: https://www.simplifimoney.com/

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api

Installation
------------

.. code-block:: bash

   pip install git+https://github.com/senderic/simplifiapi

Quick Start
-----------

CLI:

.. code-block:: bash

   simplifiapi --email you@example.com --password yourpass --transactions --format csv

Python API:

.. code-block:: python

   from simplifiapi.client import Client

   client = Client()
   token = client.get_token("you@example.com", "yourpass")
   if client.verify_token(token):
       datasets = client.get_datasets()
       transactions = client.get_transactions(datasets[0]["id"])

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
