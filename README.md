billtag
=======

Itemizes complex online (beer) orders.

Usage
-----

Create (or copy-paste in) the order confirmation as TSV (tab-separated values). Name the columns:

* `name` - the name of the line item
* `qty` - total quantity of items on this line
* `total` - total for this line -- mutually exclusive with `unit`
* `unit` - unit price for this line -- mutually exclusive with `total`
* `discount` - a discount % for this line (0..1)
* `tags` - a string of tags for this line (one character = one tag).

(See `examples/` for examples.)

Then run `python billtag.py that_file.tsv`, and voila!

Also see `--help` for additional options.