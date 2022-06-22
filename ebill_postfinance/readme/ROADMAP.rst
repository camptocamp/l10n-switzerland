ToDo
----

* Add option to import the contract subscription (csv)
* Add the download of this csv from web service, but what is the endpoint ?
* Implement the yellow bill xml format


Nice to have
------------

* Add a link to the failed job in the chatter message.
* Add an action on partner to create a ebilling contract.



Question for Postfinance
------------------------

If I send the same invoice multiple time should I use the same Transaction Id ?

    Only if it is in invalid state, I think

Difference between SearchInvoices and GetInvoiceListBiller ?

Any reason I should use GetInvoiceBiller (I already have it, I uploaded it) ?

    Or it has additional information ?
    Legally needed ?

Check my question about message format ?
What are the advantages of the yellowbill format ?

How can I simulate a registration on the test platform ?

I see I can download a list of subscription change csv/xml but what is the api call for it ?



Handling exceptions with the api
--------------------------------

Implemented ErrorTest and ErrorException from the ping, to see the returned error, but both return the same exception

```
 File "src/lxml/etree.pyx", line 1831, in lxml.etree.QName.__init__
  File "src/lxml/apihelpers.pxi", line 1734, in lxml.etree._tagValidOrRaise
Exception
The above exception was the direct cause of the following exception:
Traceback (most recent call last):
  File "/odoo/src/odoo/http.py", line 640, in _handle_exception
    return super(JsonRequest, self)._handle_exception(exception)
  File "/odoo/src/odoo/http.py", line 316, in _handle_exception
    raise exception.with_traceback(None) from new_cause
ValueError: Invalid tag name '000'

```
