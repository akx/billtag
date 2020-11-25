import argparse
import re
from collections import Counter, defaultdict
from decimal import Decimal
from fractions import Fraction
from itertools import chain
from operator import itemgetter


def read_tsv(fp):
    headers = []
    for i, line in enumerate(fp):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = line.split("\t")
        if not headers:
            headers = line
            continue
        yield dict(zip(headers, line))


def parse_decimal(value: str) -> Decimal:
    return Decimal(re.sub(r"[^0-9.,-]+", "", value).replace(",", "."))


def fraction_as_decimal(value: Fraction) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)


def process(
    data,
    *,
    rounding=2,
    currency_multiplier=1,
    delivery=0,
    default_discount=0,
    use_price_shares_for_delivery=False,
):
    by_tag = defaultdict(list)
    total_price = 0
    tag_unit_shares = Counter()
    tag_price_shares = Counter()
    for line in data:
        try:
            qty = int(line["qty"])
        except:
            raise NotImplementedError("invalid qty in line %r" % line)
        if "total" in line:
            line_price = parse_decimal(line["total"])
        elif "unit" in line:
            line_price = parse_decimal(line["unit"]) * qty
        else:
            raise NotImplementedError("no total or unit in line %r" % line)
        discount_perc = (
            parse_decimal(line["discount"]) if "discount" in line else default_discount
        )
        if discount_perc > 0:
            discount_mul = 1 - discount_perc
            line_price *= discount_mul
        line_price *= currency_multiplier
        if line_price == 0:
            raise NotImplementedError("price of line %r equals 0" % line)
        total_price += line_price
        name = line["name"]
        tags = Counter(line["tags"])
        total_tags = sum(tags.values())
        for tag, count in tags.items():
            share = Fraction(count, total_tags)
            split_price = round(Decimal(float(share)) * line_price, rounding)
            tag_unit_shares[tag] += share * qty
            tag_price_shares[tag] += split_price
            by_tag[tag].append(
                {
                    "line": line,
                    "name": name,
                    "share": share,
                    "total_qty": qty,
                    "split_qty": (share * qty),
                    "total_price": line_price,
                    "split_price": split_price,
                }
            )

    if delivery != 0:
        if use_price_shares_for_delivery:
            # When using price shares, simplify the decimal prices up to fractions
            delivery_share_map = {
                tag: Fraction(int(cnt)) for (tag, cnt) in tag_price_shares.items()
            }
        else:
            delivery_share_map = tag_unit_shares

        share_total = sum(delivery_share_map.values())
        delivery *= currency_multiplier
        total_price += delivery
        for tag, share in delivery_share_map.items():
            share /= share_total
            by_tag[tag].append(
                {
                    "line": None,
                    "name": "* Delivery",
                    "share": share,
                    "total_qty": 1,
                    "split_qty": share,
                    "total_price": delivery,
                    "split_price": round(delivery * Decimal(float(share)), rounding),
                }
            )

    return {
        "by_tag": by_tag,
        "total_price": total_price,
        "total_split_price": sum(i["split_price"] for i in chain(*by_tag.values())),
    }


def print_itemization(processed):
    for tag, tag_items in sorted(processed["by_tag"].items()):
        total_price = sum(item["split_price"] for item in tag_items)
        total_qty = sum(item["split_qty"] for item in tag_items)
        header_line = "%s: %s items, total split price %.2f" % (
            tag,
            round(fraction_as_decimal(total_qty), 3),
            total_price,
        )
        print(header_line)
        print("=" * len(header_line))
        name_len = max(len(item["name"]) for item in tag_items)
        for item in sorted(tag_items, key=itemgetter("name")):
            print(
                "%-*s | %6s | %6s"
                % (
                    name_len,
                    item["name"],
                    item["split_qty"],
                    item["split_price"],
                )
            )
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-r", "--rounding", default=2, type=int)
    ap.add_argument("-c", "--currency-multiplier", default=1, type=parse_decimal)
    ap.add_argument(
        "-d",
        "--delivery",
        default=0,
        type=parse_decimal,
        help="add total delivery (in foreign currency), weighted by line total",
    )
    ap.add_argument(
        "--default-discount",
        default=0,
        type=parse_decimal,
        help="set default discount for lines that set none",
    )
    ap.add_argument(
        "--use-price-shares-for-delivery",
        default=False,
        action="store_true",
    )

    args = ap.parse_args()
    with open(args.input) as infp:
        data = list(read_tsv(infp))
    processed = process(
        data,
        rounding=args.rounding,
        currency_multiplier=args.currency_multiplier,
        delivery=args.delivery,
        default_discount=args.default_discount,
        use_price_shares_for_delivery=args.use_price_shares_for_delivery,
    )
    print_itemization(processed)
    print("[>] Total price: %s" % processed["total_split_price"])
    rounding_remainder = processed["total_price"] - processed["total_split_price"]
    if rounding_remainder:
        print("[*] Rounding remainder: %s" % rounding_remainder)


if __name__ == "__main__":
    main()
